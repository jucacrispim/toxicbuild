# -*- coding: utf-8 -*-

import time
from behave import when, then, given
from tests.webui.steps.base_steps import (  # noqa f811
    given_logged_in_webui)


@when('he clicks in the settings button')
def click_settings_button(context):
    browser = context.browser
    el = browser.find_elements_by_class_name('fa-wrench')[0]
    el.click()

    # wait for the settings page
    browser.wait_text_become_present('Manage slaves')


@when('clicks in the Manage slaves menu')
def click_manage_slave_menu(context):
    browser = context.browser
    el = browser.find_element_by_id('manage-slaves-link')
    el.click()

    # here I wait for the slave list page to appear looking for the
    # help text
    browser.wait_text_become_present('Slaves are the ones')


@when('clicks in the add slave button')
def click_add_slave_button(context):
    browser = context.browser
    el = browser.find_elements_by_class_name('fa-plus')[0]
    el.click()


@then('he sees the add slave page')
def see_add_slave_page(context):
    browser = context.browser
    browser.wait_text_become_present('Add slave')


@given('the user is in the add slave page')
def is_in_add_slave_page(self):
    pass


@when('he fills the slave name field')
def fill_slave_name(context):
    browser = context.browser
    el = browser.find_elements_by_class_name('slave-details-name')[1]
    el.send_keys('some-name')


@when('fills the host field')
def fill_slave_host(context):
    browser = context.browser
    el = browser.find_elements_by_class_name('slave-details-host')[1]
    el.send_keys('some.host')


@when('fills the port field')
def fill_slave_port(context):
    browser = context.browser
    el = browser.find_elements_by_class_name('slave-details-port')[1]
    el.send_keys(1234)


@when('fills the token field')
def fill_token_field(context):
    browser = context.browser
    el = browser.find_elements_by_class_name('slave-details-token')[1]
    el.send_keys('some-token')


@when('clicks in the save changes button')
@when('clicks in the add new slave button')
def click_add_new_slave_button(context):
    browser = context.browser
    el = browser.find_element_by_id('btn-save-obj')
    time.sleep(0.5)
    el.click()


@given('the user is in the slave settings page')
def is_in_slave_settings_page(context):
    browser = context.browser
    browser.wait_text_become_present('General configurations')
    el = browser.find_elements_by_class_name('btn-delete-slave')[1]
    browser.wait_element_become_visible(el)


@when('he clicks in the use ssl button')
def click_use_ssl(context):
    browser = context.browser
    el = browser.find_element_by_id('slave-use-ssl')
    browser.click(el)


@when('he clicks in the close page button')
def click_close_btn(context):
    browser = context.browser
    btn = browser.find_element_by_class_name('close-btn')
    browser.click(btn)
    browser.wait_text_become_present('Manage slaves')


@then('he sees the slaves list')
def see_slave_list(context):
    browser = context.browser
    el = browser.find_elements_by_class_name('slave-info')[1]
    browser.wait_element_become_visible(el)


@given('the user is in the slaves list page')
def is_in_slaves_list_page(context):
    pass


@when('he navigates to the slave settings page')
def navigate_to_slave_settings_page(context):
    browser = context.browser

    el = browser.find_elements_by_class_name('fa-ellipsis-h')[1]
    el.click()
    browser.click_link('Settings')
    browser.wait_text_become_present('General configurations')


@when('clicks in the delete slave button')
def click_delete_button(context):
    browser = context.browser

    el = browser.find_elements_by_class_name('btn-delete-slave')[1]
    browser.wait_element_become_visible(el)

    browser.click(el)


@when('clicks in the delete slave button in the modal')
def click_delete_button_modal(context):
    browser = context.browser

    el = browser.find_element_by_id('btn-remove-obj')
    browser.wait_element_become_visible(el)
    el.click()
