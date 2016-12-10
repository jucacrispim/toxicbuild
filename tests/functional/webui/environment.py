# -*- coding: utf-8 -*-

import asyncio
from toxicbuild.ui.models import Slave
from tests.functional import (start_slave, stop_slave, start_master,
                              stop_master, start_webui, stop_webui)
from tests.functional.webui import SeleniumBrowser


def create_browser(context):
    """Creates a new selenium browser using Chrome driver and
    sets it in the behave context.

    :param context: Behave's context."""
    context.browser = SeleniumBrowser()


def quit_browser(context):
    """Quits the selenium browser.

    :param context: Behave's context."""
    context.browser.quit()


@asyncio.coroutine
def del_slave(context):
    """Deletes the slave created in the tests"""

    try:
        slave = yield from Slave.get(slave_name='some-slave')
        yield from slave.delete()
    except:
        pass


def before_feature(context, feature):
    """Executed before every feature. It starts a slave, a master,
    a webui and creates a selenium browser.

    :param context: Behave's context.
    :param feature: The feature being executed."""

    start_slave()
    start_master()
    start_webui()
    create_browser(context)


def after_feature(context, feature):
    """Executed after every feature. It stops the webui, the master,
    the slave and quits the selenium browser.

    :param context: Behave's context.
    :param feature: The feature that was executed."""

    loop = asyncio.get_event_loop()
    loop.run_until_complete(del_slave(context))

    quit_browser(context)
    stop_webui()
    stop_master()
    stop_slave()
