# -*- coding: utf-8 -*-

# Copyright 2015-2017 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

from asyncio import ensure_future
import functools
import os
import re
import shutil
from threading import Thread
from mongoengine import PULL
from mongomotor import Document, EmbeddedDocument
from mongomotor.fields import (StringField, IntField, ReferenceField,
                               DateTimeField, ListField, BooleanField,
                               EmbeddedDocumentField)
from toxicbuild.core import utils
from toxicbuild.master.build import BuildSet, Builder, BuildManager
from toxicbuild.master.exceptions import CloneException
from toxicbuild.master.plugins import MasterPlugin
from toxicbuild.master.pollers import Poller
from toxicbuild.master.signals import (build_started, build_finished,
                                       repo_status_changed, repo_added)
from toxicbuild.master.slave import Slave
from toxicbuild.master.utils import OwnedDocument


# The thing here is: When a repository poller is scheduled, I need to
# keep track of the hashes so I can remove it from the scheduler
# when needed.
# The format is {repourl: hash} for update_code
# and {repourl-start-pending: hash} for starting pending builds
_scheduler_hashes = {}


async def _update_code(repo_id):
    """Calls the update_code method of a repo. We must use this instead of
    use reload() in the update_code method because the reload() causes a
    massive memory leak."""

    repo = await Repository.get(id=repo_id)
    await repo.update_code()


class RepositoryBranch(EmbeddedDocument):
    name = StringField(required=True)
    notify_only_latest = BooleanField(default=False)

    def to_dict(self):
        return {'name': self.name,
                'notify_only_latest': self.notify_only_latest}


class Repository(OwnedDocument, utils.LoggerMixin):
    """Repository is where you store your code and where toxicbuild
    looks for incomming changes."""

    name = StringField(required=True, unique=True)
    url = StringField(required=True, unique=True)
    update_seconds = IntField(default=300, required=True)
    vcs_type = StringField(required=True, default='git')
    branches = ListField(EmbeddedDocumentField(RepositoryBranch))
    slaves = ListField(ReferenceField(Slave, reverse_delete_rule=PULL))
    clone_status = StringField(choices=('cloning', 'ready', 'clone-exception'),
                               default='cloning')
    plugins = ListField(EmbeddedDocumentField(MasterPlugin))
    # max number of builds in parallel that this repo exeutes
    # If None, there's no limit for parallel builds.
    parallel_builds = IntField()

    meta = {
        'ordering': ['name']
    }

    _plugins_instances = {}

    def __init__(self, *args, **kwargs):
        from toxicbuild.master import scheduler

        super(Repository, self).__init__(*args, **kwargs)
        self.scheduler = scheduler
        self._poller_instance = None
        self.build_manager = BuildManager(self)
        self._old_status = None

    async def to_dict(self, id_as_str=False):
        my_dict = {'id': self.id, 'name': self.name, 'url': self.url,
                   'update_seconds': self.update_seconds,
                   'vcs_type': self.vcs_type,
                   'branches': [b.to_dict() for b in self.branches],
                   'slaves': [s.to_dict(id_as_str)
                              for s in (await self.slaves)],
                   'plugins': [p.to_dict() for p in self.plugins],
                   'parallel_builds': self.parallel_builds,
                   'clone_status': self.clone_status}
        if id_as_str:
            my_dict['id'] = str(self.id)

        return my_dict

    @property
    def workdir(self):
        """ The directory where the source code of this repository is
        cloned into
        """

        workdir = re.sub(re.compile('http(s|)://'), '', self.url)
        workdir = workdir.replace('/', '-').replace('@', '-').replace(':', '')
        workdir = workdir.strip()
        return os.path.join('src', workdir)

    @property
    def poller(self):
        if self._poller_instance is None:
            vcs_type = self.vcs_type
            self._poller_instance = Poller(self, vcs_type, self.workdir)

        return self._poller_instance

    async def get_status(self):
        """Returns the status for the repository. The status is the
        status of the last buildset created for this repository that is
        not pending."""

        last_buildset = await BuildSet.objects(repository=self).order_by(
            '-created').first()

        clone_statuses = ['cloning', 'clone-exception']
        if not last_buildset and self.clone_status in clone_statuses:
            status = self.clone_status
        elif not last_buildset:
            status = 'ready'
        else:
            status = last_buildset.get_status()
            i = 1
            while status == BuildSet.PENDING:
                # we do not consider pending builds for the repo status
                start = i
                stop = start + 1
                last_buildset = BuildSet.objects(repository=self).order_by(
                    '-created')[start:stop]
                last_buildset = await last_buildset.first()

                if not last_buildset:
                    status = 'ready'
                    break

                status = last_buildset.get_status()
                i += 1
        return status

    @classmethod
    async def create(cls, name, url, owner, update_seconds, vcs_type,
                     slaves=None, branches=None, parallel_builds=None):
        """ Creates a new repository and schedule it.

        :param name: Repository name.
        :param url: Repository version control system url
        :param owner: :class:`~toxicbuild.master.users.User` or
          :class:`~toxicbuild.master.users.Organization` that owns the
          repository.
        :param update_seconds: How long we should wait until
          poll the changes again.
        :param vcs_type: Which type of version control system this
          repository uses.
        :param slaves: A list of slaves for this repository.
        :param branches: A list of branches config for this repository.
        :params parallel_builds: How many paralles builds this repository
          executes. If None, there is no limit."""

        slaves = slaves or []
        branches = branches or []

        repo = cls(url=url, update_seconds=update_seconds, vcs_type=vcs_type,
                   slaves=slaves, name=name, branches=branches,
                   parallel_builds=parallel_builds, owner=owner)
        await repo.save()
        repo_added.send(str(repo.id))
        repo.schedule()
        return repo

    async def remove(self):
        """ Removes all builds and builders and revisions related to the
        repository, removes the poller from the scheduler, removes the
        source code from the file system and then removes the repository.
        """

        builds = BuildSet.objects.filter(repository=self)
        await builds.delete()

        builders = Builder.objects.filter(repository=self)
        await builders.delete()

        revisions = RepositoryRevision.objects.filter(repository=self)
        await revisions.delete()

        try:
            sched_hash = _scheduler_hashes[self.url]
            self.scheduler.remove_by_hash(sched_hash)
            del _scheduler_hashes[self.url]

            pending_hash = _scheduler_hashes['{}-start-pending'.format(
                self.url)]
            self.scheduler.remove_by_hash(pending_hash)
            del _scheduler_hashes['{}-start-pending'.format(self.url)]
        except KeyError:  # pragma no cover
            # means the repository was not scheduled
            pass

        # removes the repository from the file system.
        Thread(target=shutil.rmtree, args=[self.workdir]).start()

        await self.delete()

    @classmethod
    async def get(cls, **kwargs):
        """Returns a repository instance

        :param kwargs: kwargs to match the repository."""
        repo = await cls.objects.get(**kwargs)
        return repo

    async def update_code(self):
        """Updates the repository's code. It is just a wrapper for
        self.poller.poll, so I can handle exceptions here."""

        with_clone = False
        try:
            with_clone = await self.poller.poll()
            clone_status = 'ready'
        except CloneException:
            with_clone = True
            clone_status = 'clone-exception'

        self.clone_status = clone_status
        await self.save()

        if with_clone:
            repo_status_changed.send(str(self.id), old_status='cloning',
                                     new_status=self.clone_status)

    def schedule(self):
        """Schedules all needed actions for a repository. The actions are:

        * Update source code using ``self.update_code``
        * Starts builds that are pending using
          ``self.build_manager.start_pending``.
        * Connects to ``build_started`` and ``build_finished`` signals
          to handle changing of status.
        * Runs the enabled plugins."""

        self.log('Scheduling {url}'.format(url=self.url))
        # we store this hashes so we can remove it from the scheduler when
        # we remove the repository.

        # adding update_code
        update_fn = functools.partial(_update_code, self.id)
        sched_hash = self.scheduler.add(update_fn, self.update_seconds)
        _scheduler_hashes[self.url] = sched_hash

        # adding start_pending
        start_pending_hash = self.scheduler.add(
            self.build_manager.start_pending, 120)
        _scheduler_hashes['{}-start-pending'.format(
            self.url)] = start_pending_hash

        # connecting to build signals
        build_started.connect(self._check_for_status_change)
        build_finished.connect(self._check_for_status_change)

        # starting plugins
        for plugin in self.plugins:
            self._run_plugin(plugin)

    @classmethod
    async def schedule_all(cls):
        """ Schedule all repositories. """

        repos = await cls.objects.all().to_list()
        for repo in repos:
            repo.schedule()

    async def add_slave(self, slave):
        """Adds a new slave to a repository.

        :param slave: A slave instance."""
        self.slaves
        slaves = await self.slaves
        slaves.append(slave)
        self.slaves = slaves
        await self.save()
        return slave

    async def remove_slave(self, slave):
        """Removes a slave from a repository.

        :param slave: A slave instance."""
        slaves = await self.slaves
        slaves.pop(slaves.index(slave))
        await self.update(set__slaves=slaves)
        return slave

    async def add_or_update_branch(self, branch_name,
                                   notify_only_latest=False):
        """Adds a new branch to this repository. If the branch
        already exists updates it with a new value.

        :param branch_name: The name of a branch
        :param notify_only_latest: If we should build only the most
          recent build of this branch"""

        # this is a shitty way of doing this. What is the
        # better way?
        def get_branch(branch_name):
            for b in self.branches:
                if b.name == branch_name:
                    return b

        branch = get_branch(branch_name)
        if branch:
            branch.notify_only_latest = notify_only_latest
        else:
            branch = RepositoryBranch(name=branch_name,
                                      notify_only_latest=notify_only_latest)
            self.branches.append(branch)

        await self.save()

    async def remove_branch(self, branch_name):
        """Removes a branch from this repository.

        :param branch_name: The branch name."""

        await self.update(pull__branches__name=branch_name)

    async def get_latest_revision_for_branch(self, branch):
        """ Returns the latest revision for a given branch

        :param branch: branch name
        """
        latest = RepositoryRevision.objects.filter(
            repository=self, branch=branch).order_by('-commit_date')

        latest = await latest.first()

        return latest

    async def get_latest_revisions(self):
        """ Returns the latest revision for all known branches
        """
        branches = await self.get_known_branches()
        revs = {}
        for branch in branches:
            rev = await self.get_latest_revision_for_branch(branch)
            revs[branch] = rev

        return revs

    async def get_known_branches(self):
        """ Returns the names for the branches that already have some
        revision here.
        """
        branches = await RepositoryRevision.objects.filter(
            repository=self).distinct('branch')

        return branches

    async def add_revision(self, branch, commit, commit_date, author, title):
        """ Adds a revision to the repository.

        :param commit: commit uuid
        :param branch: branch name
        :param commit_date: commit's date (on authors time)
        """
        revision = RepositoryRevision(repository=self, commit=commit,
                                      branch=branch, commit_date=commit_date,
                                      author=author, title=title)
        await revision.save()
        return revision

    def _run_plugin(self, plugin):
        key = '{}-plugin-{}'.format(self.url, plugin.name)
        type(self)._plugins_instances[key] = plugin
        ensure_future(plugin.run(self))

    def _stop_plugin(self, plugin):
        key = '{}-plugin-{}'.format(self.url, plugin.name)
        plugin = type(self)._plugins_instances[key]
        ensure_future(plugin.stop())
        del type(self)._plugins_instances[key]

    async def enable_plugin(self, plugin_name, **plugin_config):
        """Enables a plugin to this repository.

        :param plugin_name: The name of the plugin that is being enabled.
        :param plugin_config: A dictionary containing the plugin's
          configuration."""

        plugin_cls = MasterPlugin.get_plugin(name=plugin_name)
        plugin = plugin_cls(**plugin_config)
        self.plugins.append(plugin)
        await self.save()
        self._run_plugin(plugin)

    def _match_kw(self, plugin, **kwargs):
        """True if the plugin's attributes match the
        kwargs.

        :param plugin: A plugin instance.
        :param kwargs: kwargs to match the plugin"""

        for k, v in kwargs.items():
            try:
                attr = getattr(plugin, k)
            except AttributeError:
                return False
            else:
                if attr != v:
                    return False

        return True

    async def disable_plugin(self, **kwargs):
        """Disables a plugin to the repository.

        :param kwargs: kwargs to match the plugin."""
        matched = [p for p in self.plugins if self._match_kw(p, **kwargs)]
        for p in matched:
            self.plugins.remove(p)
            self._stop_plugin(p)
        await self.save()

    async def add_builds_for_slave(self, buildset, slave, builders=[]):
        """Adds a buildset to the build queue of a given slave
        for this repository.

        :param buildset: An instance of
          :class:`toxicbuild.master.build.BuildSet`.
        :param slave: An instance of :class:`toxicbuild.master.build.Slave`.
        """
        await self.build_manager.add_builds_for_slave(
            buildset, slave, builders=builders)

    async def _check_for_status_change(self, sender, build):
        """Called when a build is started or finished. If this event
        makes the repository change its status triggers a
        ``repo_status_changed`` signal.

        :param sender: The object that sent the signal
        :param build: The build that was started or finished"""

        status = await self.get_status()
        if status != self._old_status:
            repo_status_changed.send(str(self.id), old_status=self._old_status,
                                     new_status=status)
            self._old_status = status


class RepositoryRevision(Document):
    """A commit in the code tree."""

    repository = ReferenceField(Repository, required=True)
    commit = StringField(required=True)
    branch = StringField(required=True)
    author = StringField(required=True)
    title = StringField(required=True)
    commit_date = DateTimeField(required=True)

    @classmethod
    async def get(cls, **kwargs):
        ret = await cls.objects.get(**kwargs)
        return ret
