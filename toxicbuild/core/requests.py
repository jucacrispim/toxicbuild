# -*- coding: utf-8 -*-
"""This module implements a simple asynchronous interface for
http requests.

Usage:
------

.. code-block:: python

    from toxicbuild.core import requests
    response = yield from requests.get('http://google.com/')
    print(response.text)
"""

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
import aiohttp


class Response:
    """Encapsulates a response from a http request"""

    def __init__(self, status, text):
        """Constructor for Response.

        :param status: The response status.
        :param text: The response text."""
        self.status = status
        self.text = text


@asyncio.coroutine
def _request(method, url, **kwargs):
    """Performs a http request and returns an instance of
    :class:`toxicbuild.core.requests.Response`

    :param method: The requrest's method.
    :param url: Request's url.
    :param kwargs: Arguments passed to aiohttp.ClientSession.request
        method.
    """

    loop = asyncio.get_event_loop()

    client = aiohttp.ClientSession(loop=loop)
    try:
        resp = yield from client.request(method, url, **kwargs)
        status = resp.status
        text = yield from resp.text()
        yield from resp.release()
    finally:
        client.close()

    return Response(status, text)


@asyncio.coroutine
def get(url, **kwargs):
    """Performs a http GET request

    :param url: Request's url.
    :param kwargs: Args passed to :func:`toxicbuild.core.requests._request`.
    """

    method = 'GET'
    resp = yield from _request(method, **kwargs)
    return resp


@asyncio.coroutine
def post(url, **kwargs):
    """Performs a http POST request

    :param url: Request's url.
    :param kwargs: Args passed to :func:`toxicbuild.core.requests._request`.
    """

    method = 'POST'
    resp = yield from _request(method, **kwargs)
    return resp


@asyncio.coroutine
def put(url, **kwargs):
    """Performs a http PUT request

    :param url: Request's url.
    :param kwargs: Args passed to :func:`toxicbuild.core.requests._request`.
    """

    method = 'PUT'
    resp = yield from _request(method, **kwargs)
    return resp


@asyncio.coroutine
def delete(url, **kwargs):
    """Performs a http DELETE request

    :param url: Request's url.
    :param kwargs: Args passed to :func:`toxicbuild.core.requests._request`.
    """

    method = 'DELETE'
    resp = yield from _request(method, **kwargs)
    return resp
