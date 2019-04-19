# -*- coding: utf-8 -*-
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

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

from unittest import TestCase
from unittest.mock import Mock, patch

from toxicbuild.master import aws

from tests import async_test, AsyncMagicMock


class EC2InstanceTest(TestCase):

    @patch.object(aws, 'settings', Mock())
    def setUp(self):
        self.instance = aws.EC2Instance('some-id', 'a-region')

    @patch.object(aws.aiobotocore, 'get_session', Mock())
    def test_get_session(self):
        self.instance._get_session()
        self.assertTrue(aws.aiobotocore.get_session.called)

    def test_get_client(self):
        session = Mock()
        self.instance._get_session = Mock(return_value=session)

        self.instance._get_client()

        self.assertTrue(session.create_client.called)

    @async_test
    async def test_get_description(self):
        client = AsyncMagicMock()
        client.close = Mock()
        client.describe_instances.return_value = {
            'Reservations': [{'Instances': [{'some': 'value'}]}]}

        self.instance._get_client = Mock(return_value=client)

        r = await self.instance.get_description()

        self.assertEqual(r['some'], 'value')
        self.assertTrue(client.close.called)

    @async_test
    async def test_get_status(self):
        self.instance.get_description = AsyncMagicMock(
            return_value={'State': {'Name': 'running'}})

        status = await self.instance.get_status()

        self.assertEqual(status, 'running')

    @async_test
    async def test_is_running(self):
        self.instance.get_status = AsyncMagicMock(return_value='running')

        r = await self.instance.is_running()

        self.assertTrue(r)

    @async_test
    async def test_is_stopped(self):
        self.instance.get_status = AsyncMagicMock(return_value='running')

        r = await self.instance.is_stopped()

        self.assertFalse(r)

    @async_test
    async def test_wait_for_status_ok(self):
        self.instance.get_status = AsyncMagicMock(return_value='running')
        r = await self.instance._wait_for_status('running')

        self.assertTrue(r)

    @patch.object(aws.asyncio, 'sleep', AsyncMagicMock())
    @async_test
    async def test_wait_for_status_timeout(self):
        self.instance.get_status = AsyncMagicMock(return_value='running')
        with self.assertRaises(TimeoutError):
            await self.instance._wait_for_status('stopped')

    @async_test
    async def test_start(self):
        self.instance._run_method = AsyncMagicMock()
        self.instance._wait_for_status = AsyncMagicMock()
        await self.instance.start()

        expected_call_args = (
            ('start_instances',), {'InstanceIds': [self.instance.instance_id]})

        called_args = self.instance._run_method.call_args

        self.assertEqual(expected_call_args, called_args)

        self.assertEqual(self.instance._wait_for_status.call_args[0][0],
                         'running')

    @async_test
    async def test_stop(self):
        self.instance._run_method = AsyncMagicMock()
        self.instance._wait_for_status = AsyncMagicMock()
        await self.instance.stop()

        expected_call_args = (
            ('stop_instances',), {'InstanceIds': [self.instance.instance_id]})

        called_args = self.instance._run_method.call_args

        self.assertEqual(expected_call_args, called_args)

        self.assertEqual(self.instance._wait_for_status.call_args[0][0],
                         'stopped')