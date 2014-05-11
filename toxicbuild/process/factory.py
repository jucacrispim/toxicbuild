# -*- coding: utf-8 -*-

from buildbot.process.factory import BuildFactory
from toxicbuild.process.build import DynamicBuild


class DynamicBuildFactory(BuildFactory):
    buildClass = DynamicBuild

    def __init__(self, venv_path, pyversion, steps=None):
        self.venv_path = venv_path
        self.pyversion = pyversion
        BuildFactory.__init__(self, steps)

    def newBuild(self, requests):
        b = BuildFactory.newBuild(self, requests)
        b.venv_path = self.venv_path
        b.pyversion = self.pyversion
        return b
