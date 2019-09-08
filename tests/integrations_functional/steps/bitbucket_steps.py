# -*- coding: utf-8 -*-
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbulid.

# toxicbulid is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbulid is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbulid. If not, see <http://www.gnu.org/licenses/>.

from behave import when, then, given

from toxicbuild.integrations import settings


@when('clicks in the bitbucket import repos button')
def click_bitbucket_import(context):
    browser = context.browser
    btn = browser.wait_element_become_present(
        lambda: browser.find_element_by_class_name('fa-bitbucket'))
    btn.click()


@then('he is sent to the bitbucket login page')
@given('the user is in the bitbucket login page')
def is_in_bitbucket_login_page(context):
    browser = context.browser
    el = browser.find_element_by_id('username')

    assert el


@when('he fills the bitbucket username field')
def fill_username(context):
    browser = context.browser
    el = browser.find_element_by_id('username')
    el.send_keys(settings.BITBUCKET_USER)
    btn = browser.find_element_by_id('login-submit')
    btn.click()


@when('fills the bitbucket password field')
def fill_passwd(context):
    browser = context.browser
    el = browser.wait_element_become_present(
        lambda: browser.find_element_by_id('password'))
    el.send_keys(settings.BITBUCKET_PASSWD)


@when('clicks in the bitbucket login button')
def click_login_btn(context):
    browser = context.browser
    btn = browser.find_element_by_id('login-submit')
    btn.click()


@then('his repositories beeing imported from bitbucket')
def user_sees_repositories_imported(context):
    browser = context.browser

    def fn():
        repo_row = browser.wait_text_become_present('toxic-bbtest',
                                                    timeout=1)
        return bool(repo_row)

    r = browser.refresh_until(fn)
    assert r
    browser.get(settings.TOXICUI_URL + 'logout')
