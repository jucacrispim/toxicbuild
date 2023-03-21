# -*- coding: utf-8 -*-
# Copyright 2019, 2023 Juca Crispim <juca@poraodojuca.net>

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
from unittest.mock import patch, Mock, AsyncMock
from toxicbuild.core import build_config
from tests import async_test
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
                  AsyncMock(spec=build_config.get_toxicbuildconf_yaml,
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

    def test_list_builders_from_config_language(self):
        config = {'language': 'python',
                  'versions': ['3.6', '3.7']}

        builders = build_config.list_builders_from_config(config, 'master')
        self.assertEqual(len(builders), 2)

    def test_list_builders_from_config_no_branch(self):
        slave = Mock()
        slave.name = 'myslave'
        config = {'builders':
                  [{'name': 'b0'},
                   {'name': 'b1', 'branches': ['other'],
                    'slaves': ['other']},
                   {'name': 'b2',
                    'slaves': ['myslave'], 'branches': ['master']}]}
        builders = build_config.list_builders_from_config(
            config, slave=slave)
        self.assertEqual(len(builders), 2)
        self.assertNotIn({'name': 'b1', 'branch': 'other',
                          'slave': 'other'}, builders)

    def test_list_builders_from_config_no_branch_no_slave(self):
        slave = Mock()
        slave.name = 'myslave'
        config = {'builders':
                  [{'name': 'b0'},
                   {'name': 'b1', 'branches': ['other'],
                    'slaves': ['other']},
                   {'name': 'b2',
                    'slaves': ['myslave'], 'branches': ['master']}]}
        builders = build_config.list_builders_from_config(config)
        self.assertEqual(len(builders), 3)

    def test_load_config_py(self):
        conf = 'BLA = 1'
        conf = build_config.load_config('py', conf)
        self.assertEqual(conf.BLA, 1)

    def test_load_config_yml(self):
        conf = 'BLA: 1'
        conf = build_config.load_config('yml', conf)
        self.assertEqual(conf['BLA'], 1)


class APTPluginConfigTest(TestCase):

    def test_get_config(self):
        conf = {'system_packages': ['package']}
        expected = {'name': 'apt-install',
                    'packages': ['package']}
        plugin = build_config.APTPluginConfig(conf)
        self.assertEqual(expected, plugin.get_config())


class PythonPluginTest(TestCase):

    def test_get_config(self):
        conf = {'requirements_file': 'req.txt'}
        lang_ver = 'python3.5'
        expected = {'name': 'python-venv',
                    'pyversion': lang_ver,
                    'requirements_file': 'req.txt'}
        plugin = build_config.PythonPluginConfig(lang_ver, conf)
        self.assertEqual(expected, plugin.get_config())


class LanguageConfigTest(TestCase):

    def setUp(self):
        self.conf = {'language': 'some-lang',
                     'os': [],
                     'versions': []}

    def test_get_lang_versions_no_version(self):
        conf = build_config.LanguageConfig(self.conf)
        expected = ['some-lang']
        r = conf._get_lang_versions()

        self.assertEqual(expected, r)

    def test_get_lang_versions(self):
        self.conf['versions'] = ['1.1', '1.2']
        conf = build_config.LanguageConfig(self.conf)
        expected = ['some-lang1.1', 'some-lang1.2']
        r = conf._get_lang_versions()

        self.assertEqual(expected, r)

    def test_get_platforms(self):
        self.conf['os'] = ['redhat', 'debian']
        conf = build_config.LanguageConfig(self.conf)
        expected = [('some-lang', 'redhat', 'some-lang-redhat'),
                    ('some-lang', 'debian', 'some-lang')]
        lang_vers = conf._get_lang_versions()
        r = conf._get_platforms(lang_vers)

        self.assertEqual(expected, r)

    def test_get_platforms_docker(self):
        self.conf['os'] = ['redhat', 'debian']
        self.conf['docker'] = True
        conf = build_config.LanguageConfig(self.conf)
        expected = [('some-lang', 'redhat', 'docker-some-lang-redhat'),
                    ('some-lang', 'debian', 'docker-some-lang')]
        lang_vers = conf._get_lang_versions()
        r = conf._get_platforms(lang_vers)

        self.assertEqual(expected, r)

    def test_get_plugins_bad_os(self):
        os_name = 'a-bad-one'
        self.conf['system_packages'] = ['a-package']
        conf = build_config.LanguageConfig(self.conf)
        with self.assertRaises(build_config.ConfigError):
            conf._get_plugins(os_name, 'some-lang1.1')

    def test_get_plugins_ok_os(self):
        os_name = 'debian'
        self.conf['system_packages'] = ['a-package']
        conf = build_config.LanguageConfig(self.conf)
        r = conf._get_plugins(os_name, 'some-lang1.1')

        self.assertEqual(len(r), 1)

    def test_plugins_language(self):
        self.conf['language'] = 'python'
        os_name = 'debian'
        lang_ver = 'python3.7'
        conf = build_config.LanguageConfig(self.conf)
        r = conf._get_plugins(os_name, lang_ver)

        expected = [{'name': 'python-venv',
                     'pyversion': 'python3.7',
                     'requirements_file': 'requirements.txt'}]

        self.assertEqual(r, expected)

    def test_builders_already_exist(self):
        conf = build_config.LanguageConfig(self.conf)
        builders = [Mock()]
        conf._builders = builders

        self.assertEqual(builders, conf.builders)

    def test_builders(self):
        self.conf['versions'] = ['1.1', '1.2']
        self.conf['os'] = ['debian', 'redhat']
        conf = build_config.LanguageConfig(self.conf)

        builders = conf.builders

        self.assertEqual(len(builders), 4)
        self.assertTrue(builders[0]['envvars'] is not None)
