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

import asyncio
from .build import BuildSet, Builder


class Waterfall:
    """Waterfall is an abstraction to have a single object with
    a repository's branches, builders and buildsets all at once.
    """

    def __init__(self, repository, branch=None):
        self.repo = repository
        self.branch = branch
        self.buildsets = None
        self.builders = None
        self.branches = None

    @classmethod
    async def get(cls, repository, branch=None):
        waterfall = cls(repository, branch=branch)
        await waterfall.load()
        return waterfall

    async def load(self):
        self.buildsets = BuildSet.objects.filter(
            repository=self.repo).order_by('-created')
        if self.branch:
            self.buildsets = self.buildsets.filter(branch=self.branch)

        self.buildsets = await self.buildsets[0:10].exclude(
            'builds__output').to_list()
        ids = [b._data['builder'].id for bs in self.buildsets
               for b in bs.builds]
        futs = [
            Builder.objects.filter(id__in=ids).order_by('position').to_list(),
            self.repo.get_known_branches()
        ]
        r = await asyncio.gather(*futs)
        self.builders = r[0]
        self.branches = r[1]

    async def to_dict(self):
        r = {
            'branches': self.branches,
            'buildsets': [bs.to_dict(builds=True) for bs in self.buildsets],
            'builders': [await b.to_dict() for b in self.builders]
        }

        return r
