# -*- coding: utf-8 -*-

import time
from behave import when, then, given
from selenium.common.exceptions import NoSuchElementException
from tests.functional.webui.steps.base_steps import (  # noqa f811
    given_logged_in_webui)


# Scenario: The user inserts a new slave without required information

@when('he clicks in the add slave button')
def step_impl(context):
    browser = context.browser
    btn = browser.find_element_by_id('add-slave-btn')
    browser.click(btn)


@when('sees the slave modal')  # noqa f401
def step_impl(context):
    browser = context.browser
    el = browser.find_element_by_id('addSlaveModalLabel')
    is_present = browser.wait_element_become_visible(el)
    assert is_present


@when('fills the name field with "{slave_name}"')  # noqa f401
def step_impl(context, slave_name):
    browser = context.browser
    input_element = browser.find_element_by_id('slave_name')
    input_element.send_keys(slave_name)


@when('fills the host field with "{slave_host}"')  # noqa f401
def step_impl(context, slave_host):
    browser = context.browser
    input_element = browser.find_element_by_id('slave_host')
    input_element.send_keys(slave_host)


@when('fills the port field with "{slave_port}"')  # noqa f401
def step_impl(context, slave_port):
    browser = context.browser
    input_element = browser.find_element_by_id('slave_port')
    input_element.send_keys(slave_port)


@when('clicks in the save button')  # noqa f401
def step_impl(context):
    browser = context.browser
    btn = browser.find_element_by_id('btn-save-slave')
    browser.click(btn)


@then('he sees the token field label in red')  # noqa f401
def step_impl(context):
    browser = context.browser
    is_present = browser.find_element_by_class_name('has-error')
    assert is_present


# Scenario: The user inserts a new slave and that works

@given('the user already tried to save a slave')  # noqa f401
def step_impl(context):
    browser = context.browser
    assert browser.find_element_by_id('addSlaveModalLabel').is_displayed()
    assert browser.find_element_by_class_name('has-error')


@when('fills the token field with "{slave_token}"')  # noqa f401
def step_impl(context, slave_token):
    browser = context.browser
    input_element = browser.find_element_by_id('slave_token')
    input_element.send_keys(slave_token)


@then('he sees the new slave in the slave list')  # noqa f401
def step_impl(context):
    browser = context.browser
    txt = 'some-slave'
    is_present = browser.wait_text_become_present(txt)
    assert is_present


# Scenario: A user removes a slave

@given('a user is logged in the system and has a slave')  # noqa f401
def step_impl(context):
    pass


@when('he clicks in the edit slave button')  # noqa f401
def step_impl(context):
    time.sleep(1)
    browser = context.browser
    btn = browser.find_element_by_class_name('btn-edit-slave')
    browser.click(btn)


@when('clicks in the delete button')  # noqa f401
def step_impl(context):
    browser = context.browser
    btn = browser.find_element_by_id('btn-delete-slave')
    browser.click(btn)


@then('the slave is removed from the slave list')  # noqa f401
def step_impl(context):
    browser = context.browser
    try:
        browser.implicitly_wait(0)
        rows = browser.find_elements_by_class_name('slave-row')
    except NoSuchElementException:
        rows = []
    finally:
        browser.implicitly_wait(10)

    assert not rows
