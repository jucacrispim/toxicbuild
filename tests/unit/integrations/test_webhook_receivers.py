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

import asyncio
import base64
import json
from unittest.mock import Mock, patch
import tornado
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.integrations import webhook_receivers
from tests import async_test, AsyncMagicMock, create_autospec


class GithubWebhookReceiverTest(AsyncTestCase):

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    def setUp(self):
        super().setUp()
        body = webhook_receivers.json.dumps({
            "zen": "Speak like a human.",
            "hook_id": 'ZZZZZ',
            "hook": {
                "type": "App",
                "id": 'XXXXX',
                "name": "web",
                "active": True,
                "events": [
                    "pull_request",
                    "status"
                ],
                "config": {
                    "content_type": "json",
                    "insecure_ssl": "0",
                    "url": "http://ci.poraodojuca.net:9999/github/webhooks/"
                },
                "updated_at": "2018-01-01T04:25:35Z",
                "created_at": "2018-01-01T04:25:35Z",
                "app_id": 'YYYYY'
            }
        })
        request = Mock()
        request.body = body.encode('utf-8')
        request.arguments = {}
        application = Mock()
        application.ui_methods = {}
        self.webhook_receiver = webhook_receivers.GithubWebhookReceiver(
            application, request)

    @patch.object(webhook_receivers, 'settings', Mock())
    @async_test
    async def test_get_user_from_cookie_without_cookie(self):
        self.webhook_receiver.get_secure_cookie = Mock(return_value=None)
        user = await self.webhook_receiver._get_user_from_cookie()
        self.assertIsNone(user)

    @patch.object(webhook_receivers, 'settings', Mock())
    @async_test
    async def test_get_user_from_cookie(self):
        user = webhook_receivers.User(email='bla@bla.com')
        await user.save()
        try:
            cookie = base64.encodebytes(
                json.dumps({'id': str(user.id)}).encode('utf-8'))
            self.webhook_receiver.get_secure_cookie = Mock(return_value=cookie)
            ret_user = await self.webhook_receiver._get_user_from_cookie()
            self.assertEqual(user.id, ret_user.id)
        finally:
            await user.delete()

    @patch.object(webhook_receivers, 'settings', Mock())
    @gen_test
    def test_authenticate_without_user(self):
        self.webhook_receiver._get_user_from_cookie = AsyncMagicMock(
            return_value=None)
        self.webhook_receiver.redirect = Mock()
        yield self.webhook_receiver.authenticate()
        url = self.webhook_receiver.redirect.call_args[0][0]
        self.assertIn('redirect=', url)

    @patch.object(webhook_receivers, 'settings', Mock())
    @gen_test
    def test_authenticate_without_installation_id(self):
        self.webhook_receiver._get_user_from_cookie = AsyncMagicMock(
            return_value=Mock())
        self.webhook_receiver.params = {}
        self.webhook_receiver.redirect = Mock()
        with self.assertRaises(webhook_receivers.HTTPError):
            yield self.webhook_receiver.authenticate()

    @patch.object(
        webhook_receivers.GithubInstallation, 'create', AsyncMagicMock())
    @patch.object(webhook_receivers, 'settings', Mock())
    @gen_test
    def test_authenticate(self):
        self.webhook_receiver._get_user_from_cookie = AsyncMagicMock(
            return_value=Mock())
        self.webhook_receiver.params = {'installation_id': 1234}
        self.webhook_receiver.redirect = Mock()
        yield self.webhook_receiver.authenticate()
        self.assertTrue(webhook_receivers.GithubInstallation.create.called)

    def test_parse_body(self):
        self.webhook_receiver._parse_body()
        self.assertEqual(
            self.webhook_receiver.body,
            webhook_receivers.json.loads(
                self.webhook_receiver.request.body.decode()))

    def test_parse_body_no_body(self):
        self.webhook_receiver.request.body = None
        self.webhook_receiver._parse_body()
        self.assertIsNone(self.webhook_receiver.body)

    def test_check_event_type_ping(self):
        self.webhook_receiver.request.headers = {'X-GitHub-Event': 'ping'}
        self.webhook_receiver.prepare()
        r = self.webhook_receiver._check_event_type()
        self.assertEqual(r, 'ping')

    def test_check_event_with_action(self):
        self.webhook_receiver.request.headers = {
            'X-GitHub-Event': 'repository'}
        self.webhook_receiver.prepare()
        self.webhook_receiver.body = {'action': 'created'}
        r = self.webhook_receiver._check_event_type()
        self.assertEqual(r, 'repository-created')

    @patch.object(webhook_receivers.LoggerMixin, 'log', Mock())
    def test_check_event_type_None(self):
        self.webhook_receiver.request.headers = {'X-GitHub-Event': None}
        self.webhook_receiver.prepare()
        r = self.webhook_receiver._check_event_type()
        self.assertIsNone(r)

    @patch.object(webhook_receivers.LoggerMixin, 'log', Mock())
    @async_test
    async def test_receive_webhook_ping(self):
        self.webhook_receiver.request.headers = {'X-GitHub-Event': 'ping'}
        self.webhook_receiver.prepare()
        self.webhook_receiver.body['app_id'] = 'some-app-id'
        self.webhook_receiver._validate = AsyncMagicMock()
        msg = await self.webhook_receiver.receive_webhook()
        self.assertEqual(msg['code'], 200)
        self.assertEqual(msg['msg'], 'ping handled successfully')

    @patch.object(webhook_receivers.GithubInstallation, 'objects',
                  AsyncMagicMock())
    @async_test
    async def test_handle_push(self):
        body = {'installation': {'id': '123'},
                'repository': {'id': '1234'}}
        self.webhook_receiver.body = body
        await self.webhook_receiver._handle_push()
        install = webhook_receivers.GithubInstallation.objects.get.return_value
        self.assertTrue(install.update_repository.called)

    @patch.object(webhook_receivers.GithubInstallation, 'objects',
                  AsyncMagicMock())
    @async_test
    async def test_handle_install_repo_added(self):
        body = {'installation': {'id': '123'},
                'repositories_added': [{'full_name': 'my/repo'}]}
        self.webhook_receiver.body = body
        tasks = await self.webhook_receiver._handle_install_repo_added()
        await asyncio.gather(*tasks)
        install = webhook_receivers.GithubInstallation.objects.get.return_value
        self.assertTrue(install.import_repository.called)

    @patch.object(webhook_receivers.GithubInstallation, 'objects',
                  AsyncMagicMock())
    @async_test
    async def test_handle_install_repo_removed(self):
        body = {'installation': {'id': '123'},
                'repositories_removed': [{'id': '4321'}]}
        self.webhook_receiver.body = body
        await self.webhook_receiver._handle_install_repo_removed()
        install = webhook_receivers.GithubInstallation.objects.get.return_value
        self.assertTrue(install.remove_repository.called)

    @patch.object(webhook_receivers.LoggerMixin, 'log', Mock())
    @async_test
    async def test_receive_webhook_unknown(self):
        self.webhook_receiver.request.headers = {
            'X-GitHub-Event': 'I-dont-know'}
        self.webhook_receiver.prepare()
        self.webhook_receiver._validate = AsyncMagicMock()
        with self.assertRaises(webhook_receivers.HTTPError):
            await self.webhook_receiver.receive_webhook()

    @patch.object(
        webhook_receivers.GithubWebhookReceiver, '_get_install',
        AsyncMagicMock(
            spec=webhook_receivers.GithubWebhookReceiver._get_install))
    @async_test
    async def test_handle_pull_request_opended_different_repos(self):
        install = create_autospec(
            spec=webhook_receivers.GithubInstallation,
            mock_cls=AsyncMagicMock)

        self.webhook_receiver._get_install.return_value = install

        body = {
            'pull_request': {
                'head': {'repo': {'id': 'some-id'},
                         'label': 'someone:repo', 'ref': 'some-branch',
                         'clone_url': 'http://somewhere.com/repo.git'},
                'base': {'repo': {'id': 'other-id'}}}}

        self.webhook_receiver.body = body
        await self.webhook_receiver._handle_pull_request_opened()
        called = install.update_repository.call_args[1]
        self.assertEqual(sorted(list(called.keys())), [
                         'external', 'wait_for_lock'])

    @patch.object(
        webhook_receivers.GithubWebhookReceiver, '_get_install',
        AsyncMagicMock(
            spec=webhook_receivers.GithubWebhookReceiver._get_install))
    @async_test
    async def test_handle_pull_request_opended_same_repo(self):
        body = {
            'pull_request': {
                'head': {'repo': {'id': 'some-id'}, 'ref': 'some-branch'},
                'base': {'repo': {'id': 'some-id'}}}}

        self.webhook_receiver.body = body
        install = create_autospec(
            spec=webhook_receivers.GithubInstallation,
            mock_cls=AsyncMagicMock)

        self.webhook_receiver._get_install.return_value = install
        await self.webhook_receiver._handle_pull_request_opened()
        self.assertTrue(install.update_repository.called)

    @patch.object(
        webhook_receivers.GithubWebhookReceiver, '_get_install',
        AsyncMagicMock(
            spec=webhook_receivers.GithubWebhookReceiver._get_install))
    @async_test
    async def test_handle_check_run_rerequested(self):
        install = create_autospec(
            spec=webhook_receivers.GithubInstallation,
            mock_cls=AsyncMagicMock)

        self.webhook_receiver._get_install.return_value = install

        body = {'repository': {'id': 123},
                'check_run': {'check_suite': {'head_branch': 'master',
                                              'head_sha': 'asdf123'}}}

        self.webhook_receiver.body = body
        await self.webhook_receiver._handle_check_run_rerequested()
        self.assertTrue(install.repo_request_build.called)

    @patch.object(
        webhook_receivers.GithubWebhookReceiver, '_get_install',
        AsyncMagicMock(
            spec=webhook_receivers.GithubWebhookReceiver._get_install))
    @async_test
    async def test_handle_install_deleted(self):
        await self.webhook_receiver._handle_install_deleted()
        install = self.webhook_receiver._get_install.return_value
        self.assertTrue(install.delete.called)

    @patch.object(webhook_receivers.GithubApp, 'get_app', AsyncMagicMock(
        spec=webhook_receivers.GithubApp.get_app,
        return_value=create_autospec(
            spec=webhook_receivers.GithubApp,
            mock_cls=AsyncMagicMock)))
    @async_test
    async def test_validate(self):
        app = webhook_receivers.GithubApp.get_app.return_value
        app.validate_token = Mock(
            spec=webhook_receivers.GithubApp.validate_token)
        await self.webhook_receiver._validate()
        self.assertTrue(app.validate_token.called)

    @patch.object(webhook_receivers.GithubApp, 'get_app', AsyncMagicMock(
        spec=webhook_receivers.GithubApp.get_app,
        return_value=create_autospec(
            spec=webhook_receivers.GithubApp,
            mock_cls=AsyncMagicMock)))
    @async_test
    async def test_validate_bad(self):
        app = webhook_receivers.GithubApp.get_app.return_value
        app.validate_token.side_effect = webhook_receivers.BadSignature
        with self.assertRaises(webhook_receivers.HTTPError):
            await self.webhook_receiver._validate()

    def test_hello(self):
        expected = {'code': 200, 'msg': 'Hi there!'}
        r = self.webhook_receiver.hello()
        self.assertEqual(r, expected)
