# -*- coding: utf-8 -*-

import os
from buildbot import interfaces
from buildbot.process.build import Build
from buildbot.steps.source.git import Git
from buildbot.steps.shell import ShellCommand
from toxicbuild.db.models import RevisionConfig
from toxicbuild.config import ConfigReader


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
        revconf = RevisionConfig.get_revconf(branch, revision=revision)
        self.steps = self.get_steps(revconf)

        self.setStepFactories(self.steps)
        return Build.setupBuild(self, *args, **kwargs)

    def get_steps(self, revconf):
        # I think the 'right' place for it should be in the
        # BuildFactory class but the revision is not known there
        # so I need to do it here.
        steps = self.get_default_steps(revconf)
        config = ConfigReader(revconf.config)
        for cmd in config.steps:
            step = self.create_step(cmd)
            steps.append(step)

        return steps

    def create_step(self, cmd):
        env = self.get_step_env()
        scmd = ShellCommand(command=cmd, env=env)
        step = interfaces.IBuildStepFactory(scmd)
        return step

    def get_default_steps(self, revconf):
        env = self.get_step_env()
        git_step = interfaces.IBuildStepFactory(Git(name="checkout code",
                                                    repourl=revconf.repourl,
                                                    mode='incremental',
                                                    env=env))
        venv_cmd = ShellCommand(name='virtual env',
                                env=env,
                                command=['virtualenv', '%s' % self.venv_path,
                                         '--python=%s' % self.pyversion])
        venv_step = interfaces.IBuildStepFactory(venv_cmd)
        deps_step = interfaces.IBuildStepFactory(
            ShellCommand(name='install deps',
                         command=['pip', 'install', '-r', 'requirements.txt'],
                         env=env))

        steps = [git_step, venv_step, deps_step]
        return steps

    def get_step_env(self):
        bin_dir = os.path.join(os.path.abspath(self.venv_path), 'bin')

        env = {'PATH': [bin_dir, '${PATH}']}
        return env
