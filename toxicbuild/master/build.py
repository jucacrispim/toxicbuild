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
                                   format_timedelta, LoggerMixin)
from toxicbuild.master.exceptions import DBError
from toxicbuild.master.signals import revision_added, build_added

# The statuses used in builds  ordered by priority.
ORDERED_STATUSES = ['running', 'exception', 'fail',
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

    name = StringField()
    repository = ReferenceField('toxicbuild.master.Repository')

    @classmethod
    async def create(cls, **kwargs):
        """Creates a new Builder.

        :param kwargs: kwargs passed to the builder constructor"""
        repo = cls(**kwargs)
        await repo.save()
        return repo

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
    name = StringField(required=True)
    command = StringField(required=True)
    status = StringField(choices=STATUSES)
    output = StringField()
    started = DateTimeField(default=None)
    finished = DateTimeField(default=None)
    # the index of the step in the build.
    index = IntField(requred=True)
    total_time = IntField()

    def to_dict(self):
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
        return json.dumps(self.to_dict())


class Build(EmbeddedDocument):

    """ A set of steps for a repository. This is the object that stores
    the build data. The build is carried by the slave.
    """

    PENDING = 'pending'
    STATUSES = BuildStep.STATUSES + [PENDING]

    uuid = UUIDField(required=True, default=lambda: uuid4())
    repository = ReferenceField('toxicbuild.master.Repository', required=True)
    slave = ReferenceField('Slave', required=True)
    branch = StringField(required=True)
    named_tree = StringField(required=True)
    started = DateTimeField()
    finished = DateTimeField()
    builder = ReferenceField(Builder, required=True)
    status = StringField(default=PENDING, choices=STATUSES)
    steps = ListField(EmbeddedDocumentField(BuildStep))
    total_time = IntField()

    def to_dict(self, id_as_str=False):
        steps = [s.to_dict() for s in self.steps]
        objdict = json.loads(super().to_json())
        objdict['builder']['id'] = objdict['builder']['$oid']
        objdict['uuid'] = str(self.uuid)
        objdict['steps'] = steps
        objdict['started'] = datetime2string(self.started) if self.started \
            else ''
        objdict['finished'] = datetime2string(self.finished) if self.finished \
            else ''
        if self.total_time is not None:
            td = timedelta(seconds=self.total_time)
            objdict['total_time'] = format_timedelta(td)
        else:
            objdict['total_time'] = ''
        return objdict

    def to_json(self):
        objdict = self.to_dict(id_as_str=True)
        return json.dumps(objdict)

    async def update(self):
        """Does an atomic update in this embedded document."""

        result = await BuildSet.objects(
            builds__uuid=self.uuid).update_one(set__builds__S=self)

        if not result:
            msg = 'This EmbeddedDocument was not save to database.'
            msg += ' You can\'t update it.'
            raise DBError(msg)

        return result

    async def get_buildset(self):
        """Returns the buildset that 'owns' this build."""
        buildset = await BuildSet.objects.get(builds__uuid=self.uuid)
        return buildset

    @property
    def output(self):
        """The build output. It is the commands + the output of the steps."""
        output = []
        for step in self.steps:
            output.append(step.command + '\n')
            output.append(step.output)

        return ''.join(output)


class BuildSet(SerializeMixin, Document):

    """A list of builds associated with a revision."""

    PENDING = Build.PENDING

    repository = ReferenceField('toxicbuild.master.Repository',
                                required=True)
    revision = ReferenceField('toxicbuild.master.RepositoryRevision',
                              required=True)
    commit = StringField(required=True)
    commit_date = DateTimeField(required=True)
    branch = StringField(required=True)
    author = StringField()
    title = StringField()
    builds = ListField(EmbeddedDocumentField(Build))
    # when this buildset was first created.
    created = DateTimeField(default=now)
    # when it actually started the builds
    started = DateTimeField()
    finished = DateTimeField()
    total_time = IntField()

    meta = {
        'indexes': [
            'repository'
        ]
    }

    @queryset_manager
    def objects(doc_cls, queryset):
        return queryset.order_by('created')

    @classmethod
    async def create(cls, repository, revision, save=True):
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
        if save:
            await buildset.save()
        return buildset

    def to_dict(self, id_as_str=False):
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
        objdict = self.to_dict(id_as_str=True)
        return json.dumps(objdict)

    def get_status(self):
        build_statuses = set([b.status for b in self.builds])
        ordered_statuses = sorted(build_statuses,
                                  key=lambda i: ORDERED_STATUSES.index(i))
        return ordered_statuses[0]

    def get_pending_builds(self):
        return [b for b in self.builds if b.status == Build.PENDING]

    async def get_builds_for(self, builder=None, branch=None):

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
        self.repository = repository
        self._is_getting_builders = False
        self._is_connected_to_signals = False
        self.connect2signals()

    @property
    def build_queues(self):
        return self._build_queues[self.repository.name]

    @property
    def is_building(self):
        return self._is_building[self.repository.name]

    async def add_builds(self, revisions):
        """ Adds the builds for a given revision in the build queue.

        :param revision: A list of
          :class:`toxicbuild.master.RepositoryRevision`
          instances for the build."""

        for revision in revisions:
            buildset = await BuildSet.create(repository=self.repository,
                                             revision=revision,
                                             save=False)

            slaves = await self.repository.slaves
            for slave in slaves:
                await self.add_builds_for_slave(buildset, slave)

    async def add_builds_for_slave(self, buildset, slave, builders=[]):
        """Adds builds for a given slave on a given buildset.

        :param buildset: An instance of :class:`toxicbuild.master.BuildSet`.
        :param slaves: An instance of :class:`toxicbuild.master.Slave`.
        :param builders: A list of :class:`toxicbuild.master.Builder`. If
          not builders all builders for this slave and revision will be used.
        """

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

        while self.repository.poller.is_polling() or self._is_getting_builders:
            await asyncio.sleep(1)

        self._is_getting_builders = True
        log('checkout on {} to {}'.format(
            self.repository.url, revision.commit), level='debug')
        try:
            await self.repository.poller.vcs.checkout(revision.commit)
            try:
                conf = get_toxicbuildconf(self.repository.poller.vcs.workdir)
                names = list_builders_from_config(conf, revision.branch, slave)
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
        finally:
            self._is_getting_builders = False

        return builders

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

    def connect2signals(self):
        """ Connects the BuildManager to the revision_added signal."""

        revision_added.connect(self._revadded, sender=self.repository)
        self._is_connected_to_signals = True

    def disconnect_from_signals(self):
        revision_added.disconnect(self._revadded)
        self._is_connected_to_signals = False

    async def _revadded(self, sender, revisions):  # pragma no cover
        await self.add_builds(revisions)

    async def _set_started_for_buildset(self, buildset):
        if not buildset.started:
            buildset.started = now()
            await buildset.save()

    async def _set_finished_for_buildset(self, buildset):
        just_now = now()
        if not buildset.finished or buildset.finished < just_now:
            buildset.finished = just_now
            buildset.total_time = int((buildset.finished -
                                       buildset.started).seconds)
            await buildset.save()

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
                    build_slave = await build.slave
                    if slave == build_slave:
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

        :param slave: A :class:`toxicbuild.master.slave.Slave` instance.
        :param builds: A list of
          :class:`toxicbuild.master.build.Build` instances."""

        fs = []
        for chunk in self._get_builds_chunks(builds):
            chunk_fs = []
            for build in chunk:
                f = ensure_future(slave.build(build))
                chunk_fs.append(f)
                fs.append(f)
                await asyncio.wait(chunk_fs)

        return fs

    def _get_builds_chunks(self, builds):

        if not self.repository.parallel_builds:
            yield builds
            return

        for i in range(0, len(builds), self.repository.parallel_builds):
            yield builds[i:i + self.repository.parallel_builds]
