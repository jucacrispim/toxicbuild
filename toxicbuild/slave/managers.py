# -*- coding: utf-8 -*-

# Copyright 2015-2016 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import asyncio
from collections import defaultdict
import os
from toxicbuild.core import get_vcs
from toxicbuild.core.utils import get_toxicbuildconf, LoggerMixin
from toxicbuild.slave.build import Builder, BuildStep
from toxicbuild.slave.exceptions import (BuilderNotFound, BadBuilderConfig,
                                         BusyRepository)
from toxicbuild.slave.plugins import Plugin


class BuildManager(LoggerMixin):

    """ A manager for remote build requests
    """

    # repositories that are being cloned
    cloning_repos = set()
    # repositories that are being updated
    updating_repos = set()
    # repositories that are building something.
    # key is repo_url and value is named_tree
    building_repos = defaultdict(lambda: None)  # pragma no branch WTF??

    def __init__(self, protocol, repo_url, vcs_type, branch, named_tree):
        self.protocol = protocol
        self.repo_url = repo_url
        self.vcs = get_vcs(vcs_type)(self.workdir)
        self.branch = branch
        self.named_tree = named_tree
        self._configmodule = None

    def __enter__(self):
        if self.current_build and self.current_build != self.named_tree:
            msg = '{} is busy at {}. Can\'t work at {}'.format(
                self.repo_url, self.current_build, self.named_tree)
            raise BusyRepository(msg)

        self.current_build = self.named_tree
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.current_build = None

    @property
    def configmodule(self):
        if not self._configmodule:  # pragma: no branch
            self._configmodule = get_toxicbuildconf(self.workdir)
        return self._configmodule

    @property
    def workdir(self):
        """ The directory where the source code of this repository is
        cloned into
        """
        workdir = self.repo_url.replace('/', '-').replace('@', '').replace(
            ':', '')
        return os.path.join('src', workdir)

    @property
    def current_build(self):
        return type(self).building_repos.get(self.repo_url)

    @current_build.setter
    def current_build(self, value):
        type(self).building_repos[self.repo_url] = value

    @property
    def is_cloning(self):
        """Informs if this repository is being cloned."""

        return self.repo_url in type(self).cloning_repos

    @is_cloning.setter
    def is_cloning(self, value):
        if value is True:
            type(self).cloning_repos.add(self.repo_url)
        else:
            type(self).cloning_repos.discard(self.repo_url)

    @property
    def is_updating(self):
        """Informs it this repository is fetching changes"""
        return self.repo_url in type(self).updating_repos

    @is_updating.setter
    def is_updating(self, value):
        if value is True:
            type(self).updating_repos.add(self.repo_url)
        else:
            type(self).updating_repos.discard(self.repo_url)

    @property
    def is_working(self):
        """Informs if this repository is cloning or updating"""
        return self.is_cloning or self.is_updating

    @asyncio.coroutine
    def wait_clone(self):
        """Wait until the repository clone is complete."""

        while self.is_cloning:
            yield from asyncio.sleep(1)

    @asyncio.coroutine
    def wait_update(self):
        """Wait until the repository update is complete."""

        while self.is_updating:
            yield from asyncio.sleep(1)

    @asyncio.coroutine
    def wait_all(self):
        """Wait until clone and update are done."""

        while self.is_working:
            yield from asyncio.sleep(1)

    @asyncio.coroutine
    def update_and_checkout(self):
        """ Tries to checkout to ``self.named_tree``, if it does not
        exisit, fetches changes from the repository.
        If the repository was not cloned before, clones it first
        """

        if self.is_working:
            yield from self.wait_all()

        if not self.vcs.workdir_exists():
            yield from self.vcs.clone(self.repo_url)

        self.log('checking out to branch {}'.format(self.branch),
                 level='debug')
        yield from self.vcs.checkout(self.branch)
        yield from self.vcs.pull(self.branch)
        self.log('checking out to named_tree {}'.format(self.named_tree),
                 level='debug')
        yield from self.vcs.checkout(self.named_tree)

    # the whole purpose of toxicbuild is this!
    # see the git history and look for the first versions.
    # First thing I changed on buildbot was to add the possibility
    # to load builers from a config file.
    def list_builders(self):
        """ Returns a list with all builders names for this branch
        based on toxicbuild.conf file
        """

        try:
            builders = [b['name'] for b in self.configmodule.BUILDERS
                        if (b.get('branch') == self.branch or b.get(
                            'branch')is None)]
        except KeyError as e:
            key = str(e)
            msg = 'Your builder config does not have a required key'.format(
                key)
            raise BadBuilderConfig(msg)

        return builders

    def load_builder(self, name):
        """ Load a builder from toxicbuild.conf
        :param name: builder name
        """

        try:
            bdict = [b for b in self.configmodule.BUILDERS if (b.get(
                'branch') is None and b['name'] == name) or (b.get(
                    'branch') == self.branch and b['name'] == name)][0]
        except IndexError:
            msg = 'builder {} does not exist for {} branch {}'.format(
                name, self.repo_url, self.branch)
            raise BuilderNotFound(msg)

        # this envvars are used in all steps in this builder
        builder_envvars = bdict.get('envvars', {})
        builder = Builder(self, bdict['name'], self.workdir, **builder_envvars)
        plugins_conf = bdict.get('plugins')
        if plugins_conf:
            builder.plugins = self._load_plugins(plugins_conf)

        for plugin in builder.plugins:
            builder.steps += plugin.get_steps_before()

        for sdict in bdict['steps']:
            step = BuildStep(**sdict)
            builder.steps.append(step)

        for plugin in builder.plugins:
            builder.steps += plugin.get_steps_after()

        return builder

    # kind of wierd place for this thing
    @asyncio.coroutine
    def send_info(self, info):
        yield from self.protocol.send_response(code=0, body=info)

    def _load_plugins(self, plugins_config):
        """ Returns a list of :class:`toxicbuild.slave.plugins.Plugin`
        subclasses based on the plugins listed on the config for a builder.
        """

        plist = []
        for pdict in plugins_config:
            plugin_class = Plugin.get(pdict['name'])
            del pdict['name']
            plugin = plugin_class(**pdict)
            plist.append(plugin)
        return plist
