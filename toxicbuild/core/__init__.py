# -*- coding: utf-8 -*-

from toxicbuild.core.vcs import get_vcs
from toxicbuild.core.protocol import BaseToxicProtocol
from toxicbuild.core.client import BaseToxicClient


make_pyflakes_happy = [get_vcs, BaseToxicProtocol, BaseToxicClient]

del make_pyflakes_happy
