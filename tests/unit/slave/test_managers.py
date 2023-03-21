# -*- coding: utf-8 -*-

# Copyright 2015-2019, 2023 Juca Crispim <juca@poraodojuca.net>

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

import os
from unittest import TestCase
from unittest.mock import patch, MagicMock, Mock, AsyncMock
import tornado
import yaml
from toxicbuild.slave import managers
from tests.unit.slave import TEST_DATA_DIR
from tests import async_test

TOXICCONF_FILE = os.path.join(TEST_DATA_DIR, 'toxicbuild.yml')
with open(TOXICCONF_FILE) as fd:
    conf = fd.read()

TOXICCONF = yaml.load(conf, Loader=yaml.FullLoader)

BADTOXICCONF_FILE = os.path.join(TEST_DATA_DIR, 'badtoxicbuild.yml')
with open(BADTOXICCONF_FILE) as fd:
    conf = fd.read()

BADTOXICCONF = yaml.load(conf, Loader=yaml.FullLoader)


@patch.object(managers, 'get_toxicbuildconf_yaml',
              AsyncMock(return_value=TOXICCONF))
class BuilderManagerTest(TestCase):

    @patch.object(managers, 'get_vcs', MagicMock())
    @async_test
    async def setUp(self):
        super().setUp()
        protocol = MagicMock()

        async def s(*a, **kw):
            pass

        protocol.send_response = s

        self.manager = managers.BuildManager(protocol, 'repo-id',
                                             'git@repo.git', 'git',
                                             'master', 'v0.1')

    def tearDown(self):
        managers.BuildManager.cloning_repos = set()
        managers.BuildManager.updating_repos = set()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    def test_is_cloning_without_clone(self):
        manager = managers.BuildManager(MagicMock(), 'repo-id', 'git@repo.git',
                                        'git', 'master', 'v0.1')

        manager.is_cloning = False

        self.assertFalse(self.manager.is_cloning)

    def test_is_cloning(self):
        try:
            manager = managers.BuildManager(MagicMock(), 'repo-id',
                                            'git@repo.git', 'git',
                                            'master', 'v0.1')

            manager.is_cloning = True

            self.assertTrue(self.manager.is_cloning)

        finally:
            managers.BuildManager.cloning_repos = set()

    def test_is_updating_without_update(self):
        manager = managers.BuildManager(MagicMock(), 'repo-id', 'git@repo.git',
                                        'git', 'master', 'v0.1')

        manager.is_updating = False

        self.assertFalse(self.manager.is_updating)

    def test_is_updating(self):
        manager = managers.BuildManager(MagicMock(), 'repo-id', 'git@repo.git',
                                        'git', 'master', 'v0.1')

        manager.is_updating = True

        self.assertTrue(self.manager.is_updating)

    def test_is_working_with_clone(self):
        manager = managers.BuildManager(MagicMock(), 'repo-id', 'git@repo.git',
                                        'git', 'master', 'v0.1')

        manager.is_cloning = True

        self.assertTrue(self.manager.is_working)

    def test_is_working_with_update(self):
        manager = managers.BuildManager(MagicMock(), 'repo-id', 'git@repo.git',
                                        'git', 'master', 'v0.1')

        manager.is_updating = True

        self.assertTrue(self.manager.is_working)

    def test_is_working_not_working(self):
        manager = managers.BuildManager(MagicMock(), 'repo-id', 'git@repo.git',
                                        'git', 'master', 'v0.1')

        manager.is_updating = False
        manager.is_cloning = False

        self.assertFalse(self.manager.is_working)

    def test_current_build(self):
        manager = managers.BuildManager(MagicMock(), 'repo-id', 'git@repo.git',
                                        'git', 'master', 'v0.1')
        try:
            manager.current_build = 'v0.1'
            self.assertEqual(
                managers.BuildManager.building_repos[manager.repo_url], 'v0.1')
            self.assertTrue(manager.current_build)
        finally:
            manager.current_build = None

    def test_current_build_without_build(self):
        manager = managers.BuildManager(MagicMock(), 'repo-id', 'git@repo.git',
                                        'git', 'master', 'v0.1')
        self.assertIsNone(manager.current_build)

    def test_enter_with_other_current_build(self):
        manager = managers.BuildManager(MagicMock(), 'repo-id', 'git@repo.git',
                                        'git', 'master', 'v0.1')
        manager.current_build = 'v0.1.1'
        with self.assertRaises(managers.BusyRepository):
            with manager as m:
                del m

    def test_enter_with_same_current_build(self):
        manager = managers.BuildManager(MagicMock(), 'repo-id', 'git@repo.git',
                                        'git', 'master', 'v0.1')
        manager.current_build = 'v0.1'
        with manager as m:
            self.assertEqual(m.current_build, 'v0.1')

    def test_enter_without_current_build(self):
        manager = managers.BuildManager(MagicMock(), 'repo-id', 'git@repo.git',
                                        'git', 'master', 'v0.1')
        with manager as m:
            self.assertEqual(m.current_build, 'v0.1')

    @async_test
    async def test_wait_clone(self):
        class TBM(managers.BuildManager):
            clone_called = False
            call_count = -1

            @property
            def is_cloning(self):
                self.clone_called = True
                self.call_count += 1
                return [True, False][self.call_count]

        manager = TBM(MagicMock(), 'repo-id', 'git@repo.git', 'git', 'master',
                      'v0.1')
        await manager.wait_clone()

        self.assertTrue(manager.clone_called)

    @async_test
    async def test_wait_update(self):
        class TBM(managers.BuildManager):
            update_called = False
            call_count = -1

            @property
            def is_updating(self):
                self.update_called = True
                self.call_count += 1
                return [True, False][self.call_count]

        manager = TBM(MagicMock(), 'repo-id', 'git@repo.git', 'git', 'master',
                      'v0.1')
        await manager.wait_update()

        self.assertTrue(manager.update_called)

    @async_test
    async def test_wait_all(self):
        class TBM(managers.BuildManager):
            working_called = False
            call_count = -1

            @property
            def is_working(self):
                self.working_called = True
                self.call_count += 1
                return [True, False][self.call_count]

        manager = TBM(MagicMock(), 'repo-id', 'git@repo.git', 'git', 'master',
                      'v0.1')
        await manager.wait_all()

        self.assertTrue(manager.working_called)

    @async_test
    async def test_update_and_checkout_with_clone(self):
        self.manager.vcs.workdir_exists.return_value = False
        self.manager.vcs.checkout = AsyncMock()
        self.manager.vcs.clone = AsyncMock(spec=self.manager.vcs.clone)
        self.manager.vcs.update_submodule = AsyncMock(
            spec=self.manager.vcs.update_submodule)

        self.manager.vcs.try_set_remote = AsyncMock()
        await self.manager.update_and_checkout()

        self.assertTrue(self.manager.vcs.clone.called)
        self.assertTrue(self.manager.vcs.checkout.called)
        self.assertTrue(self.manager.vcs.try_set_remote.called)

    @async_test
    async def test_update_and_checkout_external(self):
        self.manager.vcs.workdir_exists.return_value = True
        self.manager.vcs.try_set_remote = AsyncMock()
        self.manager.vcs.import_external_branch = AsyncMock(
            spec=self.manager.vcs.import_external_branch)
        self.manager.vcs.checkout = AsyncMock()
        self.manager.vcs.update_submodule = AsyncMock(
            spec=self.manager.vcs.update_submodule)

        external = {'url': 'http://bla.com/bla.git',
                    'name': 'remote', 'branch': 'master',
                    'into': 'into'}
        await self.manager.update_and_checkout(external=external)

        self.assertFalse(self.manager.vcs.clone.called)
        self.assertTrue(self.manager.vcs.checkout.called)
        self.assertFalse(self.manager.vcs.try_set_remote.called)
        self.assertTrue(self.manager.vcs.import_external_branch.called)

    @patch.object(managers.BuildManager, 'is_working', MagicMock())
    @patch.object(managers.BuildManager, 'wait_all', AsyncMock())
    @async_test
    async def test_update_and_checkout_working(self):
        await self.manager.update_and_checkout()

        self.assertTrue(self.manager.wait_all.called)

    @async_test
    async def test_update_and_checkout_without_clone(self):
        self.manager.vcs.clone = MagicMock()
        self.manager.vcs.workdir_exists.return_value = True
        self.manager.vcs.try_set_remote = AsyncMock(
            spec=self.manager.vcs.try_set_remote)
        self.manager.vcs.checkout = AsyncMock()
        self.manager.vcs.update_submodule = AsyncMock(
            spec=self.manager.vcs.update_submodule)

        await self.manager.update_and_checkout()

        self.assertFalse(self.manager.vcs.clone.called)
        self.assertTrue(self.manager.vcs.checkout.called)

    @patch.object(managers.BuildManager, 'is_working', MagicMock())
    @patch.object(managers.BuildManager, 'wait_all', AsyncMock())
    @async_test
    async def test_update_and_checkout_working_not_wait(self):
        self.manager.vcs.checkout = Mock()
        await self.manager.update_and_checkout(work_after_wait=False)

        self.assertTrue(self.manager.wait_all.called)
        self.assertFalse(self.manager.vcs.checkout.called)

    @patch.object(managers.BuildManager, 'is_working', MagicMock())
    @patch.object(managers.BuildManager, 'wait_all', AsyncMock())
    @async_test
    async def test_update_and_checkout_new_named_tree(self):
        self.manager.vcs.get_remote_branches = AsyncMock()
        self.manager.vcs.try_set_remote = AsyncMock(
            spec=self.manager.vcs.try_set_remote)
        self.manager.vcs.checkout = AsyncMock(side_effect=[
            managers.ExecCmdError, MagicMock(), MagicMock()])
        self.manager.vcs.pull = AsyncMock(spec=self.manager.vcs.pull)
        self.manager.vcs.update_submodule = AsyncMock(
            spec=self.manager.vcs.update_submodule)
        await self.manager.update_and_checkout()

        self.assertEqual(len(self.manager.vcs.checkout.call_args_list), 3)
        self.assertTrue(self.manager.vcs.get_remote_branches.called)

    @patch.object(managers.BuildManager, 'is_working', MagicMock())
    @patch.object(managers.BuildManager, 'wait_all', AsyncMock())
    @async_test
    async def test_update_and_checkout_known_named_tree(self):
        self.manager.vcs.checkout = AsyncMock(
            spec=self.manager.vcs.checkout)
        self.manager.vcs.update_submodule = AsyncMock(
            spec=self.manager.vcs.update_submodule)
        self.manager.vcs.try_set_remote = AsyncMock(
            spec=self.manager.vcs.try_set_remote)
        await self.manager.update_and_checkout()

        self.assertEqual(len(self.manager.vcs.checkout.call_args_list), 1)

    @async_test
    async def test_list_builders(self):
        await self.manager.load_config()
        expected = ['builder1', 'builder2', 'builder3', 'builder4', 'builder5']
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
        self.assertIn('COMMIT_SHA', builder.envvars)

    @patch.object(managers, 'settings', Mock())
    @async_test
    async def test_load_builder_from_other_branch(self):
        self.manager.builders_from = 'other-branch'
        await self.manager.load_config()
        managers.settings.USE_DOCKER = False
        builder = await self.manager.load_builder('builder5')
        self.assertEqual(len(builder.steps), 1)

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

    @patch.object(managers, 'get_toxicbuildconf_yaml',
                  AsyncMock(spec=managers.get_toxicbuildconf_yaml))
    @async_test
    async def test_load_config_yaml(self):
        self.manager.config_type = 'yaml'
        await self.manager.load_config()
        self.assertTrue(managers.get_toxicbuildconf_yaml.called)
