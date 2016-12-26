# -*- coding: utf-8 -*-

# Copyright 2015 2016 Juca Crispim <juca@poraodojuca.net>

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

import asyncio
try:
    from asyncio import ensure_future
except ImportError:  # pragma no cover
    from asyncio import async as ensure_future

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
                                       repo_status_changed)
from toxicbuild.master.slave import Slave


# The thing here is: When a repository poller is scheduled, I need to
# keep track of the hashes so I can remove it from the scheduler
# when needed.
# The format is {repourl: hash} for update_code
# and {repourl-start-pending: hash} for starting pending builds
_scheduler_hashes = {}


class RepositoryBranch(EmbeddedDocument):
    name = StringField(required=True)
    notify_only_latest = BooleanField(default=False)

    def to_dict(self):
        return {'name': self.name,
                'notify_only_latest': self.notify_only_latest}


class Repository(Document, utils.LoggerMixin):
    name = StringField(required=True, unique=True)
    url = StringField(required=True, unique=True)
    update_seconds = IntField(default=300, required=True)
    vcs_type = StringField(required=True, default='git')
    branches = ListField(EmbeddedDocumentField(RepositoryBranch))
    slaves = ListField(ReferenceField(Slave, reverse_delete_rule=PULL))
    clone_status = StringField(choices=('cloning', 'ready', 'clone-exception'),
                               default='cloning')
    plugins = ListField(EmbeddedDocumentField(MasterPlugin))

    meta = {
        'ordering': ['name']
    }

    def __init__(self, *args, **kwargs):
        from toxicbuild.master import scheduler

        super(Repository, self).__init__(*args, **kwargs)
        self.scheduler = scheduler
        self._poller_instance = None
        self.build_manager = BuildManager(self)
        self._old_status = None

    @asyncio.coroutine
    def to_dict(self, id_as_str=False):
        my_dict = {'id': self.id, 'name': self.name, 'url': self.url,
                   'update_seconds': self.update_seconds,
                   'vcs_type': self.vcs_type,
                   'branches': [b.to_dict() for b in self.branches],
                   'slaves': [s.to_dict(id_as_str)
                              for s in (yield from self.slaves)],
                   'plugins': [p.to_dict() for p in self.plugins],
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

    @asyncio.coroutine
    def get_status(self):
        """Returns the status for the repository. The status is the
        status of the last buildset created for this repository that is
        not pending."""

        last_buildset = yield from BuildSet.objects(
            repository=self).order_by(
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
                last_buildset = yield from last_buildset.first()

                if not last_buildset:
                    status = 'ready'
                    break

                status = last_buildset.get_status()
                i += 1
        return status

    @classmethod
    @asyncio.coroutine
    def create(cls, name, url, update_seconds, vcs_type, slaves=None,
               branches=None):
        """ Creates a new repository and schedule it. """

        slaves = slaves or []
        branches = branches or []

        repo = cls(url=url, update_seconds=update_seconds, vcs_type=vcs_type,
                   slaves=slaves, name=name, branches=branches)
        yield from repo.save()
        repo.schedule()
        return repo

    @asyncio.coroutine
    def remove(self):
        """ Removes all builds and builders and revisions related to the
        repository, removes the poller from the scheduler, removes the
        source code from the file system and then removes the repository.
        """

        builds = BuildSet.objects.filter(repository=self)
        yield from builds.delete()

        builders = Builder.objects.filter(repository=self)
        yield from builders.delete()

        revisions = RepositoryRevision.objects.filter(repository=self)
        yield from revisions.delete()

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

        Thread(target=shutil.rmtree, args=[self.workdir]).start()

        yield from self.delete()

    @classmethod
    @asyncio.coroutine
    def get(cls, **kwargs):
        repo = yield from cls.objects.get(**kwargs)
        return repo

    @asyncio.coroutine
    def update_code(self):
        """Updates the repository's code. It is just a wrapper for
        self.poller.poll, so I can handle exceptions here."""

        # reloading so we detect changes in config
        yield from self.reload()

        with_clone = False
        try:
            with_clone = yield from self.poller.poll()
            clone_status = 'ready'
        except CloneException:
            with_clone = True
            clone_status = 'clone-exception'

        self.clone_status = clone_status
        yield from self.save()

        if with_clone:
            repo_status_changed.send(self, old_status='cloning',
                                     new_status=self.clone_status)

    def schedule(self):
        """Schedules all needed actions for a repository. The actions are:

        * Update source code using ``self.update_code``
        * Starts builds that are pending using
          ``self.build_manager.start_pending``.
        * Connects to ``build_started`` and ``build_finished`` signals
          to handle changing of status."""

        self.log('Scheduling {url}'.format(url=self.url))
        # we store this hashes so we can remove it from the scheduler when
        # we remove the repository.

        # adding update_code
        sched_hash = self.scheduler.add(self.update_code, self.update_seconds)
        _scheduler_hashes[self.url] = sched_hash

        # adding start_pending
        start_pending_hash = self.scheduler.add(
            self.build_manager.start_pending, 120)
        _scheduler_hashes['{}-start-pending'.format(
            self.url)] = start_pending_hash

        # connecting to build signals
        build_started.connect(self._check_for_status_change)
        build_finished.connect(self._check_for_status_change)

    @classmethod
    @asyncio.coroutine
    def schedule_all(cls):
        """ Schedule all repositories. """

        repos = yield from cls.objects.all().to_list()
        for repo in repos:
            repo.schedule()

    @asyncio.coroutine
    def add_slave(self, slave):
        self.slaves
        slaves = yield from self.slaves
        slaves.append(slave)
        self.slaves = slaves
        yield from self.save()
        return slave

    @asyncio.coroutine
    def remove_slave(self, slave):
        slaves = yield from self.slaves
        slaves.pop(slaves.index(slave))
        yield from self.update(set__slaves=slaves)
        return slave

    @asyncio.coroutine
    def add_or_update_branch(self, branch_name, notify_only_latest=False):
        """Adds a new branch to this repository. If the branch
        already exists updates it with a new value."""

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

        yield from self.save()

    @asyncio.coroutine
    def remove_branch(self, branch_name):
        """Removes a branch from this repository."""

        yield from self.update(pull__branches__name=branch_name)

    @asyncio.coroutine
    def get_latest_revision_for_branch(self, branch):
        """ Returns the latest revision for a given branch
        :param branch: branch name
        """
        latest = RepositoryRevision.objects.filter(
            repository=self, branch=branch).order_by('-commit_date')

        latest = yield from latest.first()

        return latest

    @asyncio.coroutine
    def get_latest_revisions(self):
        """ Returns the latest revision for all known branches
        """
        branches = yield from self.get_known_branches()
        revs = {}
        for branch in branches:
            rev = yield from self.get_latest_revision_for_branch(branch)
            revs[branch] = rev

        return revs

    @asyncio.coroutine
    def get_known_branches(self):
        """ Returns the names for the branches that already have some
        revision here.
        """
        branches = yield from RepositoryRevision.objects.filter(
            repository=self).distinct('branch')

        return branches

    @asyncio.coroutine
    def add_revision(self, branch, commit, commit_date, author, title):
        """ Adds a revision to the repository.
        :param commit: commit uuid
        :param branch: branch name
        :param commit_date: commit's date (on authors time)
        """
        revision = RepositoryRevision(repository=self, commit=commit,
                                      branch=branch, commit_date=commit_date,
                                      author=author, title=title)
        yield from revision.save()
        return revision

    @asyncio.coroutine
    def enable_plugin(self, plugin_name, **plugin_config):
        """Enables a plugin to this repository.

        :param plugin_name: The name of the plugin that is being enabled.
        :param plugin_config: A dictionary containing the configuration
          passed to the plugin."""

        plugin_cls = MasterPlugin.get_plugin(name=plugin_name)
        plugin = plugin_cls(**plugin_config)
        self.plugins.append(plugin)
        yield from self.save()
        ensure_future(plugin.run())

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

    @asyncio.coroutine
    def disable_plugin(self, **kwargs):
        """Disables a plugin to the repository.

        :param kwargs: kwargs to match the plugin."""
        matched = [p for p in self.plugins if self._match_kw(p, **kwargs)]
        for p in matched:
            self.plugins.remove(p)
        yield from self.save()

    @asyncio.coroutine
    def add_builds_for_slave(self, buildset, slave, builders=[]):
        """Adds a buildset to the build queue of a given slave
        for this repository.

        :param buildset: An instance of
          :class:`toxicbuild.master.build.BuildSet`.
        :param slave: An instance of :class:`toxicbuild.master.build.Slave`.
        """
        yield from self.build_manager.add_builds_for_slave(
            buildset, slave, builders=builders)

    @asyncio.coroutine
    def _check_for_status_change(self, sender, build):
        """Called when a build is started or finished. If this event
        makes the repository change its status triggers a
        ``repo_status_changed`` signal.

        :param build: The build that was started or finished"""

        status = yield from self.get_status()
        if status != self._old_status:
            repo_status_changed.send(self, old_status=self._old_status,
                                     new_status=status)
            self._old_status = status


class RepositoryRevision(Document):
    repository = ReferenceField(Repository, required=True)
    commit = StringField(required=True)
    branch = StringField(required=True)
    author = StringField(required=True)
    title = StringField(required=True)
    commit_date = DateTimeField(required=True)

    @classmethod
    @asyncio.coroutine
    def get(cls, **kwargs):
        ret = yield from cls.objects.get(**kwargs)
        return ret
