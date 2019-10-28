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

from functools import partial
import traceback

from toxicbuild.core.protocol import BaseToxicProtocol
from toxicbuild.poller.poller import Poller


class PollerServer(BaseToxicProtocol):

    async def client_connected(self):
        assert self.action == 'poll', 'Bad Action'
        r = await self.poll_repo()
        await self.send_response(r, code=0)
        return r

    async def poll_repo(self):
        repo_id = self.data['repo_id']
        url = self.data['url']
        vcs_type = self.data['vcs_type']
        since = self.data['since']
        known_branches = self.data['known_branches']
        branches_conf = self.data['branches_conf']
        external = self.data.get('external')
        poller = Poller(repo_id, url, branches_conf, since, known_branches,
                        vcs_type)

        if external:
            external_url = external.get('url')
            external_name = external.get('name')
            external_branch = external.get('branch')
            into = external.get('into')
            pollfn = partial(poller.external_poll, external_url, external_name,
                             external_branch, into)
        else:
            pollfn = poller.poll

        try:
            with_clone = await pollfn()
            clone_status = 'ready'
        except Exception:
            tb = traceback.format_exc()
            self.log(tb, level='error')
            with_clone = False
            clone_status = 'clone-exception'

        msg = {'with_clone': with_clone,
               'clone_status': clone_status}

        return msg
