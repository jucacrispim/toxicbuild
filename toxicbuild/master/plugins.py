# -*- coding: utf-8 -*-
"""This module implements plugins meat to be used in reaction
to some signal sent by the master in the build process.

To implement your own plugins you must to subclass
:class:`toxicbuild.master.plugins.MasterPlugin` and implement a run() method.

The class :class:`toxicbuild.master.plugins.MasterPlugin` is a mongomotor's
document that you can subclass and create your own fields to store the
plugin's config params. It already has the following fields:

- repository: A reference field to a
  :class:`toxicbuild.master.repository.Repository`
- branches: A list of branch names that triggers the plugin.
- statuses: A list of statuses that triggers the plugin.

Example:
-------

import asyncio
from mongomotor.fields import StringField
from toxicbuild.master.plugins import MasterPlugin

class MyPlugin(MasterPlugin):

    name = 'my-plugin'
    type = 'notification'

    something_to_store_on_database = StringField()

    @asyncio.coroutine
    def run(self):
       '''Here is where you implement your stuff'''

"""

# Copyright 2016 Juca Crispim <juca@poraodojuca.net>

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

import asyncio
from mongomotor.document import Document
from mongomotor.metaprogramming import AsyncDocumentMetaclass
from mongomotor.fields import ReferenceField, StringField, URLField, ListField
from toxicbuild.core import requests
from toxicbuild.core.plugins import Plugin
from toxicbuild.core.utils import datetime2string
from toxicbuild.master import Repository
from toxicbuild.master.signals import build_started, build_finished


class MetaMasterPlugin(AsyncDocumentMetaclass):
    """Metaclass that sets name and type to the class definition as
    mongo fields while keeping the interface of setting your plugin's
    name and type as string in definition time."""

    def __new__(cls, name, bases, attrs):
        attrs['_name'] = StringField(required=True, default=attrs['name'])
        attrs['_type'] = StringField(required=True, default=attrs['type'])
        new_cls = super().__new__(cls, name, bases, attrs)
        return new_cls


class MasterPlugin(Plugin, Document, metaclass=MetaMasterPlugin):
    """Base plugin for master's plugins. Master's plugins usually
    react to signals sent by the master."""

    # you must define a name and a type in your own plugin.
    name = 'BaseMasterPlugin'
    type = None

    repository = ReferenceField(Repository, required=True)
    branches = ListField(StringField())
    # statuses that trigger the plugin
    statuses = ListField(StringField())

    meta = {'allow_inheritance': True,
            'indexes': [
                'repository',
            ]}

    @classmethod
    @asyncio.coroutine
    def get(cls, **kwargs):
        """Returns an instance of a plugin configured to a repository.

        :param kwargs: kwargs to match the object. Passed to mongomotor's
          get() method.
        """

        # here we change the keys to match the fields in the database.
        # The plugin's name is stored in the key _name and
        # the plugin's type is stored in the key _type
        db_fields = [('name', '_name'), ('type', '_type')]
        for attr_name, field_name in db_fields:
            try:
                kwargs[field_name] = kwargs[attr_name]
                del kwargs[attr_name]
            except KeyError:
                pass

        plugin = yield from cls.objects.get(**kwargs)
        return plugin

    @asyncio.coroutine
    def run(self):
        """Runs the plugin. You must implement this in your plugin."""

        msg = 'You must implement a run() method in your plugin'
        raise NotImplementedError(msg)


MasterPlugin.ensure_indexes()


class SlackPlugin(MasterPlugin):
    """Plugin that send notifications about builds to slack."""

    name = 'slack-notification'
    type = 'notification'

    webhook_url = URLField(required=True)
    channel_name = StringField()

    @asyncio.coroutine
    def run(self):
        # we can't use weak references here otherwise
        # no plugin is available when the signal is sent.
        if 'running' in self.statuses:
            build_started.connect(self.send_started_msg, weak=False)

        build_finished.connect(self.send_finished_msg, weak=False)

    @asyncio.coroutine
    def _send_msg(self, message):
        """Sends a message as an incomming webhook to slack."""

        headers = {'content-type': 'application/json'}
        yield from requests.post(self.webhook_url, data=message,
                                 headers=headers)

    @asyncio.coroutine
    def send_started_msg(self, build):
        """Sends a message about a started build to a slack channel.

        :param build: A build that just started."""

        dt = datetime2string(build.started)
        build_state = 'Build *started* at *{datetime}*'.format(datetime=dt)
        repo = yield from self.repository
        title = '[{}] {}'.format(repo.name, build_state)
        msg = {'text': title}
        yield from self._send_msg(msg)

    @asyncio.coroutine
    def send_finished_msg(self, build):
        """Sends a message about a finished build to a slack channel.

        :param build: A build that just finished."""

        if build.status not in self.statuses:
            return

        dt = datetime2string(build.finished)
        build_state = 'Build *finished* at *{datetime}*'.format(datetime=dt)
        repo = yield from self.repository
        title = '[{}] {}'.format(repo.name, build_state)

        msg = {'text': title}
        yield from self._send_msg(msg)