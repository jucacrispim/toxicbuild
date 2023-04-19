# -*- coding: utf-8 -*-

import gettext
import os
from tornado import locale
from toxicbuild.core.conf import Settings

# pylint: disable=global-statement

here = os.path.dirname(os.path.abspath(__file__))

# translations for cli
cli_translations = os.path.join(here, 'translations')
gettext.install('toxicbuild.ui', cli_translations)
t = gettext.translation('toxicbuild.ui', cli_translations)
translate = t.gettext


# translations for ui
web_translations = os.path.join(here, 'translations', 'web')
locale.load_translations(web_translations)


ENVVAR = 'TOXICUI_SETTINGS'
DEFAULT_SETTINGS = 'toxicui.conf'

settings = None


def create_settings():
    global settings

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)
