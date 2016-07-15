# -*- coding: utf-8 -*-

# Copyright 2015 Juca Crispim <juca@poraodojuca.net>

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
from collections import defaultdict, deque
import json
from uuid import uuid4
from mongomotor import Document, EmbeddedDocument
from mongomotor.fields import (StringField, ListField, EmbeddedDocumentField,
                               ReferenceField, DateTimeField, UUIDField)
from tornado.platform.asyncio import to_asyncio_future
from toxicbuild.core.utils import (log, get_toxicbuildconf, now,
                                   list_builders_from_config, datetime2string,
                                   utc2localtime, LoggerMixin)
from toxicbuild.master.exceptions import DBError
from toxicbuild.master.signals import revision_added

# The statuses used in builds  ordered by priority.
ORDERED_STATUSES = ['running', 'exception', 'fail',
                    'warning', 'success', 'pending']


class SerializeMixin:

    """Simple mixin to serialization relatad stuff."""

    def to_dict(self, id_as_str=False):
        """ Transforms a Document into a dictionary."""

        objdict = json.loads(super().to_json())
        objdict['id'] = str(self.id) if id_as_str else self.id
        return objdict

    @asyncio.coroutine
    def async_to_json(self):
        """Async version of to_json. Expects a to_dict coroutine."""

        objdict = yield from self.to_dict(id_as_str=True)
        return json.dumps(objdict)


class Builder(SerializeMixin, Document):

    """ The entity responsible for execute the build steps
    """

    name = StringField()
    repository = ReferenceField('toxicbuild.master.Repository')

    @classmethod
    @asyncio.coroutine
    def create(cls, **kwargs):
        repo = cls(**kwargs)
        yield from to_asyncio_future(repo.save())
        return repo

    @classmethod
    @asyncio.coroutine
    def get(cls, **kwargs):
        builder = yield from to_asyncio_future(cls.objects.get(**kwargs))
        return builder

    @classmethod
    @asyncio.coroutine
    def get_or_create(cls, **kwargs):
        try:
            builder = yield from cls.get(**kwargs)
        except cls.DoesNotExist:
            builder = yield from cls.create(**kwargs)

        return builder

    @asyncio.coroutine
    def get_status(self):

        try:
            qs = BuildSet.objects(builds__builder=self).order_by('-started')
            last_buildset = (yield from to_asyncio_future(qs.to_list()))[0]
        except (IndexError, AttributeError):
            status = 'idle'
        else:
            # why this does not work with a listcomp?
            statuses = []
            for build in last_buildset.builds:
                builder = yield from to_asyncio_future(build.builder)
                if builder == self:
                    statuses.append(build.status)

            # statuses = [b.status for b in last_buildset.builds
            #             if (yield from to_asyncio_future(b.builder)) == self]

            ordered_statuses = sorted(statuses,
                                      key=lambda i: ORDERED_STATUSES.index(i))
            status = ordered_statuses[0]

        return status

    @asyncio.coroutine
    def to_dict(self, id_as_str=False):
        objdict = super().to_dict(id_as_str=id_as_str)
        objdict['status'] = yield from self.get_status()
        return objdict

    @asyncio.coroutine
    def to_json(self):
        return (yield from self.async_to_json())


class BuildStep(EmbeddedDocument):

    """ A step for build
    """

    STATUSES = ['running', 'fail', 'success', 'exception',
                'warning']

    name = StringField(required=True)
    command = StringField(required=True)
    status = StringField(choices=STATUSES)
    output = StringField()
    started = DateTimeField(default=None)
    finished = DateTimeField(default=None)

    def to_dict(self):
        objdict = json.loads(super().to_json())
        keys = objdict.keys()
        if 'started' not in keys:
            objdict['started'] = None
        else:
            objdict['started'] = datetime2string(self.started)

        if 'finished' not in keys:
            objdict['finished'] = None
        else:
            objdict['finished'] = datetime2string(self.finished)

        return objdict

    def to_json(self):
        return json.dumps(self.to_dict())


class Build(EmbeddedDocument):

    """ A set of steps for a repository
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

    @asyncio.coroutine
    def to_dict(self, id_as_str=False):
        builder = yield from to_asyncio_future(self.builder)
        steps = [s.to_dict() for s in self.steps]
        objdict = json.loads(super().to_json())
        objdict['builder'] = yield from builder.to_dict(id_as_str=id_as_str)
        objdict['steps'] = steps
        return objdict

    @asyncio.coroutine
    def to_json(self):
        objdict = yield from self.to_dict(id_as_str=True)
        return json.dumps(objdict)

    @asyncio.coroutine
    def update(self):
        """Does an atomic update on this embedded document."""

        result = yield from to_asyncio_future(BuildSet.objects(
            builds__uuid=self.uuid).update_one(
                set__builds__S=self))

        if not result:
            msg = 'This EmbeddedDocument was not save to database.'
            msg += ' You can\'t update it.'
            raise DBError(msg)

        return result


class BuildSet(SerializeMixin, Document):

    """A list of builds associated with a revision."""

    PENDING = Build.PENDING

    repository = ReferenceField('toxicbuild.master.Repository',
                                required=True)
    revision = ReferenceField('toxicbuild.master.RepositoryRevision',
                              required=True)
    commit = StringField(required=True)
    commit_date = DateTimeField(required=True)
    builds = ListField(EmbeddedDocumentField(Build))
    # when this buildset was first created.
    created = DateTimeField(default=now)

    @classmethod
    @asyncio.coroutine
    def create(cls, repository, revision, save=True):
        """Creates a new buildset.

        :param repository: An instance of `toxicbuild.master.Repository`.
        :param revision: An instance of `toxicbuild.master.RepositoryRevision`.
        :param save: Indicates if the instance should be saved to database.
        """

        buildset = cls(repository=repository, revision=revision,
                       commit=revision.commit,
                       commit_date=revision.commit_date)
        if save:
            yield from to_asyncio_future(buildset.save())
        return buildset

    @asyncio.coroutine
    def to_dict(self, id_as_str=False):
        objdict = super().to_dict(id_as_str=id_as_str)
        objdict['commit_date'] = datetime2string(self.commit_date)
        objdict['builds'] = []
        for b in self.builds:
            bdict = yield from b.to_dict(id_as_str=id_as_str)
            objdict['builds'].append(bdict)
        return objdict

    @asyncio.coroutine
    def to_json(self):
        return (yield from self.async_to_json())

    def get_status(self):
        build_statuses = set([b.status for b in self.builds])
        ordered_statuses = sorted(build_statuses,
                                  key=lambda i: ORDERED_STATUSES.index(i))
        return ordered_statuses[0]

    def get_pending_builds(self):
        return [b for b in self.builds if b.status == Build.PENDING]

    @asyncio.coroutine
    def get_builds_for(self, builder=None, branch=None):

        @asyncio.coroutine
        def match_builder(b):
            if not builder or (
                    yield from to_asyncio_future(b.builder)) == builder:
                return True
            return False

        def match_branch(b):
            if not branch or b.branch == branch:
                return True
            return False

        builds = [b for b in self.builds if (yield from match_builder(b)) and
                  match_branch(b)]
        return builds


class BuildManager(LoggerMixin):

    """ Controls which builds should be executed sequentially or
    in parallel.
    """

    def __init__(self, repository):
        self.repository = repository
        # each slave has its own queue
        self._build_queues = defaultdict(deque)

        # to keep track of which slave is already working
        # on consume its queue
        self._is_building = defaultdict(lambda: False)
        self._is_getting_builders = False

        self.connect2signals()

    @asyncio.coroutine
    def add_builds(self, revisions):
        """ Adds the builds for a given revision in the build queue.

        :param revision: A list of
          :class:`toxicbuild.master.RepositoryRevision`
          instances for the build."""

        for revision in revisions:
            buildset = yield from BuildSet.create(repository=self.repository,
                                                  revision=revision,
                                                  save=False)

            slaves = yield from to_asyncio_future(self.repository.slaves)
            for slave in slaves:
                yield from self.add_builds_for_slave(buildset, slave)

    @asyncio.coroutine
    def add_builds_for_slave(self, buildset, slave, builders=[]):
        """Adds builds for a given slave on a given buildset.

        :param buildset: An instance of :class:`toxicbuild.master.BuildSet`.
        :param slaves: An instance of :class:`toxicbuild.master.Slave`.
        :param builders: A list of :class:`toxicbuild.master.Builder`. If
          not builders all builders for this slave and revision.
        """

        revision = yield from to_asyncio_future(buildset.revision)
        if not builders:
            builders = yield from self.get_builders(slave, revision)

        for builder in builders:
            build = Build(repository=self.repository, branch=revision.branch,
                          named_tree=revision.commit, slave=slave,
                          builder=builder)

            buildset.builds.append(build)
            yield from to_asyncio_future(buildset.save())

            self.log('build added for named_tree {} on branch {}'.format(
                revision.commit, revision.branch), level='debug')

        self._build_queues[slave.name].append(buildset)
        if not self._is_building[slave.name]:  # pragma: no branch
            asyncio.async(self._execute_builds(slave))

    @asyncio.coroutine
    def get_builders(self, slave, revision):
        """ Get builders for a given slave and revision.

        :param slave: A :class:`toxicbuild.master.slave.Slave` instance.
        :param revision: A
          :class:`toxicbuild.master.repository.RepositoryRevision`.
        """

        while self.repository.poller.is_polling() or self._is_getting_builders:
            yield from asyncio.sleep(1)

        self._is_getting_builders = True
        log('checkout on {} to {}'.format(
            self.repository.url, revision.commit), level='debug')
        try:
            yield from self.repository.poller.vcs.checkout(revision.commit)
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
                builder = yield from Builder.get_or_create(
                    name=name, repository=self.repository)
                builders.append(builder)
        finally:
            self._is_getting_builders = False

        return builders

    def connect2signals(self):
        """ Connects the BuildManager to the revision_added signal."""

        @asyncio.coroutine
        def revadded(sender, revisions):  # pragma no cover
            yield from self.add_builds(revisions)

        # connect here needs not to be weak otherwise no
        # receiver is available when polling is triggered by the
        # scheduler.
        revision_added.connect(revadded, sender=self.repository, weak=False)

    @asyncio.coroutine
    def _execute_builds(self, slave):
        """ Execute the builds in the queue of a given slave.

        :param slave: A :class:`toxicbuild.master.slave.Slave` instance."""

        self._is_building[slave.name] = True
        try:
            while True:
                try:
                    buildset = self._build_queues[slave.name].popleft()
                except IndexError:
                    break

                builds = []
                for build in buildset.builds:
                    build_slave = yield from to_asyncio_future(build.slave)
                    if slave == build_slave:
                        builds.append(build)
                if builds:
                    yield from self._execute_in_parallel(slave, builds)
        finally:
            self._is_building[slave.name] = False

    @asyncio.coroutine
    def _execute_in_parallel(self, slave, builds):
        """Executes builds in parallel in a slave.

        :param slave: A :class:`toxicbuild.master.slave.Slave` instance.
        :param builds: A list of
          :class:`toxicbuild.master.build.Build` instances."""

        fs = []
        for build in builds:
            f = asyncio.async(slave.build(build))
            fs.append(f)

        yield from asyncio.wait(fs)
        return fs
