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
                               ReferenceField, DateTimeField, BooleanField,
                               IntField)
from tornado.platform.asyncio import to_asyncio_future
from toxicbuild.core.utils import (log, string2datetime, get_toxicbuildconf,
                                   list_builders_from_config, datetime2string,
                                   utc2localtime)
from toxicbuild.master.client import get_build_client
from toxicbuild.master.signals import (build_started, build_finished,
                                       revision_added, step_started,
                                       step_finished)


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

    STATUSES = ('running', 'fail', 'success', 'exception')

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

    PENDING = 'pending'
    STATUSES = ('pending', 'running', 'fail', 'success', 'exception')

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


class Slave(Document):

    """ Slaves are the entities that actualy do the work
    of execute steps. The comunication to slaves is through
    the network (using :class:`toxicbuild.master.client.BuildClient`)
    and all code, including toxicbuild.conf, is executed on slave.
    """
    name = StringField(required=True, unique=True)
    host = StringField(required=True)
    port = IntField(required=True)
    is_alive = BooleanField(default=False)

    @classmethod
    @asyncio.coroutine
    def create(cls, **kwargs):
        slave = cls(**kwargs)
        yield from to_asyncio_future(slave.save())
        return slave

    @classmethod
    @asyncio.coroutine
    def get(cls, **kwargs):
        slave = yield from to_asyncio_future(cls.objects.get(**kwargs))
        return slave

    @asyncio.coroutine
    def get_client(self):
        """ Returns a :class:`toxicbuild.master.client.BuildClient` instance
        already connected to the server.
        """
        connected_client = yield from get_build_client(self, self.host,
                                                       self.port)
        return connected_client

    @asyncio.coroutine
    def healthcheck(self):
        """ Check if the build server is up and running
        """
        with (yield from self.get_client()) as client:
            alive = yield from client.healthcheck()

        self.is_alive = alive
        # using yield instead of yield from because mongomotor's
        # save returns a tornado Future, not a asyncio Future
        yield from to_asyncio_future(self.save())
        return self.is_alive

    @asyncio.coroutine
    def list_builders(self, revision):
        """ List builder available in for a given revision

        :param revision: An instance of
          :class:`toxicbuild.master.repositories.RepositoryRevision`
        """
        repository = yield from to_asyncio_future(revision.repository)
        repo_url = repository.url
        vcs_type = repository.vcs_type
        branch = revision.branch
        named_tree = revision.commit

        with (yield from self.get_client()) as client:
            builders = yield from client.list_builders(repo_url, vcs_type,
                                                       branch, named_tree)

        builders = [(yield from Builder.get_or_create(repository=repository,
                                                      name=bname))
                    for bname in builders]

        builders = yield from builders
        return list(builders)

    @asyncio.coroutine
    def build(self, build):
        """ Connects to a build server and requests a build on that server

        :param build: An instance of :class:`toxicbuild.master.build.Build`
        """

        with (yield from self.get_client()) as client:
            build_info = yield from client.build(build)
        return build_info

    @asyncio.coroutine
    def _process_build_info(self, build, build_info):
        """ This method is called by the client when some information about
        the build is sent by the build server.
        """
        # when there's the steps key it's a build info

        if 'steps' in build_info:
            repo = yield from to_asyncio_future(build.repository)
            build.status = build_info['status']
            build.started = string2datetime(build_info['started'])
            finished = build_info['finished']
            if finished:
                build.finished = string2datetime(finished)

            yield from to_asyncio_future(build.save())
            if not build.finished:
                msg = 'build started at {}'.format(build_info['started'])
                self.log(msg)
                build_started.send(repo, build=build)
            else:
                msg = 'build finished at {}'.format(build_info['finished'])
                self.log(msg)
                build_finished.send(repo, build=build)

        else:
            # here is the step info
            yield from self._set_step_info(build, build_info['cmd'],
                                           build_info['name'],
                                           build_info['status'],
                                           build_info['output'],
                                           build_info['started'],
                                           build_info['finished'])

    @asyncio.coroutine
    def _set_step_info(self, build, cmd, name, status, output, started,
                       finished):

        repo = yield from to_asyncio_future(build.repository)
        requested_step = None

        for step in build.steps:
            if step.command == cmd:
                step.status = status
                step.output = output
                step.finished = string2datetime(finished)
                requested_step = step
                msg = 'step {} finished at {} with status'.format(
                    step.command, finished, step.status)
                self.log(msg, level='debug')
                step_finished.send(repo, build=build, step=requested_step)

        if not requested_step:
            requested_step = BuildStep(name=name, command=cmd,
                                       status=status, output=output,
                                       started=string2datetime(started))
            msg = 'step {} started at {}'.format(requested_step.command,
                                                 started)
            self.log(msg, level='debug')
            step_started.send(repo, build=build, step=requested_step)
            build.steps.append(requested_step)

        yield from to_asyncio_future(build.save())

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
          :class:`toxicbuild.master.repositories.RepositoryRevision`
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
        :param slave: A :class:`toxicbuild.master.build.Slave` instance."""

        number = yield from self._get_next_build_number(builder)
        build = Build(repository=self.repository, branch=branch,
                      named_tree=named_tree, slave=slave,
                      builder=builder, number=number)

        yield from to_asyncio_future(build.save())
        self.log('build added for named_tree {} on branch {}'.format(named_tree,
                                                                     branch))
        self._build_queues[slave.name].append(build)

        if not self._is_building[slave.name]:  # pragma: no branch
            asyncio.async(self._execute_builds(slave))

    @asyncio.coroutine
    def get_builders(self, slave, revision):
        """ Get builders for a given slave and revision.

        :param slave: A :class:`toxicbuild.master.build.Slave` instance.
        :param revision: A
          :class:`toxicbuild.master.repositories.RepositoryRevision`.
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

        :param slave: A :class:`toxicbuild.master.build.Slave` instance."""

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

        :param slave: A :class:`toxicbuild.master.build.Slave` instance.
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
