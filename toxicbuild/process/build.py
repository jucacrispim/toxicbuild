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
        self.builder_dict = {}
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

        self.config = ConfigReader(revconf.config)

        try:
            self.builder_dict = self.config.getBuilder(self.builder.name)
        except Exception as e:
            name = "Config Error!"
            self.steps = [self._createBombStep(name=name, exception=e)]
        else:
            self.steps = self.getSteps()

        self.setStepFactories(self.steps)
        Build.setupBuild(self, *args, **kwargs)

    def getSteps(self):
        # I think the 'right' place for it should be in the
        # BuildFactory class but the revision is not known there
        # so I need to do it here.
        steps = self.getCandiesSteps()

        configured_steps = self.builder_dict['steps']
        for cmd in configured_steps:
            step = self.create_step(cmd)
            steps.append(step)
        return steps

    def getCandiesSteps(self):
        steps = []
        try:
            candies = self.getCandies()
        except Exception as e:
            step_name = 'Candy config error!'
            step = BombStep(name=step_name, exception=e)
            steps.append(interfaces.IBuildStepFactory(step))
            candies = []

        for candy in candies:
            try:
                steps += candy.getSteps()
            except NotImplementedError:
                pass

        return steps

    def getCandies(self):
        candies = []
        candies_config = self.builder_dict.get('candies') or []
        if not candies_config:
            return candies

        for cdict in candies_config:
            cname = cdict['name']
            candy_class = Candy.getCandy(cname)
            candy = candy_class(**cdict)
            candies.append(candy)

        return candies

    def create_step(self, cmd):
        env = self.get_step_env()
        scmd = ShellCommand(env=env, **cmd)
        step = interfaces.IBuildStepFactory(scmd)
        return step

    def get_step_env(self):
        env = {}
        for candy in self.getCandies():
            try:
                env.update(candy.getEnv())
            except NotImplementedError:
                pass

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
