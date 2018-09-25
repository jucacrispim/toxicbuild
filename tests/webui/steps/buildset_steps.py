# -*- coding: utf-8 -*-

from behave import when, then, given
from selenium.common.exceptions import StaleElementReferenceException
from tests.webui.steps.base_steps import (  # noqa f811
    given_logged_in_webui, then_sees_message)


@when('he clicks in the summary link')
def click_summary_link(context):
    browser = context.browser

    def fn():
        try:
            el = browser.find_elements_by_xpath('//a[@title="Summary"]')[1]
        except IndexError:
            el = None

        return el

    el = browser.wait_element_become_present(fn)

    el.click()
    el = browser.find_element_by_class_name('fa-th')
    browser.wait_element_become_visible(el)


@then('he sees the buildset list page')
def see_buildset_list_page(context):
    browser = context.browser
    el_list = browser.find_elements_by_class_name('buildset-info')

    assert len(el_list) > 1


@given('the user is in the buildset list page')
def is_in_buildset_list_page(context):
    browser = context.browser
    browser.wait_text_vanishes('badge-primary')


@when('he clicks in the reschedule button')
def click_reschedule_button(context):
    browser = context.browser

    def fn():
        try:
            el = browser.find_elements_by_class_name('fa-redo')[1]
        except IndexError:
            el = None

        return el

    el = browser.wait_element_become_present(fn)
    try:
        browser.wait_element_become_visible(el)
    except StaleElementReferenceException:
        el = browser.wait_element_become_present(fn)
        browser.wait_element_become_visible(el)

    browser.wait_element_become_visible(el)
    el.click()


@then('he sees the buildset running')
def see_buildset_running(context):
    browser = context.browser
    browser.wait_text_become_present('badge-primary')


@given('the user already rescheduled a buildset')
def already_rescheduled_buildset(context):
    browser = context.browser
    el = browser.find_elements_by_class_name('badge-primary')[0]
    browser.wait_element_become_visible(el)


@when('he clicks in the buildset details link')
def click_in_buildset_details_link(context):
    browser = context.browser
    el = browser.find_elements_by_class_name('buildset-details-link')[3]
    try:
        browser.wait_element_become_visible(el)
    except StaleElementReferenceException:
        el = browser.find_elements_by_class_name('buildset-details-link')[3]
        browser.wait_element_become_visible(el)

    el.click()


@then('he sees the buildset details page')
def see_buildset_details(context):
    browser = context.browser

    def fn():
        try:
            el = browser.find_elements_by_class_name(
                'buildset-details-header')[1]
        except IndexError:
            el = None

        return el

    el = browser.wait_element_become_present(fn)
    browser.wait_element_become_visible(el)
