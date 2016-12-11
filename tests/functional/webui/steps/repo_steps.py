# -*- coding: utf-8 -*-

from behave import when, then, given
from selenium.common.exceptions import NoSuchElementException
from tests.functional.webui.steps.base_steps import (  # noqa f811
    given_logged_in_webui)
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
    input_element.send_keys(repo_name)

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


@when('fills the update seconds field with "{update_seconds}"')  # noqa f401
def step_impl(context, update_seconds):
    browser = context.browser
    input_element = browser.find_element_by_id('repo_update_seconds')
    input_element.send_keys(update_seconds)


@when('selects a slave named "{slave_name}"')  # noqa f401
def step_impl(context, slave_name):
    browser = context.browser
    select = browser.find_element_by_id('repo_slaves')
    select.find_element_by_xpath(
        "//select/option[@value='{}']".format(slave_name)).click()


@then('he sees the "{msg}" message')  # noqa f401
def step_impl(context, msg):
    browser = context.browser
    is_present = browser.wait_text_become_present(msg)
    assert is_present


@then('the repo status "{status}"')  # noqa f401
def step_impl(context, status):
    browser = context.browser
    cls_name = 'btn-{}'.format(status)
    el = browser.find_element_by_class_name(cls_name)
    assert el


@given('the user is logged in the web interface and has a repo')  # noqa f401
def step_impl(context):
    pass


@when('he clicks in the edit repo button')  # noqa f401
def step_impl(context):
    browser = context.browser
    btn = browser.find_element_by_class_name('btn-edit-repo')
    browser.click(btn)


@when('clicks in the delete repo button')  # noqa f401
def step_impl(context):
    browser = context.browser
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
