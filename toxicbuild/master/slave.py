# -*- coding: utf-8 -*-

# Copyright 2016 Juca Crispim <juca@poraodojuca.net>

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
import traceback
from mongomotor import Document
from mongomotor.fields import (StringField, IntField, BooleanField)
from tornado.platform.asyncio import to_asyncio_future
from toxicbuild.core.exceptions import ToxicClientException, BadJsonData
from toxicbuild.core.utils import string2datetime, LoggerMixin, now
from toxicbuild.master.build import BuildStep, Builder
from toxicbuild.master.client import get_build_client
from toxicbuild.master.signals import (build_started, build_finished,
                                       step_started, step_finished)


class Slave(Document, LoggerMixin):

    """ Slaves are the entities that actualy do the work
    of execute steps. The comunication to slaves is through
    the network (using :class:`toxicbuild.master.client.BuildClient`).
    The steps are actually decided by the slave.
    """
    name = StringField(required=True, unique=True)
    host = StringField(required=True)
    port = IntField(required=True)
    token = StringField(required=True)
    is_alive = BooleanField(default=False)

    meta = {
        'ordering': ['name']
    }

    @classmethod
    @asyncio.coroutine
    def create(cls, **kwargs):
        slave = cls(**kwargs)
        yield from to_asyncio_future(slave.save())
        return slave

    def to_dict(self, id_as_str=False):
        my_dict = {'name': self.name, 'host': self.host,
                   'port': self.port, 'token': self.token,
                   'is_alive': self.is_alive, 'id': self.id}
        if id_as_str:
            my_dict['id'] = str(self.id)
        return my_dict

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
          :class:`toxicbuild.master.repository.RepositoryRevision`
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

            try:
                build_info = yield from client.build(build)
            except (ToxicClientException, BadJsonData):
                output = traceback.format_exc()
                build.status = 'exception'
                build.started = build.started or now()
                build.finished = build.finished or now()
                exception_step = BuildStep(output=output, started=now(),
                                           finished=now(), status='exception',
                                           command='', name='exception')
                build.steps.append(exception_step)

                yield from build.update()
                build_info = build.to_dict()

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

            yield from build.update()

            if not build.finished:
                msg = 'build started at {}'.format(build_info['started'])
                self.log(msg)
                build_started.send(repo, build=build)
            else:
                msg = 'build finished at {} with status {}'.format(
                    build_info['finished'], build.status)
                self.log(msg)
                build_finished.send(repo, build=build)

        else:
            # here is the step info
            yield from self._set_step_info(build, build_info['cmd'],
                                           build_info['name'],
                                           build_info['status'],
                                           build_info['output'],
                                           build_info['started'],
                                           build_info['finished'],
                                           build_info['index'])

    @asyncio.coroutine
    def _set_step_info(self, build, cmd, name, status, output, started,
                       finished, index):

        repo = yield from to_asyncio_future(build.repository)
        requested_step = None

        for step in build.steps:
            if step.command == cmd:
                step.status = status
                step.output = output
                step.finished = string2datetime(finished)
                requested_step = step
                msg = 'step {} finished at {} with status {}'.format(
                    step.command, finished, step.status)
                self.log(msg, level='debug')
                step_finished.send(repo, build=build, step=requested_step)

        if not requested_step:
            requested_step = BuildStep(name=name, command=cmd,
                                       status=status, output=output,
                                       started=string2datetime(started),
                                       index=index)
            msg = 'step {} started at {}'.format(requested_step.command,
                                                 started)
            self.log(msg, level='debug')
            step_started.send(repo, build=build, step=requested_step)
            build.steps.append(requested_step)

            yield from build.update()
        else:
            # yield from step.update()
            pass
