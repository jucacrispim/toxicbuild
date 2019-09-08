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

from asyncio import ensure_future
from collections import OrderedDict
import copy

from mongomotor import Document
from mongomotor.fields import (
    ListField,
    StringField,
    ReferenceField,
    ObjectIdField
)
from mongomotor.metaprogramming import AsyncTopLevelDocumentMetaclass

from toxicbuild.common.fields import (
    PrettyListField,
    PrettyStringField,
    PrettyURLField
)

from toxicbuild.core.plugins import Plugin, PluginMeta
from toxicbuild.core.utils import LoggerMixin


_TRANSLATE_TABLE = {PrettyListField: 'list',
                    ListField: 'list',
                    PrettyStringField: 'string',
                    PrettyURLField: 'url',
                    StringField: 'string',
                    ReferenceField: 'string',
                    ObjectIdField: 'string'}


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
