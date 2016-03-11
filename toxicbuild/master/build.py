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
from mongomotor import Document, EmbeddedDocument
from mongomotor.fields import (StringField, ListField, EmbeddedDocumentField,
                               ReferenceField, DateTimeField, IntField)
from tornado.platform.asyncio import to_asyncio_future
from toxicbuild.core.utils import (log, get_toxicbuildconf,
                                   list_builders_from_config, datetime2string,
                                   utc2localtime)
from toxicbuild.master.signals import revision_added


class Builder(Document):

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
            qs = Build.objects.filter(builder=self).order_by('-started')
            last = (yield from to_asyncio_future(qs.to_list()))[0]
        except (IndexError, AttributeError):
            status = 'idle'
        else:
            status = last.status
        return status


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
        objson = super().to_json()
        objdict = json.loads(objson)
        keys = objdict.keys()
        if 'started' not in keys:
            objdict['started'] = None
        else:
            objdict['started'] = datetime2string(
                utc2localtime(self.started))

        if 'finished' not in keys:
            objdict['finished'] = None
        else:
            objdict['finished'] = datetime2string(
                utc2localtime(self.finished))

        return objdict

    def to_json(self):
        return json.dumps(self.to_dict())


class Build(Document):

    """ A set of steps for a repository
    """

    STATUSES = BuildStep.STATUSES + ['pending']
    PENDING = 'pending'

    repository = ReferenceField('toxicbuild.master.Repository', required=True)
    slave = ReferenceField('Slave', required=True)
    branch = StringField(required=True)
    named_tree = StringField(required=True)
    started = DateTimeField()
    finished = DateTimeField()
    builder = ReferenceField(Builder, required=True)
    # A build number is considered by the number of builds
    # of a builder.
    number = IntField(required=True)
    status = StringField(default=PENDING, choices=STATUSES)
    steps = ListField(EmbeddedDocumentField(BuildStep))

    def to_dict(self):
        steps = [s.to_dict() for s in self.steps]
        objson = super().to_json()
        objdict = json.loads(objson)
        objdict['steps'] = steps
        return objdict

    def to_json(self):
        return json.dumps(self.to_dict())

    @asyncio.coroutine
    def get_parallels(self):
        """ Returns builds that can be executed in parallel.

        Builds that can be executed in parallel are those that have the
        same branch and named_tree, but different builders.

        This method returns the parallels builds for the same slave and
        repository of this build.
        """

        parallels = type(self).objects.filter(
            id__ne=self.id, branch=self.branch, named_tree=self.named_tree,
            builder__ne=self.builder, slave=self.slave)
        parallels = yield from to_asyncio_future(parallels.to_list())
        msg = 'There are {} parallels for {}'.format(len(parallels), self.id)
        self.log(msg, level='debug')
        return parallels

    def log(self, msg, level='info'):
        log('[{}] {} '.format(type(self).__name__, msg), level)


class BuildManager:

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

        self.connect2signals()

    @asyncio.coroutine
    def add_builds(self, revisions):
        """ Adds the builds for a given revision in the build queue.

        :param revision: A list of
          :class:`toxicbuild.master.repository.RepositoryRevision`
          instances for the build."""

        for revision in revisions:
            for slave in self.repository.slaves:
                builders = yield from self.get_builders(slave, revision)
                for builder in builders:
                    yield from self.add_build(builder, revision.branch,
                                              revision.commit, slave)

    @asyncio.coroutine
    def add_build(self, builder, branch, named_tree, slave):
        """Adds a new buld to the queue.

        :param builder: A :class:`toxicbuild.master.build.Builder` instance.
        :param branch: Branch name.
        :named_tree: Named tree for the build.
        :param slave: A :class:`toxicbuild.master.slave.Slave` instance."""

        number = yield from self._get_next_build_number(builder)
        build = Build(repository=self.repository, branch=branch,
                      named_tree=named_tree, slave=slave,
                      builder=builder, number=number)

        yield from to_asyncio_future(build.save())
        self.log('build added for named_tree {} on branch {}'.format(
            named_tree, branch))
        self._build_queues[slave.name].append(build)

        if not self._is_building[slave.name]:  # pragma: no branch
            asyncio.async(self._execute_builds(slave))

    @asyncio.coroutine
    def get_builders(self, slave, revision):
        """ Get builders for a given slave and revision.

        :param slave: A :class:`toxicbuild.master.slave.Slave` instance.
        :param revision: A
          :class:`toxicbuild.master.repository.RepositoryRevision`.
        """
        self.log('checkout on {} to {}'.format(
            self.repository.url, revision.commit), level='debug')
        yield from self.repository.poller.vcs.checkout(revision.commit)
        try:
            conf = get_toxicbuildconf(self.repository.poller.vcs.workdir)
            names = list_builders_from_config(conf, revision.branch, slave)
        except Exception as e:
            msg = 'Something wrong with your toxicbuild.conf. Original '
            msg += 'exception was:\n {}'.format(str(e))
            self.log(msg, level='warning')
            return []

        builders = []
        for name in names:
            builder = yield from Builder.get_or_create(
                name=name, repository=self.repository)
            builders.append(builder)

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
                    build = self._build_queues[slave.name].popleft()
                    # the build could be executed in parallel with some
                    # other preceding build
                    while build.status != build.PENDING:
                        build = self._build_queues[slave.name].popleft()
                except IndexError:
                    break

                parallels = [build] + (yield from build.get_parallels())
                yield from self._execute_in_parallel(slave, parallels)
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

    @asyncio.coroutine
    def _get_next_build_number(self, builder):
        """Returns the next build number for a given build.

        :param builder: A :class:`toxicbuild.master.build.Builder`
          instance."""

        qs = Build.objects.filter(builder=builder).order_by('-number')
        try:
            build = (yield from to_asyncio_future(qs.to_list()))[0]
        except IndexError:
            number = 0
        else:
            number = build.number + 1

        return number

    def log(self, msg, level='info'):
        log('[{}] {} '.format(type(self).__name__, msg), level)
