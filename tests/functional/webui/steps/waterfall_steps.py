# -*- coding: utf-8 -*-

import time
from behave import when, then, given
from tests.functional.webui.steps.base_steps import (  # noqa f811
    given_logged_in_webui)


@when('he clicks in the waterfall button')
def step_impl(context):
    browser = context.browser
    time.sleep(0.3)
    btn = browser.find_element_by_id('btn-status-repo-bla')
    browser.click(btn)


@then('he sees a list of builds in the waterfall')  # noqa f401
def step_impl(context):
    browser = context.browser
    elements = browser.find_elements_by_class_name('builder')
    assert len(elements) == 3


@given('the user is already in the waterfall')  # noqa f401
def step_impl(context):
    pass


@when('he sees the builds running')  # noqa f401
def step_impl(context):
    browser = context.browser
    elements = browser.find_elements_by_class_name('step-running')
    assert elements
    time.sleep(0.3)

@then('he waits for all builds to complete')  # noqa f401
def step_impl(context):
    browser = context.browser
    timeout = 10
    c = 0
    running = browser.find_elements_by_class_name('step-running')
    while bool(running) and c < timeout:
        time.sleep(1)
        running = browser.find_elements_by_class_name('step-running')
        c += 1
    assert bool(running) is False


@when('he clicks in the buildset details button')      # noqa f401
def step_impl(context):
    browser = context.browser
    btn = browser.find_element_by_class_name('btn-buildset-details')
    browser.click(btn)


@then('he sees the buildset details modal')  # noqa 401
def step_impl(context):
    browser = context.browser
    el = browser.find_element_by_id('buildsetDetailsModal')
    is_visible = browser.wait_element_become_visible(el)
    assert is_visible


@then('closes the details modal')  # noqa f401
def step_impl(context):
    browser = context.browser
    btn = browser.find_element_by_class_name('close')
    browser.click(btn)


@when('he clicks in the step details button')  # noqa f401
def step_impl(context):
    browser = context.browser
    btn = browser.find_element_by_class_name('btn-step-details')
    browser.click(btn)


@then('he sees the step details modal')  # noqa f401
def step_impl(context):
    browser = context.browser
    el = browser.find_element_by_id('stepDetailsModal')
    is_visible = browser.wait_element_become_visible(el)
    assert is_visible
