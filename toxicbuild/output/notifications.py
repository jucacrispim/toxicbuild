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
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

from asyncio import ensure_future
import copy
from collections import OrderedDict, defaultdict
import json
import urllib
from mongomotor import Document
from mongomotor.fields import (StringField, ListField, ReferenceField,
                               ObjectIdField)
from mongomotor.metaprogramming import AsyncTopLevelDocumentMetaclass
from toxicbuild.core import requests
from toxicbuild.core.mail import MailSender as MailSenderCore
from toxicbuild.core.plugins import Plugin, PluginMeta
from toxicbuild.core.utils import (LoggerMixin, datetime2string,
                                   string2datetime)
from toxicbuild.integrations.github import GithubInstallation
from toxicbuild.integrations.gitlab import GitLabInstallation
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


async def send_email(recipients, subject, message):

    async with MailSender(recipients) as sender:
        await sender.send(subject, message)

    return True


class MetaNotification(PluginMeta, AsyncTopLevelDocumentMetaclass):
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

        attrs['_events'] = ListField(StringField())

        new_cls = super().__new__(cls, name, bases, attrs)
        if getattr(new_cls, 'events', None) is None:
            setattr(new_cls, 'events', [])

        new_cls._events.default = new_cls.events
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sender = None

    @classmethod
    def _create_field_dict(cls, field):
        try:
            fdict = {'pretty_name': field.pretty_name,
                     'name': field.name,
                     'required': field.required,
                     'type': _TRANSLATE_TABLE[type(field)]}
        except (KeyError, AttributeError):
            fdict = {'pretty_name': '',
                     'name': field.name,
                     'required': field.required,
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
        del good['events']
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
        fields['events'] = cls.events
        fields.move_to_end('branches')
        fields.move_to_end('statuses')
        del fields['id']
        del fields['_name']
        del fields['_pretty_name']
        del fields['_description']
        del fields['_events']
        if to_serialize:
            fields = cls._translate_schema(fields)
        return fields

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
        self.log('Running notification for {}'.format(self.sender['id']),
                 level='debug')

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

    @classmethod
    def get_repo_notifications(cls, repository_id, event=None):
        """Returns a queryset with the notifications for a given repository
        and event.

        :param repository_id: The id of the repository that sent an event.
        :param event: The event that will trigger notifications."""

        if event:
            events_kw = {'_events': event}
        else:
            events_kw = {'_events': []}

        return cls.objects.filter(repository_id=repository_id, **events_kw)


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

        await send_email(self.recipients, subject, message)

    async def send_finished_message(self, buildset_info):
        dt = buildset_info['finished']
        repo_name = self.sender['name']
        subject = '[ToxicBuild][{}] Build finished at {}'.format(repo_name, dt)
        message = 'A build finished for the repository {}'.format(repo_name)
        message += '\n\ncommit: {}\ntitle: {}'.format(buildset_info['commit'],
                                                      buildset_info['title'])
        message += '\ntotal time: {}\nstatus: {}'.format(
            buildset_info['total_time'], buildset_info['status'])

        await send_email(self.recipients, subject, message)


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


class GithubCheckRunNotification(Notification):
    """A plugin that creates a check run reacting to a buildset that
    was added, started or finished."""

    name = 'github-check-run'
    """The name of the plugin"""

    events = ['buildset-added', 'buildset-started', 'buildset-finished']
    """Events that trigger the plugin."""

    no_list = True

    run_name = 'ToxicBuild CI'
    """The name displayed on github."""

    installation = ReferenceField(GithubInstallation)
    """The :class:`~toxicbuild.integrations.github.GithubInstallation`
    that owns the notification. It is needed because each installation has
    its own auth token and it is needed send the checks.
    """

    async def run(self, buildset_info):
        """Executed when a notification about a build arrives. Reacts
        to buildsets that started or finished.

        :param buildset_info: A dictionary with information about a buildset.
        """

        self.log('Sending notification to github for buildset {}'.format(
            buildset_info['id']), level='info')
        self.log('Info is: {}'.format(buildset_info), level='debug')

        self.sender = buildset_info['repository']
        status = buildset_info['status']
        status_tb = defaultdict(lambda: 'completed')

        status_tb.update({'pending': 'queued',
                          'running': 'in_progress'})
        run_status = status_tb[status]

        conclusion_tb = defaultdict(lambda: 'failure')
        conclusion_tb.update({'success': 'success'})
        conclusion = conclusion_tb[status]

        await self._send_message(buildset_info, run_status, conclusion)

    def _get_payload(self, buildset_info, run_status, conclusion):

        payload = {'name': self.run_name,
                   'head_branch': buildset_info['branch'],
                   'head_sha': buildset_info['commit'],
                   'status': run_status}

        started_at = buildset_info.get('started')
        if started_at:
            dt = string2datetime(started_at)
            started_at = datetime2string(
                dt, dtformat="%Y-%m-%dT%H:%M:%S%z")

            started_at = started_at.replace('+0000', 'Z')
            payload.update({'started_at': started_at})

        if run_status == 'completed':
            dt = string2datetime(buildset_info['finished'])
            completed_at = datetime2string(
                dt, dtformat="%Y-%m-%dT%H:%M:%S%z")

            completed_at = completed_at.replace('+0000', 'Z')
            payload.update(
                {'completed_at': completed_at,
                 'conclusion': conclusion})

        return payload

    async def _send_message(self, buildset_info, run_status, conclusion):
        full_name = self.sender['external_full_name']
        install = await self.installation
        url = settings.GITHUB_API_URL + 'repos/{}/check-runs'.format(
            full_name)

        self.log('sending check for {} buildset {}'.format(
            url, buildset_info['id']), level='debug')

        payload = self._get_payload(buildset_info, run_status, conclusion)

        header = await install.get_header(
            accept='application/vnd.github.antiope-preview+json')
        data = json.dumps(payload)
        r = await requests.post(url, headers=header, data=data)

        self.log('response from check for buildset {} - status: {}'.format(
            buildset_info['id'], r.status), level='debug')
        self.log(r.text, level='debug')


class GitlabCommitStatusNotification(Notification):
    """A plugin that sets a commit status reacting to a buildset that
    was added, started or finished."""

    name = 'gitlab-commit-status'
    """The name of the plugin"""

    events = ['buildset-added', 'buildset-started', 'buildset-finished']
    """Events that trigger the plugin."""

    no_list = True

    installation = ReferenceField(GitLabInstallation)
    """The :class:`~toxicbuild.integrations.gitlab.GitLabInstallation`
    that owns the notification. It is needed because each installation has
    its own auth token and it is needed send the checks.
    """

    async def run(self, buildset_info):
        """Executed when a notification about a build arrives. Reacts
        to buildsets that started or finished.

        :param buildset_info: A dictionary with information about a buildset.
        """

        self.log('Sending notification to gitlab for buildset {}'.format(
            buildset_info['id']), level='info')
        self.log('Info is: {}'.format(buildset_info), level='debug')
        self.sender = buildset_info['repository']
        await self._send_message(buildset_info)

    async def _send_message(self, buildset_info):

        status_tb = {'pending': 'pending',
                     'preparing': 'running',
                     'running': 'running',
                     'success': 'success',
                     'fail': 'failed',
                     'canceled': 'canceled',
                     'exception': 'failed',
                     'warning': 'failed'}

        full_name = urllib.parse.quote(self.sender['external_full_name'],
                                       safe='')
        sha = buildset_info['commit']
        url = settings.GITLAB_API_URL + 'projects/{}/statuses/{}'.format(
            full_name, sha)
        state = status_tb[buildset_info['status']]

        params = {'sha': sha,
                  'ref': buildset_info['branch'],
                  'state': state}
        install = await self.installation
        header = await install.get_header()

        r = await requests.post(url, headers=header, params=params)

        self.log('response from check for buildset {} - status: {}'.format(
            buildset_info['id'], r.status), level='debug')
        self.log(r.text, level='debug')
