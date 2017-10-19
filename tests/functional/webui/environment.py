# -*- coding: utf-8 -*-

import asyncio
from toxicbuild.master import create_settings_and_connect
from toxicbuild.slave import create_settings
from toxicbuild.ui import create_settings as create_settings_ui

# settings needed to the test data. This needs to be before the
# import from ui.models
create_settings()
create_settings_ui()
create_settings_and_connect()

from toxicbuild.ui.models import Slave, Repository  # noqa 402
from tests.functional import (start_slave, stop_slave,  # noqa 402
                              start_master,
                              stop_master, start_webui, stop_webui,
                              REPO_DIR)
from tests.functional.webui import SeleniumBrowser  # noqa 402


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
def create_slave(context):
    """Creates a slave to be used in repo tests"""

    yield from Slave.add(name='repo-slave', host='localhost', port=2222,
                         token='123')


@asyncio.coroutine
def del_slave(context):
    """Deletes the slaves created in the tests"""

    slaves = yield from Slave.list()
    for slave in slaves:
        yield from slave.delete()


@asyncio.coroutine
def create_repo(context):
    """Creates a new repo to be used in tests"""

    repo = yield from Repository.add(name='repo-bla', update_seconds=1,
                                     vcs_type='git', url=REPO_DIR,
                                     slaves=['repo-slave'])

    yield from repo.add_branch('master', False)


@asyncio.coroutine
def del_repo(context):
    """Deletes the repositories created in tests."""

    repos = yield from Repository.list()
    for repo in repos:
        yield from repo.delete()


def before_feature(context, feature):
    """Executed before every feature. It starts a slave, a master,
    a webui and creates a selenium browser.

    :param context: Behave's context.
    :param feature: The feature being executed."""

    start_slave()
    start_master()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_slave(context))
    start_webui()
    create_browser(context)
    if 'waterfall.feature' in feature.filename:
        loop.run_until_complete(create_repo(context))


def after_feature(context, feature):
    """Executed after every feature. It stops the webui, the master,
    the slave, quits the selenium browser and deletes data created in
    tests.

    :param context: Behave's context.
    :param feature: The feature that was executed."""

    loop = asyncio.get_event_loop()
    loop.run_until_complete(del_slave(context))
    loop.run_until_complete(del_repo(context))

    quit_browser(context)
    stop_webui()
    stop_master()
    stop_slave()
