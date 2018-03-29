# -*- coding: utf-8 -*-

import os
import asyncio
import atexit
from unittest.mock import MagicMock


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'functional', 'data')
MASTER_ROOT_DIR = os.path.join(DATA_DIR, 'master')


def async_test(f):

    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        coro = asyncio.coroutine(f)
        loop.run_until_complete(coro(*args, **kwargs))

    return wrapper


def close_loop():
    try:
        asyncio.get_event_loop().close()
    except (AttributeError, RuntimeError, SystemError):
        pass


atexit.register(close_loop)


class AsyncMagicMock(MagicMock):

    def __init__(self, *args, **kwargs):
        aiter_items = kwargs.pop('aiter_items', None)
        super().__init__(*args, **kwargs)
        self.aiter_items = aiter_items
        self._c = 0

    def __call__(self, *a, **kw):
        s = super().__call__(*a, **kw)

        async def ret():
            return s

        return ret()

    def __bool__(self):
        return True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc, exc_type, exc_tb):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.aiter_items:
            try:
                waste_time = type(self)()
                await waste_time()
                v = self.aiter_items[self._c]
                self._c += 1
            except IndexError:
                self._c = 0
                raise StopAsyncIteration
            return v
