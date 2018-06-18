# -*- coding: utf-8 -*-
# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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

import time
from aiozk import exc
from aiozk.recipes.shared_lock import SharedLock

__doc__ = """This module only exists to overwrite a method from aiozk.
I oppend a `pr <https://github.com/tipsi/aiozk/pull/22>` to fix that. It it
gets approved, when the a new version is released with that, this thing must
be removed."""


class ToxicSharedLock(SharedLock):
    """This class is just to patch the original one to correct a bug
    with the acquire timeout. I oppend a
    `PR <https://github.com/tipsi/aiozk/pull/22>` to fix that. It it
    gets approved, when the a new version is released with that, this
    thing must be removed."""

    async def wait_in_line(self, znode_label, timeout=None, blocked_by=None):
        time_limit = None
        if timeout is not None:
            time_limit = time.time() + timeout

        await self.create_unique_znode(znode_label)

        while True:
            if time_limit and time.time() >= time_limit:
                raise exc.TimeoutError

            owned_positions, contenders = await self.analyze_siblings()
            if znode_label not in owned_positions:  # pragma no cover
                raise exc.SessionLost

            blockers = contenders[:owned_positions[znode_label]]
            if blocked_by:
                blockers = [
                    contender for contender in blockers
                    if self.determine_znode_label(contender) in blocked_by
                ]

            if not blockers:
                break

            try:
                await self.wait_on_sibling(blockers[-1], timeout)
            except exc.TimeoutError:
                await self.delete_unique_znode(znode_label)

        return self.make_contextmanager(znode_label)
