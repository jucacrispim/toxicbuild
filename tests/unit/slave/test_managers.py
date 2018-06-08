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
import os
from unittest import TestCase
from unittest.mock import patch, MagicMock, Mock
import tornado
from toxicbuild.core.utils import load_module_from_file
from toxicbuild.slave import plugins, managers
from tests.unit.slave import TEST_DATA_DIR
from tests import async_test, AsyncMagicMock

TOXICCONF = os.path.join(TEST_DATA_DIR, 'toxicbuild.conf')
TOXICCONF = load_module_from_file(TOXICCONF)

BADTOXICCONF = os.path.join(TEST_DATA_DIR, 'badtoxicbuild.conf')
BADTOXICCONF = load_module_from_file(BADTOXICCONF)


@patch.object(managers, 'get_toxicbuildconf',
              Mock(return_value=TOXICCONF))
class BuilderManagerTest(TestCase):

    @patch.object(managers, 'get_vcs', MagicMock())
    @async_test
    async def setUp(self):
        super().setUp()
        protocol = MagicMock()

        @asyncio.coroutine
        def s(*a, **kw):
            pass

        protocol.send_response = s

        self.manager = managers.BuildManager(protocol, 'git@repo.git', 'git',
                                             'master', 'v0.1')

    def tearDown(self):
        managers.BuildManager.cloning_repos = set()
        managers.BuildManager.updating_repos = set()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    def test_is_cloning_without_clone(self):
        manager = managers.BuildManager(MagicMock(), 'git@repo.git', 'git',
                                        'master', 'v0.1')

        manager.is_cloning = False

        self.assertFalse(self.manager.is_cloning)

    def test_is_cloning(self):
        try:
            manager = managers.BuildManager(MagicMock(), 'git@repo.git', 'git',
                                            'master', 'v0.1')

            manager.is_cloning = True

            self.assertTrue(self.manager.is_cloning)

        finally:
            managers.BuildManager.cloning_repos = set()

    def test_is_updating_without_update(self):
        manager = managers.BuildManager(MagicMock(), 'git@repo.git', 'git',
                                        'master', 'v0.1')

        manager.is_updating = False

        self.assertFalse(self.manager.is_updating)

    def test_is_updating(self):
        manager = managers.BuildManager(MagicMock(), 'git@repo.git', 'git',
                                        'master', 'v0.1')

        manager.is_updating = True

        self.assertTrue(self.manager.is_updating)

    def test_is_working_with_clone(self):
        manager = managers.BuildManager(MagicMock(), 'git@repo.git', 'git',
                                        'master', 'v0.1')

        manager.is_cloning = True

        self.assertTrue(self.manager.is_working)

    def test_is_working_with_update(self):
        manager = managers.BuildManager(MagicMock(), 'git@repo.git', 'git',
                                        'master', 'v0.1')

        manager.is_updating = True

        self.assertTrue(self.manager.is_working)

    def test_is_working_not_working(self):
        manager = managers.BuildManager(MagicMock(), 'git@repo.git', 'git',
                                        'master', 'v0.1')

        manager.is_updating = False
        manager.is_cloning = False

        self.assertFalse(self.manager.is_working)

    def test_current_build(self):
        manager = managers.BuildManager(MagicMock(), 'git@repo.git', 'git',
                                        'master', 'v0.1')
        try:
            manager.current_build = 'v0.1'
            self.assertEqual(
                managers.BuildManager.building_repos[manager.repo_url], 'v0.1')
            self.assertTrue(manager.current_build)
        finally:
            manager.current_build = None

    def test_current_build_without_build(self):
        manager = managers.BuildManager(MagicMock(), 'git@repo.git', 'git',
                                        'master', 'v0.1')
        self.assertIsNone(manager.current_build)

    def test_enter_with_other_current_build(self):
        manager = managers.BuildManager(MagicMock(), 'git@repo.git', 'git',
                                        'master', 'v0.1')
        manager.current_build = 'v0.1.1'
        with self.assertRaises(managers.BusyRepository):
            with manager as m:
                del m

    def test_enter_with_same_current_build(self):
        manager = managers.BuildManager(MagicMock(), 'git@repo.git', 'git',
                                        'master', 'v0.1')
        manager.current_build = 'v0.1'
        with manager as m:
            self.assertEqual(m.current_build, 'v0.1')

    def test_enter_without_current_build(self):
        manager = managers.BuildManager(MagicMock(), 'git@repo.git', 'git',
                                        'master', 'v0.1')
        with manager as m:
            self.assertEqual(m.current_build, 'v0.1')

    @async_test
    def test_wait_clone(self):
        class TBM(managers.BuildManager):
            clone_called = False
            call_count = -1

            @property
            def is_cloning(self):
                self.clone_called = True
                self.call_count += 1
                return [True, False][self.call_count]

        manager = TBM(MagicMock(), 'git@repo.git', 'git', 'master', 'v0.1')
        yield from manager.wait_clone()

        self.assertTrue(manager.clone_called)

    @async_test
    def test_wait_update(self):
        class TBM(managers.BuildManager):
            update_called = False
            call_count = -1

            @property
            def is_updating(self):
                self.update_called = True
                self.call_count += 1
                return [True, False][self.call_count]

        manager = TBM(MagicMock(), 'git@repo.git', 'git', 'master', 'v0.1')
        yield from manager.wait_update()

        self.assertTrue(manager.update_called)

    @async_test
    def test_wait_all(self):
        class TBM(managers.BuildManager):
            working_called = False
            call_count = -1

            @property
            def is_working(self):
                self.working_called = True
                self.call_count += 1
                return [True, False][self.call_count]

        manager = TBM(MagicMock(), 'git@repo.git', 'git', 'master', 'v0.1')
        yield from manager.wait_all()

        self.assertTrue(manager.working_called)

    @async_test
    def test_update_and_checkout_with_clone(self):
        self.manager.vcs.workdir_exists.return_value = False
        self.manager.vcs.checkout = MagicMock()
        self.manager.vcs.try_set_remote = AsyncMagicMock()
        yield from self.manager.update_and_checkout()

        self.assertTrue(self.manager.vcs.clone.called)
        self.assertTrue(self.manager.vcs.checkout.called)
        self.assertTrue(self.manager.vcs.try_set_remote.called)

    @async_test
    def test_update_and_checkout_external(self):
        self.manager.vcs.workdir_exists.return_value = True
        self.manager.vcs.checkout = MagicMock()
        self.manager.vcs.try_set_remote = AsyncMagicMock()
        self.manager.vcs.import_external_branch = AsyncMagicMock(
            spec=self.manager.vcs.import_external_branch)

        external = {'url': 'http://bla.com/bla.git',
                    'name': 'remote', 'branch': 'master',
                    'into': 'into'}
        yield from self.manager.update_and_checkout(external=external)

        self.assertFalse(self.manager.vcs.clone.called)
        self.assertTrue(self.manager.vcs.checkout.called)
        self.assertFalse(self.manager.vcs.try_set_remote.called)
        self.assertTrue(self.manager.vcs.import_external_branch.called)

    @patch.object(managers.BuildManager, 'is_working', MagicMock())
    @patch.object(managers.BuildManager, 'wait_all', MagicMock())
    @async_test
    def test_update_and_checkout_working(self):
        yield from self.manager.update_and_checkout()

        self.assertTrue(self.manager.wait_all.called)

    @async_test
    def test_update_and_checkout_without_clone(self):
        self.manager.vcs.clone = MagicMock()
        self.manager.vcs.checkout = MagicMock()
        self.manager.vcs.workdir_exists.return_value = True

        yield from self.manager.update_and_checkout()

        self.assertFalse(self.manager.vcs.clone.called)
        self.assertTrue(self.manager.vcs.checkout.called)

    @patch.object(managers.BuildManager, 'is_working', MagicMock())
    @patch.object(managers.BuildManager, 'wait_all', MagicMock())
    @async_test
    def test_update_and_checkout_working_not_wait(self):
        self.manager.vcs.checkout = Mock()
        yield from self.manager.update_and_checkout(work_after_wait=False)

        self.assertTrue(self.manager.wait_all.called)
        self.assertFalse(self.manager.vcs.checkout.called)

    @patch.object(managers.BuildManager, 'is_working', MagicMock())
    @patch.object(managers.BuildManager, 'wait_all', MagicMock())
    @async_test
    def test_update_and_checkout_new_named_tree(self):
        self.manager.vcs.checkout = MagicMock(side_effect=[
            managers.ExecCmdError, MagicMock(), MagicMock()])
        self.manager.vcs.get_remote_branches = AsyncMagicMock()
        yield from self.manager.update_and_checkout()

        self.assertEqual(len(self.manager.vcs.checkout.call_args_list), 3)
        self.assertTrue(self.manager.vcs.get_remote_branches.called)

    @patch.object(managers.BuildManager, 'is_working', MagicMock())
    @patch.object(managers.BuildManager, 'wait_all', MagicMock())
    @async_test
    def test_update_and_checkout_known_named_tree(self):
        self.manager.vcs.checkout = MagicMock()
        yield from self.manager.update_and_checkout()

        self.assertEqual(len(self.manager.vcs.checkout.call_args_list), 1)

    @async_test
    async def test_list_builders(self):
        await self.manager.load_config()
        expected = ['builder1', 'builder2', 'builder3', 'builder4']
        returned = self.manager.list_builders()

        self.assertEqual(returned, expected)

    def test_list_builders_with_bad_builder_config(self):
        self.manager._config = BADTOXICCONF
        with self.assertRaises(managers.BadBuilderConfig):
            self.manager.list_builders()

    @async_test
    async def test_branch_match(self):
        await self.manager.load_config()
        builder = {'name': 'builder', 'branch': 'master'}
        self.branch = 'master'
        self.assertTrue(self.manager._branch_match(builder))

    def test_branch_match_no_branch(self):
        builder = {'name': 'builder'}
        self.branch = 'master'
        self.assertTrue(self.manager._branch_match(builder))

    def test_branch_match_no_match(self):
        builder = {'name': 'builder', 'branch': 'other'}
        self.branch = 'master'
        self.assertFalse(self.manager._branch_match(builder))

    @patch.object(managers, 'settings', Mock())
    @async_test
    async def test_load_builder(self):
        await self.manager.load_config()
        managers.settings.USE_DOCKER = False
        builder = await self.manager.load_builder('builder1')
        self.assertEqual(len(builder.steps), 2)

    @patch.object(managers, 'settings', Mock())
    @patch.object(managers, 'DockerContainerBuilder', Mock())
    @async_test
    async def test_load_builder_docker(self):
        await self.manager.load_config()
        managers.settings.USE_DOCKER = True
        await self.manager.load_builder('builder1')
        self.assertTrue(managers.DockerContainerBuilder.called)

    @patch.object(managers, 'settings', Mock())
    @async_test
    async def test_load_builder_with_plugin(self):
        managers.settings.USE_DOCKER = False
        await self.manager.load_config()
        builder = await self.manager.load_builder('builder3')
        self.assertEqual(len(builder.steps), 3)

    @async_test
    async def test_load_builder_with_not_found(self):
        with self.assertRaises(managers.BuilderNotFound):
            await self.manager.load_config()
            builder = await self.manager.load_builder('builder300')
            del builder

    @patch.object(managers, 'settings', Mock())
    @async_test
    async def test_load_builder_with_envvars(self):
        managers.settings.USE_DOCKER = False
        await self.manager.load_config()
        builder = await self.manager.load_builder('builder4')
        self.assertTrue(builder.envvars)

    @patch.object(managers.SlavePlugin, 'create_data_dir', AsyncMagicMock())
    @async_test
    async def test_load_plugins(self):
        plugins_conf = [{'name': 'python-venv',
                         'pyversion': '/usr/bin/python3.4'}]
        returned = await self.manager._load_plugins(plugins_conf)

        self.assertEqual(type(returned[0]), plugins.PythonVenvPlugin)
        self.assertTrue(returned[0].create_data_dir.called)

    @patch.object(managers.SlavePlugin, 'create_data_dir', AsyncMagicMock())
    @async_test
    async def test_load_plugins_no_data_dir(self):
        plugins_conf = [{'name': 'apt-install',
                         'packages': ['some-package', 'other']}]
        returned = await self.manager._load_plugins(plugins_conf)

        self.assertEqual(type(returned[0]), plugins.AptInstallPlugin)
        self.assertFalse(returned[0].create_data_dir.called)

    @async_test
    async def test_load_plugins_no_name(self):
        plugins_conf = [{'pyversion': '/usr/bin/python3.4'}]
        with self.assertRaises(managers.BadPluginConfig):
            await self.manager._load_plugins(plugins_conf)

    @patch.object(managers, 'get_toxicbuildconf_yaml',
                  AsyncMagicMock(spec=managers.get_toxicbuildconf_yaml))
    @async_test
    async def test_load_config_yaml(self):
        self.manager.config_type = 'yaml'
        await self.manager.load_config()
        self.assertTrue(managers.get_toxicbuildconf_yaml.called)

    @async_test
    async def test_get_builder_steps_str(self):
        builder = Mock()
        builder.plugins = []
        bdict = {'name': 'bla', 'steps': ['ls', 'cmd2']}
        steps = await self.manager._get_builder_steps(builder, bdict)
        self.assertEqual(len(steps), 2)
