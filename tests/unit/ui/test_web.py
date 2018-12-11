# -*- coding: utf-8 -*-

# Copyright 2015-2018 Juca Crispim <juca@poraodojuca.net>

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
from unittest import TestCase
from unittest.mock import MagicMock, patch
import tornado
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.ui import web, models, utils
from tests import AsyncMagicMock, async_test, create_autospec


class ToxicRequestTest(TestCase):

    def setUp(self):
        base_req = {'a': [b'a'],
                    'b': [b'a', b'b']}
        self.req = web.ToxicRequest(base_req)

    def test_getitem_one(self):
        expected = 'a'
        returned = self.req['a']
        self.assertEqual(expected, returned)

    def test_getitem_list(self):
        expected = ['a', 'b']
        returned = self.req['b']
        self.assertEqual(expected, returned)

    def test_get(self):
        expected = ['a', 'b']
        returned = self.req.get('b')
        self.assertEqual(expected, returned)

    def test_get_default(self):
        expected = 'default'
        returned = self.req.get('c', 'default')
        self.assertEqual(expected, returned)

    def test_items(self):
        expected = [('a', 'a'), ('b', ['a', 'b'])]
        returned = list(self.req.items())
        self.assertEqual(expected, returned)


class CookieAuthHandlerMixinTest(TestCase):

    def setUp(self):
        super().setUp()

        class TestHandler(web.CookieAuthHandlerMixin, web.BasePyroHandler):
            pass

        request = MagicMock()
        request.cookies = {}
        application = MagicMock()
        application.settings = {'cookie_secret': 'bladjfçajf'}

        self.handler = TestHandler(application, request=request)

    @async_test
    async def test_prepare_without_cookie(self):
        with self.assertRaises(web.HTTPError):
            await self.handler.async_prepare()

    @async_test
    async def test_prepare_with_cookie(self):
        content = web.base64.encodebytes(web.json.dumps(
            {'id': 'asdf',
             'email': 'a@a.com',
             'username': 'zé'}).encode('utf-8'))

        self.handler.set_secure_cookie(web.COOKIE_NAME, content)
        self.handler.request.cookies[
            web.COOKIE_NAME] = self.handler._new_cookie[web.COOKIE_NAME]
        r = await self.handler.async_prepare()
        self.assertTrue(r)


class TemplateHandlerTest(TestCase):

    @async_test
    async def setUp(self):
        super().setUp()
        request = MagicMock()
        request.cookies = {}
        request.body = '{}'
        application = MagicMock()
        self.handler = web.LoginHandler(application, request=request)
        await self.handler.async_prepare()

    @patch.object(web, 'render_template', MagicMock(
        spec=web.render_template, return_value='<html>mytemplate</html>'))
    def test_render_template(self):
        self.handler.write = MagicMock()
        self.handler.render_template('some/template.html', {'my': 'context'})
        self.assertTrue(self.handler.write.called)


class LoggedTemplateHandlerTest(TestCase):

    def setUp(self):
        super().setUp()
        request = MagicMock()
        request.cookies = {}
        request.body = '{}'
        application = MagicMock()
        application.settings = {'cookie_secret': 'bladjfçajf'}
        self.handler = web.LoggedTemplateHandler(application, request=request)

    @patch.object(web.CookieAuthHandlerMixin, 'async_prepare',
                  AsyncMagicMock(spec=web.CookieAuthHandlerMixin.async_prepare,
                                 side_effect=web.HTTPError))
    @async_test
    async def test_async_preprare_not_logged(self):
        self.handler.redirect = MagicMock()
        await self.handler.async_prepare()
        self.assertTrue(self.handler.redirect.called)

    @patch.object(web.CookieAuthHandlerMixin, 'async_prepare',
                  AsyncMagicMock(
                      spec=web.CookieAuthHandlerMixin.async_prepare))
    @async_test
    async def test_async_preprare(self):
        self.handler.redirect = MagicMock()
        await self.handler.async_prepare()
        self.assertFalse(self.handler.redirect.called)


class RegisterHandlerTest(TestCase):

    @async_test
    async def setUp(self):
        super().setUp()
        request = MagicMock()
        request.cookies = {}
        request.body = '{}'
        application = MagicMock()
        application.settings = {'cookie_secret': 'bladjfçajf'}
        self.handler = web.RegisterHandler(application, request=request)
        await self.handler.async_prepare()

    def test_show_register_page(self):
        self.handler.render_template = MagicMock()
        self.handler.set_xsrf_cookie = MagicMock()
        self.handler.show_register_page()
        self.assertTrue(self.handler.set_xsrf_cookie.called)
        self.assertTrue(self.handler.render_template.called)


class LoginHandlerTest(TestCase):

    @async_test
    async def setUp(self):
        super().setUp()
        request = MagicMock()
        request.cookies = {}
        request.body = '{}'
        application = MagicMock()
        application.settings = {'cookie_secret': 'bladjfçajf'}
        self.handler = web.LoginHandler(application, request=request)
        await self.handler.async_prepare()

    @async_test
    async def test_do_login_missing_param(self):
        self.handler.body = {'username_or_email': 'a@a.com'}
        with self.assertRaises(web.HTTPError):
            await self.handler.do_login()

    @patch.object(web.User, 'authenticate', AsyncMagicMock(
        side_effect=Exception))
    @async_test
    async def test_do_login_bad_auth(self):
        self.handler.body = {'username_or_email': 'a@a.com',
                             'password': 'somepassword'}
        with self.assertRaises(web.HTTPError):
            await self.handler.do_login()

    @patch.object(web.User, 'authenticate', AsyncMagicMock(
        spec=web.User.authenticate))
    @async_test
    async def test_do_login(self):
        user = MagicMock()
        user.id = 'some-id'
        user.email = 'a@a.com'
        user.username = 'a'
        web.User.authenticate.return_value = user
        self.handler.body = {'username_or_email': 'a@a.com',
                             'password': 'somepassword'}
        self.handler.set_secure_cookie = MagicMock()
        await self.handler.do_login()
        self.assertTrue(self.handler.set_secure_cookie.called)

    @async_test
    async def test_do_logout(self):
        self.handler.clear_cookie = MagicMock()
        self.handler.redirect = MagicMock()
        self.handler.request.body = None
        await self.handler.async_prepare()
        self.handler.do_logout()
        self.assertTrue(self.handler.clear_cookie.called)

    def test_show_login_page(self):
        self.handler.render_template = MagicMock()
        self.handler.show_login_page()
        template = self.handler.render_template.call_args[0][0]
        self.assertEqual(template, self.handler.login_template)

    def test_show_reset_password_page(self):
        self.handler.render_template = MagicMock()
        self.handler.show_reset_password_page()
        template = self.handler.render_template.call_args[0][0]
        self.assertEqual(template, self.handler.reset_password_template)


@patch.object(models.Repository, 'get_client', AsyncMagicMock(
    spec=models.Repository.get_client, return_value=MagicMock()))
class ModelRestHandlerTest(TestCase):

    @async_test
    async def setUp(self):
        self.model = models.Repository
        application, request = MagicMock(), MagicMock()
        application.ui_methods = {}
        self.handler = web.ModelRestHandler(application, request,
                                            model=self.model)
        body = {'name': 'something', 'url': 'https://someurl.com',
                'vcs_type': 'git'}
        self.handler.request.body = web.json.dumps(body)
        self.handler.request.arguments = {}
        await self.handler.async_prepare()
        self.handler.user = AsyncMagicMock()
        self.handler.user.id = 'asdf'

    @async_test
    async def test_add(self):
        client = models.Repository.get_client.return_value
        client.__enter__.return_value.repo_add = AsyncMagicMock()
        client.__enter__.return_value.repo_add.return_value = {
            'id': '123', 'name': 'something'}
        self.model.get_client = AsyncMagicMock(return_value=client)
        json_resp = await self.handler.add()
        self.assertEqual(web.json.loads(json_resp)['id'], '123')

    @async_test
    async def test_get_or_list_get(self):
        args = {'id': [b'123']}
        self.handler.request.arguments = args
        await self.handler.async_prepare()
        client = models.Repository.get_client.return_value
        client.__enter__.return_value.repo_get = AsyncMagicMock()
        client.__enter__.return_value.repo_get.return_value = {
            'id': '123', 'name': 'something'}
        self.model.get_client = AsyncMagicMock(return_value=client)
        json_resp = await self.handler.get_or_list()
        self.assertEqual(web.json.loads(json_resp)['id'], '123')

    @async_test
    async def test_get_or_list_list(self):
        client = models.Repository.get_client.return_value
        client.__enter__.return_value.repo_list = AsyncMagicMock()
        client.__enter__.return_value.repo_list.return_value = [
            {'id': '123', 'name': 'something'},
            {'id': '234', 'name': 'othername'}]
        self.model.get_client = AsyncMagicMock(return_value=client)
        json_resp = await self.handler.get_or_list()
        self.assertEqual(web.json.loads(json_resp)['items'][1]['id'], '234')

    @async_test
    async def test_update(self):
        client = models.Repository.get_client.return_value
        client.__enter__.return_value.repo_get = AsyncMagicMock()
        client.__enter__.return_value.repo_get.return_value = {
            'id': '123', 'name': 'something'}
        self.model.get_client = AsyncMagicMock(return_value=client)
        self.handler.body = {'parallel_builds': 2}
        json_resp = await self.handler.update()
        self.assertIn('id', web.json.loads(json_resp).keys())

    @async_test
    async def test_delete(self):
        client = models.Repository.get_client.return_value
        client.__enter__.return_value.repo_get = AsyncMagicMock()
        client.__enter__.return_value.repo_get.return_value = {
            'id': '123', 'name': 'something'}
        self.model.get_client = AsyncMagicMock(return_value=client)
        resp = await self.handler.delete_item()
        self.assertEqual(resp, {'delete': 'ok'})


class UserPublicRestHandler(TestCase):

    @async_test
    async def setUp(self):
        self.model = web.User
        application, request = MagicMock(), MagicMock()
        request.body = web.json.dumps({})
        application.ui_methods = {}
        application.settings = {'cookie_secret': 'sdf'}
        self.handler = web.UserPublicRestHandler(application, request,
                                                 model=self.model)
        self.handler._get_user_from_cookie = MagicMock()
        await self.handler.async_prepare()

    @patch.object(web.User, 'exists', AsyncMagicMock(return_value=True,
                                                     spec=web.User.exists))
    @async_test
    async def test_check_exists(self):
        r = await self.handler.check_exists()
        self.assertTrue(r)

    @patch.object(web.User, 'add', AsyncMagicMock(spec=web.User.add,
                                                  return_value=MagicMock()))
    @async_test
    async def test_add(self):
        self.handler.body = {'email': 'a@a.com', 'username': 'mra',
                             'password': 'asdf'}
        new_user = web.User.add.return_value
        new_user.username = 'bla'
        new_user.email = 'bla@a.com'
        new_user.id = 'some-id'
        await self.handler.add()
        user = web.User.add.return_value
        self.assertTrue(user.to_dict.called)
        self.assertTrue(web.User.add.called)

    @patch.object(web.User, 'request_password_reset', AsyncMagicMock())
    @async_test
    async def test_request_password_reset(self):
        email = 'a@a.com'
        url = 'http://bla.nada/reset?token={token}'
        self.handler.body = {
            'email': email,
            'reset_password_url': url}
        await self.handler.request_password_reset()

        self.assertTrue(self.model.request_password_reset.called_with(
            email, url))

    @patch.object(web.User, 'request_password_reset', AsyncMagicMock(
        side_effect=web.UserDoesNotExist))
    @async_test
    async def test_request_password_reset_bad_user(self):
        email = 'a@a.com'
        url = 'http://bla.nada/reset?token={token}'
        self.handler.body = {
            'email': email,
            'reset_password_url': url}

        with self.assertRaises(web.HTTPError):
            await self.handler.request_password_reset()

    @patch.object(web.User, 'change_password_with_token', AsyncMagicMock())
    @async_test
    async def test_change_password_with_token(self):
        token = 'asdf'
        password = '123'
        self.handler.body = {'token': token,
                             'password': password}
        await self.handler.change_password_with_token()

        self.assertTrue(self.model.change_password_with_token.called_with(
            token, password))

    @patch.object(web.User, 'change_password_with_token', AsyncMagicMock(
        side_effect=web.BadResetPasswordToken))
    @async_test
    async def test_change_password_with_token_bad_token(self):
        token = 'asdf'
        password = '123'
        self.handler.body = {'token': token,
                             'password': password}

        with self.assertRaises(web.HTTPError):
            await self.handler.change_password_with_token()


class UserRestHandlerTest(TestCase):

    def setUp(self):
        application, request = MagicMock(), MagicMock()
        application.ui_methods = {}
        self.handler = web.UserRestHandler(application, request,
                                           model=web.User)

    @async_test
    async def test_change_user_password(self):
        self.handler.body = {'username_or_email': 'a@a.com',
                             'old_password': 'old-password',
                             'new_password': 'new-password'}

        self.handler.model.change_password = AsyncMagicMock(
            spec=self.handler.model.change_password, return_value=True)
        await self.handler.change_password()
        self.assertTrue(self.handler.model.change_password.called)


class ReadOnlyRestHandlerTest(TestCase):

    @async_test
    async def setUp(self):
        application, request = MagicMock(), MagicMock()
        request.body = web.json.dumps({})
        application.ui_methods = {}
        self.handler = web.ReadOnlyRestHandler(application,
                                               request)
        self.handler._get_user_from_cookie = MagicMock()
        await self.handler.async_prepare()

    def test_invalid(self):
        with self.assertRaises(web.HTTPError):
            self.handler.invalid()


class BuildSetRestHandlerTest(TestCase):

    @async_test
    async def setUp(self):
        self.model = web.BuildSet
        application, request = MagicMock(), MagicMock()
        request.body = web.json.dumps({})
        application.ui_methods = {}
        self.handler = web.CookieAuthBuildSetHandler(application,
                                                     request,
                                                     model=self.model)
        self.handler._get_user_from_cookie = MagicMock()
        await self.handler.async_prepare()

    @patch.object(web.BuildSet, 'list', AsyncMagicMock(spec=web.BuildSet.list))
    @async_test
    async def test_list_or_get_list(self):
        self.handler.query = {'repo_name': 'somename'}
        self.handler.model.list.return_value = [web.BuildSet(
            MagicMock(), ordered_kwargs={'id': 'someid'})]
        items = await self.handler.list_or_get()
        self.assertEqual(len(items['items']), 1)

    @patch.object(web.BuildSet, 'get', AsyncMagicMock(spec=web.BuildSet.get))
    @async_test
    async def test_list_or_get_get(self):
        self.handler.query = {'buildset_id': 'some-id'}
        self.handler.model.get.return_value = web.BuildSet(
            MagicMock(), ordered_kwargs={'id': 'some-id'})
        buildset = await self.handler.list_or_get()
        self.assertTrue(buildset['id'])

    @async_test
    async def test_list_or_get_bad_request(self):
        with self.assertRaises(web.HTTPError):
            await self.handler.list_or_get()


class BuildHandlerTest(TestCase):

    @async_test
    async def setUp(self):
        self.model = web.Build
        application, request = MagicMock(), MagicMock()
        request.body = web.json.dumps({})
        application.ui_methods = {}
        self.handler = web.CookieAuthBuildHandler(application,
                                                  request,
                                                  model=self.model)
        self.handler._get_user_from_cookie = MagicMock()
        await self.handler.async_prepare()

    @async_test
    async def test_get_build_no_uuid(self):
        with self.assertRaises(web.HTTPError):
            await self.handler.get_build()

    @patch.object(web.Build, 'get', AsyncMagicMock(spec=web.Build.get))
    @async_test
    async def test_get_build(self):
        self.handler.query = {'build_uuid': 'some-uuid'}
        web.Build.get.return_value = web.Build(MagicMock(), {'builder': {}})
        await self.handler.get_build()
        self.assertTrue(web.Build.get.called)


class WaterfallRestHandlerTest(TestCase):

    @async_test
    async def setUp(self):
        self.model = web.BuildSet
        application, request = MagicMock(), MagicMock()
        request.body = web.json.dumps({})
        application.ui_methods = {}
        self.handler = web.CookieAuthWaterfallHandler(application,
                                                      request,
                                                      model=self.model)
        self.handler._get_user_from_cookie = MagicMock()
        await self.handler.async_prepare()

    @patch.object(web.BuildSet, 'list', AsyncMagicMock(spec=web.BuildSet.list))
    @patch.object(web.WaterfallRestHandler, '_get_builders', AsyncMagicMock(
        spec=web.WaterfallRestHandler._get_builders))
    @async_test
    async def test_get_waterfall(self):
        web.BuildSet.list.return_value = [web.BuildSet(MagicMock(), {})]
        web.WaterfallRestHandler._get_builders.return_value = [
            web.Builder(MagicMock(), {})]
        self.handler.query = {'repo_name': 'some/repo'}
        r = await self.handler.get_waterfall()
        self.assertTrue(r)

    @async_test
    async def test_get_waterfall_no_repo_name(self):
        with self.assertRaises(web.HTTPError):
            await self.handler.get_waterfall()

    @patch.object(web.Builder, 'list', AsyncMagicMock(spec=web.Builder.list))
    @async_test
    async def test_get_builders(self):
        buildsets = [web.BuildSet(
            MagicMock(), ordered_kwargs={'id': 'someid',
                                         'builds': [
                                             {'builder': {'id': 'some-id'}}]})]

        await self.handler._get_builders(buildsets)

        called = web.Builder.list.call_args[1]
        expected = {'id__in': ['some-id']}
        self.assertEqual(called, expected)


class RepositoryRestHandlerTest(TestCase):

    @async_test
    async def setUp(self):
        self.model = web.Repository
        application, request = MagicMock(), MagicMock()
        request.body = web.json.dumps({})
        application.ui_methods = {}
        self.handler = web.CookieAuthRepositoryRestHandler(application,
                                                           request,
                                                           model=self.model)
        self.handler._get_user_from_cookie = MagicMock()
        await self.handler.async_prepare()

    @patch.object(web.Repository, 'get', AsyncMagicMock(
        spec=web.Repository.get,
        return_value=create_autospec(spec=web.Repository,
                                     mock_cls=AsyncMagicMock)))
    @patch.object(web.Slave, 'get', AsyncMagicMock(
        spec=web.Slave.get,
        return_value=create_autospec(spec=web.Slave,
                                     mock_cls=AsyncMagicMock)))
    @async_test
    async def test_add_slave(self):
        self.handler.query = {'name': 'somerepo'}
        self.handler.body = {'name': 'bla'}
        r = await self.handler.add_slave()
        self.assertEqual(r['repo-add-slave'], 'slave added')

    @patch.object(web.Repository, 'get', AsyncMagicMock(
        spec=web.Repository.get,
        return_value=create_autospec(spec=web.Repository,
                                     mock_cls=AsyncMagicMock)))
    @patch.object(web.Slave, 'get', AsyncMagicMock(
        spec=web.Slave.get,
        return_value=create_autospec(spec=web.Slave,
                                     mock_cls=AsyncMagicMock)))
    @async_test
    async def test_remove_slave(self):
        self.handler.query = {'name': 'somerepo'}
        self.handler.body = {'name': 'bla'}
        r = await self.handler.remove_slave()
        self.assertEqual(r['repo-remove-slave'], 'slave removed')

    @patch.object(web.Repository, 'get', AsyncMagicMock(
        spec=web.Repository.get,
        return_value=create_autospec(spec=web.Repository,
                                     mock_cls=AsyncMagicMock)))
    @async_test
    async def test_add_branch(self):
        self.handler.body = {'add_branches': [{'branch_name': 'master',
                                               'notify_only_latest': True}]}
        r = await self.handler.add_branch()
        self.assertEqual(r['repo-add-branch'], '1 branches added')

    @patch.object(web.Repository, 'get', AsyncMagicMock(
        spec=web.Repository.get,
        return_value=create_autospec(spec=web.Repository,
                                     mock_cls=AsyncMagicMock)))
    @async_test
    async def test_remove_branch(self):
        self.handler.body = {'remove_branches': [{'branch_name': 'master'}]}
        r = await self.handler.remove_branch()
        self.assertEqual(r['repo-remove-branch'], '1 branches removed')

    @patch.object(web.Repository, 'get', AsyncMagicMock(
        spec=web.Repository.get,
        return_value=create_autospec(spec=web.Repository,
                                     mock_cls=AsyncMagicMock)))
    @async_test
    async def test_start_build(self):
        self.handler.body = {'branch': 'master'}
        r = await self.handler.start_build()
        self.assertTrue(r)

    @patch.object(web.Repository, 'get', AsyncMagicMock(
        spec=web.Repository.get,
        return_value=create_autospec(spec=web.Repository,
                                     mock_cls=AsyncMagicMock)))
    @async_test
    async def test_cancel_build(self):
        self.handler.body = {'build_uuid': 'some-uuid'}
        r = await self.handler.cancel_build()
        self.assertTrue(r)

    @patch.object(web.Repository, 'get', AsyncMagicMock(
        spec=web.Repository.get,
        return_value=create_autospec(spec=web.Repository,
                                     mock_cls=AsyncMagicMock)))
    @async_test
    async def test_enable(self):
        self.handler.query = {'id': 'some-id'}
        r = await self.handler.enable()
        self.assertTrue(r)

    @patch.object(web.Repository, 'get', AsyncMagicMock(
        spec=web.Repository.get,
        return_value=create_autospec(spec=web.Repository,
                                     mock_cls=AsyncMagicMock)))
    @async_test
    async def test_disable(self):
        self.handler.query = {'id': 'some-id'}
        r = await self.handler.disable()
        self.assertTrue(r)


class SlaveRestHandlerTest(TestCase):

    @async_test
    async def setUp(self):
        self.model = web.Slave
        application, request = MagicMock(), MagicMock()
        request.body = web.json.dumps({})
        application.ui_methods = {}
        self.handler = web.CookieAuthSlaveRestHandler(application,
                                                      request,
                                                      model=self.model)
        self.handler._get_user_from_cookie = MagicMock()
        await self.handler.async_prepare()

    def test_query_has_pk(self):
        self.handler.query = {'name': 'bla'}
        has_pk = self.handler._query_has_pk()
        self.assertTrue(has_pk)


class NotificationRestHandlerTest(TestCase):

    def setUp(self):
        super().setUp()
        request = MagicMock()
        request.arguments = {}
        application = MagicMock()
        self.handler = web.NotificationRestHandler(application,
                                                   request=request)

    @patch.object(web.Notification, 'enable', AsyncMagicMock(
        spec=web.Notification.enable))
    @async_test
    async def test_enable(self):
        notif_name = b'some-notif'
        repo_id = b'some-repo-id'
        self.handler.body = {'some': 'field'}
        await self.handler.enable(notif_name, repo_id)
        self.assertTrue(web.Notification.enable.called)

    @patch.object(web.Notification, 'disable', AsyncMagicMock(
        spec=web.Notification.disable))
    @async_test
    async def test_disable(self):
        notif_name = b'some-notif'
        repo_id = b'some-repo-id'
        self.handler.body = {'some': 'field'}
        await self.handler.disable(notif_name, repo_id)
        self.assertTrue(web.Notification.disable.called)

    @patch.object(web.Notification, 'update', AsyncMagicMock(
        spec=web.Notification.update))
    @async_test
    async def test_update(self):
        notif_name = b'some-notif'
        repo_id = b'some-repo-id'
        self.handler.body = {'some': 'field'}
        self.handler.body = {'some': 'field'}
        await self.handler.update(notif_name, repo_id)
        self.assertTrue(web.Notification.update.called)

    @patch.object(web.Notification, 'list', AsyncMagicMock(
        spec=web.Notification.list, return_value=[]))
    @async_test
    async def test_list_no_repo_id(self):
        self.handler.query = {}
        await self.handler.list()
        self.assertTrue(web.Notification.list.called)

    @patch.object(web.Notification, 'list', AsyncMagicMock(
        spec=web.Notification.list, return_value=[]))
    @async_test
    async def test_list(self):
        self.handler.query = {'repo_id': 'some-id'}
        await self.handler.list()
        self.assertTrue(web.Notification.list.called)


@patch.object(web.LoggedTemplateHandler, 'redirect', MagicMock())
class StreamHandlerTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        request = MagicMock()
        request.arguments = {}
        application = MagicMock()
        self.handler = web.StreamHandler(application, request=request)

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    def test_prepare(self):
        self.handler._get_user = MagicMock()

        self.handler.prepare()
        self.handler._get_user.called

    @patch.object(web.Repository, 'get', AsyncMagicMock(
        spec=web.Repository.get, return_value=web.Repository(MagicMock(),
                                                             {'id': 'asdf'})))
    @async_test
    async def test_get_repo_id_repo_name(self):
        self.handler.request.arguments = {'repo_name': [b'my/repo']}
        repo_id = await self.handler._get_repo_id()
        self.assertEqual(repo_id, 'asdf')

    @async_test
    async def test_get_repo_id(self):
        self.handler.request.arguments = {'repo_id': [b'some-id']}
        repo_id = await self.handler._get_repo_id()
        self.assertEqual(repo_id, 'some-id')

    @async_test
    async def test_get_repo_id_type_error(self):
        repo_id = await self.handler._get_repo_id()
        self.assertIsNone(repo_id)

    @patch.object(web, 'StreamConnector', MagicMock())
    @patch.object(web.Repository, 'get', AsyncMagicMock(
        return_value=MagicMock()))
    @async_test
    async def test_open(self):
        self.handler.request.arguments = {'repo_name': [b'asdf']}
        web.StreamConnector.plug = AsyncMagicMock()
        await self.handler.open('repo-status')
        self.assertTrue(web.StreamConnector.plug.called)
        self.assertTrue(self.handler.repo_id)
        self.assertEqual(self.handler.action, 'repo-status')

    @gen_test
    def test_receiver(self):
        sender = MagicMock()
        message = {'event_type': 'build_started'}
        sbi = MagicMock()

        self.handler._send_build_info = sbi

        self.handler.events['build_started'] = self.handler._send_build_info
        self.handler.action = 'builds'
        self.handler.receiver(sender, **message)
        yield from asyncio.sleep(0.001)
        self.assertTrue(sbi.called)

    @patch.object(web.traceback, 'format_exc', MagicMock())
    @gen_test
    def test_receiver_exception(self):
        sender = MagicMock()
        message = {'event_type': 'build_started'}
        sbi = MagicMock(side_effect=Exception)

        self.handler._send_build_info = sbi

        self.handler.events['build_started'] = self.handler._send_build_info
        self.handler.action = 'builds'
        self.handler.log = MagicMock()
        self.handler.receiver(sender, **message)
        yield from asyncio.sleep(0.001)
        self.assertTrue(sbi.called)
        self.assertTrue(web.traceback.format_exc.called)
        self.assertTrue(self.handler.log.called)

    @patch.object(utils, 'settings', MagicMock())
    def test_format_info_dt(self):
        utils.settings.TIMEZONE = 'America/Sao_Paulo'
        utils.settings.DTFORMAT = '%d/%m/%Y %H:%M:%S'
        info = {'started': '3 9 25 08:53:38 2017 -0000',
                'finished': '3 9 25 08:53:44 2017 -0000'}
        self.handler._format_info_dt(info)
        self.assertFalse(info['started'].endswith('0000'))

    @patch.object(utils, 'settings', MagicMock())
    def test_format_info_dt_buildset(self):
        utils.settings.TIMEZONE = 'America/Sao_Paulo'
        utils.settings.DTFORMAT = '%d/%m/%Y %H:%M:%S'
        info = {'buildset': {'started': '3 9 25 08:53:38 2017 -0000',
                             'finished': '3 9 25 08:53:44 2017 -0000',
                             'created': '3 9 25 08:53:44 2017 -0000',
                             'commit_date': '3 9 25 08:53:44 2017 -0000'}}
        self.handler._format_info_dt(info)
        self.assertFalse(info['buildset']['created'].endswith('0000'))
        self.assertFalse(info['buildset']['started'].endswith('0000'))
        self.assertFalse(info['buildset']['commit_date'].endswith('0000'))

    def test_write2sock(self):
        body = {'some': 'response'}
        self.handler.write_message = MagicMock()
        self.handler.write2sock(body)
        self.assertTrue(self.handler.write_message.called)

    def test_write2sock_with_connection_closed(self):
        body = {'some': 'response'}
        self.handler.write_message = MagicMock(side_effect=web.WebSocketError)
        self.handler.log = MagicMock()
        self.handler.write2sock(body)
        self.assertTrue(self.handler.write_message.called)
        self.assertTrue(self.handler.log.called)

    @patch.object(web, 'StreamConnector', MagicMock())
    def test_on_close(self):
        self.handler.on_close()
        self.assertTrue(web.StreamConnector.unplug.called)

    def test_send_step_output_info(self):
        self.handler.request.arguments = {
            'uuid': ['some-uuid'.encode('utf-8')]}

        info = {'uuid': 'sfdaf1', 'build': {'uuid': 'some-uuid'}}
        self.handler.write2sock = MagicMock()
        self.handler._send_step_output_info(info)
        self.assertTrue(self.handler.write2sock.called)

    def test_send_step_output_info_wrong_uuid(self):
        self.handler.request.arguments = {
            'uuid': ['sfdafs1'.encode('utf-8')]}

        info = {'uuid': 'sfdaf1', 'build': {'uuid': 'some-uuid'}}
        self.handler.write2sock = MagicMock()
        self.handler._send_step_output_info(info)
        self.assertFalse(self.handler.write2sock.called)

    @gen_test
    def test_send_build_info(self):
        self.handler.request.arguments = {
            'repository_id': ['1'.encode('utf-8')]}
        self.handler.write2sock = MagicMock()
        info = {'event_type': 'repo_status_changed',
                'repository': {'id': '1'}}

        self.handler._send_build_info(info)
        self.assertTrue(self.handler.write2sock.called)

    @gen_test
    def test_send_raw_info(self):
        info = {'event_type': 'repo_status_changed',
                'status': 'other'}

        self.handler.write2sock = MagicMock()
        self.handler._send_raw_info(info)
        self.assertTrue(self.handler.write2sock.called)


class DashboardHandlerTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        request = MagicMock()
        application = MagicMock()
        application.settings = {'cookie_secret': 'bladjfçajf'}
        self.handler = web.DashboardHandler(application, request=request)

    @patch.object(web, 'render_template', MagicMock(return_value='asdf',
                                                    spec=web.render_template))
    def test_get_main_template(self):
        self.handler._get_main_template()

        called = web.render_template.call_args
        called_template = called[0][0]
        called_context = called[0][2]
        self.assertEqual(called_template, self.handler.main_template)
        self.assertEqual(called_context, {})

    @patch.object(web, 'render_template', MagicMock(return_value='asdf',
                                                    spec=web.render_template))
    def test_get_settings_template(self):
        self.handler._get_settings_template('repositories')

        called = web.render_template.call_args
        called_template = called[0][0]
        called_context = called[0][2]
        expected_keys = ['github_import_url', 'settings_type']
        self.assertEqual(called_template, self.handler.settings_template)
        self.assertEqual(expected_keys, list(called_context.keys()))

    @patch.object(web, 'render_template', MagicMock(return_value='asdf',
                                                    spec=web.render_template))
    def test_get_settings_main_template_repo(self):
        settings_type = 'repositories'
        self.handler._get_settings_main_template(settings_type)
        called = web.render_template.call_args
        called_template = called[0][0]
        called_context = called[0][2]
        expected_keys = ['github_import_url']
        self.assertEqual(called_template, self.handler.repo_settings_template)
        self.assertEqual(expected_keys, list(called_context.keys()))

    @patch.object(web, 'render_template', MagicMock(return_value='asdf',
                                                    spec=web.render_template))
    def test_get_settings_main_template_slave(self):
        settings_type = 'slaves'
        self.handler._get_settings_main_template(settings_type)
        called = web.render_template.call_args
        called_template = called[0][0]
        called_context = called[0][2]
        expected_keys = []
        self.assertEqual(called_template, self.handler.slave_settings_template)
        self.assertEqual(expected_keys, list(called_context.keys()))

    @patch.object(web, 'render_template', MagicMock(return_value='asdf',
                                                    spec=web.render_template))
    def test_get_settings_main_template_ui(self):
        settings_type = 'ui'
        self.handler._get_settings_main_template(settings_type)
        called = web.render_template.call_args
        called_template = called[0][0]
        called_context = called[0][2]
        expected_keys = []
        self.assertEqual(called_template, self.handler.ui_settings_template)
        self.assertEqual(expected_keys, list(called_context.keys()))

    @patch.object(web, 'render_template', MagicMock(return_value='asdf',
                                                    spec=web.render_template))
    def test_get_settings_main_template_user(self):
        settings_type = 'user'
        self.handler._get_settings_main_template(settings_type)
        called = web.render_template.call_args
        called_template = called[0][0]
        called_context = called[0][2]
        expected_keys = []
        self.assertEqual(called_template, self.handler.user_settings_template)
        self.assertEqual(expected_keys, list(called_context.keys()))

    @patch.object(web, 'render_template', MagicMock(return_value='asdf',
                                                    spec=web.render_template))
    def test_get_settings_main_template_bad_settings(self):
        settings_type = 'bad'
        with self.assertRaises(web.BadSettingsType):
            self.handler._get_settings_main_template(settings_type)

    @patch.object(web, 'render_template', MagicMock(return_value='asdf',
                                                    spec=web.render_template))
    def test_get_buildset_list_template(self):
        full_name = 'some/one'
        self.handler._get_buildset_list_template(full_name)
        called = web.render_template.call_args
        called_template = called[0][0]
        called_context = called[0][2]
        expected_keys = ['repo_full_name']
        self.assertEqual(called_template, self.handler.buildset_list_template)
        self.assertEqual(expected_keys, list(called_context.keys()))

    @patch.object(web, 'render_template', MagicMock(return_value='asdf',
                                                    spec=web.render_template))
    def test_get_waterfall_template(self):
        full_name = 'some/one'
        self.handler._get_waterfall_template(full_name)
        called = web.render_template.call_args
        called_template = called[0][0]
        called_context = called[0][2]
        expected_keys = ['repo_name']
        self.assertEqual(called_template, self.handler.waterfall_template)
        self.assertEqual(expected_keys, list(called_context.keys()))

    @patch.object(web, 'render_template', MagicMock(return_value='asdf',
                                                    spec=web.render_template))
    def test_get_repository_template(self):
        self.handler._get_repository_template()
        called = web.render_template.call_args
        called_template = called[0][0]
        called_context = called[0][2]
        self.assertEqual(called_template, self.handler.repository_template)
        self.assertEqual(called_context, {'repo_full_name': ''})

    @patch.object(web, 'render_template', MagicMock(return_value='asdf',
                                                    spec=web.render_template))
    def test_get_build_template(self):
        self.handler._get_build_template('some-uuid')
        called = web.render_template.call_args
        called_template = called[0][0]
        called_context = called[0][2]
        self.assertEqual(called_template, self.handler.build_template)
        self.assertEqual(called_context, {'build_uuid': 'some-uuid'})

    @patch.object(web, 'render_template', MagicMock(return_value='asdf',
                                                    spec=web.render_template))
    def test_get_buildset_template(self):
        self.handler._get_buildset_template('some-buildset-id', 'some-repo-id')
        called = web.render_template.call_args
        called_template = called[0][0]
        called_context = called[0][2]
        self.assertEqual(called_template, self.handler.buildset_template)
        self.assertEqual(called_context, {'buildset_id': 'some-buildset-id',
                                          'repo_id': 'some-repo-id'})

    @patch.object(web, 'render_template', MagicMock(return_value='asdf',
                                                    spec=web.render_template))
    def test_get_notifications_template(self):
        self.handler._get_notifications_template('my/repo', 'repo-id')
        called = web.render_template.call_args
        called_template = called[0][0]
        called_context = called[0][2]
        self.assertEqual(called_template, self.handler.notifications_template)
        self.assertEqual(called_context, {'repo_full_name': 'my/repo',
                                          'repo_id': 'repo-id'})

    @patch.object(web, 'render_template', MagicMock(return_value='asdf',
                                                    spec=web.render_template))
    def test_get_slave_template(self):
        self.handler._get_slave_template()
        called = web.render_template.call_args
        called_template = called[0][0]
        called_context = called[0][2]
        self.assertEqual(called_template, self.handler.slave_template)
        self.assertEqual(called_context, {'slave_full_name': ''})

    def test_show_main(self):
        self.handler.render_template = MagicMock(
            spec=self.handler.render_template)
        self.handler._get_main_template = MagicMock(
            spec=self.handler._get_main_template)

        self.handler.show_main()

        called_template = self.handler.render_template.call_args[0][0]
        called_context = self.handler.render_template.call_args[0][1]
        self.assertTrue(self.handler._get_main_template.called)
        self.assertEqual(called_template, self.handler.skeleton_template)
        self.assertIn('content', called_context)

    def test_show_main_template(self):
        self.handler._get_main_template = MagicMock(
            spec=self.handler._get_main_template)
        self.handler.write = MagicMock(spec=self.handler.write)

        self.handler.show_main_template()

        self.assertTrue(self.handler._get_main_template.called)
        self.assertTrue(self.handler.write.called)

    def test_show_settings(self):
        self.handler._get_settings_template = MagicMock(
            spec=self.handler._get_settings_template)
        self.handler.render_template = MagicMock(
            spec=self.handler.render_template)

        self.handler.show_settings(b'repositories')

        expected_keys = ['content']
        called_template = self.handler.render_template.call_args[0][0]
        called_context = self.handler.render_template.call_args[0][1]
        self.assertTrue(self.handler._get_settings_template.called)
        self.assertEqual(called_template, self.handler.skeleton_template)
        self.assertEqual(expected_keys, sorted(list(called_context.keys())))

    def test_show_settings_template(self):
        self.handler._get_settings_template = MagicMock(
            spec=self.handler._get_settings_template)
        self.handler.write = MagicMock(spec=self.handler.write)

        self.handler.show_settings_template(b'slaves')
        self.assertTrue(self.handler._get_settings_template.called)
        self.assertTrue(self.handler.write.called)

    def test_show_settings_main_template(self):
        self.handler._get_settings_main_template = MagicMock(
            spec=self.handler._get_settings_main_template)
        self.handler.write = MagicMock(spec=self.handler.write)

        self.handler.show_settings_main_template(b'slaves')
        self.assertTrue(self.handler._get_settings_main_template.called)
        self.assertTrue(self.handler.write.called)

    def test_show_repository_details(self):
        self.handler._get_repository_template = MagicMock(
            spec=self.handler._get_repository_template)
        self.handler.render_template = MagicMock(
            spec=self.handler.render_template)

        self.handler.show_repository_details(b'some/repo')

        expected_keys = ['content']
        called_template = self.handler.render_template.call_args[0][0]
        called_context = self.handler.render_template.call_args[0][1]
        self.assertTrue(self.handler._get_repository_template.called)
        self.assertEqual(called_template, self.handler.skeleton_template)
        self.assertEqual(expected_keys, sorted(list(called_context.keys())))

    @patch.object(web.Repository, 'get', AsyncMagicMock(
        spec=web.Repository.get, return_value=MagicMock()))
    @async_test
    async def test_show_repository_notifications(self):
        self.handler._get_notifications_template = MagicMock(
            spec=self.handler._get_notifications_template)
        self.handler.render_template = MagicMock(
            spec=self.handler.render_template)

        await self.handler.show_repository_notifications(b'some/repo')

        expected_keys = ['content']
        called_template = self.handler.render_template.call_args[0][0]
        called_context = self.handler.render_template.call_args[0][1]
        self.assertTrue(self.handler._get_notifications_template.called)
        self.assertEqual(called_template, self.handler.skeleton_template)
        self.assertEqual(expected_keys, sorted(list(called_context.keys())))

    def test_show_buildset_list(self):
        self.handler._get_buildset_list_template = MagicMock(
            spec=self.handler._get_buildset_list_template)
        self.handler.render_template = MagicMock(
            spec=self.handler.render_template)

        self.handler.show_repo_buildset_list(b'some/repo')

        expected_keys = ['content']
        called_template = self.handler.render_template.call_args[0][0]
        called_context = self.handler.render_template.call_args[0][1]
        self.assertTrue(self.handler._get_buildset_list_template.called)
        self.assertEqual(called_template, self.handler.skeleton_template)
        self.assertEqual(expected_keys, sorted(list(called_context.keys())))

    @patch.object(web.BuildSet, 'get', AsyncMagicMock(spec=web.BuildSet.get))
    @async_test
    async def test_show_buildset_details(self):
        self.handler._get_buildset_template = MagicMock(
            spec=type(self.handler)._get_buildset_template)
        self.handler.render_template = MagicMock(
            spec=self.handler.render_template)

        await self.handler.show_buildset_details(b'some-buildset-id')

        expected_keys = ['content']
        called_template = self.handler.render_template.call_args[0][0]
        called_context = self.handler.render_template.call_args[0][1]
        self.assertTrue(self.handler._get_buildset_template.called)
        self.assertEqual(called_template, self.handler.skeleton_template)
        self.assertEqual(expected_keys, sorted(list(called_context.keys())))

    def test_show_build_details(self):
        self.handler._get_build_template = MagicMock(
            spec=self.handler._get_build_template)
        self.handler.render_template = MagicMock(
            spec=self.handler.render_template)

        self.handler.show_build_details(b'some-uuid')

        expected_keys = ['content']
        called_template = self.handler.render_template.call_args[0][0]
        called_context = self.handler.render_template.call_args[0][1]
        self.assertTrue(self.handler._get_build_template.called)
        self.assertEqual(called_template, self.handler.skeleton_template)
        self.assertEqual(expected_keys, sorted(list(called_context.keys())))

    def test_show_waterfall(self):
        self.handler._get_waterfall_template = MagicMock(
            spec=self.handler._get_waterfall_template)
        self.handler.render_template = MagicMock(
            spec=self.handler.render_template)

        self.handler.show_repo_waterfall(b'some/repo')

        expected_keys = ['content']
        called_template = self.handler.render_template.call_args[0][0]
        called_context = self.handler.render_template.call_args[0][1]
        self.assertTrue(self.handler._get_waterfall_template.called)
        self.assertEqual(called_template, self.handler.skeleton_template)
        self.assertEqual(expected_keys, sorted(list(called_context.keys())))

    def test_show_slave_details(self):
        self.handler._get_slave_template = MagicMock(
            spec=self.handler._get_slave_template)
        self.handler.render_template = MagicMock(
            spec=self.handler.render_template)

        self.handler.show_slave_details(b'someslave')

        expected_keys = ['content']
        called_template = self.handler.render_template.call_args[0][0]
        called_context = self.handler.render_template.call_args[0][1]
        self.assertTrue(self.handler._get_slave_template.called)
        self.assertEqual(called_template, self.handler.skeleton_template)
        self.assertEqual(expected_keys, sorted(list(called_context.keys())))

    def test_show_repo_add(self):
        self.handler._get_repository_template = MagicMock(
            spec=self.handler._get_repository_template)
        self.handler.render_template = MagicMock(
            spec=self.handler.render_template)

        self.handler.show_repo_add()

        expected_keys = ['content']
        called_template = self.handler.render_template.call_args[0][0]
        called_context = self.handler.render_template.call_args[0][1]
        self.assertTrue(self.handler._get_repository_template.called)
        self.assertEqual(called_template, self.handler.skeleton_template)
        self.assertEqual(expected_keys, sorted(list(called_context.keys())))

    def test_show_repository_details_template(self):
        self.handler._get_repository_template = MagicMock(
            spec=self.handler._get_repository_template)
        self.handler.write = MagicMock(spec=self.handler.write)

        self.handler.show_repository_details_template(b'full/name')
        self.assertTrue(self.handler._get_repository_template.called)
        self.assertTrue(self.handler.write.called)

    @patch.object(web.Repository, 'get', AsyncMagicMock(
        spec=web.Repository.get, return_value=MagicMock()))
    @async_test
    async def test_show_repository_notifications_template(self):
        self.handler._get_notifications_template = MagicMock(
            spec=self.handler._get_notifications_template)
        self.handler.write = MagicMock(spec=self.handler.write)

        await self.handler.show_repository_notifications_template(b'full/name')
        self.assertTrue(self.handler._get_notifications_template.called)
        self.assertTrue(self.handler.write.called)

    def test_show_slave_details_template(self):
        self.handler._get_slave_template = MagicMock(
            spec=self.handler._get_slave_template)
        self.handler.write = MagicMock(spec=self.handler.write)

        self.handler.show_slave_details_template()
        self.assertTrue(self.handler._get_slave_template.called)
        self.assertTrue(self.handler.write.called)

    def test_show_repo_buildset_list_template(self):
        self.handler._get_buildset_list_template = MagicMock(
            spec=self.handler._get_buildset_list_template)
        self.handler.write = MagicMock(spec=self.handler.write)

        self.handler.show_repo_buildset_list_template(b'some/repo')
        self.assertTrue(self.handler._get_buildset_list_template.called)
        self.assertTrue(self.handler.write.called)

    @patch.object(web.BuildSet, 'get', AsyncMagicMock(spec=web.BuildSet.get))
    @async_test
    async def test_show_buildset_template(self):
        self.handler._get_buildset_template = MagicMock(
            spec=self.handler._get_build_template)
        self.handler.write = MagicMock(spec=self.handler.write)

        await self.handler.show_buildset_template(b'some-buildset-id')
        self.assertTrue(self.handler._get_buildset_template.called)
        self.assertTrue(self.handler.write.called)

    def test_show_build_template(self):
        self.handler._get_build_template = MagicMock(
            spec=self.handler._get_build_template)
        self.handler.write = MagicMock(spec=self.handler.write)

        self.handler.show_build_template(b'some-uuid')
        self.assertTrue(self.handler._get_build_template.called)
        self.assertTrue(self.handler.write.called)

    def test_show_repo_waterfall_template(self):
        self.handler._get_waterfall_template = MagicMock(
            spec=self.handler._get_waterfall_template)
        self.handler.write = MagicMock(spec=self.handler.write)

        self.handler.show_repo_waterfall_template(b'some/repo')
        self.assertTrue(self.handler._get_waterfall_template.called)
        self.assertTrue(self.handler.write.called)
