# -*- coding: utf-8 -*-

import os
import sys
from copy import copy
from twisted.python import log
from buildbot.config import BuilderConfig
from buildbot.config import MasterConfig as MasterConfigBase


class ConfigReader(object):
    def __init__(self, conf_in):

        try:
            self.config = self._read_config(conf_in)
            self.builders = self.getBuilders()
        except Exception as e:
            self.config = 'Config Error!'
            self.builders = [{'name': 'Config Error!'}]

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

        builders = localDict['builders']
        return {'builders': builders}

    def getBuilders(self):
        builders = []
        for b in self.config['builders']:
            builder = copy(b)
            builder['steps'] = self._getSteps(b)
            builders.append(builder)
        return builders

    def getBuilder(self, builder_name):
        for builder in self.builders:
            if builder['name'] == builder_name:
                return builder

    def _getSteps(self, builder):
        steps = builder['steps']
        steps_list = []
        for step in steps:
            s = copy(step)
            s['command'] = step['command'].split()
            steps_list.append(s)
        return steps_list


class MasterConfig(MasterConfigBase):
    def __init__(self):
        MasterConfigBase.__init__(self)
        self.db.update({'toxicbuild_db_url': 'sqlite:///toxicbuild.sqlite'})

    def check_single_master(self):  # pragma: no cover
        pass

    def load_db(self, filename, config_dict):
        MasterConfigBase.load_db(self, filename, config_dict)
        if 'db' in config_dict:
            if 'toxicbuild_db_url' in config_dict['db']:
                db_url = config_dict['db']['toxicbuild_db_url']
                self.db['toxicbuild_db_url'] = db_url


class DynamicBuilderConfig(BuilderConfig):
    def __init__(self, venv_path='venv', pyversion='/usr/bin/python3.4',
                 **kwargs):
        # argh!
        from toxicbuild.process.factory import DynamicBuildFactory

        factory = DynamicBuildFactory(venv_path, pyversion)
        kwargs['factory'] = factory
        BuilderConfig.__init__(self, **kwargs)
