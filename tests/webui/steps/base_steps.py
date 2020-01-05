# -*- coding: utf-8 -*-

import time
from toxicbuild.ui import settings
from behave import given, then, when
from tests.webui import take_screenshot


@take_screenshot
def logged_in_webui(context):
    browser = context.browser
    base_url = 'http://{}:{}/'.format(settings.TEST_WEB_HOST,
                                      settings.TORNADO_PORT)
    url = base_url + 'login'
    browser.get(url)

    if not browser.is_logged:
        browser.do_login(url, 'someguy', '123')

    el = browser.find_element_by_class_name('logout-link-container')
    browser.wait_element_become_visible(el)


given_logged_in_webui = given('the user is logged in the web interface')(
    logged_in_webui)


@take_screenshot
def sees_message(context, msg):
    browser = context.browser
    is_present = browser.wait_text_become_present(msg)
    assert is_present
    # for btn in browser.find_elements_by_class_name('close-msg'):
    #     browser.click(btn)


then_sees_message = then('he sees the "{msg}" message')(sees_message)


@take_screenshot
def navigate2settings(context):
    browser = context.browser
    btn = browser.find_element_by_xpath('a[href="/settings/repositories"]')
    browser.click(btn)
    browser.wait_text_become_present('Manage repositories')


when_navigate2settings = when('he navigates to the settings page')(
    navigate2settings)


@then('he sees the main page')
@take_screenshot
def user_sees_main_main_page_login(context):
    browser = context.browser
    txt = 'Logout'
    is_present = browser.wait_text_become_present(txt)
    assert is_present


@when('clicks in the save button')
@when('clicks in the add button')
@take_screenshot
def click_add_button(context):
    browser = context.browser
    time.sleep(0.5)
    btn = browser.find_element_by_id('btn-save-obj')
    browser.click(btn)
