# -*- coding: utf-8 -*-

# Copyright 2016 Juca Crispim <juca@poraodojuca.net>

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
from toxicbuild.core import requests
from tests import async_test


class ResponseTest(TestCase):

    def test_response(self):
        resp = requests.Response(200, 'some text')
        self.assertEqual(resp.text, 'some text')

    def test_json(self):
        resp = requests.Response(200, requests.json.dumps({'some': 'json'}))
        self.assertTrue(resp.json())


class MockResponse:

    status = 200

    @asyncio.coroutine
    def text(self):
        return 'some text'

    @asyncio.coroutine
    def release(self):
        pass


class RequestsTest(TestCase):

    @patch.object(requests.aiohttp, 'ClientSession', MagicMock())
    @async_test
    def test_request(self):
        method = 'GET'
        url = 'http://somewhere.com'

        @asyncio.coroutine
        def req(method, url, **kwargs):
            return MockResponse()

        requests.aiohttp.ClientSession.return_value.request = req
        r = yield from requests._request(method, url)
        self.assertEqual(r.text, 'some text')

    @patch.object(requests, '_request', MagicMock())
    @async_test
    def test_get(self):
        url = 'http://somewhere.com'
        self.req_type = None

        @asyncio.coroutine
        def req(method, url, **kw):
            self.req_type = method
            return requests.Response(200, 'some text')

        requests._request = req

        resp = yield from requests.get(url)
        self.assertEqual(self.req_type, 'GET')
        self.assertEqual(resp.text, 'some text')

    @patch.object(requests, '_request', MagicMock())
    @async_test
    def test_post(self):
        url = 'http://somewhere.com'
        self.req_type = None

        @asyncio.coroutine
        def req(method, url, **kw):
            self.req_type = method
            return requests.Response(200, 'some text')

        requests._request = req

        resp = yield from requests.post(url)
        self.assertEqual(self.req_type, 'POST')
        self.assertEqual(resp.text, 'some text')

    @patch.object(requests, '_request', MagicMock())
    @async_test
    def test_put(self):
        url = 'http://somewhere.com'
        self.req_type = None

        @asyncio.coroutine
        def req(method, url, **kw):
            self.req_type = method
            return requests.Response(200, 'some text')

        requests._request = req

        resp = yield from requests.put(url)
        self.assertEqual(self.req_type, 'PUT')
        self.assertEqual(resp.text, 'some text')

    @patch.object(requests, '_request', MagicMock())
    @async_test
    def test_delete(self):
        url = 'http://somewhere.com'
        self.req_type = None

        @asyncio.coroutine
        def req(method, url, **kw):
            self.req_type = method
            return requests.Response(200, 'some text')

        requests._request = req

        resp = yield from requests.delete(url)
        self.assertEqual(self.req_type, 'DELETE')
        self.assertEqual(resp.text, 'some text')
