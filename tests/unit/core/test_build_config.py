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

from unittest import TestCase
from unittest.mock import patch, Mock
from toxicbuild.core import build_config
from tests import async_test, AsyncMagicMock
from tests.unit.core import TEST_DATA_DIR


class BuildConfigTest(TestCase):

    @async_test
    async def test_get_toxicbuildconf_yaml_not_found(self):
        with self.assertRaises(FileNotFoundError):
            await build_config.get_toxicbuildconf_yaml('/i/dont/exist')

    @async_test
    async def test_get_toxicbuildconf_yaml_with_some_error(self):
        with self.assertRaises(build_config.ConfigError):
            await build_config.get_toxicbuildconf_yaml(
                TEST_DATA_DIR, 'toxicbuild_error.yml')

    @async_test
    async def test_get_toxicbuildconf_yaml(self):
        config = await build_config.get_toxicbuildconf_yaml(TEST_DATA_DIR)
        self.assertTrue(config['builders'][0])

    @patch.object(build_config, 'get_toxicbuildconf',
                  Mock(spec=build_config.get_toxicbuildconf))
    @async_test
    async def test_get_config_py(self):
        conf = await build_config.get_config('/some/workdir', 'py',
                                             'toxicbuild.conf')
        self.assertTrue(build_config.get_toxicbuildconf.called)
        self.assertTrue(conf)

    @patch.object(build_config, 'get_toxicbuildconf_yaml',
                  AsyncMagicMock(spec=build_config.get_toxicbuildconf_yaml,
                                 return_value=True))
    @async_test
    async def test_get_config_yaml(self):
        conf = await build_config.get_config('/some/workdir', 'yaml',
                                             'toxicbuild.yml')
        self.assertTrue(build_config.get_toxicbuildconf_yaml.called)
        self.assertTrue(conf)

    @patch.object(build_config, 'load_module_from_file', Mock())
    def test_get_toxicbuildconf(self):
        build_config.get_toxicbuildconf('/some/dir/')
        called_conffile = build_config.load_module_from_file.call_args[0][0]
        self.assertTrue(build_config.load_module_from_file.called)
        self.assertEqual(called_conffile, '/some/dir/toxicbuild.conf')

    def test_list_builders_from_config(self):
        confmodule = Mock()
        slave = Mock()
        slave.name = 'myslave'
        confmodule.BUILDERS = [{'name': 'b0'},
                               {'name': 'b1', 'branches': ['otheir']},
                               {'name': 'b2',
                                'slaves': ['myslave'],
                                'branches': ['mast*', 'release']},
                               {'name': 'b3', 'slaves': ['otherslave']}]
        builders = build_config.list_builders_from_config(
            confmodule, 'master', slave)
        self.assertEqual(len(builders), 2)
        self.assertNotIn({'name': 'b1', 'branch': 'other'}, builders)

    def test_list_builders_from_config_yaml(self):
        slave = Mock()
        slave.name = 'myslave'
        config = {'builders':
                  [{'name': 'b0'},
                   {'name': 'b1', 'branches': ['otheir']},
                   {'name': 'b2',
                    'slaves': ['myslave'],
                    'branches': ['mast*', 'release']},
                   {'name': 'b3', 'slaves': ['otherslave']}]}
        builders = build_config.list_builders_from_config(config, 'master',
                                                          slave,
                                                          config_type='yaml')
        self.assertEqual(len(builders), 2)
        self.assertNotIn({'name': 'b1', 'branch': 'other'}, builders)

    def test_list_builders_from_config_no_branch(self):
        confmodule = Mock()
        slave = Mock()
        slave.name = 'myslave'
        confmodule.BUILDERS = [{'name': 'b0'},
                               {'name': 'b1', 'branches': ['other'],
                                'slaves': ['other']},
                               {'name': 'b2',
                                'slaves': ['myslave'], 'branches': ['master']}]
        builders = build_config.list_builders_from_config(
            confmodule, slave=slave)
        self.assertEqual(len(builders), 2)
        self.assertNotIn({'name': 'b1', 'branch': 'other',
                          'slave': 'other'}, builders)

    def test_list_builders_from_config_no_branch_no_slave(self):
        confmodule = Mock()
        slave = Mock()
        slave.name = 'myslave'
        confmodule.BUILDERS = [{'name': 'b0'},
                               {'name': 'b1', 'branches': ['other'],
                                'slaves': ['other']},
                               {'name': 'b2',
                                'slaves': ['myslave'], 'branches': ['master']}]
        builders = build_config.list_builders_from_config(confmodule)
        self.assertEqual(len(builders), 3)
