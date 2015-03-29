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


import os
from toxicbuild.core.exceptions import ConfigError
from toxicbuild.core.utils import load_module_from_file


class Settings:
    """ Simple interface to a settings file.
    """
    def __init__(self, envvar, default_filename):
        """:param envvar: Environment variable to look for settings file name
        :param default_filename: filename to use in case environment variable
        is not set.
        """
        self._envvar = envvar
        self._default_filename = default_filename
        self._settings_module = self._get_settings_module()

    @property
    def _filename(self):
        """ Returns the filename to use as settings module. Returns the filename
        on environment variable or ``self._default_filename``.
        """
        return self._get_settings_file_from_envvar() or self._default_filename

    def _get_settings_file_from_envvar(self):
        """
        Returns the value for the environment variable ``self._envvar``
        """
        settings_file = os.environ.get(self._envvar)

        return settings_file

    def _get_settings_module(self):
        """
        Returns the module to be used as the settings module.
        """
        module = load_module_from_file(self._filename)
        return module

    def __getattr__(self, attrname):
        try:
            attr = getattr(self._settings_module, attrname)
        except AttributeError:
            msg = 'Your settings {} file does not have an attribute {}.'.\
                  format(self._filename, attrname)
            raise ConfigError(msg)

        return attr

    def __setattr__(self, attrname, value):
        # haha!
        exceptions = ['_envvar', '_default_filename', '_settings_module']
        if attrname not in exceptions:
            raise AttributeError('you can\'t set here')

        super(Settings, self).__setattr__(attrname, value)
