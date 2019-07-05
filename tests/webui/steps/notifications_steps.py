# -*- coding: utf-8 -*-

import time
from behave import when, then, given
from tests.webui.steps.base_steps import (  # noqa f811
    given_logged_in_webui, then_sees_message)


@when('he clicks in the more button in the repo info box')
def click_more_button_repo_info(context):
    browser = context.browser
    browser.refresh()

    def fn():
        try:
            el = browser.find_elements_by_class_name('fa-ellipsis-h')[-1]
            el = el if el.is_displayed() else None
        except Exception:
            el = None

        return el

    el = browser.wait_element_become_present(fn)
    browser.click(el)


@when('clicks in the settings link')
def click_settings_link(context):
    browser = context.browser

    def fn():
        try:
            el = browser.find_elements_by_class_name('dropdown-item')[-1]
            el = el if el.is_displayed() else None
        except Exception:
            el = None

        return el

    el = browser.wait_element_become_present(fn)

    browser.click(el)
    time.sleep(0.1)
    browser.refresh()
    browser.wait_text_become_present('Notifications')


@when('clicks in the notifications navigation item')
def click_notifications_nav_item(context):
    browser = context.browser
    browser.click_link('Notifications')
    browser.wait_text_become_present('Slack')


@then('he sees the notifications page')
def see_notificatios_page(context):
    browser = context.browser
    el = browser.find_element_by_class_name('notification-item')
    assert el is not None


@given('the user is in the notifications page')
def is_in_notif_page(context):
    pass


@when('he clicks in the cofigure slack notification button')
def click_configure_slack_notification(context):
    browser = context.browser

    def fn():
        try:
            el = browser.find_elements_by_class_name('fa-wrench')[1]
            el = el if el.is_displayed() else None
        except Exception:
            el = None

        return el

    el = browser.wait_element_become_present(fn)

    el.click()
    time.sleep(0.4)


@when('fills the webhook URL field')
def fill_webhook_url(context):
    browser = context.browser

    def fn():
        try:
            el = browser.find_element_by_id('id-webhook_url')
            el = el if el.is_displayed() else None
        except Exception:
            el = None

        return el

    el = browser.wait_element_become_present(fn)
    el.send_keys('https://somewhere.bla')


@when('clicks in the enable button')
def click_enable_notif_btn(context):
    browser = context.browser

    def fn():
        try:
            el = browser.find_element_by_id('btn-enable-notification')
            el = el if el.is_displayed() else None
        except Exception:
            el = None

        return el

    el = browser.wait_element_become_present(fn)

    time.sleep(0.4)
    el.click()


@given('the user has enabled the slack notification')
def has_enabled_the_slack_notification(context):
    browser = context.browser

    def fn():
        try:
            el = browser.find_elements_by_class_name('fa-wrench')[1]
            el = el if el.is_displayed() else None
        except Exception:
            el = None

        return el

    browser.refresh()
    el = browser.wait_element_become_present(fn)
    browser.wait_element_become_visible(el)


@when('clicks in the disable button')
def click_disable_notif_btn(context):
    browser = context.browser

    def fn():
        try:
            el = browser.find_element_by_id('btn-remove-obj')
            el = el if el.is_displayed() else None
        except Exception:
            el = None

        return el

    el = browser.wait_element_become_present(fn)

    el.click()
