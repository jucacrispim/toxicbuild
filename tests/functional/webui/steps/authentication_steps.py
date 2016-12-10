# -*- coding: utf-8 -*-

from behave import when, then, given
from toxicbuild.ui import settings


# Scenario: Someone try to access a page without being logged.

@when('someone tries to access a waterfall url without being logged')
def step_impl(context):
    browser = context.browser
    url = 'http://localhost:{}/waterfall/some-repo'.format(
        settings.TORNADO_PORT)
    browser.get(url)


@then('he sees the login page')  # noqa f401
def step_impl(context):
    browser = context.browser
    el = browser.find_element_by_id('inputUsername')
    assert el


# Scenario: Do login

@given('the user is in the login page')  # noqa f401
def step_impl(context):
    browser = context.browser
    url = 'http://localhost:{}/login'.format(settings.TORNADO_PORT)
    browser.get(url)


@when('he inserts "{user_name}" as user name')  # noqa f401
def step_impl(context, user_name):
    browser = context.browser
    username_input = browser.find_element_by_id('inputUsername')
    username_input.send_keys(user_name)


@when('inserts "{passwd}" as password')  # noqa f401
def step_impl(context, passwd):
    browser = context.browser
    passwd_input = browser.find_element_by_id('inputPassword')
    passwd_input.send_keys(passwd)


@when('clicks in the login button')  # noqa f401
def step_impl(context):
    browser = context.browser
    btn = browser.find_element_by_class_name('btn')
    browser.click(btn)


@then('he sees the main page')  # noqa f401
def step_impl(context):
    browser = context.browser
    txt = 'Connected to master'
    is_present = browser.wait_text_become_present(txt)
    assert is_present


# Scenario: Do logout

@given('the user is logged in the web interface')  # noqa f401
def step_impl(context):
    browser = context.browser
    url = 'http://localhost:{}/login'.format(settings.TORNADO_PORT)

    if not browser.is_logged:
        browser.do_login(url, 'someguy', '123')


@when('he clicks in the logout link')  # noqa f401
def step_impl(context):
    browser = context.browser
    browser.click_link('Logout')
