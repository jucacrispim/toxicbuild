# -*- coding: utf-8 -*-

# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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
import base64
import json
from unittest.mock import Mock, patch
import tornado
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.integrations import webhook_receivers
from tests import async_test, AsyncMagicMock, create_autospec


class BaseWebhookReceiverTest(AsyncTestCase):

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    def setUp(self):
        super().setUp()
        body = webhook_receivers.json.dumps({"some": "thing"})
        request = Mock()
        request.body = body.encode('utf-8')
        request.arguments = {}
        application = Mock()
        application.ui_methods = {}
        self.webhook_receiver = webhook_receivers.BaseWebhookReceiver(
            application, request)

    def test_get_request_signature(self):
        with self.assertRaises(NotImplementedError):
            self.webhook_receiver.get_request_signature()

    @patch.object(webhook_receivers, 'settings', Mock())
    @async_test
    async def test_get_user_from_cookie_without_cookie(self):
        self.webhook_receiver.get_secure_cookie = Mock(return_value=None)
        user = await self.webhook_receiver._get_user_from_cookie()
        self.assertIsNone(user)

    @patch.object(webhook_receivers, 'settings', Mock())
    @patch.object(webhook_receivers.UserInterface, 'get',
                  AsyncMagicMock(spec=webhook_receivers.UserInterface.get))
    @async_test
    async def test_get_user_from_cookie(self):
        user = webhook_receivers.UserInterface(
            None, dict(email='bla@bla.com', id='some-id', name='bla'))
        cookie = base64.encodebytes(
            json.dumps({'id': str(user.id)}).encode('utf-8'))
        self.webhook_receiver.get_secure_cookie = Mock(return_value=cookie)
        ret_user = await self.webhook_receiver._get_user_from_cookie()
        self.assertEqual(user.id, ret_user.id)

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

    def test_check_event_type(self):
        with self.assertRaises(NotImplementedError):
            self.webhook_receiver.check_event_type()

    @patch.object(
        webhook_receivers.BaseWebhookReceiver, 'get_request_signature',
        Mock(spec=webhook_receivers.BaseWebhookReceiver.get_request_signature))
    @async_test
    async def test_validate_webhook_error(self):
        app_cls = Mock()
        app = AsyncMagicMock()
        app.validate_token = AsyncMagicMock(
            side_effect=webhook_receivers.BadSignature)
        app_cls.get_app = AsyncMagicMock(return_value=app)

        self.webhook_receiver.APP_CLS = app_cls

        with self.assertRaises(webhook_receivers.HTTPError):
            await self.webhook_receiver.validate_webhook()

    @patch.object(
        webhook_receivers.BaseWebhookReceiver, 'get_request_signature',
        Mock(spec=webhook_receivers.BaseWebhookReceiver.get_request_signature))
    @async_test
    async def test_validate_webhook(self):
        app_cls = Mock()
        app = AsyncMagicMock()
        app.validate_token = AsyncMagicMock()
        app_cls.get_app = AsyncMagicMock(return_value=app)

        self.webhook_receiver.APP_CLS = app_cls

        r = await self.webhook_receiver.validate_webhook()
        self.assertTrue(r)

    def test_hello(self):
        expected = {'code': 200, 'msg': 'Hi there!'}
        r = self.webhook_receiver.hello()
        self.assertEqual(r, expected)

    @patch.object(webhook_receivers.LoggerMixin, 'log', Mock())
    @async_test
    async def test_receive_webhook(self):
        self.webhook_receiver.validate_webhook = AsyncMagicMock()
        self.webhook_receiver.check_event_type = Mock(
            return_value='some-event')

        async def some_event():
            return 'ok'

        self.webhook_receiver.events = {'some-event': some_event}
        self.webhook_receiver.prepare()
        msg = await self.webhook_receiver.receive_webhook()
        self.assertEqual(msg['code'], 200)

    @patch.object(webhook_receivers.LoggerMixin, 'log', Mock())
    @async_test
    async def test_receive_webhook_bad_event(self):
        self.webhook_receiver.validate_webhook = AsyncMagicMock()
        self.webhook_receiver.check_event_type = Mock()
        self.webhook_receiver.prepare()
        with self.assertRaises(webhook_receivers.HTTPError):
            await self.webhook_receiver.receive_webhook()

    @patch.object(webhook_receivers, 'settings', Mock())
    @gen_test
    def test_setup_without_user(self):
        # if trying to setup wihtout a user, we should be redireced
        # to the login page of the webui.
        self.webhook_receiver._get_user_from_cookie = AsyncMagicMock(
            return_value=None)
        self.webhook_receiver.redirect = Mock()
        yield self.webhook_receiver.setup()
        url = self.webhook_receiver.redirect.call_args[0][0]
        self.assertIn('redirect=', url)
        self.assertTrue(self.webhook_receiver.request.full_url.called)

    @patch.object(webhook_receivers, 'settings', Mock())
    @gen_test
    def test_setup_ok(self):
        self.webhook_receiver._get_user_from_cookie = AsyncMagicMock(
            return_value=Mock())
        self.webhook_receiver.redirect = Mock()
        self.webhook_receiver.create_installation = Mock()
        yield self.webhook_receiver.setup()

        self.assertTrue(self.webhook_receiver.create_installation.called)

    def test_get_repo_external_id(self):
        with self.assertRaises(NotImplementedError):
            self.webhook_receiver.get_repo_external_id()

    @async_test
    async def test_handle_push(self):
        self.webhook_receiver.get_repo_external_id = Mock()
        self.webhook_receiver.get_install = AsyncMagicMock()
        await self.webhook_receiver.handle_push()

        install = self.webhook_receiver.get_install.return_value
        self.assertTrue(install.update_repository.called)

    def test_get_pull_request_source(self):
        with self.assertRaises(NotImplementedError):
            self.webhook_receiver.get_pull_request_source()

    def test_get_pull_request_target(self):
        with self.assertRaises(NotImplementedError):
            self.webhook_receiver.get_pull_request_target()

    @patch.object(
        webhook_receivers.BaseWebhookReceiver, 'get_install',
        AsyncMagicMock(
            spec=webhook_receivers.BaseWebhookReceiver.get_install))
    @async_test
    async def test_handle_pull_request_different_repos(self):
        install = create_autospec(
            spec=webhook_receivers.GithubIntegration,
            mock_cls=AsyncMagicMock)

        self.webhook_receiver.get_install.return_value = install
        self.webhook_receiver.get_pull_request_source = Mock(
            spec=self.webhook_receiver.get_pull_request_source,
            return_value={'id': 'some-id',
                          'url': 'https://some-clone.url',
                          'name': 'bla',
                          'branch': 'feature'}
        )

        self.webhook_receiver.get_pull_request_target = Mock(
            spec=self.webhook_receiver.get_pull_request_source,
            return_value={'id': 'other-id',
                          'branch': 'master'}
        )
        await self.webhook_receiver.handle_pull_request()
        called = install.update_repository.call_args[1]
        self.assertEqual(sorted(list(called.keys())), [
                         'external', 'repo_branches', 'wait_for_lock'])

    @patch.object(
        webhook_receivers.BaseWebhookReceiver, 'get_install',
        AsyncMagicMock(
            spec=webhook_receivers.BaseWebhookReceiver.get_install))
    @async_test
    async def test_handle_pull_request_opended_same_repo(self):
        install = create_autospec(
            spec=webhook_receivers.GithubIntegration,
            mock_cls=AsyncMagicMock)

        self.webhook_receiver.get_install.return_value = install

        self.webhook_receiver.get_pull_request_source = Mock(
            spec=self.webhook_receiver.get_pull_request_source,
            return_value={'id': 'some-id',
                          'url': 'https://some-clone.url',
                          'name': 'bla',
                          'branch': 'feature'}
        )

        self.webhook_receiver.get_pull_request_target = Mock(
            spec=self.webhook_receiver.get_pull_request_source,
            return_value={'id': 'some-id',
                          'branch': 'master'}
        )

        await self.webhook_receiver.handle_pull_request()
        self.assertTrue(install.update_repository.called)
        called = install.update_repository.call_args[1]
        self.assertEqual(sorted(list(called.keys())), [
            'repo_branches', 'wait_for_lock'])

    def test_create_installation_without_code(self):
        # installation_id is sent as a get param by github
        user = Mock()
        self.webhook_receiver.params = {}
        with self.assertRaises(webhook_receivers.HTTPError):
            self.webhook_receiver.create_installation(user)

    @async_test
    async def test_create_installation(self):
        user = Mock()
        self.webhook_receiver.INSTALL_CLS = Mock()
        self.webhook_receiver.INSTALL_CLS.create = AsyncMagicMock()
        self.webhook_receiver.params = {'code': 'some-code',
                                        'state': 'some-state'}
        await self.webhook_receiver.create_installation(user)
        self.assertTrue(self.webhook_receiver.INSTALL_CLS.create.called)

    @async_test
    async def test_get_install(self):
        self.webhook_receiver.params = {'installation_id': 'asf'}
        self.webhook_receiver.APP_CLS = AsyncMagicMock()
        await self.webhook_receiver.get_install()
        self.assertTrue(self.webhook_receiver.APP_CLS.objects.get.called)


class GithubWebhookReceiverTest(AsyncTestCase):

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    def setUp(self):
        super().setUp()
        body = webhook_receivers.json.dumps({
            "zen": "Speak like a human.",
            "hook_id": 'ZZZZZ',
            "repository": {"id": "some-id"},
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
    @gen_test
    def test_create_installation_without_installation_id(self):
        # installation_id is sent as a get param by github
        user = Mock()
        self.webhook_receiver.params = {}
        self.webhook_receiver.redirect = Mock()
        with self.assertRaises(webhook_receivers.HTTPError):
            yield self.webhook_receiver.create_installation(user)

    @patch.object(
        webhook_receivers.GithubIntegration, 'create', AsyncMagicMock())
    @patch.object(webhook_receivers, 'settings', Mock())
    @gen_test
    def test_create_installation_ok(self):
        # if everything ok, we create a installation.
        user = Mock()
        self.webhook_receiver.params = {'installation_id': 1234}
        self.webhook_receiver.redirect = Mock()
        yield self.webhook_receiver.create_installation(user)
        self.assertTrue(webhook_receivers.GithubIntegration.create.called)

    def test_check_event_type_ping(self):
        self.webhook_receiver.request.headers = {'X-GitHub-Event': 'ping'}
        self.webhook_receiver.prepare()
        r = self.webhook_receiver.check_event_type()
        self.assertEqual(r, 'ping')

    def test_check_event_with_action(self):
        self.webhook_receiver.request.headers = {
            'X-GitHub-Event': 'repository'}
        self.webhook_receiver.prepare()
        self.webhook_receiver.body = {'action': 'created'}
        r = self.webhook_receiver.check_event_type()
        self.assertEqual(r, 'repository-created')

    @patch.object(webhook_receivers.LoggerMixin, 'log', Mock())
    def test_check_event_type_None(self):
        self.webhook_receiver.request.headers = {'X-GitHub-Event': None}
        self.webhook_receiver.prepare()
        r = self.webhook_receiver.check_event_type()
        self.assertIsNone(r)

    @patch.object(webhook_receivers.GithubIntegration, 'objects',
                  AsyncMagicMock())
    @async_test
    async def test_handle_install_repo_added(self):
        body = {'installation': {'id': '123'},
                'repositories_added': [{'full_name': 'my/repo'}]}
        self.webhook_receiver.body = body
        tasks = await self.webhook_receiver._handle_install_repo_added()
        await asyncio.gather(*tasks)
        install = webhook_receivers.GithubIntegration.objects.get.return_value
        self.assertTrue(install.import_repository.called)

    @patch.object(webhook_receivers.GithubIntegration, 'objects',
                  AsyncMagicMock())
    @async_test
    async def test_handle_install_repo_removed(self):
        body = {'installation': {'id': '123'},
                'repositories_removed': [{'id': '4321'}]}
        self.webhook_receiver.body = body
        await self.webhook_receiver._handle_install_repo_removed()
        install = webhook_receivers.GithubIntegration.objects.get.return_value
        self.assertTrue(install.remove_repository.called)

    def test_get_pull_request_source(self):
        body = {
            'pull_request': {
                'head': {'repo': {'id': 'some-id'},
                         'label': 'someone:repo', 'ref': 'some-branch',
                         'clone_url': 'http://somewhere.com/repo.git'}}
        }

        self.webhook_receiver.body = body

        source = self.webhook_receiver.get_pull_request_source()

        self.assertTrue(source['url'])

    def test_get_pull_request_target(self):
        body = {
            'pull_request': {
                'base': {'repo': {'id': 'other-id'}, 'ref': 'master'}}
        }

        self.webhook_receiver.body = body

        target = self.webhook_receiver.get_pull_request_target()

        self.assertTrue(target['id'])

    @patch.object(
        webhook_receivers.GithubWebhookReceiver, 'get_install',
        AsyncMagicMock(
            spec=webhook_receivers.GithubWebhookReceiver.get_install))
    @async_test
    async def test_handle_check_run_rerequested(self):
        install = create_autospec(
            spec=webhook_receivers.GithubIntegration,
            mock_cls=AsyncMagicMock)

        self.webhook_receiver.get_install.return_value = install

        body = {'repository': {'id': 123},
                'check_run': {'check_suite': {'head_branch': 'master',
                                              'head_sha': 'asdf123'}}}

        self.webhook_receiver.body = body
        await self.webhook_receiver._handle_check_run_rerequested()
        self.assertTrue(install.repo_request_build.called)

    @patch.object(
        webhook_receivers.GithubWebhookReceiver, 'get_install',
        AsyncMagicMock(
            spec=webhook_receivers.GithubWebhookReceiver.get_install))
    @async_test
    async def test_handle_install_deleted(self):
        await self.webhook_receiver._handle_install_deleted()
        install = self.webhook_receiver.get_install.return_value
        self.assertTrue(install.delete.called)

    @patch.object(webhook_receivers.GithubApp, 'get_app', AsyncMagicMock(
        spec=webhook_receivers.GithubApp.get_app,
        return_value=create_autospec(
            spec=webhook_receivers.GithubApp,
            mock_cls=AsyncMagicMock)))
    @async_test
    async def test_validate_webhook(self):
        app = webhook_receivers.GithubApp.get_app.return_value
        app.validate_token = Mock(
            spec=webhook_receivers.GithubApp.validate_token)
        await self.webhook_receiver.validate_webhook()
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
            await self.webhook_receiver.validate_webhook()

    def test_get_repo_external_id(self):
        self.webhook_receiver.prepare()
        expected = 'some-id'
        r = self.webhook_receiver.get_repo_external_id()

        self.assertEqual(r, expected)


class GitlabWebhookReceiverTest(AsyncTestCase):

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    def setUp(self):
        super().setUp()
        body = webhook_receivers.json.dumps({
            "object_kind": "push",
            "before": "95790bf891e76fee5e1747ab589903a6a1f80f22",
            "after": "da1560886d4f094c3e6c9ef40349f7d38b5d27d7",
            "ref": "refs/heads/master",
            "checkout_sha": "da1560886d4f094c3e6c9ef40349f7d38b5d27d7",
            "user_id": 4,
            "user_name": "John Smith",
            "user_username": "jsmith",
            "user_email": "john@example.com",
            "user_avatar": "https://s.gravatar.com/avatar/d4c...",
            "project_id": 15,
            "project": {
                "id": 15,
                "name": "Diaspora",
                "description": "",
                "web_url": "http://example.com/mike/diaspora",
                "avatar_url": None,
                "git_ssh_url": "git@example.com:mike/diaspora.git",
                "git_http_url": "http://example.com/mike/diaspora.git",
                "namespace": "Mike",
                "visibility_level": 0,
                "path_with_namespace": "mike/diaspora",
                "default_branch": "master",
                "homepage": "http://example.com/mike/diaspora",
                "url": "git@example.com:mike/diaspora.git",
                "ssh_url": "git@example.com:mike/diaspora.git",
                "http_url": "http://example.com/mike/diaspora.git"
            },
            "repository": {
                "name": "Diaspora",
                "url": "git@example.com:mike/diaspora.git",
                "description": "",
                "homepage": "http://example.com/mike/diaspora",
                "git_http_url": "http://example.com/mike/diaspora.git",
                "git_ssh_url": "git@example.com:mike/diaspora.git",
                "visibility_level": 0
            },
            "commits": [
                {
                    "id": "b6568db1bc1dcd7f8b4d5a946b0b91f9dacd7327",
                    "message": "Update Catalan translation to e38cb41.",
                    "timestamp": "2011-12-12T14:27:31+02:00",
                    "url": "http://example.com/mike/diaspora/commit/b656...",
                    "author": {
                        "name": "Jordi Mallach",
                        "email": "jordi@softcatala.org"
                    },
                    "added": ["CHANGELOG"],
                    "modified": ["app/controller/application.rb"],
                    "removed": []
                },
                {
                    "id": "da1560886d4f094c3e6c9ef40349f7d38b5d27d7",
                    "message": "fixed readme",
                    "timestamp": "2012-01-03T23:36:29+02:00",
                    "url": "http://example.com/mike/diaspora/commit/da156...",
                    "author": {
                        "name": "GitLab dev user",
                        "email": "gitlabdev@dv6700.(none)"
                    },
                    "added": ["CHANGELOG"],
                    "modified": ["app/controller/application.rb"],
                    "removed": []
                }
            ],
            "total_commits_count": 4
        })
        request = Mock()
        request.body = body.encode('utf-8')
        request.arguments = {}
        application = Mock()
        application.ui_methods = {}
        self.webhook_receiver = webhook_receivers.GitlabWebhookReceiver(
            application, request)
        self.webhook_receiver.prepare()

    def test_state_is_valid_no_state(self):
        self.webhook_receiver.params = {}
        with self.assertRaises(webhook_receivers.HTTPError):
            self.webhook_receiver.state_is_valid()

    @patch.object(webhook_receivers, 'settings', Mock())
    @patch('toxicbuild.core.utils.log')
    def test_state_is_valid(self, *a, **kw):
        webhook_receivers.settings.TORNADO_OPTS = {
            'cookie_secret': 'some-secret'}
        self.webhook_receiver.params = {'state': 'some-state'}
        r = self.webhook_receiver.state_is_valid()
        self.assertFalse(r)

    @patch.object(webhook_receivers.GitlabWebhookReceiver, 'state_is_valid',
                  Mock(return_value=False))
    def test_create_installation_invalid_state(self):
        user = Mock()
        self.webhook_receiver.params = {'code': 'some-code',
                                        'state': 'some-state'}
        with self.assertRaises(webhook_receivers.HTTPError):
            self.webhook_receiver.create_installation(user)

    @patch.object(webhook_receivers.GitlabWebhookReceiver, 'state_is_valid',
                  Mock(return_value=True))
    @patch.object(
        webhook_receivers.BaseWebhookReceiver, 'create_installation',
        Mock(spec=webhook_receivers.BaseWebhookReceiver.create_installation))
    def test_create_installation_ok(self):
        user = Mock()
        self.webhook_receiver.params = {'code': 'some-code',
                                        'state': 'some-state'}
        self.webhook_receiver.create_installation(user)
        self.assertTrue(
            webhook_receivers.BaseWebhookReceiver.create_installation.called)

    def test_check_event_type(self):

        et = self.webhook_receiver.check_event_type()
        self.assertEqual(et, 'push')

    def test_check_event_type_no_body(self):
        self.webhook_receiver.body = None
        et = self.webhook_receiver.check_event_type()
        self.assertEqual(et, None)

    def test_get_repo_external_id(self):

        self.assertEqual(self.webhook_receiver.get_repo_external_id(), 15)

    @patch.object(
        webhook_receivers.BaseWebhookReceiver, 'validate_webhook',
        AsyncMagicMock(
            spec=webhook_receivers.BaseWebhookReceiver.validate_webhook))
    @async_test
    async def test_validate_webhook(self):
        await self.webhook_receiver.validate_webhook()
        self.assertTrue(
            webhook_receivers.BaseWebhookReceiver.validate_webhook.called)

    def test_get_pull_request_source(self):
        self.webhook_receiver.body = {
            "object_kind": "merge_request",
            "object_attributes": {
                "id": 99,
                "target_branch": "master",
                "source_branch": "ms-viewport",
                "source_project_id": 14,
                "author_id": 51,
                "assignee_id": 6,
                "title": "MS-Viewport",
                "created_at": "2013-12-03T17:23:34Z",
                "updated_at": "2013-12-03T17:23:34Z",
                "milestone_id": None,
                "state": "opened",
                "merge_status": "unchecked",
                "target_project_id": 14,
                "iid": 1,
                "description": "",
                "source": {
                    "name": "Awesome Project",
                    "description": "Aut reprehenderit ut est.",
                    "web_url": "http://example.com/awesome_space/project",
                    "avatar_url": None,
                    "git_ssh_url": "git@example.com:awesome_space/project.git",
                    "git_http_url": "http://example.com/space/project.git",
                    "namespace": "Awesome Space",
                    "visibility_level": 20,
                    "path_with_namespace": "awesome_space/awesome_project",
                    "default_branch": "master",
                    "homepage": "http://example.com/awesome_selfpace/project",
                    "url": "http://example.com/awesome_space/project.git",
                    "ssh_url": "git@example.com:awesome_space/project.git",
                    "http_url": "http://example.com/awesome_space/project.git"
                },
                "target": {
                    "name": "Awesome Project",
                    "description": "Aut reprehenderit ut est.",
                    "web_url": "http://example.com/awesome_space/project",
                    "avatar_url": None,
                    "git_ssh_url": "git@example.com:awesome_space/project.git",
                    "git_http_url": "http://example.com/space/project.git",
                    "namespace": "Awesome Space",
                    "visibility_level": 20,
                    "path_with_namespace": "awesome_space/awesome_project",
                    "default_branch": "master",
                    "homepage": "http://example.com/awesome_space/project",
                    "url": "http://example.com/awesome_space/project.git",
                    "ssh_url": "git@example.com:awesome_space/project.git",
                    "http_url": "http://example.com/awesome_space/project.git"
                },

            },
        }
        r = self.webhook_receiver.get_pull_request_source()

        self.assertTrue(r['branch'])

    def test_get_pull_request_target(self):
        self.webhook_receiver.body = {
            "object_kind": "merge_request",
            "object_attributes": {
                "id": 99,
                "target_branch": "master",
                "source_branch": "ms-viewport",
                "source_project_id": 14,
                "author_id": 51,
                "assignee_id": 6,
                "title": "MS-Viewport",
                "created_at": "2013-12-03T17:23:34Z",
                "updated_at": "2013-12-03T17:23:34Z",
                "milestone_id": None,
                "state": "opened",
                "merge_status": "unchecked",
                "target_project_id": 14,
                "iid": 1,
                "description": "",
                "source": {
                    "name": "Awesome Project",
                    "description": "Aut reprehenderit ut est.",
                    "web_url": "http://example.com/awesome_space/project",
                    "avatar_url": None,
                    "git_ssh_url": "git@example.com:awesome_space/project.git",
                    "git_http_url": "http://example.com/space/project.git",
                    "namespace": "Awesome Space",
                    "visibility_level": 20,
                    "path_with_namespace": "awesome_space/awesome_project",
                    "default_branch": "master",
                    "homepage": "http://example.com/awesome_selfpace/project",
                    "url": "http://example.com/awesome_space/project.git",
                    "ssh_url": "git@example.com:awesome_space/project.git",
                    "http_url": "http://example.com/awesome_space/project.git"
                },
                "target": {
                    "name": "Awesome Project",
                    "description": "Aut reprehenderit ut est.",
                    "web_url": "http://example.com/awesome_space/project",
                    "avatar_url": None,
                    "git_ssh_url": "git@example.com:awesome_space/project.git",
                    "git_http_url": "http://example.com/space/project.git",
                    "namespace": "Awesome Space",
                    "visibility_level": 20,
                    "path_with_namespace": "awesome_space/awesome_project",
                    "default_branch": "master",
                    "homepage": "http://example.com/awesome_space/project",
                    "url": "http://example.com/awesome_space/project.git",
                    "ssh_url": "git@example.com:awesome_space/project.git",
                    "http_url": "http://example.com/awesome_space/project.git"
                },

            },
        }
        r = self.webhook_receiver.get_pull_request_target()

        self.assertTrue(r['branch'])

    def test_request_signature(self):
        self.webhook_receiver.request.headers = {'X-Gitlab-Token': 'token'}
        r = self.webhook_receiver.get_request_signature()
        self.assertEqual(r, 'token')


class BitbucketWebhookReceriverTest(AsyncTestCase):

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    def setUp(self):
        super().setUp()
        body = webhook_receivers.json.dumps({"some": "thing"})
        request = Mock()
        request.body = body.encode('utf-8')
        request.headers = {'X-Event-Key': 'repo:push'}
        request.arguments = {}
        application = Mock()
        application.ui_methods = {}

        self.webhook_receriver = webhook_receivers.BitbucketWebhookReceiver(
            application, request)

    def test_check_event_type(self):
        self.assertEqual(self.webhook_receriver.check_event_type(),
                         'repo:push')

    def test_get_request_signature(self):
        self.webhook_receriver.params = {'token': 'bla'}
        self.assertEqual(self.webhook_receriver.get_request_signature(),
                         'bla')

    def test_get_external_id(self):
        self.webhook_receriver.body = {
            'repository': {
                'uuid': 'the-repo-uuid'
            }
        }

        self.assertEqual(self.webhook_receriver.get_external_id(),
                         'the-repo-uuid')

    def test_get_pull_request_source(self):
        self.webhook_receriver.body = {
            'source': {
                'repository': {
                    'name': 'the-repo',
                    'uuid': 'the-uuid'
                },
                'branch': 'master'
            }
        }

        self.assertEqual(
            self.webhook_receriver.get_pull_request_source()['branch'],
            'master')

    def test_get_pull_request_target(self):
        self.webhook_receriver.body = {
            'target': {
                'repository': {
                    'name': 'the-repo',
                    'uuid': 'the-uuid'
                },
                'branch': 'master'
            }
        }

        self.assertEqual(
            self.webhook_receriver.get_pull_request_target()['branch'],
            'master')
