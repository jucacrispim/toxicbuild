# -*- coding: utf-8 -*-

from behave import given, when, then

from toxicbuild.ui import settings

from tests.webui.steps.base_steps import (  # noqa f811
    given_logged_in_webui, then_sees_message)


@given('is in the waterfall')
def is_in_waterfall(context):
    browser = context.browser
    base_url = 'http://localhost:{}/'.format(settings.TORNADO_PORT)
    waterfall_url = '{}someguy/repo-bla/waterfall'.format(base_url)
    browser.get(waterfall_url)


@when('he clicks in the reschedule buildset button in the waterfall')
def click_reschedule(context):
    browser = context.browser

    def fn():
        try:
            el = browser.find_elements_by_class_name('fa-redo')[1]
        except IndexError:
            el = None

        return el

    el = browser.wait_element_become_present(fn)

    el.click()


@given('the user already rescheduled a buildset in the waterfall')
def buildset_already_rescheduled(context):
    browser = context.browser

    def fn():
        try:
            el = browser.find_elements_by_class_name('build-pending')[1]
        except IndexError:
            el = None

        return el

    el = browser.wait_element_become_present(fn)
    assert el


@when('the user clicks in the build details button')
def click_buildetails_button(context):
    browser = context.browser

    def fn():
        try:
            el = browser.find_elements_by_class_name('fa-info')[1]
        except IndexError:
            el = None

        return el

    el = browser.wait_element_become_present(fn)
    el.click()


@then('he sees the build details page')
def see_build_details(context):
    browser = context.browser

    def fn():
        try:
            el = browser.find_elements_by_class_name(
                'build-details-container')[0]
        except IndexError:
            el = None

        return el

    el = browser.wait_element_become_present(fn)
    assert el


@given('the user is in the build details page')
def is_in_build_details_page(context):
    pass


@then('he waits for the build to finish')
def wait_build_finish(context):
    browser = context.browser

    def fn():
        el = browser.find_elements_by_class_name('build-total-time')[0]
        if el.text:
            return el
        else:
            return None

    el = browser.wait_element_become_present(fn)
    assert el
