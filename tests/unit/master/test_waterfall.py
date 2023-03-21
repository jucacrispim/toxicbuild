# -*- coding: utf-8 -*-
# Copyright 2020, 2023 Juca Crispim <juca@poraodojuca.net>

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
from unittest.mock import patch, AsyncMock

from toxicbuild.master import waterfall, hole, build
from toxicbuild.master.build import BuildSet, Build

from tests import async_test
from .utils import RepoTestData


class WaterfallTest(TestCase, RepoTestData):

    @patch.object(BuildSet, 'notify', AsyncMock(spec=BuildSet.notify))
    @async_test
    async def setUp(self):
        await self._create_db_revisions()

    @async_test
    async def tearDown(self):
        await hole.Slave.drop_collection()
        await hole.Repository.drop_collection()
        await build.BuildSet.drop_collection()
        await build.Builder.drop_collection()
        await hole.User.drop_collection()

    @async_test
    async def test_load(self):
        w = await waterfall.Waterfall.get(self.repo)
        self.assertTrue(w.branches)
        self.assertTrue(w.builders)

    @async_test
    async def test_load_with_branch(self):
        w = await waterfall.Waterfall.get(self.repo, branch='dev')
        self.assertTrue(w.branches)
        self.assertFalse(w.builders)

    @async_test
    async def test_to_dict(self):
        w = await waterfall.Waterfall.get(self.repo)
        d = await w.to_dict()
        self.assertTrue(d['branches'])
        self.assertTrue(d['buildsets'])
        self.assertTrue(d['builders'])

    async def _create_db_revisions(self):
        await super()._create_db_revisions()
        self.buildset = await BuildSet.create(self.repo, self.revision)
        self.build = Build(repository=self.repo, slave=self.slave,
                           branch='master', named_tree='123',
                           builder=self.builder)
        self.buildset.builds.append(self.build)
        await self.buildset.save()
