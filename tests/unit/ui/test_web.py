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
from toxicbuild.ui import web


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
        self.handler.request.arguments = {'url': 'bla@bla.com'}

        yield self.handler.get()

        called_args = self.mock_model.get.call_args[1]

        self.assertEqual(called_args, {'url': 'bla@bla.com'})

    @gen_test
    def test_add(self):
        kwargs = {'url': 'bla@bla.com',
                  'name': 'test'}
        yield from self.handler.add(**kwargs)

        self.assertTrue(self.mock_model.add.called)

    @gen_test
    def test_post(self):
        kwargs = {'url': 'bla@bla.com', 'name': 'test'}
        self.handler.request.arguments = kwargs

        yield self.handler.post()

        called_args = self.mock_model.add.call_args[1]

        self.assertEqual(called_args, kwargs)

    @gen_test
    def test_delete(self):
        item = MagicMock()

        @asyncio.coroutine
        def get_item(**kw):
            return item

        self.handler.get_item = get_item
        kwargs = {'name': 'some-repo'}
        self.handler.request.arguments = kwargs
        yield self.handler.delete()

        self.assertTrue(item.delete.called)


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

        self.assertEqual(handler.request.arguments, expected)

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
        yield self.handler.delete()
        self.assertIn('repo_name', self.handler.request.arguments)

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

        self.handler.request.arguments = {'name': 'myrepo',
                                          'branch': 'master'}
        yield from self.handler.start_build()
        self.assertTrue(sb_mock.called)

    @patch.object(web.BaseModelHandler, 'post', MagicMock())
    @gen_test
    def test_post_without_start_build(self):
        post_mock = MagicMock()
        web.BaseModelHandler.post = gen.coroutine(lambda *args: post_mock())
        yield self.handler.post()

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


class MainHandlerTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        request = MagicMock()
        application = MagicMock()
        self.handler = web.MainHandler(application, request=request)

    @patch.object(web, 'Repository', MagicMock())
    @patch.object(web, 'Slave', MagicMock())
    @patch.object(web, 'settings', MagicMock)
    @gen_test
    def test_get(self):
        web.settings.HOLE_HOST = 'localhost'
        web.settings.HOLE_PORT = 1234
        self.handler.render_template = MagicMock()

        expected_context = {'repos': None, 'slaves': None,
                            'get_btn_class': self.handler._get_btn_class,
                            'master_location': 'localhost:1234'}

        yield self.handler.get()
        context = self.handler.render_template.call_args[0][1]

        self.assertEqual(expected_context, context)

    def test_get_btn_class(self):
        status = 'fail'
        returned = self.handler._get_btn_class(status)

        self.assertEqual(returned, 'danger')


class ApplicationTest(unittest.TestCase):

    def test_urls(self):
        expected = ['/api/repo/(.*)$',
                    '/api/slave/(.*)$']

        for url in web.api_app.urls:
            pat = url.regex.pattern
            self.assertIn(pat, expected)

        self.assertEqual(len(web.api_app.urls), 2)
