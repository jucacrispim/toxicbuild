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
import copy
from mongomotor import EmbeddedDocument
from mongoengine.base.metaclasses import DocumentMetaclass
from mongomotor.fields import StringField, URLField, ListField
from toxicbuild.core import requests
from toxicbuild.core.plugins import Plugin
from toxicbuild.core.utils import datetime2string
from toxicbuild.master.signals import build_started, build_finished


_translate_table = {ListField: 'list',
                    StringField: 'string',
                    URLField: 'url'}


class MetaMasterPlugin(DocumentMetaclass):
    """Metaclass that sets name and type to the class definition as
    mongo fields while keeping the interface of setting your plugin's
    name and type as string in definition time."""

    def __new__(cls, name, bases, attrs):
        attrs['_name'] = StringField(required=True, default=attrs['name'])
        attrs['_type'] = StringField(required=True, default=attrs['type'])
        new_cls = super().__new__(cls, name, bases, attrs)
        return new_cls


class MasterPlugin(Plugin, EmbeddedDocument, metaclass=MetaMasterPlugin):
    """Base plugin for master's plugins. Master's plugins usually
    react to signals sent by the master."""

    # you must define a name and a type in your own plugin.
    name = 'BaseMasterPlugin'
    type = None

    branches = ListField(StringField())
    # statuses that trigger the plugin
    statuses = ListField(StringField())

    meta = {'allow_inheritance': True}

    @classmethod
    def _translate_schema(cls, fields):
        """Converts the db fields into strings that can be
        serialized."""

        good = copy.copy(fields)
        del good['name']
        del good['type']
        translation = {k: _translate_table[type(v)] for k, v in good.items()}
        translation['name'] = fields['name']
        translation['type'] = fields['type']
        return translation

    @classmethod
    def get_schema(cls, to_serialize=False):
        """Returns a dictionary with the schema of the plugin."""
        fields = copy.copy(cls._fields)
        fields['type'] = cls.type
        fields['name'] = cls.name
        del fields['_type']
        del fields['_name']
        if to_serialize:
            fields = cls._translate_schema(fields)
        return fields

    def to_dict(self):
        schema = type(self).get_schema()
        objdict = {k: getattr(self, k) for k in schema.keys()}
        return objdict

    @asyncio.coroutine
    def run(self):
        """Runs the plugin. You must implement this in your plugin."""

        msg = 'You must implement a run() method in your plugin'
        raise NotImplementedError(msg)

    @asyncio.coroutine
    def stop(self):
        """Stops the plugin. Here is where you may disconnect from signals
        or other stuff needed to stop your plugin."""


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
    def stop(self):
        build_started.disconnect(self.send_started_msg)
        build_finished.disconnect(self.send_finished_msg)

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
        repo = self._instance
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
        repo = self._instance
        title = '[{}] {}'.format(repo.name, build_state)

        msg = {'text': title}
        yield from self._send_msg(msg)
