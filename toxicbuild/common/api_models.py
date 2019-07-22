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
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.


from collections import OrderedDict
import datetime
import importlib
import json

from toxicbuild.core import requests
from toxicbuild.core.utils import string2datetime
from .utils import is_datetime, format_datetime


__doc__ = """Module with base models that are populated using a remote api.
"""


class BaseModel:
    # These references are fields that refer to other objects.
    # Note that this references are not always references on
    # database, they may be (and most are) embedded documents
    # that are simply treated as other objects.
    references = {}

    # This is for the cli only. Do not use.
    _client = None

    def __init__(self, requester, ordered_kwargs):
        # here is where we transform the dictonaries from the
        # master's response into objects that are references.
        # Note that we can't use **kwargs here because we want to
        # keep the order of the attrs.
        self.__ordered__ = [k for k in ordered_kwargs.keys()]

        for name, cls in self.references.items():
            cls = self._get_ref_cls(cls)
            if not isinstance(ordered_kwargs.get(name), (dict, cls)):
                ordered_kwargs[name] = [cls(requester, kw) if not
                                        isinstance(kw, cls)
                                        else kw
                                        for kw in ordered_kwargs.get(name, [])]
            else:
                obj = ordered_kwargs[name]
                ordered_kwargs[name] = cls(requester, obj) if not isinstance(
                    obj, cls) else obj

        for key, value in ordered_kwargs.items():
            if is_datetime(value):
                value = string2datetime(value)
            setattr(self, key, value)
            self.__ordered__.append(key)

        self.requester = requester

    def __eq__(self, other):
        return isinstance(self, type(other)) and self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def _get_ref_cls(self, cls):
        if isinstance(cls, str):
            module, cls_name = cls.rsplit('.', 1)
            module = importlib.import_module(module)
            cls = getattr(module, cls_name)
        return cls

    def to_dict(self, dtformat=None, tzname=None):
        """Transforms a model into a dict.

        :param dtformat: Format for datetimes.
        :param tzname: A timezone name.
        """

        attrs = [a for a in self.__ordered__ if not a.startswith('_')]

        d = OrderedDict()
        for attr in attrs:
            objattr = getattr(self, attr)
            is_ref = attr == 'references'
            if not (callable(objattr) and not is_ref):  # pragma no branch

                if isinstance(objattr, datetime.datetime):
                    objattr = format_datetime(objattr, dtformat, tzname)

                d[attr] = objattr

        return d

    def to_json(self, *args, **kwargs):
        """Transforms a model into a json.

        :param args: Positional arguments passed to
          :meth:`~toxicbuild.ui.models.BaseModel.to_dict`.
        :param kwargs: Named arguments passed to
          :meth:`~toxicbuild.ui.models.BaseModel.to_dict`.
        """

        d = self.to_dict(*args, **kwargs)
        return json.dumps(d)

    @classmethod
    def _handle_name_or_id(cls, prefix, kw):
        name = kw.pop('name', None)
        key = '{}_name_or_id'.format(prefix)
        if name:
            kw[key] = name

        obj_id = kw.pop('id', None)
        if obj_id:
            kw[key] = obj_id


class Notification(BaseModel):
    """Integration with the notifications api."""

    settings = None

    def __init__(self, ordered_kwargs):
        super().__init__(None, ordered_kwargs)

    @classmethod
    def api_url(cls):
        return getattr(cls.settings, 'NOTIFICATIONS_API_URL', None)

    @classmethod
    def api_token(cls):
        return getattr(cls.settings, 'NOTIFICATIONS_API_TOKEN', None)

    @classmethod
    def _get_headers(cls):
        return {'Authorization': 'token: {}'.format(cls.api_token())}

    @classmethod
    def _get_notif_url(cls, notif_name):
        url = '{}/{}'.format(cls.api_url(), notif_name)
        return url

    @classmethod
    async def list(cls, obj_id=None):
        """Lists all the notifications available.

        :param obj_id: The of of an repository. If not None, the notifications
          will return the values of the configuration for that repository."""

        url = '{}/list/'.format(cls.api_url())
        if obj_id:
            url += obj_id
        headers = cls._get_headers()
        r = await requests.get(url, headers=headers)
        notifications = r.json()['notifications']
        return [cls(n) for n in notifications]

    @classmethod
    async def enable(cls, repo_id, notif_name, **config):
        """Enables a notification for a given repository.

        :param repo_id: The id of the repository to enable the notification.
        :param notif_name: The name of the notification.
        :param config: A dictionary with the config values for the
          notification.
        """

        url = cls._get_notif_url(notif_name)
        config['repository_id'] = repo_id
        headers = cls._get_headers()
        r = await requests.post(url, headers=headers, data=json.dumps(config))
        return r

    @classmethod
    async def disable(cls, repo_id, notif_name):
        """Disables a notification for a given repository.

        :param repo_id: The id of the repository to enable the notification.
        :param notif_name: The name of the notification.
        """
        url = cls._get_notif_url(notif_name)
        config = {'repository_id': repo_id}
        headers = cls._get_headers()
        r = await requests.delete(url, headers=headers,
                                  data=json.dumps(config))
        return r

    @classmethod
    async def update(cls, repo_id, notif_name, **config):
        """Updates a notification for a given repository.

        :param repo_id: The id of the repository to enable the notification.
        :param notif_name: The name of the notification.
        :param config: A dictionary with the new config values for the
          notification.
        """
        url = cls._get_notif_url(notif_name)
        config['repository_id'] = repo_id
        headers = cls._get_headers()
        r = await requests.put(url, headers=headers, data=json.dumps(config))
        return r
