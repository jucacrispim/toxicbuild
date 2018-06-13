# -*- coding: utf-8 -*-

# Copyright 2015-2018 Juca Crispim <juca@poraodojuca.net>

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
from asyncio import ensure_future
from collections import defaultdict, deque
from datetime import timedelta
import json
from uuid import uuid4
from mongoengine.queryset import queryset_manager
from mongomotor import Document, EmbeddedDocument
from mongomotor.fields import (StringField, ListField, EmbeddedDocumentField,
                               ReferenceField, DateTimeField, UUIDField,
                               IntField)
from toxicbuild.core.utils import (log, get_toxicbuildconf, now,
                                   list_builders_from_config, datetime2string,
                                   format_timedelta, LoggerMixin,
                                   localtime2utc, set_tzinfo,
                                   get_toxicbuildconf_yaml)
from toxicbuild.master.document import ExternalRevisionIinfo
from toxicbuild.master.exceptions import (DBError, ImpossibleCancellation)
from toxicbuild.master.exchanges import build_notifications
from toxicbuild.master.signals import build_added, build_cancelled
from toxicbuild.master.utils import (get_build_config_type,
                                     get_build_config_filename)


# The statuses used in builds  ordered by priority.
ORDERED_STATUSES = ['running', 'cancelled', 'exception', 'fail',
                    'warning', 'success', 'pending']


class SerializeMixin:

    """Simple mixin to serialization relatad stuff."""

    def to_dict(self, id_as_str=False):
        """ Transforms a Document into a dictionary.

        :param id_as_str: If true, transforms the id field into a string.
        """

        objdict = json.loads(super().to_json())
        objdict['id'] = str(self.id) if id_as_str else self.id
        return objdict

    async def async_to_json(self):
        """Async version of to_json. Expects a to_dict coroutine."""

        objdict = await self.to_dict(id_as_str=True)
        return json.dumps(objdict)


class Builder(SerializeMixin, Document):

    """ The entity responsible for executing the build steps.
    """

    name = StringField(required=True)
    """The name of the builder."""

    repository = ReferenceField('toxicbuild.master.Repository')
    """A referece to the :class:`~toxicbuild.master.repository.Repository` that
    owns the builder"""

    @classmethod
    async def create(cls, **kwargs):
        """Creates a new Builder.

        :param kwargs: kwargs passed to the builder constructor"""
        builder = cls(**kwargs)
        await builder.save()
        return builder

    @classmethod
    async def get(cls, **kwargs):
        """Returns a builder instance."""
        builder = await cls.objects.get(**kwargs)
        return builder

    @classmethod
    async def get_or_create(cls, **kwargs):
        """Returns a builder instance. If it does not exist, creates it.

        :param kwargs: kwargs to match the builder."""
        try:
            builder = await cls.get(**kwargs)
        except cls.DoesNotExist:
            builder = await cls.create(**kwargs)

        return builder

    async def get_status(self):
        """Returns the builder status."""

        try:
            qs = BuildSet.objects(builds__builder=self).order_by('-created')
            last_buildset = await qs[0]
        except (IndexError, AttributeError):
            status = 'idle'
        else:
            statuses = []
            for build in last_buildset.builds:
                builder = await build.builder
                if builder == self:
                    statuses.append(build.status)

            ordered_statuses = sorted(statuses,
                                      key=lambda i: ORDERED_STATUSES.index(i))
            status = ordered_statuses[0]

        return status

    async def to_dict(self, id_as_str=False):
        """Returns a dictionary for this builder.

        :param id_as_str: If true, the object id will be converted to string"""

        objdict = super().to_dict(id_as_str=id_as_str)
        objdict['status'] = await self.get_status()
        return objdict

    async def to_json(self):
        """Returns a json for this builder."""
        return (await self.async_to_json())


class BuildStep(EmbeddedDocument):

    """ A step for a build. This is the object that will store
    the step data. Who actually execute the steps is the slave.
    """

    STATUSES = ['running', 'fail', 'success', 'exception',
                'warning']

    uuid = UUIDField(required=True, default=lambda: uuid4())
    """The uuid that indentifies the build step"""

    name = StringField(required=True)
    """The name of the step. Will be displayed in the ui."""

    command = StringField(required=True)
    """The command that executes the step"""

    status = StringField(choices=STATUSES)
    """The current status of the step. May be one of the values in STATUSES`"""

    output = StringField()
    """The output of the step"""

    started = DateTimeField(default=None)
    """When the step stated. It msut be in UTC."""

    finished = DateTimeField(default=None)
    """When the step finished. It msut be in UTC."""

    # the index of the step in the build.
    index = IntField(requred=True)
    """The index of the step in the build."""

    total_time = IntField()
    """The total time spen in the step."""

    def to_dict(self):
        """Returns a dict representation of the BuildStep."""

        objdict = json.loads(super().to_json())
        objdict['uuid'] = str(self.uuid)
        keys = objdict.keys()
        if 'started' not in keys:
            objdict['started'] = None
        else:
            objdict['started'] = datetime2string(self.started)

        if 'finished' not in keys:
            objdict['finished'] = None
        else:
            objdict['finished'] = datetime2string(self.finished)

        total = format_timedelta(timedelta(seconds=self.total_time)) \
            if self.total_time is not None else ''
        objdict['total_time'] = total

        return objdict

    def to_json(self):
        """Returns a json representation of the BuildStep."""

        return json.dumps(self.to_dict())


class Build(EmbeddedDocument):

    """ A set of steps for a repository. This is the object that stores
    the build data. The build is carried by the slave.
    """

    PENDING = 'pending'
    CANCELLED = 'cancelled'
    STATUSES = BuildStep.STATUSES + [PENDING, CANCELLED]
    CONFIG_TYPES = ['py', 'yaml']

    uuid = UUIDField(required=True, default=lambda: uuid4())
    """An uuid that identifies the build"""

    repository = ReferenceField('toxicbuild.master.Repository', required=True)
    """A referece to the :class:`~toxicbuild.master.repository.Repository` that
    owns the build"""

    slave = ReferenceField('Slave', required=True)
    """A reference to the :class:`~toxicbuild.master.slave.Slave` that will
    execute the build."""

    branch = StringField(required=True)
    """The branch of the code that will be tested."""

    named_tree = StringField(required=True)
    """A identifier of the commit, a sha, a tag name, etc..."""

    started = DateTimeField()
    """When the build was started. It must be in UTC."""

    finished = DateTimeField()
    """When the build was finished. It must be in UTC."""

    builder = ReferenceField(Builder, required=True)
    """A reference to an instance of
    :class:`~toxicbuild.master.build.Builder`."""

    status = StringField(default=PENDING, choices=STATUSES)
    """The current status of the build. May be on of the values in
    :attr:`~toxicbuild.master.build.Build.STATUSES`.
    """

    steps = ListField(EmbeddedDocumentField(BuildStep))
    """A list of :class:`~toxicbuild.master.build.BuildStep`"""

    total_time = IntField()
    """The total time of the build execution."""

    external = EmbeddedDocumentField(ExternalRevisionIinfo)
    """A reference to
      :class:`~toxicbuild.master.document.ExternalRevisionIinfo`"""

    def to_dict(self, id_as_str=False):
        """Transforms the object into a dictionary.

        :param id_as_str: Indicates if the id should be a string or an
          ObjectId instance."""

        steps = [s.to_dict() for s in self.steps]
        objdict = json.loads(super().to_json())
        objdict['builder']['id'] = objdict['builder']['$oid']
        objdict['uuid'] = str(self.uuid)
        objdict['steps'] = steps
        objdict['started'] = datetime2string(
            self.started) if self.started else ''
        objdict['finished'] = datetime2string(
            self.finished) if self.finished else ''
        if self.total_time is not None:
            td = timedelta(seconds=self.total_time)
            objdict['total_time'] = format_timedelta(td)
        else:
            objdict['total_time'] = ''

        if self.external:
            objdict['external'] = self.external.to_dict()
        else:
            objdict['external'] = {}
        return objdict

    def to_json(self):
        """Returns a json representation of the buld."""

        objdict = self.to_dict(id_as_str=True)
        return json.dumps(objdict)

    async def update(self):
        """Does an atomic update in this embedded document."""

        qs = BuildSet.objects.no_cache().filter(builds__uuid=self.uuid)
        result = await qs.update(set__builds__S=self)

        if not result:
            msg = 'This EmbeddedDocument was not save to database.'
            msg += ' You can\'t update it.'
            raise DBError(msg)

        return result

    async def get_buildset(self):
        """Returns the buildset that 'owns' this build."""
        buildset = await BuildSet.objects.no_cache().get(
            builds__uuid=self.uuid)
        return buildset

    @property
    def output(self):
        """The build output. It is the commands + the output of the steps."""
        output = []
        for step in self.steps:
            output.append(step.command + '\n')
            output.append(step.output)

        return ''.join(output)

    @classmethod
    async def get(cls, uuid):
        """Returns a build based on a uuid.

        :param uuid: The uuid of the build."""

        buildset = await BuildSet.objects.get(builds__uuid=uuid)
        for build in buildset.builds:  # pragma no branch
            if str(build.uuid) == str(uuid):  # pragma no branch
                return build

    async def notify(self, event_type):
        """Send a notification to the `build_notification` exchange
        informing about `event_type`

        :param event_type: The name of the event."""
        msg = self.to_dict()
        repo = await self.repository
        msg.update({'repository_id': str(repo.id),
                    'event_type': event_type})
        await build_notifications.publish(msg)

    async def cancel(self):
        """Cancel the build if it is not started yet."""
        if self.status != type(self).PENDING:
            raise ImpossibleCancellation

        self.status = 'cancelled'
        repo = await self.repository
        await self.update()
        build_cancelled.send(str(repo.id), build=self)


class BuildSet(SerializeMixin, Document):

    """A list of builds associated with a revision."""

    PENDING = Build.PENDING

    repository = ReferenceField('toxicbuild.master.Repository',
                                required=True)
    """A referece to the :class:`~toxicbuild.master.repository.Repository` that
    owns the buildset"""

    revision = ReferenceField('toxicbuild.master.RepositoryRevision',
                              required=True)
    """A reference to the
    :class:`~toxicbuild.master.repository.RepositoryRevision` that generated
    this buildset."""

    commit = StringField(required=True)
    """The identifier of the commit that generated the buildset."""

    commit_date = DateTimeField(required=True)
    """The date of the commit"""

    branch = StringField(required=True)
    """The branch of the commit"""

    author = StringField()
    """Commit author's name."""

    title = StringField()
    """Commit title"""

    builds = ListField(EmbeddedDocumentField(Build))
    """A list of :class:`~toxicbuild.master.build.Build` intances."""

    created = DateTimeField(default=now)
    """When the BuildSet was first created. It must be in UTC."""

    started = DateTimeField()
    """When the BuildSet started to run. It must be in UTC."""

    finished = DateTimeField()
    """When the buildset finished. It must be in UTC."""

    total_time = IntField()
    """The total time spent in the buildset"""

    meta = {
        'indexes': [
            'repository'
        ]
    }

    @queryset_manager
    def objects(doc_cls, queryset):  # pylint: disable=no-self-argument
        """The default querymanager for BuildSet"""

        return queryset.order_by('created')

    async def notify(self, event_type, status=None):
        """Notifies an event to the build_notifications exchange.

        :param event_type: The event type to notify about
        :param status: The status of the buildset. If None, the return
          of :meth:`~toxicbuild.master.build.Buildset.get_status` will be
          used."""

        repo = await self.repository
        repo_id = str(repo.id)
        msg = self.to_dict(id_as_str=True)
        msg['event_type'] = event_type
        msg['status'] = status or self.get_status()
        msg['repository_id'] = repo_id
        await build_notifications.publish(msg)

    @classmethod
    async def create(cls, repository, revision):
        """Creates a new buildset.

        :param repository: An instance of `toxicbuild.master.Repository`.
        :param revision: An instance of `toxicbuild.master.RepositoryRevision`.
        :param save: Indicates if the instance should be saved to database.
        """

        buildset = cls(repository=repository, revision=revision,
                       commit=revision.commit,
                       commit_date=revision.commit_date,
                       branch=revision.branch, author=revision.author,
                       title=revision.title)
        await buildset.save()
        ensure_future(buildset.notify('buildset-added'))
        return buildset

    def to_dict(self, id_as_str=False):
        """Returns a dict representation of the object"""

        objdict = super().to_dict(id_as_str=id_as_str)
        objdict['commit_date'] = datetime2string(self.commit_date)
        objdict['created'] = datetime2string(self.created)
        objdict['started'] = datetime2string(self.started) if self.started \
            else ''
        objdict['finished'] = datetime2string(self.finished) if self.finished \
            else ''

        if self.total_time is not None:
            td = timedelta(seconds=self.total_time)
            objdict['total_time'] = format_timedelta(td)
        else:
            objdict['total_time'] = ''

        objdict['builds'] = []
        for b in self.builds:
            bdict = b.to_dict(id_as_str=id_as_str)
            objdict['builds'].append(bdict)
        return objdict

    def to_json(self):
        """Returns a json representation of the object."""
        objdict = self.to_dict(id_as_str=True)
        return json.dumps(objdict)

    def get_status(self):
        """Returns the status of the BuildSet"""

        build_statuses = set([b.status for b in self.builds])
        ordered_statuses = sorted(build_statuses,
                                  key=lambda i: ORDERED_STATUSES.index(i))
        try:
            status = ordered_statuses[0]
        except IndexError:
            status = 'pending'

        return status

    def get_pending_builds(self):
        """Returns the pending builds of the buildset."""

        return [b for b in self.builds if b.status == Build.PENDING]

    async def get_builds_for(self, builder=None, branch=None):
        """Returns the builds for a specific builder and/or branch.

        :param builder: An instance of
          :class:`~toxicbuild.master.build.Builder`.
        :param branch: The name of the branch."""

        async def match_builder(b):
            if not builder or (builder and (await b.builder).id == builder.id):
                return True
            return False

        def match_branch(b):
            if not branch or b.branch == branch:
                return True
            return False

        builds = []  # miss you py3.6
        for build in self.builds:
            if await match_builder(build) and match_branch(build):
                builds.append(build)
        return builds


class BuildManager(LoggerMixin):

    """ Controls which builds should be executed sequentially or
    in parallel.
    """
    # Note that this core reached its limit. It really needs a good
    # refactor, so we can implement builds that trigger other builds
    # in other slaves in a (almost) simple way.

    # each repository has its own key the default dict
    # each slave has its own queue
    _build_queues = defaultdict(lambda: defaultdict(deque))
    # to keep track of which slave is already working
    # on consume its queue
    _is_building = defaultdict(lambda: defaultdict(lambda: False))

    def __init__(self, repository):
        """:param repository: An instance of
          :class:`~toxicbuild.master.repository.Repository.`"""
        self.repository = repository
        self._is_getting_builders = False
        self._is_connected_to_signals = False
        self.config_type = get_build_config_type()
        self.config_filename = get_build_config_filename()

    @property
    def build_queues(self):
        """Returns the build queues for a repository."""

        return self._build_queues[self.repository.name]

    @property
    def is_building(self):
        """Indicates if has some active build for a repository."""

        return self._is_building[self.repository.name]

    async def add_builds(self, revisions):
        """ Adds the builds for a given revision in the build queue.

        :param revision: A list of
          :class:`toxicbuild.master.RepositoryRevision`
          instances for the build."""

        last_bs = None
        for revision in revisions:
            if not revision.create_builds():
                continue

            buildset = await BuildSet.create(repository=self.repository,
                                             revision=revision)

            last_bs = buildset
            slaves = await self.repository.slaves
            for slave in slaves:
                await self.add_builds_for_slave(buildset, slave)

        if last_bs and self.repository.notify_only_latest(buildset.branch):
            await self.cancel_previous_pending(buildset)

    async def add_builds_for_slave(self, buildset, slave, builders=None):
        """Adds builds for a given slave on a given buildset.

        :param buildset: An instance of :class:`toxicbuild.master.BuildSet`.
        :param slaves: An instance of :class:`toxicbuild.master.Slave`.
        :param builders: A list of :class:`toxicbuild.master.Builder`. If
          not builders all builders for this slave and revision will be used.
        """

        builders = builders or []
        revision = await buildset.revision
        if not builders:
            builders = await self.get_builders(slave, revision)

        for builder in builders:
            build = Build(repository=self.repository, branch=revision.branch,
                          named_tree=revision.commit, slave=slave,
                          builder=builder)

            buildset.builds.append(build)
            await buildset.save()
            build_added.send(str(self.repository.id), build=build)

            self.log('build added for named_tree {} on branch {}'.format(
                revision.commit, revision.branch), level='debug')

        self.build_queues[slave.name].append(buildset)
        if not self.is_building[slave.name]:  # pragma: no branch
            ensure_future(self._execute_builds(slave))

    async def get_builders(self, slave, revision):
        """ Get builders for a given slave and revision.

        :param slave: A :class:`toxicbuild.master.slave.Slave` instance.
        :param revision: A
          :class:`toxicbuild.master.repository.RepositoryRevision`.
        """

        async with await self.repository.toxicbuild_conf_lock.acquire(
                routing_key=str(self.repository.id)):
            log('checkout on {} to {}'.format(
                self.repository.url, revision.commit), level='debug')
            await self.repository.vcs.checkout(revision.commit)
            try:
                if self.config_type == 'py':
                    conf = get_toxicbuildconf(self.repository.workdir)
                else:
                    conf = await get_toxicbuildconf_yaml(
                        self.repository.workdir, self.config_filename)

                builders = list_builders_from_config(
                    conf, revision.branch, slave, config_type=self.config_type)
                names = [b['name'] for b in builders]
            except Exception as e:
                msg = 'Something wrong with your toxicbuild.conf. Original '
                msg += 'exception was:\n {}'.format(str(e))
                log(msg, level='warning')
                return []

            builders = []
            for name in names:
                builder = await Builder.get_or_create(
                    name=name, repository=self.repository)
                builders.append(builder)

        return builders

    async def cancel_build(self, build_uuid):
        """Cancel a given build.

        :param build_uuid: The uuid that indentifies the build to be cancelled.
        """

        build = await Build.get(build_uuid)
        try:
            await build.cancel()
            await build.notify('build-cancelled')
            build_cancelled.send(str(self.repository.id), build=build)
        except ImpossibleCancellation:
            self.log('Could not cancel build {}'.format(build_uuid),
                     level='warning')

    async def cancel_previous_pending(self, buildset):
        """Cancels the builds previous to ``buildset``.

        :param buildset: An instance of
          :class:`~toxicbuild.master.build.BuildSet`.
        """

        repo = await buildset.repository
        to_cancel = type(buildset).objects(
            repository=repo, branch=buildset.branch,
            builds__status=Build.PENDING, created__lt=buildset.created)

        async for buildset in to_cancel:
            for build in buildset.builds:
                try:
                    await build.cancel()
                except ImpossibleCancellation:
                    pass

    async def start_pending(self):
        """Starts all pending buildsets that are not already scheduled for
        ``self.repository``."""

        buildsets = BuildSet.objects(builds__status=BuildSet.PENDING,
                                     repository=self.repository)
        buildsets = await buildsets.to_list()
        for buildset in buildsets:
            slaves = set()
            for b in buildset.builds:
                slave = await b.slave
                slaves.add(slave)

            for slave in slaves:
                # we schedule pending builds only if the slave is idle.
                if not self.build_queues[slave.name] and not \
                   self.is_building[slave.name]:

                    self.log('scheduling penging builds for {}'.format(
                        slave.name), level='debug')
                    self.log('schedule pending buildset {}'.format(str(
                        buildset.id)), level='debug')

                    self.build_queues[slave.name].append(buildset)
                    ensure_future(self._execute_builds(slave))

    async def _set_started_for_buildset(self, buildset):
        if not buildset.started:
            buildset.started = localtime2utc(now())
            await buildset.save()
            await buildset.notify('buildset-started', status='running')

    async def _set_finished_for_buildset(self, buildset):
        # reload it so we get the right info about builds and status
        buildset = await type(buildset).objects.get(id=buildset.id)

        just_now = localtime2utc(now())
        if not buildset.finished or set_tzinfo(
                buildset.finished, 0) < just_now:
            buildset.finished = just_now
            buildset.total_time = int((
                buildset.finished - set_tzinfo(buildset.started, 0)).seconds)
            await buildset.save()
            await buildset.notify('buildset-finished')

    async def _execute_builds(self, slave):
        """ Execute the buildsets in the queue of a given slave.

        :param slave: A :class:`toxicbuild.master.slave.Slave` instance."""

        self.is_building[slave.name] = True
        self.log('executing builds for {}'.format(slave.name), level='debug')
        try:
            # here we take the buildsets that are in queue and send
            # each one of them to a slave execute the builds
            while True:
                try:
                    buildset = self.build_queues[slave.name].popleft()
                except IndexError:
                    break

                builds = []
                for build in buildset.builds:
                    # we need to reload it here so we can get the
                    # updated status of the build (ie cancelled)
                    build = await type(build).get(build.uuid)
                    build_slave = await build.slave
                    if slave == build_slave and build.status == type(
                            build).PENDING:
                        builds.append(build)
                if builds:
                    await self._set_started_for_buildset(buildset)
                    await self._execute_in_parallel(slave, builds)
                    await self._set_finished_for_buildset(buildset)
                    self.log('builds for {} finished'.format(slave.name),
                             level='debug')
        finally:
            self.is_building[slave.name] = False

    async def _execute_in_parallel(self, slave, builds):
        """Executes builds in parallel in a slave.

        :param slave: A :class:`~toxicbuild.master.slave.Slave` instance.
        :param builds: A list of
          :class:`~toxicbuild.master.build.Build` instances."""

        fs = []
        for chunk in self._get_builds_chunks(builds):
            chunk = [b for b in await self._reload_builds(chunk)
                     if b.status == type(b).PENDING]
            chunk_fs = []
            for build in chunk:
                type(self.repository).add_running_build()
                f = ensure_future(slave.build(build))
                f.add_done_callback(
                    lambda r: type(self.repository).remove_running_build())
                chunk_fs.append(f)
                fs.append(f)

            if chunk_fs:
                await asyncio.wait(chunk_fs)

        return fs

    def _get_builds_chunks(self, builds):

        if not self.repository.parallel_builds:
            yield builds
            return

        for i in range(0, len(builds), self.repository.parallel_builds):
            yield builds[i:i + self.repository.parallel_builds]

    async def _reload_builds(self, builds):
        """Reloads a chunk of builds

        :param builds: A list of builds."""

        buildset = await builds[0].get_buildset()
        uuids = [b.uuid for b in builds]
        return [b for b in buildset.builds if b.uuid in uuids]
