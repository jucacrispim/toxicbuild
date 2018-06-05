# -*- coding: utf-8 -*-
"""This module implements plugins meant to be used in reaction
to some notification sent by the master, usually in the build process.

To implement your own plugins you must to subclass
:class:`toxicbuild.master.plugins.MasterPlugin` and implement a ``run``
method.

The class :class:`~toxicbuild.master.plugins.MasterPlugin` is a mongomotor's
document that you can subclass and create your own fields to store the
plugin's config params. It already has the following fields:

- branches: A list of branch names that triggers the plugin.
- statuses: A list of statuses that triggers the plugin.

Example:
^^^^^^^^

.. code-block:: python

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

        async def run(self, sender, info):
            '''Here is where you implement your stuff.

            :param sender: A repository instance.
            :param info: A dictionary with some information for the
              plugin to handle.'''

"""

# Copyright 2016-2018 Juca Crispim <juca@poraodojuca.net>

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

from asyncio import ensure_future
from collections import OrderedDict
import copy
import json
from uuid import uuid4
from mongoengine.base.metaclasses import DocumentMetaclass
from mongomotor import EmbeddedDocument
from mongomotor.fields import (StringField, URLField, ListField, UUIDField,
                               ReferenceField)
from toxicbuild.core import requests
from toxicbuild.core.plugins import Plugin, PluginMeta
from toxicbuild.core.utils import datetime2string, LoggerMixin
from toxicbuild.master.build import Build
from toxicbuild.master.mail import MailSender
from toxicbuild.master.signals import build_started, build_finished


class PrettyFieldMixin:  # pylint: disable=too-few-public-methods
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


class PrettyStringField(PrettyFieldMixin, StringField):
    pass


class PrettyURLField(PrettyFieldMixin, URLField):
    pass


class PrettyListField(PrettyFieldMixin, ListField):
    pass


_TRANSLATE_TABLE = {PrettyListField: 'list',
                    ListField: 'list',
                    PrettyStringField: 'string',
                    PrettyURLField: 'url',
                    StringField: 'string',
                    UUIDField: 'string',
                    ReferenceField: 'string'}


class MetaMasterPlugin(PluginMeta, DocumentMetaclass):
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
        if getattr(new_cls, 'events', None) is None:
            setattr(new_cls, 'events', [])
        return new_cls


class MasterPlugin(LoggerMixin, Plugin, EmbeddedDocument,
                   metaclass=MetaMasterPlugin):
    """Base plugin for master's plugins. Master's plugins usually
    react to signals sent by the master."""

    # you must define a name and a type in your own plugin.
    name = 'BaseMasterPlugin'
    pretty_name = ''
    description = "Base for master's plugins"
    type = None

    uuid = UUIDField(default=uuid4)

    meta = {'allow_inheritance': True}

    @classmethod
    def _create_field_dict(cls, field):
        try:
            fdict = {'pretty_name': field.pretty_name,
                     'name': field.name,
                     'type': _TRANSLATE_TABLE[type(field)]}
        except (KeyError, AttributeError):
            fdict = {'pretty_name': '',
                     'name': field.name,
                     'type': _TRANSLATE_TABLE[type(field)]}

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

        translation['name'] = fields['name']
        translation['type'] = fields['type']
        translation['pretty_name'] = fields['pretty_name']
        translation['description'] = fields['description']
        return translation

    @classmethod
    def get_schema(cls, to_serialize=False):
        """Returns a dictionary with the schema of the plugin."""

        # the linter does not know attrs setted dynamicaly
        ordered = cls._fields_ordered  # pylint: disable=no-member
        fields = OrderedDict()

        for of in ordered:
            fields[of] = cls._fields[of]  # pylint: disable=no-member

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

    @classmethod
    def list_for_event_type(cls, event_type, no_events=False):
        """Lists the plugins that react for a given event.

        :param event_type. The event type to match against.
        :param no_events: Indicates if the plugins with no events
        should be listed. That may be used to make plugins without events
        react to all events.
        """

        plugins = []
        for plugin in cls.__subclasses__():
            plugins += plugin.list_for_event_type(event_type=event_type,
                                                  no_events=no_events)

        return plugins + [p for p in cls.__subclasses__()
                          if not p.no_list and event_type in p.events or
                          (no_events and not p.events)]

    def to_dict(self):
        schema = type(self).get_schema()
        objdict = {k: getattr(self, k) for k in schema.keys()}
        objdict['uuid'] = str(objdict['uuid'])

        objdict['repository'] = str(self._instance.id)
        return objdict

    async def run(self, sender, info):  # pylint: disable=unused-argument
        """Runs the plugin. You must implement this in your plugin."""

        msg = 'You must implement a run() method in your plugin'
        raise NotImplementedError(msg)

    async def stop(self):
        """Stops the plugin. Here is where you may disconnect from signals
        or other stuff needed to stop your plugin."""


class NotificationPlugin(MasterPlugin):

    name = 'NotificationPlugin'
    pretty_name = ''
    description = 'Base plugin for notifications'
    type = 'notification'
    events = ['build-started', 'build-finished']

    branches = PrettyListField(StringField(), pretty_name="Branches")
    # statuses that trigger the plugin
    statuses = PrettyListField(StringField(), pretty_name="Statuses")

    meta = {'allow_inheritance': True}
    no_list = True
    sender = None

    async def run(self, sender, info):
        """Executed when a notification about a build arrives. Reacts
        to builds that started or finished.

        :param sender: An instance of
          :class:`~toxicbuild.master.repository.Repository`.
        :param info: A dictionary with information about a build."""

        self.sender = sender

        status = info['status']
        msg = 'running {} for {} with status {}'.format(self.name,
                                                        self.sender.id,
                                                        status)
        self.log(msg, level='info')

        if status not in self.statuses:
            return

        build = await Build.get(uuid=info['uuid'])

        if status == 'running':
            self._build_started(build)
        else:
            self._build_finished(build)

    async def stop(self):
        build_started.disconnect(self._build_started)
        build_finished.disconnect(self._build_finished)

    def _build_started(self, build):
        ensure_future(self._check_build('started', build))

    def _build_finished(self, build):
        ensure_future(self._check_build('finished', build))

    async def _check_build(self, sig_type, build):
        sigs = {'started': self.send_started_message,
                'finished': self.send_finished_message}

        buildset = await build.get_buildset()
        if buildset.branch in self.branches:
            coro = sigs[sig_type]
            ensure_future(coro(self.sender, build))

    async def send_started_message(self, repo, build):
        """Sends a message about a started build. You must implement
        this in your plugin.

        :param repo: A
          :class:`~toxicbuild.master.repository.Repository` instance.
        :param build: A :class:`~toxicbuild.master.build.Build` instance."""

        raise NotImplementedError

    async def send_finished_message(self, repo, build):
        """Sends a message about a finished build. You must implement
        this in your plugin.

        :param repo: A
          :class:`~toxicbuild.master.repository.Repository` instance.
        :param build: A :class:`~toxicbuild.master.build.Build` instance."""

        raise NotImplementedError

    @classmethod
    def _translate_schema(cls, to_serialize=False):
        translation = super()._translate_schema(to_serialize)
        # we move these guys here so the user defined attributes
        # appear first
        translation.move_to_end('branches')  # pylint: disable=no-member
        translation.move_to_end('statuses')  # pylint: disable=no-member
        return translation


class SlackPlugin(NotificationPlugin):
    """Plugin that send notifications about builds to slack."""

    name = 'slack-notification'
    pretty_name = "Slack"
    description = "Sends messages to a slack channel"
    type = 'notification'

    webhook_url = PrettyURLField(required=True, pretty_name='Webhook URL')
    channel_name = PrettyStringField(pretty_name="Channel name")

    def _get_message(self, text):
        return {'text': text, 'channel': self.channel_name,
                'username': 'ToxicBuild'}

    async def _send_message(self, message):
        """Sends a message as an incomming webhook to slack."""

        msg = 'sending message to slack for'
        self.log(msg, level='info')
        headers = {'Content-Type': 'application/json'}
        response = await requests.post(self.webhook_url,
                                       data=json.dumps(message),
                                       headers=headers)
        msg = 'slack response - status {} | text {}'.format(
            response.status, response.text)
        self.log(msg, level='debug')

    async def send_started_message(self, repo, build):

        dt = datetime2string(build.started)
        build_state = 'Build *started* at *{}*'.format(dt)
        title = '[{}] {}'.format(repo.name, build_state)
        msg = self._get_message(title)
        self._send_message(msg)

    async def send_finished_message(self, repo, build):

        if build.status not in self.statuses:
            return

        dt = datetime2string(build.finished)
        build_state = 'Build *finished* at *{}* with status *{}*'.format(
            dt, build.status)
        title = '[{}] {}'.format(repo.name, build_state)

        msg = self._get_message(title)
        await self._send_message(msg)


class EmailPlugin(NotificationPlugin):
    """Sends notification about builds through email"""

    name = 'email-notification'
    pretty_name = 'Email'
    description = 'Sends email messages'
    type = 'notification'

    recipients = PrettyListField(StringField(), pretty_name="Recipients")

    async def send_started_message(self, repo, build):
        buildset = await build.get_buildset()
        started = datetime2string(build.started)
        subject = '[ToxicBuild][{}] Build started at {}'.format(repo.name,
                                                                started)
        message = 'A build has just started for the repository {}.'.format(
            repo.name)

        message += '\n\ncommit: {}\ntitle: {}'.format(buildset.commit,
                                                      buildset.title)

        async with MailSender(self.recipients) as sender:
            await sender.send(subject, message)

    async def send_finished_message(self, repo, build):
        buildset = await build.get_buildset()
        dt = datetime2string(build.finished)
        subject = '[ToxicBuild][{}] Build finished at {}'.format(repo.name, dt)
        message = 'A build finished for the repository {}'.format(repo.name)
        message += '\n\ncommit: {}\ntitle: {}'.format(buildset.commit,
                                                      buildset.title)
        message += '\ntotal time: {}\nstatus: {}'.format(build.total_time,
                                                         build.status)

        async with MailSender(self.recipients) as sender:
            await sender.send(subject, message)


class CustomWebhookPlugin(NotificationPlugin):
    """Sends a POST request to a custom URL. The request
    mime type is json/application and the body of the request
    has a json with 3 keys: ``repository``, ``build`` and ``buildset``."""

    name = 'custom-webhook'
    pretty_name = 'Custom Webhook'
    description = 'Sends messages to a custom webhook.'
    type = 'notification'
    webhook_url = PrettyURLField(required=True, pretty_name='Webhook URL')

    async def _send_message(self, repo, build):
        self.log('sending message for {}'.format(repo.id), level='debug')
        buildset = await build.get_buildset()
        build_dict = build.to_dict(id_as_str=True)
        buildset_dict = buildset.to_dict(id_as_str=True)
        repo_dict = await repo.to_dict(id_as_str=True)
        msg = {'repo': repo_dict, 'buildset': buildset_dict,
               'build': build_dict}
        await requests.post(self.webhook_url, data=json.dumps(msg))

    async def send_started_message(self, repo, build):
        await self._send_message(repo, build)

    async def send_finished_message(self, repo, build):
        await self._send_message(repo, build)
