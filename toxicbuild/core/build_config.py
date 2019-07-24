# -*- coding: utf-8 -*-
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import os

import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from toxicbuild.core.exceptions import ConfigError
from toxicbuild.core.utils import (load_module_from_file, read_file,
                                   match_string)


def get_toxicbuildconf(directory):
    """Returns the toxicbuild.conf module.

    :param directory: Directory to look for toxicbuild.conf"""

    configfile = os.path.join(directory, 'toxicbuild.conf')
    return load_module_from_file(configfile)


async def get_toxicbuildconf_yaml(directory, filename='toxicbuild.yml'):
    """Returns the python objet representing the yaml build configuration.

    :param directory: The path of the directory containing the config file.
    :param filename: The actual name of the config file.
    """
    configfile = os.path.join(directory, filename)
    config = await read_file(configfile)
    try:
        return yaml.load(config, Loader=Loader)
    except yaml.scanner.ScannerError as e:
        err_msg = 'There is something wrong with your file. '
        err_msg += 'The original exception was:\n{}'.format(e.args[0])
        raise ConfigError(err_msg)


async def get_config(workdir, config_type, config_filename):
    """Returns the build configuration for a given repository.

    :param workdir: The directory where config file is located.
    :param config_type: Which type of configuration we are using,
      'py' or 'yaml'.
    :param config_filename: The filename of the config file.
    """

    if config_type == 'py':
        conf = get_toxicbuildconf(workdir)
    else:
        conf = await get_toxicbuildconf_yaml(workdir, config_filename)

    return conf


def _match_branch(branch, builder):
    if not branch or not builder.get('branches') or match_string(
            branch, builder.get('branches')):
        return True
    return False


def _match_slave(slave, builder):
    if not slave or not builder.get('slaves') or match_string(
            slave.name, builder.get('slaves')):
        return True
    return False


def list_builders_from_config(config, branch=None, slave=None,
                              config_type='yml'):
    """Lists builders from a build config

    :param config: The build configuration.
    :param branch: The branch for which builders are being listed.
    :param slave: The slave for which builders are being listed."""

    builders = []
    conf_builders = config.get('builders', [])

    if config.get('language'):
        conf_builders += LanguageConfig(config).builders

    for builder in conf_builders:

        if _match_branch(branch, builder) and _match_slave(slave, builder):
            builders.append(builder)

    return builders


class BasePluginConfig:
    """Plugin configs are meant to be used along with the LanguageConfig.
    Based in the toxicbuild.yml config we can create the build plugins
    configuration for a builder.

    .. note::

       The build plugins currently live in the slave but that is a very silly
       idea. In a future relase that's gonna change.

    """

    def __init__(self, conf):
        self.conf = conf


class APTPluginConfig(BasePluginConfig):

    def get_config(self):
        packages = self.conf.get('system_packages')
        return {'name': 'apt-install',
                'packages': packages}


class LanguagePluginConfig(BasePluginConfig):

    def __init__(self, lang_ver, conf):
        super().__init__(conf)
        self.lang_ver = lang_ver


class PythonPluginConfig(LanguagePluginConfig):

    def get_config(self):
        req = self.conf.get('requirements_file', 'requirements.txt')
        pyversion = self.lang_ver
        return {'name': 'python-venv',
                'pyversion': pyversion,
                'requirements_file': req}


class LanguageConfig:
    """An abstraction to create builders based in a language config
    in a toxicbuild.yml config file.
    """

    DEFAULT_OS = 'debian'

    SYSTEM_PACKAGES_PLUGINS = {'debian': APTPluginConfig,
                               'ubuntu': APTPluginConfig}

    LANGUAGE_PLUGINS = {'python': PythonPluginConfig}

    def __init__(self, conf):
        """Constructor for LanguageConfig.

        :param conf: The build config from the config file
        """

        self.conf = conf
        self.language = conf['language']
        self.oses = self.conf.get('os', [self.DEFAULT_OS])
        self.branches = self.conf.get('branches', [])
        self.versions = self.conf.get('versions', [])
        self._builders = None

    def _get_lang_versions(self):
        if not self.versions:
            lang_vers = [self.language]
        else:
            lang_vers = ['{}{}'.format(self.language, v)
                         for v in self.versions]
        return lang_vers

    def _get_platforms(self, lang_vers):
        plats = []
        for opsys in self.oses:
            for l in lang_vers:
                if opsys == self.DEFAULT_OS:
                    plats.append((l, opsys, l))
                else:
                    plats.append((l, opsys, '{}-{}'.format(l, opsys)))
        return plats

    def _get_plugins(self, os_name, lang_ver):
        plugins = []
        if 'system_packages' in self.conf:
            if os_name not in self.SYSTEM_PACKAGES_PLUGINS:
                raise ConfigError('OS {} is not supported yet!'.format(
                    os_name))

            plugins.append(
                self.SYSTEM_PACKAGES_PLUGINS[os_name](self.conf))

        if self.language in self.LANGUAGE_PLUGINS:
            plugins.append(self.LANGUAGE_PLUGINS[self.language](
                lang_ver, self.conf))

        return [p.get_config() for p in plugins]

    @property
    def builders(self):
        if self._builders is not None:
            return self._builders

        builders = []
        lang_vers = self._get_lang_versions()
        platforms = self._get_platforms(lang_vers)
        steps = self.conf.get('steps', [])
        envvars = self.conf.get('envvars', {})
        branches = self.conf.get('branches', [])
        for lang_ver, os_name, plat in platforms:
            builder = {'name': plat,
                       'platform': plat,
                       'steps': steps,
                       'envvars': envvars,
                       'plugins': self._get_plugins(os_name, lang_ver),
                       'branches': branches}
            builders.append(builder)

        self._builders = builders
        return self._builders
