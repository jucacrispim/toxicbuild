# -*- coding: utf-8 -*-

import time
from behave import given, when, then
from toxicbuild.ui import settings
from tests.webui.steps.base_steps import (  # noqa f811
    user_sees_main_main_page_login)


@given('the user is in the regiter page')
def user_is_in_login_page(context):
    browser = context.browser

    base_url = 'http://localhost:{}/'.format(settings.TORNADO_PORT)
    url = base_url + 'register'
    browser.get(url)


@when('he inserts the "{username}" username')
def inserts_username(context, username):
    browser = context.browser
    el = browser.find_element_by_id('username')
    el.send_keys(username)


@then('he sees the not available info message')
def see_not_available_message(context):
    browser = context.browser
    browser.wait_text_become_present('username is not available')


@when('the "{email}" email')
def insert_email(context, email):
    browser = context.browser
    el = browser.find_element_by_id('email')
    el.send_keys(email)


@when('the "{password}" password')
def insert_password(context, password):
    browser = context.browser
    el = browser.find_element_by_id('password')
    el.send_keys(password)


@when('clicks in the sign in button')
def click_sigin_button(context):
    browser = context.browser
    btn = browser.find_element_by_id('btn-register')
    time.sleep(1.5)
    browser.click(btn)
