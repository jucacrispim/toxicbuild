# -*- coding: utf-8 -*-

import os
from buildbot import interfaces
from buildbot.process.build import Build
from buildbot.steps.source.git import Git
from buildbot.steps.shell import ShellCommand
from toxicbuild import master
from toxicbuild.config import ConfigReader
from toxicbuild.candies import Candy, CandyNotFound


class DynamicBuild(Build):
    """
    Build that creates per-buid config based steps.
    """
    def __init__(self, *args, **kwargs):
        self.venv_path = None
        self.pyversion = None
        Build.__init__(self, *args, **kwargs)

    def setupBuild(self, *args, **kwargs):
        revision = self.getProperty('revision')
        branch = self.getProperty('branch') or 'master'
        # I really need to block things here, otherwise
        # I would have to change lots of things to work
        # async.
        conn = master.TOXICDB.pool.engine.connect()
        revconf = master.TOXICDB.revisionconfig._getRevisionConfig(
            conn, branch, revision=revision)
        try:
            self.config = ConfigReader(revconf.config)
        except Exception as e:
            name = "Config Error!"
            self.steps = [self._createBombStep(name=name, exception=e)]
        else:
            self.builder_dict = self.config.getBuilder(self.builder.name)
            self.steps = self.getSteps()

        self.setStepFactories(self.steps)
        Build.setupBuild(self, *args, **kwargs)

    def getSteps(self):
        # I think the 'right' place for it should be in the
        # BuildFactory class but the revision is not known there
        # so I need to do it here.
        steps = self.getCandiesSteps()

        try:
            configured_steps = self.builder_dict['steps']
        except KeyError:
            e = Exception(
                'Steps not found for builder named %s' % self.builder.name)
            step_name = 'Config Error!'
            steps.append(self._createBombStep(name=step_name, exception=e))

        for cmd in configured_steps:
            try:
                step = self.create_step(cmd)
                steps.append(step)
            except Exception as e:
                step_name = 'Step config error!'
                steps.append(self._createBombStep(name=step_name, exception=e))

        return steps

    def getCandiesSteps(self):
        steps = []
        candies = self.builder_dict.get('candies')
        if not candies:
            return steps

        for cdict in candies:
            cname = cdict['name']
            try:
                candy_class = Candy.getCandy(cname)
            except CandyNotFound as e:
                step_name = 'Candy not found!'
                steps.append(self._createBombStep(name=step_name, exception=e))
                continue

            try:
                candy = candy_class(**cdict)
            except Exception as e:
                step_name = 'Candy config error!'
                steps.append(self._createBombStep(name=step_name, exception=e))

            try:
                steps += candy.getSteps()
            except NotImplementedError:
                pass

        return steps

    def create_step(self, cmd):
        env = self.get_step_env()
        scmd = ShellCommand(env=env, **cmd)
        step = interfaces.IBuildStepFactory(scmd)
        return step

    def get_step_env(self):
        bin_dir = os.path.join(self.venv_path, 'bin')

        env = {'PATH': [bin_dir, '${PATH}']}
        return env

    def _createBombStep(self, name, exception):
        bomb_step = BombStep(name=name, exception=exception)
        return interfaces.IBuildStepFactory(bomb_step)


class BombStep(ShellCommand):
    """
    Make a build be marked as exception
    """
    def __init__(self, *args, **kwargs):
        try:
            self.exception = kwargs['exception']
            del kwargs['exception']
        except KeyError:
            self.exception = Exception

        ShellCommand.__init__(self, *args, **kwargs)

    def startStep(self, *args, **kwargs):
        raise self.exception
