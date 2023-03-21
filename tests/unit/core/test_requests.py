# -*- coding: utf-8 -*-

# Copyright 2016, 2023 Juca Crispim <juca@poraodojuca.net>

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

from unittest import TestCase
from unittest.mock import MagicMock, patch, AsyncMock
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
    headers = {}

    async def text(self):
        return 'some text'

    async def release(self):
        pass


class RequestsTest(TestCase):

    @patch.object(requests.aiohttp, 'ClientSession', MagicMock(
        return_value=MagicMock(close=AsyncMock())))
    @async_test
    async def test_request(self):
        method = 'GET'
        url = 'http://somewhere.com'

        async def req(method, url, **kwargs):
            return MockResponse()

        requests.aiohttp.ClientSession.return_value.request = req
        r = await requests._request(method, url)
        self.assertEqual(r.text, 'some text')

    @patch.object(requests.aiohttp, 'ClientSession', MagicMock(
        return_value=MagicMock(close=AsyncMock())))
    @async_test
    async def test_request_sesskw(self):
        method = 'GET'
        url = 'http://somewhere.com'

        requests.aiohttp.ClientSession.return_value.request = AsyncMock(
            return_value=AsyncMock(status=200, headers={}))
        await requests._request(method, url, sesskw={'a': 'thing',
                                                     'loop': MagicMock()})
        called_kw = requests.aiohttp.ClientSession.call_args[1]
        self.assertEqual(sorted(list(called_kw.keys())), ['a', 'loop'])

    @patch.object(requests, '_request', AsyncMock())
    @async_test
    async def test_get(self):
        url = 'http://somewhere.com'
        self.req_type = None

        async def req(method, url, **kw):
            self.req_type = method
            return requests.Response(200, 'some text')

        requests._request = req

        resp = await requests.get(url)
        self.assertEqual(self.req_type, 'GET')
        self.assertEqual(resp.text, 'some text')

    @patch.object(requests, '_request', AsyncMock())
    @async_test
    async def test_post(self):
        url = 'http://somewhere.com'
        self.req_type = None

        async def req(method, url, **kw):
            self.req_type = method
            return requests.Response(200, 'some text')

        requests._request = req

        resp = await requests.post(url)
        self.assertEqual(self.req_type, 'POST')
        self.assertEqual(resp.text, 'some text')

    @patch.object(requests, '_request', AsyncMock())
    @async_test
    async def test_put(self):
        url = 'http://somewhere.com'
        self.req_type = None

        async def req(method, url, **kw):
            self.req_type = method
            return requests.Response(200, 'some text')

        requests._request = req

        resp = await requests.put(url)
        self.assertEqual(self.req_type, 'PUT')
        self.assertEqual(resp.text, 'some text')

    @patch.object(requests, '_request', AsyncMock())
    @async_test
    async def test_delete(self):
        url = 'http://somewhere.com'
        self.req_type = None

        async def req(method, url, **kw):
            self.req_type = method
            return requests.Response(200, 'some text')

        requests._request = req

        resp = await requests.delete(url)
        self.assertEqual(self.req_type, 'DELETE')
        self.assertEqual(resp.text, 'some text')
