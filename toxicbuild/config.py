# -*- coding: utf-8 -*-

import yaml
from buildbot.config import BuilderConfig


class ConfigReader(object):
    def __init__(self, conf_in):
        self.config = yaml.load(conf_in)
        self.steps = self.parse_steps()

    def parse_steps(self):
        steps = self.config['steps']
        steps_list = []
        for step in steps:
            steps_list.append(step.split())
        return steps_list


class DynamicBuilderConfig(BuilderConfig):
    def __init__(self, venv_path='venv', pyversion='/usr/bin/python3.4',
                 **kwargs):
        # argh!
        from toxicbuild.process.factory import DynamicBuildFactory

        factory = DynamicBuildFactory(venv_path, pyversion)
        kwargs['factory'] = factory
        BuilderConfig.__init__(self, **kwargs)
