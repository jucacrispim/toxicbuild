# -*- coding: utf-8 -*-
# Copyright 2023 Juca Crispim <juca@poraodojuca.net>

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

import traceback

from toxicbuild.core.protocol import BaseToxicProtocol
from toxicbuild.core.server import ToxicServer
from toxicbuild.core.utils import log

from . import settings
from . crypto import Secret


class SecretsProtocol(BaseToxicProtocol):

    actions = {'add-or-update-secret',
               'get-secrets',
               'remove-secret'}

    @property
    def encrypted_token(self):  # pragma no cover
        return settings.ACCESS_TOKEN

    async def client_connected(self):
        assert self.action in type(self).actions, 'Bad Action'
        fname = self.action.replace('-', '_')
        try:
            meth = getattr(self, fname)
            await meth()
        except Exception:
            msg = traceback.format_exc()
            self.log(msg, level="error")
            await self.send_response(
                body={self.action: 'error', 'error': msg},
                code=1)
            return False
        else:
            return True

    async def add_or_update_secret(self):
        body = self.data['body']
        owner = body['owner']
        key = body['key']
        value = body['value']

        await Secret.add_or_update(owner, key, value)
        await self.send_response(body={'add-or-update-secret': 'ok'}, code=0)

    async def remove_secret(self):
        body = self.data['body']
        owner = body['owner']
        key = body['key']

        await Secret.remove(owner, key)
        await self.send_response(body={'remove-secret': 'ok'}, code=0)

    async def get_secrets(self):
        body = self.data['body']
        owners = body['owners']
        secrs = Secret.objects.filter(owner__in=owners).all()
        await self.send_response(
            body={'get-secrets': [s.to_dict() for s in secrs]},
            code=0)


class SecretsServer(ToxicServer):

    PROTOCOL_CLS = SecretsProtocol


def run_server(addr='0.0.0.0', port=1234, loop=None, use_ssl=False,
               **ssl_kw):  # pragma no cover
    log('Serving at {}'.format(port))
    with SecretsServer(addr, port, loop, use_ssl, **ssl_kw) as server:
        server.start()
