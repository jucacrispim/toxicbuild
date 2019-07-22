# -*- coding: utf-8 -*-
"""Integrations with Amazon web services. Used to start/stop instances.
"""
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

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

import aiobotocore

from toxicbuild.core.utils import LoggerMixin
from toxicbuild.master import settings
from toxicbuild.master.coordination import Lock


class EC2Instance(LoggerMixin):
    """Performs operations on the ec2 api"""

    def __init__(self, instance_id, region):
        self.instance_id = instance_id
        self.region = region
        self.key_id = settings.AWS_ACCESS_KEY_ID
        self.key = settings.AWS_SECRET_ACCESS_KEY

    @property
    def lock(self):
        path = '/ec2-{}'.format(self.instance_id)
        return Lock(path)

    def _get_session(self):
        loop = asyncio.get_event_loop()
        return aiobotocore.get_session(loop=loop)

    def _get_client(self):
        session = self._get_session()
        client = session.create_client(
            'ec2', region_name=self.region, aws_secret_access_key=self.key,
            aws_access_key_id=self.key_id)
        return client

    async def _run_method(self, method_name, *args, **kwargs):
        client = self._get_client()
        m = getattr(client, method_name)
        try:
            r = await m(*args, **kwargs)
        finally:
            await client.close()
        return r

    async def get_description(self):
        r = await self._run_method('describe_instances',
                                   InstanceIds=[self.instance_id])

        return r['Reservations'][0]['Instances'][0]

    async def get_status(self):
        d = await self.get_description()
        return d['State']['Name']

    async def is_running(self):
        status = await self.get_status()
        return status == 'running'

    async def is_stopped(self):
        status = await self.get_status()
        return status == 'stopped'

    async def _wait_for_status(self, status, timeout=300):
        self.log('waiting status {} for {}'.format(status, self.instance_id),
                 level='debug')
        i = 0
        while i < timeout:
            curr_status = await self.get_status()
            if status == curr_status:
                return True

            await asyncio.sleep(1)
            i += 1

        raise TimeoutError(
            'EC2Instance timed out waiting for status {} in {} seconds'.format(
                status, timeout))

    async def start(self):
        async with await self.lock.acquire_write():
            await self._run_method(
                'start_instances', InstanceIds=[self.instance_id])
            await self._wait_for_status('running')

    async def stop(self):
        async with await self.lock.acquire_write():
            await self._run_method(
                'stop_instances', InstanceIds=[self.instance_id])
            await self._wait_for_status('stopped')

    async def get_ip(self):
        d = await self.get_description()
        return d.get('PublicIpAddress')
