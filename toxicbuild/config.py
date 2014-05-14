# -*- coding: utf-8 -*-

import os
import sys
from copy import copy
from buildbot.config import BuilderConfig


class ConfigReader(object):
    def __init__(self, conf_in):

        self.config = self._read_config(conf_in)
        self.steps = self.parse_steps()

    def _read_config(self, conf_in):
        localDict = {
            'basedir': os.path.expanduser('.'),
            '__file__': os.path.abspath('nothinghere'),
        }
        old_sys_path = sys.path[:]
        sys.path.append(localDict)
        try:
            exec conf_in in localDict
        finally:
            sys.path[:] = old_sys_path

        return localDict['steps']

    def parse_steps(self):
        steps = self.config
        steps_list = []
        for step in steps:
            s = copy(step)
            s['command'] = step['command'].split()
            steps_list.append(s)
        return steps_list


class DynamicBuilderConfig(BuilderConfig):
    def __init__(self, venv_path='venv', pyversion='/usr/bin/python3.4',
                 **kwargs):
        # argh!
        from toxicbuild.process.factory import DynamicBuildFactory

        factory = DynamicBuildFactory(venv_path, pyversion)
        kwargs['factory'] = factory
        BuilderConfig.__init__(self, **kwargs)
