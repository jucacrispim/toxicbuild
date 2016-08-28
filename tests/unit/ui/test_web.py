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
import unittest
from unittest.mock import MagicMock, patch
import tornado
from tornado import gen
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.ui import web, models, settings


@patch.object(web.LoggedTemplateHandler, 'redirect', MagicMock())
class BaseModelHandlerTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        request = MagicMock()
        application = MagicMock()

        class TestRepo(web.Repository):
            pass

        self.mock_model = TestRepo
        self.mock_model.get = MagicMock(spec=web.Repository.get)
        self.mock_model.add = MagicMock(spec=web.Repository.add)

        self.handler = web.BaseModelHandler(application, request=request,
                                            **{'model': self.mock_model})

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_get_item(self):

        yield from self.handler.get_item(id='123fsdf')

        self.assertTrue(self.mock_model.get.called)

    @gen_test
    def test_get(self):

        gi_mock = MagicMock()

        @asyncio.coroutine
        def gi(**kw):
            return gi_mock(**kw)

        self.handler.get_item = gi

        self.handler.request.arguments = {'url': [b'bla@bla.com']}
        self.handler.prepare()

        yield self.handler.get()

        called_args = gi_mock.call_args[1]

        self.assertEqual(called_args, {'url': ['bla@bla.com']})

    @gen_test
    def test_add(self):
        kwargs = {'url': 'bla@bla.com',
                  'name': 'test'}

        add_mock = MagicMock()

        @asyncio.coroutine
        def add(**kw):
            return add_mock()

        self.handler.model.add = add
        yield from self.handler.add(**kwargs)

        self.assertTrue(add_mock.called)

    @patch.object(web.BaseModelHandler, 'write', MagicMock())
    @gen_test
    def test_post(self):
        kwargs = {'url': [b'bla@bla.com'], 'name': [b'test']}
        expected = {k: [p.decode() for p in v] for k, v in kwargs.items()}
        self.handler.request.arguments = kwargs

        add_mock = MagicMock()

        @asyncio.coroutine
        def add(**kw):
            return add_mock(**kw)

        self.handler.model.add = add
        self.handler.prepare()
        yield self.handler.post()

        called_args = add_mock.call_args[1]

        self.assertEqual(called_args, expected)

    @gen_test
    def test_delete(self):
        item = MagicMock()

        @asyncio.coroutine
        def get_item(**kw):
            return item

        self.handler.get_item = get_item
        kwargs = {'name': [b'some-repo']}
        self.handler.request.arguments = kwargs
        self.handler.prepare()
        yield self.handler.delete()

        self.assertTrue(item.delete.called)


@patch.object(web.LoggedTemplateHandler, 'redirect', MagicMock())
class RepositoryHandlerTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        request = MagicMock()
        request.arguments = {'name': [b'myrepo'], 'url': [b'git@bla.com'],
                             'vcs_type': [b'git'], 'update_seconds': [b'10'],
                             'slaves': [b'someslave']}
        application = MagicMock()
        self.handler = web.RepositoryHandler(application, request=request,
                                             model=web.Repository)

    def test_prepare(self):
        request = MagicMock()
        request.arguments = {'name': [b'myrepo'], 'url': [b'git@bla.com'],
                             'vcs_type': [b'git'], 'update_seconds': [b'10'],
                             'slaves': [b'someslave']}
        expected = {'name': 'myrepo', 'url': 'git@bla.com', 'vcs_type': 'git',
                    'update_seconds': '10', 'slaves': ['someslave']}
        application = MagicMock()
        handler = web.RepositoryHandler(application, request=request,
                                        model=web.Repository)

        handler.prepare()

        self.assertEqual(handler.params, expected)

    def test_prepare_start_build(self):
        request = MagicMock()
        request.arguments = {'name': [b'myrepo'], 'branch': [b'master'],
                             'builder_name': [b'bla'],
                             'slaves': [b'slave1', b'slave2'], }
        expected = {'name': 'myrepo', 'branch': 'master',
                    'builder_name': 'bla', 'slaves': ['slave1', 'slave2']}
        application = MagicMock()
        handler = web.RepositoryHandler(application, request=request,
                                        model=web.Repository)
        handler.request.uri = 'localhost:8000/start-build'
        handler.prepare()
        self.assertEqual(handler.request.arguments, expected)

    @patch.object(web.BaseModelHandler, 'delete',
                  gen.coroutine(lambda x: None))
    @gen_test
    def test_delete(self, *args):
        self.handler.prepare()
        yield self.handler.delete()
        self.assertIn('repo_name', self.handler.params)

    @gen_test
    def test_put(self):
        kwargs = {'update_seconds': [b'bla@bla.com'],
                  'name': [b'test']}

        get_item_mock = MagicMock(return_value='ok')
        get_item_mock.update = asyncio.coroutine(
            lambda *a, **kw: get_item_mock())

        @asyncio.coroutine
        def gi(**kw):
            return get_item_mock

        self.handler.get_item = gi
        self.handler.request.arguments = kwargs
        self.handler.prepare()
        yield self.handler.put()
        self.assertTrue(get_item_mock.called)

    @gen_test
    def test_add_branch(self):
        kwargs = {'branch_name': [b'master'],
                  'notify_only_latest': [b'1'],
                  'name': [b'test']}

        self.handler.request.uri = 'http://bla.com/add-branch'
        get_item_mock = MagicMock(return_value='ok')
        get_item_mock.add_branch = asyncio.coroutine(
            lambda *a, **kw: get_item_mock())

        @asyncio.coroutine
        def gi(**kw):
            return get_item_mock

        self.handler.get_item = gi
        self.handler.request.arguments = kwargs

        self.handler.prepare()
        yield from self.handler.add_branch()
        self.assertTrue(get_item_mock.called)

    @gen_test
    def test_remove_branch(self):
        kwargs = {'branch_name': [b'master'],
                  'name': [b'test']}

        get_item_mock = MagicMock(return_value='ok')
        get_item_mock.remove_branch = asyncio.coroutine(
            lambda *a, **kw: get_item_mock())

        @asyncio.coroutine
        def gi(**kw):
            return get_item_mock

        self.handler.get_item = gi
        self.handler.request.uri = 'http://bla.com/remove-branch'
        self.handler.request.arguments = kwargs
        self.handler.prepare()
        yield from self.handler.remove_branch()
        self.assertTrue(get_item_mock.called)

    @gen_test
    def test_start_build(self):
        sb_mock = MagicMock()

        @asyncio.coroutine
        def sb(branch, builder_name=None, named_tree=None, slaves=[]):
            sb_mock()

        item = MagicMock()
        item.start_build = sb

        @asyncio.coroutine
        def gi(**kwargs):
            return item

        self.handler.get_item = gi

        self.handler.request.arguments = {'name': [b'myrepo'],
                                          'branch': [b'master']}
        self.handler.request.uri = 'http://bla.com/start-build'
        self.handler.prepare()
        yield from self.handler.start_build()
        self.assertTrue(sb_mock.called)

    @patch.object(web.BaseModelHandler, 'post', MagicMock())
    @gen_test
    def test_post_without_start_build(self):
        post_mock = MagicMock()
        web.BaseModelHandler.post = gen.coroutine(lambda *args: post_mock())
        yield self.handler.post()

        self.assertTrue(post_mock.called)

    @gen_test
    def test_post_with_add_branch(self):
        post_mock = MagicMock()
        self.handler.add_branch = asyncio.coroutine(lambda *args: post_mock())
        self.handler.request.uri = 'http://localhost:1235/add-branch'
        self.handler.prepare()
        yield self.handler.post('add-branch')

        self.assertTrue(post_mock.called)

    @gen_test
    def test_post_with_remove_branch(self):
        post_mock = MagicMock()
        self.handler.remove_branch = asyncio.coroutine(
            lambda *args: post_mock())
        self.handler.request.uri = 'http://localhost:1235/add-branch'
        self.handler.prepare()
        yield self.handler.post('remove-branch')

        self.assertTrue(post_mock.called)

    @patch.object(web.BaseModelHandler, 'post', MagicMock())
    @gen_test
    def test_post_start_build(self):
        post_mock = MagicMock()
        web.BaseModelHandler.post = asyncio.coroutine(
            lambda *args: post_mock())
        self.handler.request.arguments = {'name': [b'myrepo'],
                                          'branch': [b'master']}
        self.handler.request.uri = 'http://localhost:1235/start-build'
        self.handler.write = MagicMock()

        item = MagicMock()

        @asyncio.coroutine
        def gi(**kwargs):
            return item

        self.handler.get_item = gi

        self.handler.prepare()
        yield self.handler.post('start-build')

        self.assertFalse(post_mock.called)
        self.assertTrue(item.start_build.called)


@patch.object(web.LoggedTemplateHandler, 'redirect', MagicMock())
class SlaveHandlerTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        request = MagicMock()
        request.arguments = {'name': [b'myrepo'], 'host': [b'bla.com'],
                             'port': [b'1234']}
        application = MagicMock()
        self.handler = web.SlaveHandler(application, request=request,
                                        model=web.Repository)

    def test_prepare(self):
        expected = {'name': 'myrepo', 'host': 'bla.com', 'port': '1234',
                    'token': None}

        self.handler.prepare()

        self.assertEqual(expected, self.handler.params)

    @patch.object(web.BaseModelHandler, 'delete',
                  gen.coroutine(lambda x: None))
    @gen_test
    def test_delete(self, *args):
        self.handler.prepare()
        yield self.handler.delete()
        self.assertIn('slave_name', self.handler.params)

    @gen_test
    def test_put(self):
        kwargs = {'host': [b'localhost'],
                  'name': [b'name']}

        get_item_mock = MagicMock()

        @asyncio.coroutine
        def gi(**kw):
            return get_item_mock

        self.handler.get_item = gi
        self.handler.request.arguments = kwargs
        self.handler.prepare()
        yield self.handler.put()
        self.assertTrue(get_item_mock.update.called)


class MainHandlerTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        request = MagicMock()
        application = MagicMock()
        self.handler = web.MainHandler(application, request=request)

    @patch.object(web, 'Repository', MagicMock())
    @patch.object(web, 'Slave', MagicMock())
    @gen_test
    def test_get(self):
        self.handler.render_template = MagicMock()

        expected_context = {'repos': None, 'slaves': None,
                            'get_btn_class': self.handler._get_btn_class}

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
    @patch.object(web, 'Builder', MagicMock())
    @gen_test
    def test_get(self):
        web.Builder.list = asyncio.coroutine(lambda *a, **kw: [])

        self.handler.render_template = MagicMock()
        self.handler.prepare()

        expected_context = {'buildsets': None, 'builders': [],
                            'ordered_builds': None,
                            'get_ending': self.handler._get_ending}.keys()
        yield self.handler.get('some-repo')
        context = self.handler.render_template.call_args[0][1]
        self.assertEqual(expected_context, context.keys())

    @patch.object(web, 'Builder', MagicMock())
    @gen_test
    def test_get_builders_for_buildset(self):
        self._create_test_data()

        list_mock = MagicMock(return_value=self.builders)
        web.Builder.list = asyncio.coroutine(lambda *a, **kw: list_mock(**kw))

        expected = sorted(self.builders, key=lambda b: b.name)

        returned = yield from self.handler._get_builders_for_buildsets(
            self.buildsets)
        self.assertEqual(expected, returned)
        called_args = list_mock.call_args[1]

        expected = {'id__in': [b.id for b in self.builders]}
        self.assertEqual(expected, called_args)

    @patch.object(web, 'BuildSet', MagicMock())
    @patch.object(web, 'Builder', MagicMock())
    @gen_test
    def test_ordered_builds(self):
        bd0 = models.Builder(name='z', id=0)
        bd1 = models.Builder(name='a', id=1)
        builds = [models.Build(name='z', builder=bd0),
                  models.Build(name='a', builder=bd1)]

        list_mock = MagicMock(return_value=[bd0, bd1])
        web.Builder.list = asyncio.coroutine(lambda *a, **kw: list_mock(**kw))

        self.handler._get_builders_for_buildsets = asyncio.coroutine(
            lambda b: [bd0, bd1])
        self.handler.render_template = MagicMock()
        ordered = yield self.handler.get('some-repo')
        order_func = self.handler.render_template.call_args[0][1][
            'ordered_builds']
        ordered = order_func(builds)
        self.assertTrue(ordered[0].builder.name < ordered[1].builder.name)

    def test_get_ending(self):
        builders = [models.Builder(id=1), models.Builder(id=2)]
        build = models.Build(builder=builders[1])
        expected = '</td><td>'
        returned = ''

        for end in self.handler._get_ending(build, 0, builders):
            returned += end

        self.assertEqual(expected, returned)

    def _create_test_data(self):
        builders = []
        for i in range(3):
            builders.append(models.Builder(id=i, name='bla{}'.format(i)))

        buildsets = []

        for i in range(5):

            builds = [models.Build(id=j, builder=builders[j])
                      for j in range(3)]
            buildsets.append(models.BuildSet(id=i, builds=builds))

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


class LoginHandlerTest(unittest.TestCase):

    def setUp(self):
        super().setUp()
        request = MagicMock()
        request.cookies = {}
        application = MagicMock()
        application.settings = {'cookie_secret': 'bladjfçajf'}

        class TestRepo(web.Repository):
            pass

        self.mock_model = TestRepo
        self.mock_model.get = MagicMock(spec=web.Repository.get)
        self.mock_model.add = MagicMock(spec=web.Repository.add)

        self.handler = web.LoginHandler(application, request=request)

    @patch.object(web.TemplateHandler, 'redirect', MagicMock(
        spec=web.TemplateHandler.redirect))
    def test_get_with_cookie(self):
        self.handler.set_secure_cookie(web.COOKIE_NAME, 'bla')
        self.handler.request.cookies[
            web.COOKIE_NAME] = self.handler._new_cookie[web.COOKIE_NAME]
        self.handler.get('login')
        self.assertTrue(self.handler.redirect.called)
        url = self.handler.redirect.call_args[0][0]
        self.assertEqual(url, '/')

    @patch.object(web.TemplateHandler, 'render_template', MagicMock(
        spec=web.TemplateHandler.render_template))
    def test_get_without_cookie(self):
        self.handler.get('login')
        self.assertTrue(self.handler.render_template.called)
        template = self.handler.render_template.call_args[0][0]
        self.assertEqual(template, 'login.html')

    @patch.object(web.TemplateHandler, 'redirect', MagicMock(
        spec=web.TemplateHandler.redirect))
    @patch.object(web.TemplateHandler, 'clear_cookie', MagicMock(
        spec=web.TemplateHandler.clear_cookie))
    def test_get_logout(self):
        self.handler.get('logout')
        self.assertTrue(self.handler.clear_cookie.called)
        self.assertTrue(self.handler.redirect.called)
        url = self.handler.redirect.call_args[0][0]
        self.assertEqual(url, '/')

    @patch.object(web.TemplateHandler, 'redirect', MagicMock(
        spec=web.TemplateHandler.redirect))
    def test_post_with_bad_username(self):
        self.handler.prepare()
        self.handler.params['username'] = ['mané']
        self.handler.post()
        url = self.handler.redirect.call_args[0][0]
        self.assertEqual(url, '/login?error=1')

    @patch.object(web.TemplateHandler, 'redirect', MagicMock(
        spec=web.TemplateHandler.redirect))
    def test_post_with_bad_password(self):
        self.handler.prepare()
        self.handler.params['username'] = ['someguy']
        self.handler.params['password'] = ['wrong']
        self.handler.post()
        url = self.handler.redirect.call_args[0][0]
        self.assertEqual(url, '/login?error=1')

    @patch.object(web.TemplateHandler, 'set_secure_cookie', MagicMock(
        spec=web.TemplateHandler.set_secure_cookie))
    def test_post_ok(self):
        self.handler.prepare()
        self.handler.params['username'] = ['someguy']
        self.handler.params['password'] = ['123']
        self.handler.post()
        self.assertTrue(self.handler.set_secure_cookie.called)


class LoggedTemplateHandler(unittest.TestCase):

    def setUp(self):
        super().setUp()
        request = MagicMock()
        request.cookies = {}
        application = MagicMock()
        application.settings = {'cookie_secret': 'bladjfçajf'}

        class TestRepo(web.Repository):
            pass

        self.mock_model = TestRepo
        self.mock_model.get = MagicMock(spec=web.Repository.get)
        self.mock_model.add = MagicMock(spec=web.Repository.add)

        self.handler = web.LoggedTemplateHandler(application, request=request)

    @patch.object(web.TemplateHandler, 'redirect', MagicMock(
        spec=web.TemplateHandler.redirect))
    def test_prepare_without_cookie(self):
        self.handler.prepare()
        url = self.handler.redirect.call_args[0][0]
        self.assertEqual(url, '/login')

    @patch.object(web.TemplateHandler, 'redirect', MagicMock(
        spec=web.TemplateHandler.redirect))
    def test_prepare_with_cookie(self):
        self.handler.set_secure_cookie(web.COOKIE_NAME, 'bla')
        self.handler.request.cookies[
            web.COOKIE_NAME] = self.handler._new_cookie[web.COOKIE_NAME]
        self.handler.prepare()
        self.assertFalse(self.handler.redirect.called)
