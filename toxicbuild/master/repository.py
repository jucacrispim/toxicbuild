# -*- coding: utf-8 -*-

# Copyright 2015-2020, 2023 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

from asyncio import ensure_future
import re
from bson.objectid import ObjectId
from mongoengine import PULL
from mongomotor import Document, EmbeddedDocument
from mongomotor.fields import (
    StringField,
    IntField, ReferenceField,
    DateTimeField,
    ListField,
    BooleanField,
    EmbeddedDocumentField,
    DictField,
    DynamicField
)
from toxicbuild.common.exchanges import (
    notifications,
    ui_notifications,
    scheduler_action,
)
from toxicbuild.core import utils, build_config
from toxicbuild.core.utils import string2datetime
from toxicbuild.master.build import (BuildSet, Builder, BuildManager)
from toxicbuild.master.client import get_poller_client
from toxicbuild.master.document import OwnedDocument, ExternalRevisionIinfo
from toxicbuild.master.exceptions import RepoBranchDoesNotExist
from toxicbuild.master.utils import (get_build_config_type,
                                     get_build_config_filename)
from toxicbuild.master.signals import buildset_added
from toxicbuild.master.slave import Slave

# The thing here is: When a repository poller is scheduled, I need to
# keep track of the hashes so I can remove it from the scheduler
# when needed.
# {repourl-update-code: hash}
_update_code_hashes = {}
# The is {repourl-start-pending: hash} for starting pending builds
_scheduler_hashes = {}


class RepositoryBranch(EmbeddedDocument):
    """The configuration for a branch of a repository."""

    name = StringField(required=True)
    """The name of the branch."""

    notify_only_latest = BooleanField(default=False)
    """If True, only the latest revision will be notified and only
    the last revision will generate a buildset."""

    def to_dict(self):
        """Returns a dict representation of the obj."""

        return {'name': self.name,
                'notify_only_latest': self.notify_only_latest}


class LatestBuildSet(EmbeddedDocument):
    """The most recent buildset in the repository."""

    status = StringField()
    """The buildset status"""

    commit = StringField()
    """The commit sha"""

    title = StringField()
    """The commit title"""

    started = DateTimeField()
    """When the buildset started"""

    total_time = IntField()
    """Total time in seconds spent by the buildset"""

    commit_date = DateTimeField()
    """Date of the commit"""


class Repository(OwnedDocument, utils.LoggerMixin):
    """Repository is where you store your code and where toxicbuild
    looks for incomming changes."""

    url = StringField(required=True, unique=True)
    """The url of the repository."""

    fetch_url = StringField()
    """A url used to actually fetch the code. If using some
    kind of authentication based in a url, this may change often."""

    update_seconds = IntField(default=300, required=True)
    """If the repository added manually (not imported), indicates the inteval
    for polling for new revisions."""

    vcs_type = StringField(required=True, default='git')
    """The type of vcs used in this repo."""

    branches = ListField(EmbeddedDocumentField(RepositoryBranch))
    """A list of :class:`~toxicbuild.master.repository.RepositoryBranch`.
    These branches are the ones that trigger builds. If no branches,
    all branches will trigger builds."""

    slaves = ListField(ReferenceField(Slave, reverse_delete_rule=PULL))
    """A list of :class:`~toxicbuild.master.slave.Slave`. The slaves here
    are the slaves allowed to run builds for this repo."""

    clone_status = StringField(choices=('cloning', 'ready', 'clone-exception'),
                               default='cloning')
    """The status of the clone."""

    schedule_poller = BooleanField(default=True)
    """Indicates if we should schedule periodical polls for changes in code. If
    the repo was imported from an external service that sends webhooks
    (or something else) this should be False."""

    parallel_builds = IntField()
    """Max number of builds in parallel that this repo exeutes
    If None, there's no limit for parallel builds.
    """

    enabled = BooleanField(default=True)
    """Indicates if this repository is enabled to run builds."""

    external_id = DynamicField()
    """The repository id in an external service."""

    external_full_name = StringField()
    """The full name of the repository in an external service"""

    envvars = DictField()
    """Environment variables that are used in every build in this
    repository. It is a dictionary {'VAR': 'VAL', ...}
    """

    latest_buildset = EmbeddedDocumentField(LatestBuildSet)
    """The most recent buildset for a repository."""

    meta = {
        'ordering': ['name'],
    }

    _running_builds = 0
    _stop_consuming_messages = False

    def __init__(self, *args, **kwargs):
        from toxicbuild.master import scheduler

        super(Repository, self).__init__(*args, **kwargs)
        self.scheduler = scheduler
        self.build_manager = BuildManager(self)
        self.config_type = get_build_config_type()
        self.config_filename = get_build_config_filename()

        self._old_status = None
        self._vcs_instance = None

    @classmethod
    def add_running_build(cls):
        """Add a running build to the count of running builds among all
        repositories."""
        cls._running_builds += 1

    @classmethod
    def remove_running_build(cls):
        """Removes a running build from the count of running builds among all
        repositories."""

        cls._running_builds -= 1

    @classmethod
    def get_running_builds(cls):
        """Returns the number of running builds among all the repos."""
        return cls._running_builds

    @classmethod
    async def create(cls, **kwargs):
        """Creates a new repository and schedule it if needed.

        :param kwargs: kwargs used to create the repository."""

        slaves = kwargs.pop('slaves', [])
        branches = kwargs.pop('branches', [])

        repo = cls(**kwargs, slaves=slaves, branches=branches)
        await repo.save()
        await cls._notify_repo_creation(repo)
        if repo.schedule_poller:
            repo.schedule()
        return repo

    def get_url(self):
        return self.fetch_url or self.url

    @classmethod
    async def get(cls, **kwargs):
        """Returns a repository instance and create locks if needed

        :param kwargs: kwargs to match the repository."""

        repo = await cls.objects.get(**kwargs)
        return repo

    @classmethod
    async def get_for_user(cls, user, **kwargs):
        """Returns a repository if ``user`` has permission for it.
        If not raises an error.

        :param user: User who is requesting the repository.
        :param kwargs: kwargs to match the repository.
        """
        repo = await super().get_for_user(user, **kwargs)
        return repo

    async def save(self, *args, **kwargs):
        set_full_name = (hasattr(self, '_changed_fields') and
                         ('name' in self._changed_fields or
                          'owner' in self._changed_fields))
        if set_full_name or not self.full_name:
            owner = await self.owner
            self.full_name = '{}/{}'.format(owner.name, self.name)
        r = await super().save(*args, **kwargs)
        return r

    async def to_dict(self, short=False):
        """Returns a dict representation of the object.

        :param short: Indicates if the returned dict has only basic information
        """
        my_dict = {'id': str(self.id), 'name': self.name, 'url': self.url,
                   'full_name': self.full_name,
                   'vcs_type': self.vcs_type,
                   'enabled': self.enabled,
                   'clone_status': self.clone_status}
        if not short:
            slaves = await self.slaves
            my_dict.update(
                {'external_full_name': self.external_full_name,
                 'update_seconds': self.update_seconds,
                 'fetch_url': self.fetch_url,
                 'branches': [b.to_dict() for b in self.branches],
                 'slaves': [s.to_dict(id_as_str=True) for s in slaves],
                 'parallel_builds': self.parallel_builds,
                 'envvars': self.envvars}
            )

        return my_dict

    async def get_status(self):
        """Returns the status for the repository. The status is the
        status of the last buildset created for this repository that is
        not pending."""

        last_buildset = await self.get_lastest_buildset()

        clone_statuses = ['cloning', 'clone-exception']
        if not last_buildset and self.clone_status in clone_statuses:
            status = self.clone_status
        elif not last_buildset:
            status = 'ready'
        else:
            status = last_buildset.status

        return status

    async def bootstrap(self):
        """Initialise the needed stuff. Schedules updates for code,
         start of pending builds, connect to signals.
        """

        self.schedule()

    @classmethod
    async def bootstrap_all(cls):
        async for repo in cls.objects.all():
            await repo.bootstrap()

    def schedule(self):
        """Schedules all needed actions for a repository. The actions are:

        * Sends an ``add-udpate-code`` to the scheduler server.
        * Starts builds that are pending using
          ``self.build_manager.start_pending``.
        """

        self.log('Scheduling {url}'.format(url=self.url))

        if self.schedule_poller:
            # add update_code
            update_code_hash = self.scheduler.add(self.update_code,
                                                  self.update_seconds)
            _update_code_hashes['{}-update-code'.format(
                self.url)] = update_code_hash

        # adding start_pending
        start_pending_hash = self.scheduler.add(
            self.build_manager.start_pending, 120)

        _scheduler_hashes['{}-start-pending'.format(
            self.url)] = start_pending_hash

    @classmethod
    async def schedule_all(cls):
        """ Schedule all repositories. """

        repos = await cls.objects.all().to_list()
        for repo in repos:
            repo.schedule()

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

        sched_msg = {'type': 'rm-update-code', 'repository_id': str(self.id)}
        await scheduler_action.publish(sched_msg)
        try:
            update_hash = _update_code_hashes['{}-update-code'.format(
                self.url)]
            self.scheduler.remove_by_hash(update_hash)
            del _update_code_hashes['{}-update-code'.format(
                self.url)]

            pending_hash = _scheduler_hashes['{}-start-pending'.format(
                self.url)]
            self.scheduler.remove_by_hash(pending_hash)
            del _scheduler_hashes['{}-start-pending'.format(self.url)]
        except KeyError:  # pragma no cover
            # means the repository was not scheduled
            pass

        await self.delete()

    async def request_removal(self):
        """Request the removal of a repository by publishing a message in the
        ``notifications`` queue with the routing key
        `repo-removal-requested`."""

        msg = {'repository_id': str(self.id)}
        await notifications.publish(
            msg, routing_key='repo-removal-requested')

    async def request_code_update(self, repo_branches=None, external=None):
        """Request the code update of a repository by publishing a message in
        the ``notifications`` queue with the routing key
        `repo-update-code-requested`.

        :param repo_branches: A dictionary with information about the branches
          to be updated. If no ``repo_branches`` all branches in the repo
          config will be updated.

          The dictionary has the following format.

          .. code-block:: python

             {'branch-name': {'notify_only_latest': True}}

        :param external: If we should update code from an external
          (not the origin) repository, `external` is the information about
          this remote repo.
        """

        msg = {'repository_id': str(self.id),
               'repo_branches': repo_branches,
               'external': external}
        await notifications.publish(
            msg, routing_key='update-code-requested')

    async def update_code(self, repo_branches=None, external=None):
        """Requests a code update to a poller and adds builds to the
        new revisions returned.

        :param repo_branches: A dictionary with information about the branches
          to be updated. If no ``repo_branches`` all branches in the repo
          config will be updated.

          The dictionary has the following format.

          .. code-block:: python

             {'branch-name': notify_only_latest}

        :param external: If we should update code from an external
          (not the origin) repository, `external` is the information about
          this remote repo.
        """

        async with get_poller_client(self) as client:
            ret = await client.poll_repo(branches_conf=repo_branches,
                                         external=external)

        if ret['revisions']:
            revs = []
            for rinfo in ret['revisions']:
                rev = RepositoryRevision(repository=self, **rinfo)
                rev.commit_date = string2datetime(rinfo['commit_date'])
                rev.config_type = self.config_type
                revs.append(rev)

            revs = await RepositoryRevision.objects.insert(revs)
            await self.build_manager.add_builds(revs)

        if ret['with_clone']:
            self.clone_status = ret['clone_status']
            await self.save()
            status_msg = {'repository_id': str(self.id),
                          'old_status': 'cloning',
                          'new_status': self.clone_status}
            await self._notify_status_changed(status_msg)

    async def add_slave(self, slave):
        """Adds a new slave to a repository.

        :param slave: A slave instance."""
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

    async def get_lastest_buildset(self):
        return self.latest_buildset

    async def set_latest_buildset(self, buildset):
        lb = LatestBuildSet(status=buildset.status, commit=buildset.commit,
                            title=buildset.title, started=buildset.started,
                            total_time=buildset.total_time,
                            commit_date=buildset.commit_date)
        self.latest_buildset = lb
        await self.save()

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

    async def add_revision(self, branch, commit, commit_date, author, title,
                           body=None, external=None, builders_fallback=''):
        """ Adds a revision to the repository.

        :param commit: Commit's sha
        :param branch: branch name
        :param commit_date: commit's date (on authors time)
        :param author: The author of the commit
        :param title: The commit title.
        :param body: The commit body.
        :param external: Information about an external remote if the revision
          came from an external.
        :param builders_fallback: If not None, builders from this branch will
          be used in case of the revision branch has no builders configured
          for it
        """

        kw = dict(repository=self, commit=commit,
                  branch=branch, commit_date=commit_date,
                  author=author, title=title, body=body)
        if external:
            external_rev = ExternalRevisionIinfo(**external)
            kw['external'] = external_rev

        revision = RepositoryRevision(**kw)
        await revision.save()
        return revision

    async def add_builds_for_buildset(self, buildset, conf, builders=None,
                                      builders_origin=None):
        """Adds a buildset to the build queue of a given slave
        for this repository.

        :param buildset: An instance of
          :class:`toxicbuild.master.build.BuildSet`.
        :param conf: The build configuration for the buidset.
        :param builders: The builders to use in the buids. If no builds,
          all builders for the revision will be used.
        :param builders_origin: Indicates from which branch config the builds
          came. Useful for merge requests to test agains the tests on the main
          branch.
        """
        builders = builders or []
        await self.build_manager.add_builds_for_buildset(
            buildset, conf, builders=builders,
            builders_origin=builders_origin)

    def _get_builder_kw(self, name_or_id):
        kw = {'repository': self}
        if ObjectId.is_valid(name_or_id):
            kw['id'] = name_or_id
        else:
            kw['name'] = name_or_id

        return kw

    async def start_build(self, branch, builder_name_or_id=None,
                          named_tree=None, builders_origin=None):
        """ Starts a (some) build(s) in the repository. """

        if not named_tree:
            rev = await self.get_latest_revision_for_branch(branch)
            named_tree = rev.commit
        else:
            rev = await RepositoryRevision.objects(branch=branch,
                                                   commit=named_tree).first()

        buildset = await BuildSet.create(repository=self, revision=rev)
        if not rev.config:
            self.log('No config found', level='debug')
            buildset.status = type(buildset).NO_CONFIG
            await buildset.save()
            buildset_added.send(str(self.id), buildset=buildset)
            return

        conf = self.get_config_for(rev)

        if not builder_name_or_id:
            builders, builders_origin = await self._get_builders(rev, conf)
        else:
            builders_origin = None
            kw = self._get_builder_kw(builder_name_or_id)
            builders = [(await Builder.get(**kw))]
        await self.add_builds_for_buildset(buildset, conf,
                                           builders=builders,
                                           builders_origin=builders_origin)

    async def request_build(self, branch, builder_name=None, named_tree=None,
                            slaves=None):
        """Publishes a message in the `notifications` exchange requesting
        a build. Uses the routing_key `build-requested`"""
        slaves = slaves or []
        msg = {'repository_id': str(self.id),
               'branch': branch, 'builder_name': builder_name,
               'named_tree': named_tree,
               'slaves_ids': [str(s.id) for s in slaves]}

        await notifications.publish(msg, routing_key='build-requested')

    async def cancel_build(self, build_uuid):
        """Cancels a build.

        :param build_uuid: The uuid of the build."""

        await self.build_manager.cancel_build(build_uuid)

    async def enable(self):
        self.enabled = True
        await self.save()

    async def disable(self):
        self.enabled = False
        await self.save()

    def get_branch(self, branch_name):
        """Returns an instance of
        :class:`~toxicbuild.master.repository.RepositoryBranch`"""

        for branch in self.branches:
            if branch.name == branch_name:
                return branch

        raise RepoBranchDoesNotExist(branch_name)

    def notify_only_latest(self, branch_name):
        """Indicates if a branch notifies only the latest revision.

        :param branch_name: The name of the branch."""
        try:
            branch = self.get_branch(branch_name)
            only_latest = branch.notify_only_latest
        except RepoBranchDoesNotExist:
            only_latest = True

        return only_latest

    def get_config_for(self, revision):
        """Returns the build configuration for a given revision.

        :param revision: A
          :class`~toxicbuild.master.repository.RepositoryRevision` instance.
        """

        conf = build_config.load_config(
            self.config_type, revision.config)
        return conf

    async def add_envvars(self, **envvars):
        """Adds new environment variables to this repository.

        :param envvars: A dictionary {var: val, ...}.
        """

        self.envvars.update(envvars)
        await self.save()

    async def rm_envvars(self, **envvars):
        """Removes environment variables from this repository.

        :param envvars: A dictionary {var: val, ...}.
        """

        for k in envvars:
            try:
                self.envvars.pop(k)
            except KeyError:
                pass
        await self.save()

    async def replace_envvars(self, **envvars):
        """Replaces the current environment variables of the repository.

        :param envvars: The environment variables that will replace the
          current one.
        """

        self.envvars = envvars
        await self.save()

    async def _get_builders(self, revision, conf):
        builders, origin = await self.build_manager.get_builders(
            revision, conf)

        return builders, origin

    @classmethod
    async def _notify_repo_creation(cls, repo):
        repo_added_msg = await repo.to_dict()
        await ui_notifications.publish(repo_added_msg)
        repo_added_msg['msg_type'] = 'repo_added'
        async for user in await repo.get_allowed_users():  # pragma no branch
            ensure_future(ui_notifications.publish(
                repo_added_msg, routing_key=str(user.id)))

    async def _notify_status_changed(self, status_msg):
        self.log('Notify status changed {}'.format(status_msg),
                 level='debug')
        await ui_notifications.publish(status_msg,
                                       routing_key=str(self.id))
        status_msg['msg_type'] = 'repo_status_changed'
        async for user in await self.get_allowed_users():  # pragma no branch
            ensure_future(ui_notifications.publish(
                status_msg, routing_key=str(user.id)))


class RepositoryRevision(Document):
    """A commit in the code tree."""

    repository = ReferenceField(Repository, required=True)
    """A referece to :class:`~toxicbuild.master.repository.Repository`."""

    commit = StringField(required=True)
    """The identifier of the revision, a sha, a tag name, etc..."""

    branch = StringField(required=True)
    """The name of the revison branch."""

    author = StringField(required=True)
    """The author of the commit."""

    title = StringField(required=True)
    """The title of the commit."""

    body = StringField()
    """The commit body."""

    commit_date = DateTimeField(required=True)
    """Commit's date."""

    external = EmbeddedDocumentField(ExternalRevisionIinfo)
    """A list of :class:`~toxicbuild.master.bulid.RepositoryRevisionExternal`.
    """

    builders_fallback = StringField()
    """A name of a branch. If not None, builders from this branch will be used
    if there are no builders for the branch of the revision."""

    config = StringField()
    """The build configuration for this revision"""

    config_type = StringField()
    """The type of congif used"""

    @classmethod
    async def get(cls, **kwargs):
        """Returs a RepositoryRevision object."""

        ret = await cls.objects.get(**kwargs)
        return ret

    async def to_dict(self):
        """Returns a dict representation of the object."""
        repo = await self.repository
        rev_dict = {'repository_id': str(repo.id),
                    'commit': self.commit,
                    'branch': self.branch,
                    'author': self.author,
                    'title': self.title,
                    'commit_date': utils.datetime2string(self.commit_date)}
        if self.external:
            rev_dict.update({'external': self.external.to_dict()})
        return rev_dict

    def create_builds(self):
        r"""Checks for instructions in the commit body to know if a
        revision should create builds.

        Known instructions:

        - ``ci: skip`` - If in the commit body there's this instruction,
           no builds will be created for this revision. The regex for
           match this instruction is ``(^|.*\s+)ci:\s*skip(\s+|$)``
        """
        if not self.body:
            # No body, no instructions, we create builds normally
            return True

        return not self._check_skip()

    def _get_match(self, pattern):
        if not self.body:
            return None

        for l in self.body.splitlines():
            m = re.match(pattern, l)
            if m:
                return m

    def _check_skip(self):
        skip_pattern = re.compile(r'(^|.*\s+)ci:\s*skip(\s+|$)')
        return bool(self._get_match(skip_pattern))

    def _get_builders_match(self, pattern):
        builders_match = self._get_match(pattern)
        if builders_match:
            builders = builders_match.groups()[1].split(',')
            builders = [b.strip() for b in builders]
        else:
            builders = []

        return builders

    def get_builders_conf(self):
        """Returns the builder configuration - includes and excludes -
        for a given revison in its commit body.

        Known instructions:

        - ``ci: include-builders builder-name,other-builder``: Include only
          the builders listed in the configuration. The names are separated
          by comma.

        - ``ci: exclude-builders builder-name,other-builder``: Exclude
          the builders listed in the configuration. The names are separated
          by comma.
        """

        confs = {}
        include_pattern = re.compile(
            r'(^|.*\s+)ci:\s*include-builders\s+(.*)$')

        exclude_pattern = re.compile(
            r'(^|.*\s+)ci:\s*exclude-builders\s+(.*)$')

        confs['include'] = self._get_builders_match(include_pattern)
        confs['exclude'] = self._get_builders_match(exclude_pattern)

        return confs
