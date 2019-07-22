# -*- coding: utf-8 -*-

# Copyright 2017 Juca Crispim <juca@poraodojuca.net>

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

# !!!!!!
# after user stuff was implemented, this whole thing is useless now.
# It must be removed.
# !!!!!!

import asyncio
from asyncio import ensure_future

from asyncblink import signal
from toxicbuild.core.utils import LoggerMixin
from toxicbuild.ui.client import get_hole_client
from toxicbuild.ui.utils import get_client_settings


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

    def __init__(self, user, repo_id, events):
        self.clients_connected = 0
        self.client = None
        self.repo_id = repo_id
        self.user = user
        self.events = events
        self._connected = False

    @asyncio.coroutine
    def _connect(self):
        if self._connected:
            self.log('Client already connected', level='warning')
            return

        client_settings = get_client_settings()
        client = yield from get_hole_client(self.user, **client_settings)

        yield from client.connect2stream({'event_types': self.events})
        self.client = client
        self._connected = True

    def _disconnect(self):
        self.client.disconnect()
        self._connected = False

    def _get_repo_id(self, body):
        if 'build' in body.keys():
            return body.get('build').get('repository').get('id')
        return body.get('repository', {}).get('id') or self.NONE_REPO_ID

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
            # there are the events that don't need a repo_id to be
            # delivered for the client.
            no_repo_events = ['repo_status_changed', 'buildset_started',
                              'buildset_finished', 'buildset_added']

            self.log('message {} arrived for {}'.format(event, repo_id),
                     level='debug')
            if repo_id == self.repo_id or (event in no_repo_events and
                                           self.repo_id == self.NONE_REPO_ID):
                message_arrived.send(repo_id, **body)

    @classmethod
    @asyncio.coroutine
    def _prepare_instance(cls, user, repo_id, events):
        """Returns an instance of
        :class:`toxicbuild.ui.connectors.StreamConnector` that will
        notify about messages from a specific repository.

        :param repo_id: Id of a repository. If repo_id is None, a default
          :attr:`toxicbuild.ui.connectors.StreamConnector` will be used as
          the key.
        :param events: The events that will be received."""

        if repo_id is None:
            repo_id = cls.NONE_REPO_ID

        key = (user.id, repo_id, ','.join(events))
        inst = cls._instances.get(key)
        if not inst:
            inst = cls(user, repo_id, events)
            inst.log('New connection instance', level='debug')
            cls._instances[key] = inst
            ensure_future(inst._listen())

        inst.clients_connected += 1
        return inst

    @classmethod
    def _release_instance(cls, user, repo_id, events):
        if repo_id is None:
            repo_id = cls.NONE_REPO_ID

        joined_events = ','.join(events)
        instance_key = (user.id, repo_id, joined_events)
        conn = cls._instances[instance_key]
        conn.clients_connected -= 1
        conn.log('Releasing instance. Connected clients {}'.format(
            conn.clients_connected), level='debug')

        if conn.clients_connected < 1:
            conn._disconnect()
            cls._instances.pop(instance_key)

    @classmethod
    @asyncio.coroutine
    def plug(cls, user, repo_id, events, callback):
        """Connects ``callback`` to events sent by a repository.

        :param user: The requester user.
        :param repo_id: The Id of a repository. Messages sent by this
          repository will trigger ``callback``. If repo_id is None, messages
          from all repositories will be sent to ``callback``.
        :param events: The events that will return messages.
        :param callback: A callable that will handle messages from
          a repository.
        """

        yield from cls._prepare_instance(user, repo_id, events)
        kw = {}
        if repo_id is not None:
            kw = {'sender': repo_id}

        message_arrived.connect(callback, **kw)

    @classmethod
    def unplug(cls, user, repo_id, events, callback):
        """Disconnects ``callback`` from events sent by a repository.

        :param user: The requester user.
        :param repo_id: The id of a repository.
        :param events: A list of events that will return messages.
        :param callback: A callable that will handle messages from
          a repository."""

        message_arrived.disconnect(callback, sender=repo_id)
        cls._release_instance(user, repo_id, events)
