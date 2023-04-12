# -*- coding: utf-8 -*-
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

from behave import when, then, given

from toxicbuild.integrations import settings


@when('he goes to the repository settings interface')
def go_repo_settings_page(context):
    browser = context.browser
    browser.get(settings.TOXICUI_URL + 'settings/repositories')


@when('clicks in the gitlab import repos button')
def click_gitlab_import(context):
    browser = context.browser
    btn = browser.wait_element_become_present(
        lambda: browser.find_element_by_class_name('fa-gitlab'))
    btn.click()


@then('he is sent to the gitlab login page')
@given('the user is in the gitlab login page')
def is_in_gitlab_login_page(context):
    browser = context.browser
    el = browser.find_element_by_id('user_login')

    assert el


@when('he fills the gitlab username field')
def fill_username(context):
    browser = context.browser
    el = browser.find_element_by_id('user_login')
    el.send_keys(settings.GITLAB_USER)


@when('fills the gitlab password field')
def fill_passwd(context):
    browser = context.browser
    el = browser.find_element_by_id('user_password')
    el.send_keys(settings.GITLAB_PASSWD)


@when('clicks in the accept cookies button')
def accept_cookies(context):
    browser = context.browser

    def fn():
        el = browser.find_element_by_id('onetrust-accept-btn-handler')
        return el

    el = browser.wait_element_become_present(fn)
    el.click()


@when('clicks in the gitlab login button')
def click_login_btn(context):
    browser = context.browser
    el = browser.find_element_by_class_name('js-sign-in-button')
    el.click()


# @then('he sees the gitlab authorize page')
# @given('the user is in the gitlab authorization page')
# def is_in_authorize_page(context):
#     browser = context.browser
#     browser.wait_text_become_present('Authorize')


# @when('he clicks in the authorize button')
# def click_authorize_btn(context):
#     browser = context.browser
#     btn = browser.find_element_by_class_name('btn-success')
#     btn.click()


@then('his repositories beeing imported from gitlab')
def user_sees_repositories_imported(context):
    browser = context.browser

    def fn():
        repo_row = browser.wait_text_become_present('toxic-gltest',
                                                    timeout=1)
        return bool(repo_row)

    r = browser.refresh_until(fn)
    assert r
