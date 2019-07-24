# -*- coding: utf-8 -*-

# Copyright 2015-2019 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import asyncio
from collections import defaultdict
import os
from toxicbuild.core import get_vcs
from toxicbuild.core.build_config import (list_builders_from_config,
                                          get_toxicbuildconf_yaml)
from toxicbuild.core.utils import (LoggerMixin,
                                   ExecCmdError, match_string)
from toxicbuild.slave import settings
from toxicbuild.slave.build import Builder
from toxicbuild.slave.docker import DockerContainerBuilder
from toxicbuild.slave.exceptions import (BuilderNotFound, BadBuilderConfig,
                                         BusyRepository)


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
                 config_type='yml', config_filename='toxicbuild.yml',
                 builders_from=None):
        """
        :param manager: instance of :class:`toxicbuild.slave.BuildManager.`
        :param repo_url: The repository URL
        :param vcs_type: Type of vcs used in the repository.
        :param branch: Which branch to use in the build.
        :param named_tree: A tag, commit, branch name...
        :param config_type: The type of config used. 'py' or 'yaml'.
        :param config_filename: The name of the build config file.
        :param builders_from: If not None, builders to this branch will be used
          instead of builders for the current branch.
        """
        self.protocol = protocol
        self.repo_url = repo_url
        self.vcs_type = vcs_type
        self.vcs = get_vcs(vcs_type)(self.workdir)
        self.branch = branch
        self.named_tree = named_tree
        self.config_type = config_type
        self.config_filename = config_filename
        self.builders_from = builders_from
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
        """ Loads a builder from toxicbuild.(conf|yml). If a container
        is to be used for the build, returns a container builder
        instance. Otherwise, return a Builder instance.

        :param name: builder name
        """
        builders_branch = self.builders_from or self.branch

        try:
            builders = list_builders_from_config(self.config,
                                                 branch=builders_branch,
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
            builder_cls = DockerContainerBuilder
        else:
            builder_cls = Builder

        # this envvars are used in all steps in this builder
        builder_envvars = bdict.get('envvars', {})
        builder_envvars['COMMIT_SHA'] = self.named_tree
        builder = builder_cls(self, bdict, self.workdir, platform,
                              remove_env=remove_env, **builder_envvars)

        return builder

    # kind of wierd place for this thing
    @asyncio.coroutine
    def send_info(self, info):
        yield from self.protocol.send_response(code=0, body=info)

    def log(self, msg, level='info'):
        msg = '[{}]{}'.format(self.repo_url, msg)
        super().log(msg, level=level)
