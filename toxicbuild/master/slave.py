# -*- coding: utf-8 -*-

# Copyright 2016-2019 Juca Crispim <juca@poraodojuca.net>

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

import asyncio
from collections import defaultdict
import time
import traceback
from mongomotor.fields import (StringField, IntField, BooleanField,
                               DictField, ListField)
from toxicbuild.core.exceptions import ToxicClientException, BadJsonData
from toxicbuild.core.utils import (string2datetime, LoggerMixin, now,
                                   localtime2utc)

from toxicbuild.master.aws import EC2Instance
from toxicbuild.master.build import BuildStep, Builder
from toxicbuild.master.client import get_build_client
from toxicbuild.master.document import OwnedDocument
from toxicbuild.master.exchanges import build_notifications
from toxicbuild.master.signals import (build_started, build_finished,
                                       step_started, step_finished,
                                       step_output_arrived, build_preparing)


class Slave(OwnedDocument, LoggerMixin):

    """ Slaves are the entities that actualy do the work
    of execute steps. The comunication to slaves is through
    the network (using :class:`toxicbuild.master.client.BuildClient`).
    The steps are actually decided by the slave.
    """

    INSTANCE_TYPES = ('ec2',)
    INSTANCE_CLS = {'ec2': EC2Instance}
    DYNAMIC_HOST = '<DYNAMIC-HOST>'

    host = StringField(required=True)
    """Slave's host."""

    port = IntField(required=True)
    """Port for the slave to listen."""

    token = StringField(required=True)
    """Token for authentication."""

    is_alive = BooleanField(default=False)
    """Indicates if the slave is up and running."""

    use_ssl = BooleanField(default=True)
    """Indicates if the build server in uses ssl connection."""

    validate_cert = BooleanField(default=True)
    """Indicates if the certificate from the build server should be validated.
    """

    on_demand = BooleanField(default=False)
    """If the slave is on-demand it will be started when needed and
    will be stopped when all the builds for this slave are completed.
    """

    instance_type = StringField(choices=INSTANCE_TYPES)
    """The type of instance used. Currently only 'ec2' is supported.
    """

    instance_confs = DictField()
    """Configuration paramenters for the on-demand instance.
    """

    parallel_builds = IntField(default=0)
    """Max number of builds in parallel that this slave exeutes.
    If no parallel_builds there's no limit.
    """

    queue_count = IntField(default=0)
    """How many builds are waiting to run in this repository."""

    running_count = IntField(default=0)
    """How many builds are running in this slave."""

    running_repos = ListField(StringField())
    """The ids of the repositories that have builds running in this slave.
    """

    meta = {
        'ordering': ['name']
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # So, the thing here is that we may have a race condition
        # with the last step output and the build finished messages.
        # In fact, all the build management/build server communitation already
        # is on its limits. A new implementation is needed.
        self._step_finished = defaultdict(lambda: False)
        self._step_output_cache = defaultdict(list)
        self._step_output_cache_time = defaultdict(float)
        self._step_output_cache_limit = 1  # seconds
        self._step_output_is_updating = defaultdict(lambda: False)

    async def save(self, *args, **kwargs):
        if self.on_demand and not self.host:
            self.host = self.DYNAMIC_HOST
        r = await super().save(*args, **kwargs)
        return r

    @classmethod
    async def create(cls, **kwargs):
        """Creates a new slave"""

        slave = cls(**kwargs)
        await slave.save()
        return slave

    def to_dict(self, id_as_str=False):
        """Returns a dict representation of the object."""
        host = self.host if self.host != self.DYNAMIC_HOST else ''
        my_dict = {'name': self.name, 'host': host,
                   'port': self.port, 'token': self.token,
                   'full_name': self.full_name,
                   'is_alive': self.is_alive, 'id': self.id,
                   'on_demand': self.on_demand,
                   'instance_type': self.instance_type,
                   'instance_confs': self.instance_confs}

        if id_as_str:
            my_dict['id'] = str(self.id)
        return my_dict

    @classmethod
    async def get(cls, **kwargs):
        """Returns a slave instance."""

        slave = await cls.objects.get(**kwargs)
        return slave

    @property
    def instance(self):
        """Returns an on-demand instance wrapper.
        """
        cls = self.INSTANCE_CLS[self.instance_type]
        return cls(**self.instance_confs)

    async def increment_queue(self):
        """Increments the queue's count in this slave."""

        self.queue_count += 1
        await self.update(inc__queue_count=1)

    async def decrement_queue(self):
        """Decrements the queue's count in this slave."""

        self.queue_count -= 1
        await self.update(dec__queue_count=1)

    async def add_running_repo(self, repo_id):
        """Increments the number of running builds in this slave and
        adds the repository id to the running repos list. Also decrements
        the queue count.

        :param repo_id: An id of a repository.
        """

        self.running_repos.append(str(repo_id))
        self.running_count += 1
        self.queue_count -= 1
        await self.update(dec__queue_count=1, inc__running_count=1,
                          set__running_repos=self.running_repos)

    async def rm_running_repo(self, repo_id):
        """Decrements the number of running builds in this slave and
        removes the repository id from the running repos list

        :param repo_id: An id of a repository.
        """

        self.running_repos.remove(str(repo_id))
        self.running_count -= 1
        await self.update(
            dec__running_count=1, set__running_repos=self.running_repos)

    async def start_instance(self):
        """Starts an on-demand instance if needed."""

        if not self.on_demand:
            return False

        is_running = await self.instance.is_running()
        if not is_running:
            self.log('Starting on-demand instance for {}'.format(self.id),
                     level='debug')

            await self.instance.start()

        ip = await self.instance.get_ip()
        if ip and self.host == self.DYNAMIC_HOST:
            self.host = ip

        await self.wait_service_start()
        self.log('Instance for {} started with ip {}'.format(self.id, ip),
                 level='debug')
        return ip

    async def stop_instance(self):
        """Stops an on-demand instance"""

        if not self.on_demand:
            return False

        if self.queue_count or self.running_count:
            self.log('Instance still building, not stopping it.',
                     level='debug')
            return False

        self.log('Stopping on-demand instance for {}'.format(self.id),
                 level='debug')

        is_running = await self.instance.is_running()
        if not is_running:
            self.log('Instance for {} already stopped. Leaving.'.format(
                self.id), level='debug')
            return False

        await self.instance.stop()
        self.log('Instance for {} stopped'.format(self.id), level='debug')
        return True

    async def get_client(self):
        """ Returns a :class:`~toxicbuild.master.client.BuildClient` instance
        already connected to the server.
        """
        connected_client = await get_build_client(
            self, self.host, self.port, use_ssl=self.use_ssl,
            validate_cert=self.validate_cert)
        return connected_client

    async def healthcheck(self):
        """ Check if the build server is up and running
        """
        with (await self.get_client()) as client:
            alive = await client.healthcheck()

        return alive

    async def wait_service_start(self, timeout=10):
        """Waits for the toxicslave service start in the on-demand
        instance.
        """
        self.log('waiting toxicslave service start for {}'.format(self.id),
                 level='debug')
        i = 0
        while i < timeout:
            try:
                await self.healthcheck()
                return True
            except ToxicClientException:
                raise
            except Exception as e:
                self.log('Service down {}'.format(i), level='debug')
                self.log(str(e), level='debug')

            i += 1
            await asyncio.sleep(1)

        raise TimeoutError

    async def list_builders(self, revision):
        """ List builder available in for a given revision

        :param revision: An instance of
          :class:`toxicbuild.master.repository.RepositoryRevision`
        """
        repository = await revision.repository
        repo_url = repository.url
        vcs_type = repository.vcs_type
        branch = revision.branch
        named_tree = revision.commit

        with (await self.get_client()) as client:
            builders = await client.list_builders(repo_url, vcs_type,
                                                  branch, named_tree)

        builder_instnces = []
        for bname in builders:
            builder = await Builder.get_or_create(repository=repository,
                                                  name=bname)
            builder_instnces.append(builder)

        return list(builder_instnces)

    async def _finish_build_start_exception(self, build, exc_out):
        build.status = 'exception'
        build.steps = [BuildStep(name='Exception', command='exception',
                                 output=exc_out, status='exception')]
        await build.update()

    async def build(self, build):
        """ Connects to a build server and requests a build on that server

        :param build: An instance of :class:`toxicbuild.master.build.Build`
        """
        repo = await build.repository
        await self.add_running_repo(repo.id)
        build.status = build.PREPARING
        await build.update()
        repo = await build.repository
        build_preparing.send(str(repo.id), build=build)

        try:
            await self.start_instance()
        except Exception as e:
            await self._finish_build_start_exception(build, str(e))
            return False

        with (await self.get_client()) as client:

            try:
                build_info = await client.build(
                    build, process_coro=self._process_info)
            except (ToxicClientException, BadJsonData):
                output = traceback.format_exc()
                build.status = 'exception'
                build.started = build.started or localtime2utc(now())
                build.finished = build.finished or localtime2utc(now())
                exception_step = BuildStep(output=output,
                                           started=localtime2utc(now()),
                                           finished=localtime2utc(now()),
                                           status='exception',
                                           command='', name='exception')
                build.steps.append(exception_step)

                await build.update()
                build_info = build.to_dict()
            finally:
                await self.rm_running_repo(repo.id)

        return build_info

    async def _process_info(self, build, repo, info):
        """ Method used to process information sent by
        the build server about an in progress build.

        :param build: The build that is being executed
        :param repo: The repository that owns the build.
        :param info: A dictionary. The information sent by the
          slave that is executing the build.
        """

        # if we need one more conditional here is better to use
        # a map...
        if info['info_type'] == 'build_info':
            await self._process_build_info(build, repo, info)

        elif info['info_type'] == 'step_info':
            await self._process_step_info(build, repo, info)

        else:
            await self._process_step_output_info(build, repo, info)

    async def _process_build_info(self, build, repo, build_info):
        build.status = build_info['status']
        build.started = string2datetime(build_info['started'])
        finished = build_info['finished']
        if finished:
            build.finished = string2datetime(finished)
            build.total_time = (build.finished - build.started).seconds

        await build.update()

        if not build.finished:
            msg = 'build started at {}'.format(build_info['started'])
            self.log(msg)
            build_started.send(str(repo.id), build=build)
            await build.notify('build-started')
        else:
            msg = 'build finished at {} with status {}'.format(
                build_info['finished'], build.status)
            self.log(msg)
            build_finished.send(str(repo.id), build=build)
            step = build.steps[-1]
            status = build_info['steps'][-1]['status']
            finished = build_info['steps'][-1]['finished']
            await self._fix_last_step_status(build, step, status, finished)
            await build.notify('build-finished')

    async def _process_step_info(self, build, repo, step_info):

        cmd = step_info['cmd']
        name = step_info['name']
        status = step_info['status']
        output = step_info['output']
        started = step_info['started']
        finished = step_info['finished']
        index = step_info['index']
        uuid = step_info['uuid']

        if finished:
            self._step_finished[uuid] = True
            msg = 'step {} {} finished at {} with status {}'.format(
                cmd, uuid, finished, status)
            self.log(msg, level='debug')

            requested_step = await self._get_step(build, uuid)
            requested_step.status = status
            if requested_step.status == 'exception':
                requested_step.output = output if not requested_step.output \
                    else requested_step.output + output
            else:
                requested_step.output = output
            requested_step.finished = string2datetime(finished)
            requested_step.total_time = step_info['total_time']
            await build.update()
            step_finished.send(str(repo.id), build=build, step=requested_step)
            msg = requested_step.to_dict()
            msg.update({'repository_id': str(repo.id),
                        'event_type': 'step-finished'})
            await build_notifications.publish(msg)

        else:
            requested_step = BuildStep(name=name, command=cmd,
                                       status=status, output=output,
                                       started=string2datetime(started),
                                       index=index, uuid=uuid)
            build.steps.append(requested_step)
            await build.update()
            msg = 'step {} started at {}'.format(requested_step.command,
                                                 started)
            self.log(msg, level='debug')
            step_started.send(str(repo.id), build=build, step=requested_step)
            msg = requested_step.to_dict()
            msg.update({'repository_id': str(repo.id),
                        'event_type': 'step-started'})
            await build_notifications.publish(msg)
            if step_info.get('last_step_status'):
                last_step = build.steps[-2]
                status = step_info.get('last_step_status')
                finished = step_info.get('last_step_finished')
                await self._fix_last_step_status(build, last_step,
                                                 status, finished)

    async def _fix_last_step_status(self, build, step, status, finished):
        # this fixes the bug with the status of the step that
        # in someway was getting lost here in the slave.
        step.status = status
        step.finished = string2datetime(finished)
        await build.update()

    async def _update_build_step_info(self, build, step_info):
        # we need this cache here to avoid excessive memory consumption
        # if we try to update the step output every time a line arrives.
        output = step_info['output']
        uuid = step_info['uuid']
        self._step_output_cache[uuid].append(output)

        now = time.time()
        if not self._step_output_cache_time[uuid]:
            self._step_output_cache_time[
                uuid] = now + self._step_output_cache_limit

        is_updating = self._step_output_is_updating[uuid]
        if self._step_output_cache_time[uuid] >= now or is_updating:
            return False

        self._step_output_is_updating[uuid] = True
        step = await self._get_step(build, uuid, wait=True)
        # the thing here is that while we are waiting for the step,
        # the step may have finished, so we don'to anything in this case.
        if self._step_finished[uuid]:
            self.log('Step {} already finished. Leaving...'.format(uuid),
                     level='debug')
            del self._step_output_cache[uuid]
            return False

        output = [step.output or ''] + self._step_output_cache[uuid]
        step.output = ''.join(output)
        del self._step_output_is_updating[uuid]
        del self._step_output_cache[uuid]
        del self._step_output_cache_time[uuid]
        await build.update()
        return True

    async def _process_step_output_info(self, build, repo, info):
        uuid = info['uuid']
        msg = 'step_output_arrived for {}'.format(uuid)
        self.log(msg, level='debug')

        info['repository'] = {'id': str(repo.id)}
        info['build'] = {'uuid': str(build.uuid),
                         'repository': {'id': str(repo.id)}}
        info['output'] = info['output'] + '\n'
        step_output_arrived.send(str(repo.id), step_info=info)

        await self._update_build_step_info(build, info)

    async def _get_step(self, build, step_uuid, wait=False):
        """Returns a step from ``build``. Returns None if the requested
        step is not present in the build.

        :param build: A :class:`toxicbuild.master.build.Build` instance.
        :param step_uuid: The uuid of the requested step.
        """

        # this is ridiculous, but the idea of waitig for the step is
        # that sometimes a info - ie step_output_info - may arrive here
        # before the step started info, so we need to wait a little.
        build_inst = build

        async def _get():

            build = await type(build_inst).get(build_inst.uuid)
            build_steps = build.steps
            for i, step in enumerate(build_steps):
                if str(step.uuid) == str(step_uuid):
                    build_inst.steps[i] = step
                    return step

        step = await _get()
        limit = 20
        n = 0
        while not step and wait:
            await asyncio.sleep(0.001)
            step = await _get()
            n += 1
            if n >= limit:
                wait = False

        return step
