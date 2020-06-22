# -*- coding: utf-8 -*-

import asyncio
import atexit

from toxicbuild.common.coordination import ToxicZKClient  # noqa: F402


def clean():
    loop = asyncio.get_event_loop()
    if ToxicZKClient._zk_client:
        try:
            loop.run_until_complete(ToxicZKClient._zk_client.close())
        except Exception:
            pass


atexit.register(clean)
