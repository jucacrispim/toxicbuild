# -*- coding: utf-8 -*-

# Copyright 2017 Juca Crispim <juca@poraodojuca.net>

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

from unittest import TestCase
from unittest.mock import Mock, patch
from datetime import datetime
from toxicbuild.master.build import Build, BuildSet, Builder
from toxicbuild.master.repository import Repository, RepositoryRevision
from toxicbuild.master.slave import Slave
from toxicbuild.master.users import User
from toxicbuild.ui import utils, models
from tests import async_test, AsyncMagicMock


class UtilsDateTimeTest(TestCase):

    @patch.object(utils, 'settings', Mock())
    def test_get_dtformat(self):
        utils.settings.DTFORMAT = '%y %a'
        returned = utils.get_dtformat()
        self.assertEqual(returned, utils.settings.DTFORMAT)

    def test_get_dtformat_no_settings(self):
        returned = utils.get_dtformat()
        self.assertEqual(returned, utils.DTFORMAT)


class BuildsetUtilsTest(TestCase):

    @async_test
    async def setUp(self):
        self.user = User(email='a@a.com')
        await self.user.save()
        self.repository = Repository(name='bla', url='http://bla.com/bla.git',
                                     vcs_type='git', update_seconds=10,
                                     owner=self.user)
        await self.repository.save()
        self.revision = RepositoryRevision(repository=self.repository,
                                           branch='master', commit='asdf',
                                           author='zé ruela',
                                           title='sometitle',
                                           commit_date=datetime.now())
        await self.revision.save()
        self.builder = Builder(name='bla-builder', repository=self.repository)
        await self.builder.save()
        self.buildset = BuildSet(revision=self.revision,
                                 repository=self.repository,
                                 branch='master', commit='asdf',
                                 commit_date=datetime.now(),
                                 number=1)
        self.slave = Slave(name='someslave', host='localhost', port=1234,
                           token='adfs', owner=self.user)
        await self.slave.save()
        self.build = Build(repository=self.repository,
                           branch='master', named_tree='asdf',
                           slave=self.slave, builder=self.builder,
                           number=1)
        self.buildset.builds.append(self.build)
        await self.buildset.save()

    @async_test
    async def tearDown(self):
        await RepositoryRevision.drop_collection()
        await Slave.drop_collection()
        await BuildSet.drop_collection()
        await Builder.drop_collection()
        await Repository.drop_collection()
        await User.drop_collection()

    @patch.object(models.Builder, 'list', AsyncMagicMock(
        spec=models.Builder.list))
    @async_test
    async def test_get_builders_for_buildset(self):
        buildset = models.BuildSet(self.user,
                                   ordered_kwargs=self.buildset.to_dict())
        expected = sorted([self.builder])
        builder = await self.builder.to_dict()
        models.Builder.list.return_value = [models.Builder(
            self.user, ordered_kwargs=builder)]
        returned = await utils.get_builders_for_buildsets(self.user,
                                                          [buildset])
        called_args = models.Builder.list.call_args[1]

        expected = {'id__in': [str(b.id) for b in [self.builder]]}
        self.assertEqual(expected, called_args)

        self.assertEqual(returned[0].id, str(self.builder.id))
