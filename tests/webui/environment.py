# -*- coding: utf-8 -*-

import asyncio
import os
from toxicbuild.core.utils import log
from toxicbuild.master import create_settings_and_connect
from toxicbuild.slave import create_settings
from toxicbuild.ui import create_settings as create_settings_ui
from toxicbuild.output import (
    create_settings_and_connect as create_settings_output)
from tests.functional import (REPO_DIR,
                              SLAVE_ROOT_DIR, MASTER_ROOT_DIR, UI_ROOT_DIR,
                              OUTPUT_ROOT_DIR)

# settings needed to the test data. This needs to be before the
# import from ui.models

toxicmaster_conf = os.environ.get('TOXICMASTER_SETTINGS')
if not toxicmaster_conf:
    toxicmaster_conf = os.path.join(MASTER_ROOT_DIR, 'toxicmaster.conf')
    os.environ['TOXICMASTER_SETTINGS'] = toxicmaster_conf

toxicslave_conf = os.environ.get('TOXICSLAVE_SETTINGS')
if not toxicslave_conf:
    toxicslave_conf = os.path.join(SLAVE_ROOT_DIR, 'toxicslave.conf')
    os.environ['TOXICSLAVE_SETTINGS'] = toxicslave_conf

toxicweb_conf = os.environ.get('TOXICUI_SETTINGS')
if not toxicweb_conf:
    toxicweb_conf = os.path.join(UI_ROOT_DIR, 'toxicui.conf')
    os.environ['TOXICUI_SETTINGS'] = toxicweb_conf

toxicoutput_conf = os.environ.get('TOXICOUTPUT_SETTINGS')
if not toxicoutput_conf:
    toxicoutput_conf = os.path.join(OUTPUT_ROOT_DIR, 'toxicoutput.conf')
    os.environ['TOXICOUTPUT_SETTINGS'] = toxicoutput_conf

create_settings()
create_settings_ui()
create_settings_and_connect()
create_settings_output()

from toxicbuild.master.exchanges import scheduler_action  # noqa f402
from toxicbuild.ui import settings  # noqa f402
from toxicbuild.master.users import User  # noqa f402
from toxicbuild.ui.models import Slave, Repository  # noqa 402
from tests.functional import (start_slave, stop_slave,  # noqa 402
                              start_master, stop_master,
                              start_poller, stop_poller,
                              start_scheduler, stop_scheduler,
                              start_output, stop_output,
                              start_webui, stop_webui,
                              REPO_DIR)
from tests.webui import SeleniumBrowser  # noqa 402


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

    yield from Slave.add(context.user, name='repo-slave', host='localhost',
                         owner=context.user,
                         port=2222,
                         token='123',
                         use_ssl=True,
                         validate_cert=False)


@asyncio.coroutine
def del_slave(context):
    """Deletes the slaves created in the tests"""

    slaves = yield from Slave.list(context.user)
    for slave in slaves:
        try:
            yield from slave.delete()
        except Exception as e:
            log('Error deleting slave ' + str(e), level='warning')


@asyncio.coroutine
def create_repo(context):
    """Creates a new repo to be used in tests"""

    yield from scheduler_action.connection.connect()
    yield from scheduler_action.declare()

    repo = yield from Repository.add(context.user,
                                     name='repo-bla', update_seconds=1,
                                     owner=context.user,
                                     vcs_type='git', url=REPO_DIR,
                                     slaves=['repo-slave'])

    yield from repo.add_branch('master', False)


async def create_user(context):
    user = User(email='someguy@bla.com', is_superuser=True)
    user.set_password('123')
    await user.save()
    context.user = user
    context.user.id = str(context.user.id)


async def del_user(context):
    await context.user.delete()


@asyncio.coroutine
def del_repo(context):
    """Deletes the repositories created in tests."""

    repos = yield from Repository.list(context.user)
    for repo in repos:
        try:
            yield from repo.delete()
            yield from scheduler_action.declare()
            yield from scheduler_action.queue_delete()
            yield from scheduler_action.connection.disconnect()
        except Exception as e:
            log('Error deleting repo ' + str(e), level='warning')

    from toxicbuild.master.repository import Repository as RepoModel

    yield from RepoModel.drop_collection()


async def create_root_user(context):
    user = User(id=settings.ROOT_USER_ID, username='already-exists',
                email='nobody@nowhere.nada', allowed_actions=['add_user'])
    await user.save()


def before_all(context):
    start_slave()
    start_poller()
    start_scheduler()
    start_output()
    start_master()
    start_webui()

    create_browser(context)

    async def create(context):
        await create_user(context)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(create(context))


def before_feature(context, feature):
    """Executed before every feature. It starts a slave, a master,
    a webui and creates a selenium browser.

    :param context: Behave's context.
    :param feature: The feature being executed."""

    async def create(context):
        await create_slave(context)

        if 'waterfall.feature' in feature.filename or \
           'notifications.feature' in feature.filename:
            await create_repo(context)

        elif 'register.feature' in feature.filename:
            await create_root_user(context)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(create(context))


def after_feature(context, feature):
    """Executed after every feature. It stops the webui, the master,
    the slave, quits the selenium browser and deletes data created in
    tests.

    :param context: Behave's context.
    :param feature: The feature that was executed."""

    async def delete(context):
        await del_slave(context)
        await del_repo(context)
        await User.drop_collection()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(delete(context))


def before_scenario(context, scenario):
    if scenario.name == 'A user cancels a build':
        # we stop the slave so we can be sure the build is pending
        # when we try to cancel it
        stop_slave()


def after_scenario(context, scenario):
    if scenario.name == 'A user cancels a build':
        # starting it for the other tests, if any
        start_slave()


def after_all(context):

    stop_webui()
    stop_output()
    stop_scheduler()
    stop_poller()
    stop_master()
    stop_slave()

    async def delete(context):
        await del_user(context)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(delete(context))

    quit_browser(context)
