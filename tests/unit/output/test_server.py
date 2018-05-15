# -*- coding: utf-8 -*-

# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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
from unittest.mock import patch
from toxicbuild.core.exchange import JsonAckMessage
from toxicbuild.master.plugins import NotificationPlugin
from toxicbuild.master.repository import Repository
from toxicbuild.master.users import User
from toxicbuild.output import server
from toxicbuild.output.exchanges import connect_exchanges, disconnect_exchanges
from tests import async_test, AsyncMagicMock


class OutputMethodServerTest(TestCase):

    @async_test
    async def setUp(self):
        await connect_exchanges()
        self.server = server.OutputMethodServer()
        self.user = User(email='a@a.com')
        await self.user.save()
        self.repo = Repository(name='my-repo',
                               url='http://somewhere.com/bla.git',
                               vcs_type='git', update_seconds=100,
                               owner=self.user)
        await self.repo.save()
        await self.repo.enable_plugin('custom-webhook',
                                      webhook_url='http://bla.com')

    @async_test
    async def tearDown(self):
        await Repository.drop_collection()
        await User.drop_collection()
        await disconnect_exchanges()

    @patch.object(NotificationPlugin, 'run', AsyncMagicMock(
        spec=NotificationPlugin.run))
    @async_test
    async def test_run_plugins(self):
        msg = {'repository_id': str(self.repo.id),
               'event_type': 'build-finished'}
        await self.server.run_plugins(msg)
        self.assertTrue(NotificationPlugin.run.called)

    @patch.object(server, 'repo_notifications', AsyncMagicMock(
        spec=server.repo_notifications))
    @patch.object(server.OutputMethodServer, 'run_plugins', AsyncMagicMock(
        spec=server.OutputMethodServer.run_plugins))
    @async_test
    async def test_handle_repo_notifications(self):
        msg = AsyncMagicMock(spec=JsonAckMessage)
        msg.body = {'event_type': 'repo-added',
                    'repository_id': str(self.repo.id)}
        server.repo_notifications.consume.return_value = AsyncMagicMock(
            aiter_items=[msg])

        t = await self.server._handle_repo_notifications()
        await t
        self.assertTrue(self.server.run_plugins.called)

    @patch.object(server, 'build_notifications', AsyncMagicMock(
        spec=server.build_notifications))
    @patch.object(server.OutputMethodServer, 'run_plugins', AsyncMagicMock(
        spec=server.OutputMethodServer.run_plugins))
    @async_test
    async def test_handle_build_notifications(self):
        msg = AsyncMagicMock(spec=JsonAckMessage)
        msg.body = {'event_type': 'build-added',
                    'repository_id': str(self.repo.id)}
        server.build_notifications.consume.return_value = AsyncMagicMock(
            aiter_items=[msg])

        t = await self.server._handle_build_notifications()
        await t
        self.assertTrue(self.server.run_plugins.called)

    @async_test
    async def test_run(self):
        self.server._handle_build_notifications = AsyncMagicMock(
            spec=self.server._handle_build_notifications)

        self.server._handle_repo_notifications = AsyncMagicMock(
            spec=self.server._handle_repo_notifications)

        await self.server.run()
        self.assertTrue(self.server._handle_repo_notifications.called)
        self.assertTrue(self.server._handle_build_notifications.called)
