# -*- coding: utf-8 -*-
# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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

from behave import given, when, then
from toxicbuild.integrations import settings
from tests.functional.webui.steps.authentication_steps import (  # noqa F401
    user_inserts_password_login, user_inserts_username_login,
    user_clicks_login_button, user_sees_main_main_page_login)


@given('the user is sent to the setup url by github')
def user_redirected_from_githbu(context):
    # Here we assume github redirected us correctly and
    # we simply access the setup page.
    browser = context.browser
    browser.get(settings.GITHUB_SETUP_URL)


@when('he is redirected to the login page')
def user_redirected_to_main_page(context):
    browser = context.browser
    login = browser.find_element_by_class_name('login-container')
    assert login


@then('his repositories beeing imported from github')
def user_sees_repositories_imported(context):
    browser = context.browser
    repo_row = browser.wait_text_become_present('toxic-ghintegration-test')
    assert repo_row
