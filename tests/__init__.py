# -*- coding: utf-8 -*-

import asyncio
import atexit
from unittest.mock import MagicMock


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

    def __call__(self, *a, **kw):
        s = super().__call__(*a, **kw)

        async def ret():
            return s

        return ret()

    def __bool__(self):
        return True


AsyncMagicMock.__aenter__ = AsyncMagicMock()
#AsyncMagicMock.__aexit__ = AsyncMagicMock()
#AsyncMagicMock.__bool__ = lambda: True
