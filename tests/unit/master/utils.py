# -*- coding: utf-8 -*-
# Copyright 2020 Juca Crispim <juca@poraodojuca.net>

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

import datetime

from toxicbuild.master import users, repository, build, slave


class RepoTestData:

    async def _create_db_revisions(self):
        self.owner = users.User(email='zezinho@nada.co', password='123')
        await self.owner.save()
        self.repo = repository.Repository(
            name='reponame', url="git@somewhere.com/project.git",
            vcs_type='git', update_seconds=100, clone_status='ready',
            owner=self.owner)
        await self.repo.save()

        await self.repo.save()
        rep = self.repo
        now = datetime.datetime.now()
        self.builder = await build.Builder.get_or_create(
            name='builder0',
            repository=self.repo,
            position=0)
        self.slave = await slave.Slave.create(name='slave',
                                              host='localhost',
                                              port=1234,
                                              token='asdf',
                                              owner=self.owner)
        self.revs = []
        self.repo.slaves = [self.slave]
        await self.repo.save()
        for r in range(2):
            for branch in ['master', 'dev']:
                rev = repository.RepositoryRevision(
                    repository=rep, commit='123asdf{}'.format(str(r)),
                    branch=branch,
                    author='ze',
                    title='commit {}'.format(r),
                    config='language: python',
                    commit_date=now + datetime.timedelta(r))

                await rev.save()
                self.revs.append(rev)

        self.revision = repository.RepositoryRevision(
            repository=self.repo,
            branch='master',
            commit='asdf',
            author='j@d.com',
            title='bla',
            config='language: python',
            commit_date=now)
        await self.revision.save()
        # creating another repo just to test the known branches stuff.
        self.other_repo = repository.Repository(name='bla', url='/bla/bla',
                                                update_seconds=300,
                                                vcs_type='git',
                                                owner=self.owner)
        await self.other_repo.save()

        for r in range(2):
            for branch in ['b1', 'b2']:
                rev = repository.RepositoryRevision(
                    author='ze',
                    title='commit {}'.format(r),
                    repository=self.other_repo,
                    commit='123asdf{}'.format(str(r)),
                    branch=branch,
                    config='language: python',
                    commit_date=now + datetime.timedelta(r))

                await rev.save()
