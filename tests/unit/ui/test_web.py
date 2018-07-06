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
import unittest
from unittest import TestCase
from unittest.mock import MagicMock, patch
import tornado
from tornado import gen
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
        request = MagicMock()
        request.cookies = {}
        application = MagicMock()
        application.settings = {'cookie_secret': 'bladjfçajf'}
        self.handler = web.CookieAuthHandlerMixin(application, request=request)

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
        args = {'id':  [b'123']}
        self.handler.request.arguments = args
        await self.handler.async_prepare()
        client = models.Repository.get_client.return_value
        client.__enter__.return_value.repo_get = AsyncMagicMock()
        client.__enter__.return_value.repo_get.return_value = {'id': '123',
                                                               'name': 'something'}
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
    async def test_enable_plugin(self):
        self.handler.body = {'plugin_name': 'someplugin',
                             'param1': 'value1'}
        r = await self.handler.enable_plugin()
        self.assertTrue(r)

    @patch.object(web.Repository, 'get', AsyncMagicMock(
        spec=web.Repository.get,
        return_value=create_autospec(spec=web.Repository,
                                     mock_cls=AsyncMagicMock)))
    @async_test
    async def test_disable_plugin(self):
        self.handler.body = {'plugin_name': 'someplugin'}
        r = await self.handler.disable_plugin()
        self.assertTrue(r)

    @patch.object(web.Plugin, 'list', AsyncMagicMock(
        spec=web.Plugin.list,
        return_value=[MagicMock(), MagicMock()]))
    @async_test
    async def test_list_plugins(self):
        self.handler.body = {'plugin_name': 'someplugin'}
        r = await self.handler.list_plugins()
        self.assertEqual(len(r['items']), 2)

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

    def test_get_repo_id(self):
        self.handler.request.arguments = {'repo_id': [b'asdf']}
        repo_id = self.handler._get_repo_id()
        self.assertEqual(repo_id, 'asdf')

    def test_get_repo_id_with_repository_id(self):
        self.handler.request.arguments = {'repository_id': [b'asdf']}
        repo_id = self.handler._get_repo_id()
        self.assertEqual(repo_id, 'asdf')

    def test_get_repo_id_type_error(self):
        repo_id = self.handler._get_repo_id()
        self.assertIsNone(repo_id)

    @patch.object(web, 'StreamConnector', MagicMock())
    @gen_test
    def test_open(self):
        self.handler.request.arguments = {'repo_id': [b'asdf']}
        plug = MagicMock()
        web.StreamConnector.plug = asyncio.coroutine(lambda *a, **kw: plug())
        self.handler.prepare()
        f = self.handler.open('repo-status')
        yield from f
        self.assertTrue(plug.called)
        self.assertTrue(self.handler.repo_id)
        self.assertEqual(self.handler.action, 'repo-status')

    @gen_test
    def test_bad_message_type_logger(self):
        self.handler.log = MagicMock()
        self.handler._bad_message_type_logger(
            {'event_type': 'unknown'})
        self.assertTrue(self.handler.log.called)

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

    @gen_test
    def test_receiver_wrong_action(self):
        sender = MagicMock()
        message = {'event_type': 'build_started'}
        sbi = MagicMock()

        self.handler._send_build_info = sbi

        self.handler.events['build_started'] = self.handler._send_build_info
        self.handler.action = 'build-step'
        self.handler.receiver(sender, **message)
        yield from asyncio.sleep(0.001)
        self.assertFalse(sbi.called)

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
                             'created': '3 9 25 08:53:44 2017 -0000'}}
        self.handler._format_info_dt(info)
        self.assertFalse(info['buildset']['created'].endswith('0000'))
        self.assertFalse(info['buildset']['started'].endswith('0000'))

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
        self.handler.prepare()
        self.handler.on_close()
        self.assertTrue(web.StreamConnector.unplug.called)

    def test_send_step_output_info(self):
        self.handler.request.arguments = {
            'uuid': ['sfdaf1'.encode('utf-8')]}

        info = {'uuid': 'sfdaf1'}
        self.handler.write2sock = MagicMock()
        self.handler._send_step_output_info(info)
        self.assertTrue(self.handler.write2sock.called)

    def test_send_step_output_info_wrong_uuid(self):
        self.handler.request.arguments = {
            'uuid': ['sfdafs1'.encode('utf-8')]}

        info = {'uuid': 'sfdaf1'}
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


class MainHandlerTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        request = MagicMock()
        application = MagicMock()
        application.settings = {'cookie_secret': 'bladjfçajf'}
        self.handler = web.MainHandler(application, request=request)

    @patch.object(web.Repository, 'list', MagicMock())
    @patch.object(web, 'Slave', MagicMock())
    @patch.object(web, 'Plugin', MagicMock())
    @gen_test
    def test_get(self):
        self.handler.render_template = MagicMock()

        content = web.base64.encodebytes(web.json.dumps(
            {'id': 'asdf',
             'email': 'a@a.com',
             'username': 'zé'}).encode('utf-8'))
        self.handler.set_secure_cookie(web.COOKIE_NAME, content)
        self.handler.request.cookies = {}
        self.handler.request.cookies[
            web.COOKIE_NAME] = self.handler._new_cookie[web.COOKIE_NAME]

        expected_context = {'repos': None, 'slaves': None, 'plugins': None,
                            'get_btn_class': self.handler._get_btn_class,
                            'github_import_url': '#'}
        self.handler.prepare()
        yield self.handler.get()
        context = self.handler.render_template.call_args[0][1]

        self.assertEqual(expected_context, context)

    def test_get_btn_class(self):
        status = 'fail'
        returned = self.handler._get_btn_class(status)

        self.assertEqual(returned, 'danger')


@patch.object(web.LoggedTemplateHandler, 'redirect', MagicMock())
class WaterfallHandlerTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        request = MagicMock()
        application = MagicMock()
        self.handler = web.WaterfallHandler(application, request=request)

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @patch.object(web, 'BuildSet', MagicMock())
    @patch.object(web, 'Repository', MagicMock())
    @patch.object(web, 'get_builders_for_buildsets', AsyncMagicMock())
    @gen_test
    def test_get(self):
        self.handler.render_template = MagicMock()
        self.handler.prepare()

        expected_context = {'buildsets': None, 'builders': [],
                            'ordered_builds': None,
                            'repository': 'repo',
                            'fmtdt': lambda: None,
                            'get_ending': self.handler._get_ending}.keys()
        yield self.handler.get('some-repo')
        context = self.handler.render_template.call_args[0][1]
        self.assertEqual(expected_context, context.keys())

    @patch.object(models.Builder, 'list', MagicMock())
    @gen_test
    def test_get_builders_for_buildset(self):
        self._create_test_data()

        list_mock = MagicMock(return_value=self.builders)
        models.Builder.list = asyncio.coroutine(lambda *a, **kw: list_mock(
            **kw))

        expected = sorted(self.builders, key=lambda b: b.name)

        self.handler.prepare()
        returned = yield from self.handler._get_builders_for_buildsets(
            self.buildsets)
        self.assertEqual(expected, returned)
        called_args = list_mock.call_args[1]

        expected = {'id__in': [b.id for b in self.builders]}
        self.assertEqual(expected, called_args)

    @patch.object(web, 'BuildSet', MagicMock())
    @patch.object(models.Builder, 'list', MagicMock())
    @patch.object(web, 'Repository', MagicMock())
    @gen_test
    def test_ordered_builds(self):
        requester = MagicMock()
        bd0 = models.Builder(requester, dict(name='z', id=0))
        bd1 = models.Builder(requester, dict(name='a', id=1))
        builds = [models.Build(requester, dict(name='z', builder=bd0)),
                  models.Build(requester, dict(name='a', builder=bd1))]

        list_mock = MagicMock(return_value=[bd0, bd1])
        models.Builder.list = asyncio.coroutine(lambda *a, **kw: list_mock(
            **kw))

        self.handler._get_builders_for_buildsets = asyncio.coroutine(
            lambda b: [bd0, bd1])
        self.handler.render_template = MagicMock()
        self.handler.prepare()
        ordered = yield self.handler.get('some-repo')
        order_func = self.handler.render_template.call_args[0][1][
            'ordered_builds']
        ordered = order_func(builds)
        self.assertTrue(ordered[0].builder.name < ordered[1].builder.name)

    def test_get_ending(self):
        requester = MagicMock()
        builders = [models.Builder(requester, dict(id=1)),
                    models.Builder(requester, dict(id=2))]
        build = models.Build(requester, dict(builder=builders[1]))
        expected = '</td><td class="builder-column builder-column-id-1'
        expected += ' builder-column-index-1">'
        returned = ''

        for end in self.handler._get_ending(build, 0, builders):
            returned += end

        self.assertEqual(expected, returned)

    def _create_test_data(self):
        requester = MagicMock()
        builders = []
        for i in range(3):
            kw = dict(id=i, name='bla{}'.format(i))
            builders.append(models.Builder(requester, kw))

        buildsets = []

        for i in range(5):
            builds = [models.Build(requester, dict(id=j, builder=builders[j]))
                      for j in range(3)]
            kw = dict(id=i, builds=builds)
            buildsets.append(models.BuildSet(requester, kw))

        self.builders = builders
        self.buildsets = buildsets


class ApplicationTest(unittest.TestCase):

    def test_urls(self):
        expected = ['/api/repo/(.*)$',
                    '/api/slave/(.*)$']

        for url in web.api_app.urls:
            pat = url.regex.pattern
            self.assertIn(pat, expected)

        self.assertEqual(len(web.api_app.urls), 2)
