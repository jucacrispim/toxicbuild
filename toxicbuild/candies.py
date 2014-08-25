# -*- coding: utf-8 -*-

import os
from buildbot import interfaces
from buildbot.steps.shell import ShellCommand
from buildbot.steps.source.git import Git
from toxicbuild.exceptions import CandyNotFound


class Candy(object):
    """
    Candies are collections of steps for common tasks.
    """

    name = 'Candy'

    def __init__(*args, **kwargs):
        pass

    def getSteps(self):
        """
        Returns a list of steps to be used a build
        """
        raise NotImplementedError

    def getEnv(self):
        """
        Returns a dictionary with the environment variables
        to be used. Use the buildbot's steps env dict syntax.
        """

        raise NotImplementedError

    @classmethod
    def getCandies(cls):
        return cls.__subclasses__()

    @classmethod
    def getCandy(cls, candy_name):
        for candy in cls.getCandies():
            if candy.name == candy_name:
                return candy

        raise CandyNotFound('Candy %s does not exist' % candy_name)


class PythonVirtualenv(Candy):
    """
    Candy for python projects using virtualenv.
    It has steps to create a new virtualenv and install
    dependencies using pip and a requirements.txt file.
    """

    name = 'python-virtualenv'

    def __init__(self, **kwargs):
        if not kwargs.has_key('venv_path') or not kwargs.has_key('pyversion'):
            raise Exception('venv_path and pyversion params are mandatory')

        self.venv_path = kwargs.get('venv_path')
        self.pyversion = kwargs.get('pyversion')

    def getSteps(self):
        env = self.getEnv()
        create_env = ShellCommand(
            name='Creating virtualenv at %s' % self.venv_path,
            command=['virtualenv', '%s' % self.venv_path,
                     '--python=%s' % self.pyversion],
            env=env)

        install_deps = ShellCommand(
            name='Installing dependencies with pip',
            command=['pip', 'install', '-r', 'requirements.txt'],
            env=env)

        steps = [interfaces.IBuildStepFactory(create_env),
                 interfaces.IBuildStepFactory(install_deps)]

        return steps

    def getEnv(self):
        bin_dir = os.path.join(self.venv_path, 'bin')
        env = {'PATH': [bin_dir, '${PATH}']}
        return env


class GitUpdateAndCheckout(Candy):
    name = 'git-update-and-checkout'

    def __init__(self, **kwargs):
        if not kwargs.has_key('repourl') or not kwargs.has_key('named_tree'):
            raise Exception('repourl and named_tree params are mandatory')

        self.repourl = kwargs.get('repourl')
        self.named_tree = kwargs.get('named_tree')

    def getSteps(self):
        update = Git(
            name="updating code at %s" % self.repourl,
            repourl=self.repourl,
            mode='incremental')

        checkout = ShellCommand(
            name="Checking out to %s" % self.named_tree,
            command=['git', 'checkout', '%s' % self.named_tree])

        steps = [interfaces.IBuildStepFactory(update),
                 interfaces.IBuildStepFactory(checkout)]

        return steps
