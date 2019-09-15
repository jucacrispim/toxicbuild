# -*- coding: utf-8 -*-

import asyncio
import atexit

from toxicbuild.common.coordination import ToxicZKClient  # noqa: F402


def clean():
    loop = asyncio.get_event_loop()
    if ToxicZKClient._zk_client:
        loop.run_until_complete(ToxicZKClient._zk_client.close())


atexit.register(clean)
