# -*- coding: utf-8 -*-
# package with behave tests

import time
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains


class SeleniumBrowserException(Exception):
    pass


class SeleniumBrowser(webdriver.Chrome):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maximize_window()

    def click(self, element):
        """Clicks in a element using ActionChains.

        :param element: Um elemento para clicar."""

        action = ActionChains(self).click(element)
        action.perform()

    def wait_text_become_present(self, text, timeout=5):
        """Waits until a text is present in the page source.

        :param text: The text that should be present in the page.
        :param timeout: timeout in seconds for the operation."""

        r = int(timeout * 10)

        for index in range(r):
            time.sleep(0.1)
            if text in self.page_source:
                return True

        raise SeleniumBrowserException(
            'text %s not present after %s seconds' % (text, timeout))

    def do_login(self, url, username, passwd):
        """Do login in the web interface.

        :param url: Login page url.
        :param username: Username for login.
        :param passwd: Password for login."""

        self.get(url)
        username_input = self.find_element_by_id('inputUsername')
        username_input.send_keys(username)

        passwd_input = self.find_element_by_id('inputPassword')
        passwd_input.send_keys(passwd)
        btn = self.find_element_by_class_name('btn')
        self.click(btn)

    def click_link(self, link_text):
        """Clicks in  link indicated by link_text"""

        self.find_element_by_partial_link_text(link_text).click()

    @property
    def is_logged(self):
        """True if the browser is already logged in the web interface."""

        try:
            self.find_element_by_id('inputPassword')
            return False
        except NoSuchElementException:
            return True

    def wait_element_become_visible(self, el, timeout=5):
        """Waits until an element become visible.

        :param el: A page element
        :param timeout: Timeout for the operation."""

        r = int(timeout * 10)

        for index in range(r):
            time.sleep(0.1)
            if el.is_displayed():
                return True

        raise SeleniumBrowserException(
            'The element %s not visible after %s seconds' % (el, timeout))
