# -*- coding: utf-8 -*-

from copy import copy
import yaml
from buildbot.config import BuilderConfig


class ConfigReader(object):
    def __init__(self, conf_in):
        self.config = yaml.load(conf_in)
        self.steps = self.parse_steps()

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
