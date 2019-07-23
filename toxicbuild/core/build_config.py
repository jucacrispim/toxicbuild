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
                              config_type='py'):
    """Lists builders from a build config

    :param config: The build configuration.
    :param branch: The branch for which builders are being listed.
    :param slave: The slave for which builders are being listed."""

    builders = []
    if config_type == 'py':
        conf_builders = config.BUILDERS
    else:
        conf_builders = config['builders']
    for builder in conf_builders:

        if _match_branch(branch, builder) and _match_slave(slave, builder):
            builders.append(builder)

    return builders
