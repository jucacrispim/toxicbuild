# -*- coding: utf-8 -*-
# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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

import asyncio
from toxicbuild.master.users import User
from tests.webui import SeleniumBrowser
from tests.webui.environment import create_root_user
from tests.integrations_functional import start_all, stop_all


def create_browser(context):
    """Creates a new selenium browser using Chrome driver and
    sets it in the behave context.

    :param context: Behave's context."""
    context.browser = SeleniumBrowser()


def quit_browser(context):
    """Quits the selenium browser.

    :param context: Behave's context."""
    context.browser.quit()


async def del_repo(context):
    """Deletes the repositories created in tests."""

    from toxicbuild.master.exchanges import scheduler_action

    await scheduler_action.declare()
    await scheduler_action.queue_delete()
    await scheduler_action.connection.disconnect()

    from toxicbuild.master.repository import Repository as RepoModel

    await RepoModel.drop_collection()


async def create_user(context):
    user = User(email='someguy@bla.com', is_superuser=True)
    user.set_password('123')
    await user.save()
    context.user = user
    context.user.id = str(context.user.id)


async def del_user(context):
    await context.user.delete()


def before_all(context):
    start_all()

    create_browser(context)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_user(context))
    loop.run_until_complete(create_root_user(context))


def after_feature(context, feature):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(del_repo(context))

    from toxicbuild.integrations.github import GithubIntegration
    loop.run_until_complete(GithubIntegration.drop_collection())
    loop.run_until_complete(User.drop_collection())


def after_all(context):
    stop_all()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(del_user(context))

    quit_browser(context)
