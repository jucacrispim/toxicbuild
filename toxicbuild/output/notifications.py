# -*- coding: utf-8 -*-
"""This module implements notifications for repositories. Notifications are
triggered by the master, reacting to messages that come throught the exchanges.

To implement your own notifications you must to subclass
:class:`~toxicbuild.output.notifications.Notification` and implement a ``run``
method.

The class :class:`~toxicbuild.output.notifications.Notification` is a
mongomotor document that you can subclass and create your own fields to store
the notification config params. It already has the following fields:

- branches: A list of branch names that triggers the plugin.
- statuses: A list of statuses that triggers the plugin.

Example:
^^^^^^^^

.. code-block:: python

    from mongomotor.fields import StringField
    from toxicbuild.output.notifications import Notification

    class MyNotification(Notification):

        # you must define name
        name = 'my-notification'

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

from asyncio import ensure_future
import copy
from collections import OrderedDict
import json
from mongomotor import Document
from mongomotor.fields import (StringField, ListField, ReferenceField,
                               ObjectIdField)
from mongomotor.metaprogramming import AsyncDocumentMetaclass
from toxicbuild.core import requests
from toxicbuild.core.mail import MailSender as MailSenderCore
from toxicbuild.core.plugins import Plugin, PluginMeta
from toxicbuild.core.utils import LoggerMixin
from toxicbuild.master.utils import (PrettyListField, PrettyStringField,
                                     PrettyURLField)
from toxicbuild.output import settings


_TRANSLATE_TABLE = {PrettyListField: 'list',
                    ListField: 'list',
                    PrettyStringField: 'string',
                    PrettyURLField: 'url',
                    StringField: 'string',
                    ReferenceField: 'string',
                    ObjectIdField: 'string'}


class MailSender(MailSenderCore):
    """Mail sender that take its configurations from the settings file"""

    def __init__(self, recipients):
        smtp_settings = {'host': settings.SMTP_HOST,
                         'port': settings.SMTP_PORT,
                         'mail_from': settings.SMTP_MAIL_FROM,
                         'username': settings.SMTP_USERNAME,
                         'password': settings.SMTP_PASSWORD,
                         'validate_certs': settings.SMTP_VALIDATE_CERTS,
                         'starttls': settings.SMTP_STARTTLS}
        super().__init__(recipients, **smtp_settings)


class MetaNotification(PluginMeta, AsyncDocumentMetaclass):
    """Metaclass that sets name to the class definition as
    mongo fields while keeping the interface of setting your notification's
    name as string in definition time."""

    def __new__(cls, name, bases, attrs):
        attrs['_name'] = PrettyStringField(required=True,
                                           default=attrs['name'])
        attrs['_pretty_name'] = PrettyStringField(
            default=attrs.get('pretty_name'))
        attrs['_description'] = PrettyStringField(default=attrs.get(
            'description'))

        new_cls = super().__new__(cls, name, bases, attrs)
        if getattr(new_cls, 'events', None) is None:
            setattr(new_cls, 'events', [])
        return new_cls


class Notification(LoggerMixin, Plugin, Document, metaclass=MetaNotification):
    """Base class for notifications. It creates 3 fields:

    - ``repository_id``: The id of the repository that sends notifications.
    - ``branches``: A list of branches that may send notifications. If no
      branch, all branches may send messages.
    - ``statuses``: A list of statuses that may send notifications. If no
      status, all statuses may send notifications."""

    repository_id = ObjectIdField(required=True)
    branches = PrettyListField(StringField(), pretty_name='branches')
    statuses = PrettyListField(StringField(), pretty_name='statuses')

    name = 'BaseNotification'
    pretty_name = ''
    description = "Base for notifications"

    # events that trigger Notification and its subclasses. You may change
    # it in your own notification
    events = ['buildset-started', 'buildset-finished']

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
        del good['pretty_name']
        del good['description']
        translation = OrderedDict()

        for k, v in good.items():
            translation[k] = cls._create_field_dict(v)

        translation['name'] = fields['name']
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

        fields['name'] = cls.name
        fields['pretty_name'] = cls.pretty_name
        fields['description'] = cls.description
        del fields['_name']
        del fields['_pretty_name']
        del fields['_description']
        if to_serialize:
            fields = cls._translate_schema(fields)
        return fields

    @classmethod
    def list_for_event_type(cls, event_type, no_events=False):
        """Lists the notifications that react for a given event.

        :param event_type. The event type to match against.
        :param no_events: Indicates if the plugins with no events should
          be listed. That may be used to make plugins without events react
          to all events.
        """

        notifications = []
        for notification in cls.__subclasses__():
            notifications += notification.list_for_event_type(
                event_type=event_type, no_events=no_events)

        return notifications + [n for n in cls.__subclasses__()
                                if not n.no_list and event_type in n.events or
                                (no_events and not n.events)]

    def to_dict(self):
        schema = type(self).get_schema()
        objdict = {k: getattr(self, k) for k in schema.keys()}

        objdict['repository'] = str(self.repository_id)
        return objdict

    async def run(self, buildset_info):
        """Executed when a notification about a build arrives. Reacts
        to buildsets that started or finished.

        :param buildset_info: A dictionary with information about a buildset.
        """

        self.sender = buildset_info['repository']

        status = buildset_info['status']
        branch = buildset_info['branch']
        msg = 'running {} for {} branch {} with status {}'.format(
            self.name, self.sender['id'], branch, status)
        self.log(msg, level='info')

        if self.statuses and status not in self.statuses:
            return

        elif self.branches and branch not in self.branches:
            return

        if status == 'running':
            ensure_future(self.send_started_message(buildset_info))
        else:
            ensure_future(self.send_finished_message(buildset_info))

    async def send_started_message(self, buildset_info):
        """Sends a message when a buildset is started. You must override it.
        """

        raise NotImplementedError

    async def send_finished_message(self, buildset_info):
        """Sends a message when a buildset is finished. You must override it.
        """

        raise NotImplementedError


class SlackNotification(Notification):
    """Plugin that send notifications about builds to slack."""

    name = 'slack-notification'
    pretty_name = "Slack"
    description = "Sends messages to a slack channel"

    webhook_url = PrettyURLField(required=True, pretty_name='Webhook URL')
    channel_name = PrettyStringField(pretty_name="Channel name")

    def _get_message(self, text):
        return {'text': text, 'channel': self.channel_name,
                'username': 'ToxicBuild'}

    async def _send_message(self, message):
        log_msg = 'sending message for {}'.format(self.sender['id'])
        self.log(log_msg, level='info')

        headers = {'Content-Type': 'application/json'}

        response = await requests.post(self.webhook_url,
                                       data=json.dumps(message),
                                       headers=headers)

        log_msg = 'slack response for {} - status {}'.format(self.sender['id'],
                                                             response.status)
        self.log(log_msg, level='info')
        self.log(response.text, level='debug')

    async def send_started_message(self, buildset_info):

        dt = buildset_info['started']
        build_state = 'Buildset *started* at *{}*'.format(dt)
        title = '[{}] {}'.format(self.sender['name'], build_state)
        msg = self._get_message(title)
        await self._send_message(msg)

    async def send_finished_message(self, buildset_info):

        dt = buildset_info['finished']
        build_state = 'Buildset *finished* at *{}* with status *{}*'.format(
            dt, buildset_info['status'])
        title = '[{}] {}'.format(self.sender['name'], build_state)

        msg = self._get_message(title)
        await self._send_message(msg)


class EmailNotification(Notification):
    """Sends notification about buildsets through email"""

    name = 'email-notification'
    pretty_name = 'Email'
    description = 'Sends email messages'

    recipients = PrettyListField(StringField(), pretty_name="Recipients",
                                 required=True)

    async def send_started_message(self, buildset_info):
        started = buildset_info['started']
        repo_name = self.sender['name']
        subject = '[ToxicBuild][{}] Build started at {}'.format(
            repo_name, started)
        message = 'A build has just started for the repository {}.'.format(
            repo_name)

        message += '\n\ncommit: {}\ntitle: {}'.format(buildset_info['commit'],
                                                      buildset_info['title'])

        async with MailSender(self.recipients) as sender:
            await sender.send(subject, message)

    async def send_finished_message(self, buildset_info):
        dt = buildset_info['finished']
        repo_name = self.sender['name']
        subject = '[ToxicBuild][{}] Build finished at {}'.format(repo_name, dt)
        message = 'A build finished for the repository {}'.format(repo_name)
        message += '\n\ncommit: {}\ntitle: {}'.format(buildset_info['commit'],
                                                      buildset_info['title'])
        message += '\ntotal time: {}\nstatus: {}'.format(
            buildset_info['total_time'], buildset_info['status'])

        async with MailSender(self.recipients) as sender:
            await sender.send(subject, message)


class CustomWebhookNotification(Notification):
    """Sends a POST request to a custom URL. The request content type is
    application/json and the body of the request has a json with information
    about a buildset. """

    name = 'custom-webhook'
    pretty_name = 'Custom Webhook'
    description = 'Sends messages to a custom webhook.'

    webhook_url = PrettyURLField(required=True, pretty_name='Webhook URL')

    async def _send_message(self, buildset_info):
        repo = buildset_info['repository']

        self.log('sending message for {} to {}'.format(
            repo['id'], self.webhook_url), level='info')

        headers = {'Content-Type': 'application/json'}
        r = await requests.post(self.webhook_url,
                                data=json.dumps(buildset_info),
                                headers=headers)

        msg = 'response for {} - status: {}'.format(repo['id'], r.status)
        self.log(msg, level='info')

    async def send_started_message(self, buildset_info):
        await self._send_message(buildset_info)

    async def send_finished_message(self, buildset_info):
        await self._send_message(buildset_info)
