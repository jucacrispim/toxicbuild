# -*- coding: utf-8 -*-

import os
import gettext
from toxicbuild.core.conf import Settings
from toxicbuild.ui.client import get_hole_client

here = os.path.dirname(os.path.abspath(__file__))
translations = os.path.join(here, 'translations')

gettext.install('toxicbuild.ui', translations)

ENVVAR = 'TOXICUI_SETTINGS'
DEFAULT_SETTINGS = 'toxicui.conf'

settings = Settings(ENVVAR, DEFAULT_SETTINGS)


make_pyflakes_happy = [get_hole_client]

del make_pyflakes_happy
