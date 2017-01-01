# -*- coding: utf-8 -*-

from toxicbuild.ui import settings
from behave import given


def logged_in_webui(context):
    browser = context.browser
    base_url = 'http://localhost:{}/'.format(settings.TORNADO_PORT)
    url = base_url + 'login'
    browser.get(url)

    if not browser.is_logged:
        browser.do_login(url, 'someguy', '123')

    txt = 'Connected to master'
    browser.wait_text_become_present(txt)


given_logged_in_webui = given('the user is logged in the web interface')(
    logged_in_webui)
