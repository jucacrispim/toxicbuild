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

# !!!!!!
# after user stuff was implemented, this whole thing is useless now.
# It must be removed.
# !!!!!!

import asyncio
try:
    from asyncio import async as ensure_future
except ImportError:  # pragma no cover
    from asyncio import ensure_future

from asyncblink import signal
from toxicbuild.core.utils import LoggerMixin
from toxicbuild.ui import settings
from toxicbuild.ui.client import get_hole_client


message_arrived = signal('message-arrived')


class StreamConnector(LoggerMixin):
    """Class responsible for connecting the ui with the master's stream.
    It is done so we don't have one connection open for each client.

    We have a client for each repository and the clients register callables
    to receive the messages sent throught the stream. To use it, simply
    plug a callback to the connector:

    .. code-block:: python

       from toxicbuild.ui.models import Repository
       repo = yield from Repository.get(id='some-id')

       def callback(sender, **message):
           print(message)

       StreamConnector.plug(repo, callback)

    When you are done, unplug it.

    .. code-block:: python

       StreamConnector.unplug(repo, callback)

    """

    NONE_REPO_ID = 'NONE-REPO-ID'
    # limit is not implemented
    _clients_limit = 10
    _instances = {}

    def __init__(self, user, repo_id):
        self.clients_connected = 0
        self.client = None
        self.repo_id = repo_id
        self.user = user
        self._connected = False

    @asyncio.coroutine
    def _connect(self):
        if self._connected:
            self.log('Client already connected', level='warning')
            return

        host = settings.HOLE_HOST
        port = settings.HOLE_PORT
        client = yield from get_hole_client(self.user, host, port)
        yield from client.connect2stream()
        self.client = client
        self._connected = True

    def _disconnect(self):
        self.client.disconnect()
        self._connected = False

    def _get_repo_id(self, body):
        if 'build' in body.keys():
            return body.get('build').get('repository').get('id')
        return body.get('repository', {}).get('id')

    @asyncio.coroutine
    def _listen(self):
        yield from self._connect()
        while self._connected:
            response = yield from self.client.get_response()
            body = response.get('body')
            if body is None:
                self.log('Bad data from stream. Skipping',
                         level='warning')
                break

            repo_id = self._get_repo_id(body)
            event = body.get('event_type')
            if repo_id == self.repo_id or event == 'repo_status_changed':
                message_arrived.send(repo_id, **body)

    @classmethod
    @asyncio.coroutine
    def _prepare_instance(cls, user, repo_id):
        """Returns an instance of
        :class:`toxicbuild.ui.connectors.StreamConnector` that will
        notify about messages from a specific repository.

        :param repo_id: Id of a repository. If repo_id is None, a default
          :attr:`toxicbuild.ui.connectors.StreamConnector` will be used as
          the key."""

        if repo_id is None:
            repo_id = cls.NONE_REPO_ID

        inst = cls._instances.get((user.id, repo_id))
        if not inst:
            inst = cls(user, repo_id)
            cls._instances[(user.id, repo_id)] = inst
            ensure_future(inst._listen())

        inst.clients_connected += 1
        return inst

    @classmethod
    def _release_instance(cls, user, repo_id):

        if repo_id is None:
            repo_id = cls.NONE_REPO_ID

        conn = cls._instances[(user.id, repo_id)]
        conn.clients_connected -= 1

        if conn.clients_connected < 1:
            conn._disconnect()
            cls._instances.pop((user.id, repo_id))

    @classmethod
    @asyncio.coroutine
    def plug(cls, user, repo_id, callback):
        """Connects ``callback`` to events sent by a repository.

        :param user: The requester user.
        :param repo_id: The Id of a repository. Messages sent by this
          repository will trigger ``callback``. If repo_id is None, messages
          from all repositories will be sent to ``callback``.
        :param callback: A callable that will handle messages from
          a repository."""

        yield from cls._prepare_instance(user, repo_id)
        kw = {}
        if repo_id is not None:
            kw = {'sender': repo_id}

        message_arrived.connect(callback, **kw)

    @classmethod
    def unplug(cls, user, repo_id, callback):
        """Disconnects ``callback`` from events sent by a repository.

        :param user: The requester user.
        :param repo_id: The id of a repository.
        :param callback: A callable that will handle messages from
          a repository."""

        message_arrived.disconnect(callback, sender=repo_id)
        cls._release_instance(user, repo_id)
