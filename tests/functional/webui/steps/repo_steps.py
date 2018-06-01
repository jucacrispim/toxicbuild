# -*- coding: utf-8 -*-

import time
from behave import when, then, given
from selenium.common.exceptions import NoSuchElementException
from tests.functional.webui.steps.base_steps import (  # noqa f811
    given_logged_in_webui, then_sees_message)
from tests.functional import REPO_DIR


@when('he clicks in the add repo button')
def step_impl(context):
    browser = context.browser
    btn = browser.find_element_by_id('add-repo-btn')
    browser.click(btn)


@when('sees the repo modal')  # noqa f401
def step_impl(context):
    browser = context.browser
    el = browser.find_element_by_id('repoModal')
    is_present = browser.wait_element_become_visible(el)
    assert is_present


@when('fills the repo name field with "{repo_name}"')  # noqa f401
def step_impl(context, repo_name):
    browser = context.browser
    input_element = browser.find_element_by_id('repo_name')
    for l in repo_name:
        browser.click(input_element)
        input_element.send_keys(l)


@when('clicks in the save repo button')  # noqa f401
def step_impl(context):
    browser = context.browser
    btn = browser.find_element_by_id('btn-save-repo')
    browser.click(btn)


@then('he sees the required fields in red')  # noqa f401
def step_impl(context):
    browser = context.browser
    assert browser.find_element_by_id('repoModal').is_displayed()
    assert browser.find_element_by_class_name('has-error')


@given('the user already tried to save a repo')  # noqa f401
def step_impl(context):
    browser = context.browser
    assert browser.find_element_by_id('repoModal').is_displayed()


@when('he fills the url field with a repo url')  # noqa f401
def step_impl(context):
    browser = context.browser
    input_element = browser.find_element_by_id('repo_url')
    input_element.send_keys(REPO_DIR)


@when('selects a slave named "{slave_name}"')  # noqa f401
def step_impl(context, slave_name):
    browser = context.browser
    select = browser.find_element_by_id('repo_slaves')
    select.find_element_by_xpath(
        "//select/option[@value='{}']".format(slave_name)).click()


@then('the repo status "{status}"')  # noqa f401
def step_impl(context, status):
    browser = context.browser
    cls_name = 'btn-{}'.format(status)
    el = browser.find_element_by_class_name(cls_name)
    assert el


@given('the user already inserted a new repo')  # noqa f401
def step_impl(context):
    pass


@when('he clicks in the configure output methods button')  # noqa f401
def step_impl(context):
    browser = context.browser
    btn = browser.find_element_by_class_name('btn-edit-plugin')
    browser.click(btn)


@when('sees the output methods modal')  # noqa f401
def step_impl(context):
    browser = context.browser
    el = browser.find_element_by_id('outputPluginModal')
    is_present = browser.wait_element_become_visible(el)
    assert is_present


@when('clicks in the enable ckeckbox')  # noqa f401
def step_impl(context):
    browser = context.browser
    el = browser.find_element_by_xpath('//input[@type="checkbox"]')
    browser.click(el)


@when('fills the webhook url field with "{webhook_url}"')  # noqa f401
def step_impl(context, webhook_url):
    browser = context.browser
    el_input = browser.find_element_by_xpath('//input[@name="webhook_url"]')
    el_input.send_keys(webhook_url)


@when('fills the channel name field with "{channel_name}"')  # noqa f401
def step_impl(context, channel_name):
    browser = context.browser
    el_input = browser.find_element_by_xpath('//input[@name="channel_name"]')
    el_input.send_keys(channel_name)


@when('fills the branches field with "{branches}"')  # noqa f401
def step_impl(context, branches):
    browser = context.browser
    el_input = browser.find_element_by_xpath('//input[@name="branches"]')
    el_input.send_keys(branches)


@when('fills the statuses field with "{statuses}')  # noqa f401
def step_impl(context, statuses):
    browser = context.browser
    el_input = browser.find_element_by_xpath('//input[@name="statuses"]')
    el_input.send_keys(statuses)


@when('clicks in the save plugin button')  # noqa f401
def step_impl(context):
    browser = context.browser
    btn = browser.find_element_by_id('btn-save-plugins')
    browser.click(btn)


@given('the user is logged in the web interface and has a repo')  # noqa f401
def step_impl(context):
    pass


@when('he clicks in the edit repo button')  # noqa f401
def step_impl(context):
    time.sleep(1)
    browser = context.browser
    btn = browser.find_element_by_class_name('btn-edit-repo')
    browser.click(btn)


@when('clicks in the delete repo button')  # noqa f401
def step_impl(context):
    browser = context.browser
    time.sleep(0.5)
    btn = browser.find_element_by_id('btn-delete-repo')
    browser.click(btn)


@then('the repo is removed from the repo list')  # noqa f401
def step_impl(context):
    browser = context.browser
    try:
        browser.implicitly_wait(0)
        rows = browser.find_elements_by_class_name('repo-row')
    except NoSuchElementException:
        rows = []
    finally:
        browser.implicitly_wait(10)

    assert not rows
