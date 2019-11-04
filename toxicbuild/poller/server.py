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

import asyncio
from functools import partial
import traceback

from toxicbuild.core.protocol import BaseToxicProtocol
from toxicbuild.core.server import ToxicServer
from toxicbuild.core.utils import log
from toxicbuild.poller import settings
from toxicbuild.poller.poller import Poller


class PollerProtocol(BaseToxicProtocol):

    @property
    def encrypted_token(self):  # pragma no cover
        return settings.ACCESS_TOKEN

    async def client_connected(self):
        assert self.action == 'poll', 'Bad Action'
        self.log('client polling', level='debug')
        asyncio.ensure_future(self.poll_repo())
        await self.send_response(body={'poll': 'polling'}, code=0)
        self.close_connection()
        self.log('client disconnected from poller', level='debug')
        return True

    async def poll_repo(self):
        body = self.data['body']
        repo_id = body['repo_id']
        url = body['url']
        vcs_type = body['vcs_type']
        since = body['since']
        known_branches = body['known_branches']
        branches_conf = body['branches_conf']
        external = body.get('external')
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


class PollerServer(ToxicServer):

    PROTOCOL_CLS = PollerProtocol


def run_server(addr='0.0.0.0', port=1234, loop=None, use_ssl=False,
               **ssl_kw):  # pragma no cover
    log('Serving at {}'.format(port))
    with PollerServer(addr, port, loop, use_ssl, **ssl_kw) as server:
        server.start()
