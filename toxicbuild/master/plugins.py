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
^^^^^^^^

.. code-block:: python

    import asyncio
    from mongomotor.fields import StringField
    from toxicbuild.master.plugins import MasterPlugin

    class MyPlugin(MasterPlugin):

        # you must define name and type
        name = 'my-plugin'
        type = 'notification'
        # optionally you may define pretty_name and description
        pretty_name = "My Plugin"
        description = "A very cool plugin"
        something_to_store_on_database = PrettyStringField()

        @asyncio.coroutine
        def run(self):
            '''Here is where you implement your stuff'''

"""

# Copyright 2016, 2017 Juca Crispim <juca@poraodojuca.net>

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
from collections import OrderedDict
import copy
from mongomotor import EmbeddedDocument
from mongoengine.base.metaclasses import DocumentMetaclass
from mongomotor.fields import StringField, URLField, ListField
from toxicbuild.core import requests
from toxicbuild.core.plugins import Plugin
from toxicbuild.core.utils import datetime2string
from toxicbuild.master.signals import build_started, build_finished


class PrettyField:
    """A field with a descriptive name for humans"""

    def __init__(self, *args, **kwargs):
        keys = ['pretty_name', 'description']
        for k in keys:
            setattr(self, k, kwargs.get(k))
            try:
                del kwargs[k]
            except KeyError:
                pass

        super().__init__(*args, **kwargs)


class PrettyStringField(PrettyField, StringField):
    pass


class PrettyURLField(PrettyField, URLField):
    pass


class PrettyListField(PrettyField, ListField):
    pass


_translate_table = {PrettyListField: 'list',
                    PrettyStringField: 'string',
                    PrettyURLField: 'url',
                    StringField: 'string'}


class MetaMasterPlugin(DocumentMetaclass):
    """Metaclass that sets name and type to the class definition as
    mongo fields while keeping the interface of setting your plugin's
    name and type as string in definition time."""

    def __new__(cls, name, bases, attrs):
        attrs['_name'] = PrettyStringField(required=True,
                                           default=attrs['name'])
        attrs['_type'] = PrettyStringField(
            required=True, default=attrs['type'])
        attrs['_pretty_name'] = PrettyStringField(
            default=attrs.get('pretty_name'))
        attrs['_description'] = PrettyStringField(default=attrs.get(
            'description'))

        new_cls = super().__new__(cls, name, bases, attrs)
        return new_cls


class MasterPlugin(Plugin, EmbeddedDocument, metaclass=MetaMasterPlugin):
    """Base plugin for master's plugins. Master's plugins usually
    react to signals sent by the master."""

    # you must define a name and a type in your own plugin.
    name = 'BaseMasterPlugin'
    pretty_name = ''
    description = "Base for master's plugins"
    type = None

    branches = PrettyListField(StringField(), pretty_name="Branches")
    # statuses that trigger the plugin
    statuses = PrettyListField(StringField(), pretty_name="Statuses")

    meta = {'allow_inheritance': True}

    @classmethod
    def _create_field_dict(cls, field):
        try:
            fdict = {'pretty_name': field.pretty_name,
                     'name': field.name,
                     'type': _translate_table[type(field)]}
        except (KeyError, AttributeError):
            fdict = {'pretty_name': '',
                     'name': field.name,
                     'type': _translate_table[type(field)]}

        return fdict

    @classmethod
    def _translate_schema(cls, fields):
        """Converts the db fields into strings that can be
        serialized."""

        good = copy.copy(fields)
        del good['name']
        del good['type']
        del good['pretty_name']
        del good['description']
        translation = OrderedDict()

        for k, v in good.items():
            translation[k] = cls._create_field_dict(v)

        # we move these guys here so the user defined attributes
        # appear first
        translation.move_to_end('branches')
        translation.move_to_end('statuses')
        translation['name'] = fields['name']
        translation['type'] = fields['type']
        translation['pretty_name'] = fields['pretty_name']
        translation['description'] = fields['description']
        return translation

    @classmethod
    def get_schema(cls, to_serialize=False):
        """Returns a dictionary with the schema of the plugin."""

        ordered = cls._fields_ordered
        fields = OrderedDict()

        for of in ordered:
            fields[of] = cls._fields[of]

        fields['type'] = cls.type
        fields['name'] = cls.name
        fields['pretty_name'] = cls.pretty_name
        fields['description'] = cls.description
        del fields['_type']
        del fields['_name']
        del fields['_pretty_name']
        del fields['_description']
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
    pretty_name = "Slack"
    description = "Send a message to a slack channel"

    webhook_url = PrettyURLField(required=True, pretty_name='Webhook URL')
    channel_name = PrettyStringField(pretty_name="Channel name")

    @asyncio.coroutine
    def run(self):
        if 'running' in self.statuses:
            build_started.connect(self.send_started_msg)

        build_finished.connect(self.send_finished_msg)

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
    def send_started_msg(self, repo, build):
        """Sends a message about a started build to a slack channel.

        :param build: A build that just started."""

        dt = datetime2string(build.started)
        build_state = 'Build *started* at *{datetime}*'.format(datetime=dt)
        title = '[{}] {}'.format(repo.name, build_state)
        msg = {'text': title}
        yield from self._send_msg(msg)

    @asyncio.coroutine
    def send_finished_msg(self, repo, build):
        """Sends a message about a finished build to a slack channel.

        :param build: A build that just finished."""

        if build.status not in self.statuses:
            return

        dt = datetime2string(build.finished)
        build_state = 'Build *finished* at *{datetime}*'.format(datetime=dt)
        title = '[{}] {}'.format(repo.name, build_state)

        msg = {'text': title}
        yield from self._send_msg(msg)
