# -*- coding: utf-8 -*-

from toxicbuild.core.vcs import get_vcs
from toxicbuild.core.protocol import BaseToxicProtocol


make_pyflakes_happy = [get_vcs, BaseToxicProtocol]

del make_pyflakes_happy
