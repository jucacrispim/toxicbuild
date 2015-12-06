# -*- coding: utf-8 -*-

# Copyright 2015 Juca Crispim <juca@poraodojuca.net>

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
import os
from toxicbuild.core import get_vcs
from toxicbuild.core.utils import get_toxicbuildconf
from toxicbuild.slave.build import Builder, BuildStep
from toxicbuild.slave.exceptions import BuilderNotFound
from toxicbuild.slave.plugins import Plugin


class BuildManager:

    """ A manager for remote build requests
    """

    def __init__(self, protocol, repo_url, vcs_type, branch, named_tree):
        self.protocol = protocol
        self.repo_url = repo_url
        self.vcs = get_vcs(vcs_type)(self.workdir)
        self.branch = branch
        self.named_tree = named_tree
        self._configmodule = None

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

    @asyncio.coroutine
    def update_and_checkout(self):
        """ Fetches changes on repository and checkout to ``self.named_tree``.
        If the repository was not cloned before, clones it first

        """
        if not self.vcs.workdir_exists():
            yield from self.vcs.clone(self.repo_url)

        yield from self.vcs.checkout(self.branch)
        yield from self.vcs.pull(self.branch)
        yield from self.vcs.checkout(self.named_tree)

    # the whole purpose of toxicbuild is this!
    # see the git history and look for the first versions.
    # First thing I changed on buildbot was to add the possibility
    # to load builers from a config file.
    def list_builders(self):
        """ Returns a list with all builders names for this branch
        based on toxicbuild.conf file
        """

        builders = [b['name'] for b in self.configmodule.BUILDERS
                    if (b.get('branch') == self.branch or b.get(
                        'branch')is None)]

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

        builder = Builder(self, bdict['name'], self.workdir)
        plugins_conf = bdict.get('plugins')
        if plugins_conf:
            builder.plugins = self._load_plugins(plugins_conf)

        for plugin in builder.plugins:
            builder.steps += plugin.get_steps_before()

        for sdict in bdict['steps']:
            sname, command = sdict['name'], sdict['command']
            step = BuildStep(sname, command)
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
