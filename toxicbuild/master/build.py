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
import datetime
from mongomotor import Document, EmbeddedDocument
from mongomotor.fields import (StringField, ListField, EmbeddedDocumentField,
                               ReferenceField, DateTimeField, BooleanField,
                               IntField)
from toxicbuild.core.utils import log
from toxicbuild.master.client import get_build_client
from toxicbuild.master.signals import (build_started, build_finished,
                                       build_added, revision_added,
                                       step_started, step_finished)


class Builder(Document):

    """ The entity responsible for execute the build steps
    """

    name = StringField()
    repository = ReferenceField('toxicbuild.master.Repository')


class BuildStep(EmbeddedDocument):

    """ A step for build
    """
    name = StringField(required=True)
    command = StringField(required=True)
    status = StringField(required=True)
    output = StringField()
    started = DateTimeField()
    finished = DateTimeField()


class Build(Document):

    """ A set of steps for a repository
    """
    repository = ReferenceField('toxicbuild.master.Repository', required=True)
    slave = ReferenceField('Slave', required=True)
    branch = StringField(required=True)
    named_tree = StringField(required=True)
    started = DateTimeField()
    finished = DateTimeField()
    builder = ReferenceField(Builder, required=True)
    status = StringField(default='pending')
    steps = ListField(EmbeddedDocumentField(BuildStep))


class Slave(Document):

    """ Slaves are the entities that actualy do the work
    of execute steps. The comunication to slaves is through
    the network (using :class:`toxicbuild.master.client.BuildClient`)
    and all code, including toxicbuild.conf, is executed on slave.
    """
    host = StringField()
    port = IntField()
    is_alive = BooleanField(default=False)

    @classmethod
    @asyncio.coroutine
    def create(cls, host, port):
        slave = cls(host=host, port=port)
        yield slave.save()
        return slave

    @classmethod
    @asyncio.coroutine
    def get(cls, host, port):
        slave = yield cls.objects.get(host=host, port=port)
        return slave

    @asyncio.coroutine
    def get_client(self):
        """ Returns a :class:`toxicbuild.master.client.BuildClient` instance
        already connected to the server.
        """
        connected_client = yield from get_build_client(self.host, self.port)
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
        yield self.save()
        return self.is_alive

    @asyncio.coroutine
    def list_builders(self, revision):
        """ List builder available in for a given revision

        :param revision: An instance of
          :class:`toxicbuild.master.repositories.RepositoryRevision`
        """
        repository = yield revision.repository
        repo_url = repository.url
        vcs_type = repository.vcs_type
        branch = revision.branch
        named_tree = revision.commit

        with (yield from self.get_client()) as client:
            builders = yield from client.list_builders(repo_url, vcs_type,
                                                       branch, named_tree)
        return builders

    @asyncio.coroutine
    def build(self, build):
        """ Connects to a build server and requests a build on that server

        :param build: An instance of :class:`toxicbuild.master.build.Build`
        """

        # messy method! not so sure if this works! be careful! sorry!
        # It supposedly works as follows:
        # client.build() is a generator, each iteration returns a info about
        # the build. It sends 2 infos about steps, when it is started and when
        # it is finished and the last respose from the server is the
        # info about the build itself.
        repository = yield build.repository

        with (yield from self.get_client()) as client:
            builder_name = (yield build.builder).name
            for build_info in client.build(repository.url, repository.vcs_type,
                                           build.branch, build.named_tree,
                                           builder_name):

                # Ahhh! bad place for step time stuff. Need to put it on
                # slave
                build.started = datetime.datetime.now()
                yield build.save()
                build_started.send(self, build=build)

                # response with total_steps is the last one
                if 'total_steps' in build_info:
                    break

                step = yield from self._get_step(build, build_info['cmd'],
                                                 build_info['name'],
                                                 build_info['status'],
                                                 build_info['output'])

                # when a running step is sent it means that the step
                # has just started
                if step.status == 'running':
                    msg = 'Executing command {} for {}'.format(
                        step.command, repository.url)

                    self.log(msg)
                    step.started = datetime.datetime.now()
                    yield build.save()
                    step_started.send(self, build=build, step=step)

                # here the step was finished
                else:
                    msg = 'Command {} for {} finished with output {}'.format(
                        step.command,  repository.url, step.output)

                    self.log(msg)
                    # same time stuff shit
                    step.finished = datetime.datetime.now()
                    step_finished.send(self, build=build, step=step)

        build.status = build_info['status']
        build.finished = datetime.datetime.now()
        # again the asyncio Future vs tornado Future
        yield build.save()
        build_finished.send(self, build)
        return build

    def log(self, msg):
        basemsg = '[slave {} - {}] '.format((self.host, self.port),
                                            datetime.datetime.now())
        msg = basemsg + msg
        log(msg)

    @asyncio.coroutine
    def _get_step(self, build, cmd, name, status, output):
        requested_step = None
        for step in build.steps:
            if step.command == cmd:
                step.status = status
                step.output = output
                requested_step = step

        if not requested_step:
            requested_step = BuildStep(name=name, command=cmd,
                                       status=status, output=output)
            build.steps.append(requested_step)

        yield build.save()
        return requested_step


class BuildManager:

    """ A manager for builds
    """

    @classmethod
    @asyncio.coroutine
    def add_builds(cls, sender, revision):
        """ Asks for builders for ``revision`` and creates all nedded
        :class:`toxicbuild.master.Build` instances.

        :param sender: The vcs instance that sent the signal
        :param revision: Instance of :class:`toxicubuild.master.build.Slave`
        """
        repository = yield revision.repository
        for slave in repository.slaves:
            builders = yield from slave.list_builders(revision)
            for builder_name in builders:
                try:
                    builder = yield Builder.objects.get(name=builder_name,
                                                        repository=repository)
                except Builder.DoesNotExist:
                    builder = Builder(name=builder_name, repository=repository)
                    yield builder.save()

                build = Build(repository=repository, branch=revision.branch,
                              named_tree=revision.commit, slave=slave,
                              builder=builder)

                yield build.save()
                build_added.send(cls, build=build)

    @classmethod
    @asyncio.coroutine
    def execute_build(cls, sender, build):
        slave = yield build.slave
        asyncio.async(slave.build(build))


# This first signal is sent by a vcs when a new revision is detected.
revision_added.connect(BuildManager.add_builds)

# This one is sent by BuildManager when a new build is added to db.
build_added.connect(BuildManager.execute_build)
