# -*- coding: utf-8 -*-

from toxicbuild.ui import settings
from behave import given, then, when


def logged_in_webui(context):
    browser = context.browser
    base_url = 'http://localhost:{}/'.format(settings.TORNADO_PORT)
    url = base_url + 'login'
    browser.get(url)

    if not browser.is_logged:
        browser.do_login(url, 'someguy', '123')

    el = browser.find_element_by_class_name('logout-link-container')
    browser.wait_element_become_visible(el)


given_logged_in_webui = given('the user is logged in the web interface')(
    logged_in_webui)


def sees_message(context, msg):
    browser = context.browser
    is_present = browser.wait_text_become_present(msg)
    assert is_present
    # for btn in browser.find_elements_by_class_name('close-msg'):
    #     browser.click(btn)


then_sees_message = then('he sees the "{msg}" message')(sees_message)


def navigate2settings(context):
    browser = context.browser
    btn = browser.find_element_by_xpath('a[href="/settings/repositories"]')
    browser.click(btn)
    browser.wait_text_become_present('Manage repositories')


when_navigate2settings = when('he navigates to the settings page')(
    navigate2settings)
