# -*- coding: utf-8 -*-

import time
from behave import when, then, given
from selenium.common.exceptions import NoSuchElementException
from tests.webui.steps.base_steps import (  # noqa f811
    given_logged_in_webui, then_sees_message, when_navigate2settings)
from tests.functional import REPO_DIR


@when('he clicks in the add repository link')
def click_add_repo_btn(context):
    browser = context.browser
    btn = browser.find_element_by_xpath('//a[@href="/repository/add"]')
    browser.wait_element_become_visible(btn)
    browser.click(btn)


@then('he sees the add repository page')
def sees_add_repo_page(context):
    browser = context.browser
    browser.wait_text_become_present('Add repository')


@given('the user is in the add repo page')
def is_in_the_add_repo_page(context):
    browser = context.browser
    is_present = browser.wait_text_become_present('Add repository')
    assert is_present
    time.sleep(0.5)


@when('he fills the name with a repo name')
def fill_repo_name(context):
    browser = context.browser
    name_input = browser.find_elements_by_class_name('repo-details-name')[1]
    name_input.send_keys('MyNewRepo')


@when('fills the url field with a repo url')
def fill_repo_url(context):
    browser = context.browser
    url_input = browser.find_elements_by_class_name('repo-details-url')[1]
    url_input.send_keys(REPO_DIR)


@when('clicks in the add repo button')
def click_add_repo_button(context):
    browser = context.browser
    time.sleep(0.5)
    btn = browser.find_element_by_id('btn-save-repo')
    browser.click(btn)


@given('the user is in the repository settings page')
def is_in_repo_settings_page(context):
    browser = context.browser
    el = browser.find_element_by_class_name('fa-list')
    browser.wait_element_become_visible(el)


@when('he clicks in the Advanced element')
def click_advanced_config(context):
    browser = context.browser
    el = browser.find_elements_by_class_name('repo-config-advanced-span')[1]
    browser.wait_element_become_visible(el)
    browser.click(el)


@given('he sees the advanced options')
@then('he sees the advanced options')
def see_advanced_options(context):
    browser = context.browser
    el = browser.find_elements_by_class_name('repo-branches-ul')[1]
    browser.wait_element_become_visible(el)


@then('sees the advanced help in the side bar')
def see_advanced_help(context):
    browser = context.browser
    sidebar_help = browser.find_element_by_id('parallel-builds-config-p')
    browser.wait_element_become_visible(sidebar_help)


@when('he clicks in the add branch button')
def clicks_branch_button(context):
    browser = context.browser
    btn = browser.find_elements_by_class_name('add-branch-btn')[1]
    browser.click(btn)
    el = browser.find_element_by_id('addBranchModal')
    browser.wait_element_become_visible(el)


@when('fills the branch name')
def fill_branch_name(context):
    browser = context.browser
    el = browser.find_element_by_id('repo-branch-name')
    el.send_keys('master')
    time.sleep(0.5)


@when('clicks in the add branch button')
def click_add_branch_button(context):
    browser = context.browser
    el = browser.find_element_by_id('btn-add-branch')
    browser.click(el)
    time.sleep(0.5)


@then('he sees the new branch config in the list')
def see_new_branch(context):
    browser = context.browser
    el = browser.find_elements_by_class_name('repo-branches-li')[2]
    browser.wait_element_become_visible(el)


@given('the user already added a branch config')
def already_added_branch(context):
    pass


@when('he clicks in the remove branch config button')
def click_remove_branch_btn(context):
    browser = context.browser
    btn = browser.find_elements_by_class_name('remove-branch-btn')[2]
    browser.click(btn)


@then('he sees the no branch config info in the list')
def see_no_branch_config_info(context):
    browser = context.browser
    el = browser.find_elements_by_class_name('no-item-placeholder')[1]
    browser.wait_element_become_visible(el)


@when('he clicks in the slave enabled check button')
def click_slave_enabled_check(context):
    browser = context.browser
    xpath = '//li[@class="repo-slaves-li box-shadow-light box-white"]'
    xpath += '/div/div/label[@class="btn btn-success toggle-on"]'

    el = browser.find_element_by_xpath(xpath)
    browser.wait_element_become_visible(el)
    browser.click(el)


@then('he sees the slave disabled check button')
def see_slave_disabled_check(context):
    browser = context.browser
    xpath = '//li[@class="repo-slaves-li box-shadow-light box-white"]'
    xpath += '/div/div/label[@class="btn btn-secondary active toggle-off"]'

    el = browser.find_element_by_xpath(xpath)
    browser.wait_element_become_visible(el)


@when('he clicks in the slave disabled check button')
def clicks_slave_disabled_btn(context):
    browser = context.browser
    xpath = '//li[@class="repo-slaves-li box-shadow-light box-white"]'
    xpath += '/div/div/label[@class="btn btn-secondary active toggle-off"]'

    el = browser.find_element_by_xpath(xpath)
    browser.wait_element_become_visible(el)
    browser.click(el)


@then('he sees the slave enabled check button')
def see_slave_enabled_check(context):
    browser = context.browser
    xpath = '//li[@class="repo-slaves-li box-shadow-light box-white"]'
    xpath += '/div/div/label[@class="btn btn-success toggle-on"]'

    el = browser.find_element_by_xpath(xpath)
    browser.wait_element_become_visible(el)


@when('he clicks in the repo enabled check button')
def click_repo_enabled_check(context):
    browser = context.browser
    xpath = '//div[@class="repo-info-container {}"]'.format(
        'repository-info-enabled-container repo-enabled')
    xpath += '/div/div/label[@class="btn btn-success toggle-on"]'

    el = browser.find_element_by_xpath(xpath)
    browser.wait_element_become_visible(el)
    browser.click(el)


@then('he sees the repo disabled check button')
def see_repo_disabled_check(context):
    browser = context.browser
    xpath = '//div[@class="repo-info-container {}"]'.format(
        'repository-info-enabled-container repo-enabled')
    xpath += '/div/div/label[@class="btn btn-secondary active toggle-off"]'

    el = browser.find_element_by_xpath(xpath)
    browser.wait_element_become_visible(el)


@when('he clicks in the close button')
def click_close_btn(context):
    browser = context.browser
    btn = browser.find_element_by_class_name('close-btn')
    browser.click(btn)
    el = browser.find_element_by_id('no-repos-message')
    browser.wait_element_become_visible(el)


@when('clicks in the manage repositories link')
def click_manage_repos_link(context):
    browser = context.browser
    browser.click_link('manage')
    browser.wait_text_become_present('Manage repositories')
    el = browser.find_element_by_class_name('fa-plus')
    browser.wait_element_become_visible(el)


@then('he sees a list of repositories')
def see_repo_list(context):
    browser = context.browser
    el = browser.find_elements_by_class_name('repository-info')[1]
    browser.wait_element_become_visible(el)


@given('the user is in the repository management page')
def is_in_repo_management_page(context):
    pass


@when('he clicks in the repo disabled ckeck button')
def click_repo_disabled_button(context):
    browser = context.browser

    xpath = '//div[@class="repo-info-container {}"]'.format(
        'repository-info-enabled-container repo-disabled')
    xpath += '/div/div/label[@class="btn btn-secondary active toggle-off"]'

    el = browser.find_element_by_xpath(xpath)
    browser.wait_element_become_visible(el)
    browser.click(el)


@then('he sees the repo enabled check button')
def see_repo_enabled_check(context):
    browser = context.browser

    xpath = '//div[@class="repo-info-container {}"]'.format(
        'repository-info-enabled-container')
    xpath += '/div/div/label[@class="btn btn-success toggle-on"]'

    el = browser.find_element_by_xpath(xpath)
    browser.wait_element_become_visible(el)


@when('he clicks in the toxicbuild logo')
def clicks_toxicbuild_logo(context):
    browser = context.browser

    el = browser.find_elements_by_class_name('navbar-brand')[0]
    browser.click(el)
    browser.wait_text_become_present('Your Repositories')
    el = browser.find_elements_by_class_name('fa-wrench')[0]
    browser.wait_element_become_visible(el)


@when('clicks in the repo menu')
def click_repo_menu(context):
    browser = context.browser

    el = browser.find_elements_by_class_name('fa-ellipsis-h')[1]
    browser.click(el)
    el = browser.find_elements_by_class_name('dropdown-menu-right')[1]
    browser.wait_element_become_visible(el)


@when('clicks in the repo settings link')
def click_settings_link(context):
    browser = context.browser
    browser.click_link('Settings')
    browser.wait_text_become_present('General configurations')


@then('he sees the repository settings page')
def see_repo_settings_page(context):
    browser = context.browser

    el = browser.find_element_by_class_name('fa-list')
    browser.wait_element_become_visible(el)


@when('clicks in the delete repo button')
def click_delete_button(context):
    browser = context.browser
    el = browser.find_elements_by_class_name('btn-delete-repo')[1]
    browser.wait_element_become_visible(el)
    el.click()

    el = browser.find_element_by_id('removeRepoModal')
    browser.wait_element_become_visible(el)

@when('clicks in the delete repo button in the modal')
def click_delete_button_modal(context):
    browser = context.browser
    el = browser.find_element_by_id('btn-remove-repo')
    el.click()
