# -*- coding: utf-8 -*-

# Copyright 2015-2018 Juca Crispim <juca@poraodojuca.net>

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
from toxicbuild.core.utils import (get_toxicbuildconf, LoggerMixin,
                                   ExecCmdError, match_string,
                                   list_builders_from_config,
                                   get_toxicbuildconf_yaml)
from toxicbuild.slave import settings
from toxicbuild.slave.build import Builder, BuildStep
from toxicbuild.slave.docker import DockerContainerBuilder
from toxicbuild.slave.exceptions import (BuilderNotFound, BadBuilderConfig,
                                         BusyRepository, BadPluginConfig)
from toxicbuild.slave.plugins import SlavePlugin


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

    def __init__(self, protocol, repo_url, vcs_type, branch, named_tree,
                 config_type='py', config_filename='toxicbuild.conf'):
        self.protocol = protocol
        self.repo_url = repo_url
        self.vcs_type = vcs_type
        self.vcs = get_vcs(vcs_type)(self.workdir)
        self.branch = branch
        self.named_tree = named_tree
        self.config_type = config_type
        self.config_filename = config_filename
        self._config = None

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
    def config(self):
        return self._config

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

    async def load_config(self):
        if self.config_type == 'py':
            self._config = get_toxicbuildconf(self.workdir)
        else:
            self._config = await get_toxicbuildconf_yaml(self.workdir,
                                                         self.config_filename)

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
    def update_and_checkout(self, work_after_wait=True, external=None):
        """ Updates ``self.branch`` and checkout to ``self.named_tree``.

        :param work_after_wait: Indicates if we should update and checkout
          after waiting for other instance finishes its job.
        :param external: Info about a remote repository if the build should
          be executed with changes from a remote repo.
        """

        if self.is_working:
            yield from self.wait_all()
            if not work_after_wait:
                yield from self.load_config()
                return

        try:
            self.is_updating = True
            if not self.vcs.workdir_exists():
                self.log('cloning {}'.format(self.repo_url))
                yield from self.vcs.clone(self.repo_url)

            if hasattr(self.vcs, 'update_submodule'):  # pragma no branch
                self.log('updating submodule', level='debug')
                yield from self.vcs.update_submodule()

            if external:
                url = external['url']
                name = external['name']
                branch = external['branch']
                into = external['into']
                yield from self.vcs.import_external_branch(url, name, branch,
                                                           into)
            else:
                # we need to try_set_remote so if the url has changed, we
                # change it before trying fetch/checkout stuff
                yield from self.vcs.try_set_remote(self.repo_url)

            # first we try to checkout to the named_tree because if if
            # already exists here we don't need to update the code.
            try:
                self.log('checking out to named_tree {}'.format(
                    self.named_tree), level='debug')
                yield from self.vcs.checkout(self.named_tree)
            except ExecCmdError:
                # this is executed when the named_tree does not  exist
                # so we upate the code and then checkout again.
                self.log('named_tree does not exist. updating...')
                yield from self.vcs.get_remote_branches()
                self.log('checking out to branch {}'.format(self.branch),
                         level='debug')
                yield from self.vcs.checkout(self.branch)
                yield from self.vcs.pull(self.branch)
                self.log('checking out to named_tree {}'.format(
                    self.named_tree), level='debug')
                yield from self.vcs.checkout(self.named_tree)

        finally:
            self.is_updating = False

        yield from self.load_config()

    def _branch_match(self, builder):
        return builder.get('branch') is None or match_string(
            self.branch, [builder.get('branch', '')])

    # the whole purpose of toxicbuild is this!
    # see the git history and look for the first versions.
    # First thing I changed on buildbot was to add the possibility
    # to load builers from a config file.
    def list_builders(self):
        """ Returns a list with all builders names for this branch
        based on build config file
        """
        builders = list_builders_from_config(self.config,
                                             config_type=self.config_type)

        try:
            builders = [b['name'] for b in builders]
        except KeyError as e:
            key = str(e)
            msg = 'Your builder config does not have a required key {}'.format(
                key)
            raise BadBuilderConfig(msg)

        return builders

    async def load_builder(self, name):
        """ Load a builder from toxicbuild.conf. If a container
        is to be used in for the build, returns a container builder
        instance. Otherwise, return a Builder instance.

        :param name: builder name
        """
        try:
            builders = list_builders_from_config(self.config,
                                                 branch=self.branch,
                                                 config_type=self.config_type)
            bdict = [b for b in builders if b['name'] == name][0]
        except IndexError:
            msg = 'builder {} does not exist for {} branch {}'.format(
                name, self.repo_url, self.branch)
            raise BuilderNotFound(msg)

        platform = bdict.get('platform', 'linux-generic')
        remove_env = bdict.get('remove_env', True)
        # now we have all we need to instanciate the container builder if
        # needed.
        if settings.USE_DOCKER:
            builder = DockerContainerBuilder(
                self, platform, self.repo_url,
                self.vcs_type, self.branch,
                self.named_tree,
                name, self.workdir,
                remove_env=remove_env,
                config_type=self.config_type,
                config_filename=self.config_filename)
        else:
            # this envvars are used in all steps in this builder
            builder_envvars = bdict.get('envvars', {})
            builder = Builder(self, bdict['name'], self.workdir, platform,
                              remove_env=remove_env, **builder_envvars)
            builder.steps = await self._get_builder_steps(builder, bdict)

        return builder

    async def _get_builder_steps(self, builder, bdict):
        plugins_conf = bdict.get('plugins')
        steps = []

        if plugins_conf:
            builder.plugins = await self._load_plugins(plugins_conf)

        for plugin in builder.plugins:
            steps += plugin.get_steps_before()

        for sdict in bdict['steps']:
            if isinstance(sdict, str):
                sdict = {'name': sdict,
                         'command': sdict}
            step = BuildStep(**sdict)
            steps.append(step)

        for plugin in builder.plugins:
            steps += plugin.get_steps_after()

        return steps

    # kind of wierd place for this thing
    @asyncio.coroutine
    def send_info(self, info):
        yield from self.protocol.send_response(code=0, body=info)

    def log(self, msg, level='info'):
        msg = '[{}]{}'.format(self.repo_url, msg)
        super().log(msg, level=level)

    async def _load_plugins(self, plugins_config):
        """ Returns a list of :class:`toxicbuild.slave.plugins.Plugin`
        subclasses based on the plugins listed on the config for a builder.
        """

        plist = []
        for pdict in plugins_config:
            try:
                plugin_class = SlavePlugin.get_plugin(pdict['name'])
            except KeyError:
                msg = 'Your plugin config {} does not have a name'.format(
                    pdict)
                raise BadPluginConfig(msg)
            del pdict['name']
            plugin = plugin_class(**pdict)
            if getattr(plugin, 'uses_data_dir', False):
                await plugin.create_data_dir()
            plist.append(plugin)
        return plist
