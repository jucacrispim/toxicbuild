# -*- coding: utf-8 -*-

import os
import gettext
from toxicbuild.core.conf import Settings

here = os.path.dirname(os.path.abspath(__file__))
translations = os.path.join(here, 'translations')

gettext.install('toxicbuild.ui', translations)

ENVVAR = 'TOXICUI_SETTINGS'
DEFAULT_SETTINGS = 'toxicui.conf'

settings = Settings(ENVVAR, DEFAULT_SETTINGS)
