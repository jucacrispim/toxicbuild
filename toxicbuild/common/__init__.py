# -*- coding: utf-8 -*-

from .interfaces import BaseInterface
from .exchanges import conn, declare


async def common_setup(settings):
    BaseInterface.settings = settings
    await conn.connect(**settings.RABBITMQ_CONNECTION)
    await declare()
