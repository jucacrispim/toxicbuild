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
from .client import get_hole_client
from .utils import is_datetime, format_datetime, get_hole_client_settings


__doc__ = """Module with base models that are populated using a remote api.
"""


class BaseInterface:
    # These references are fields that refer to other objects.
    # Note that this references are not always references on
    # database, they may be (and most are) embedded documents
    # that are simply treated as other objects.
    references = {}

    settings = None

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
          :meth:`~toxicbuild.common.interfaces.BaseInterface.to_dict`.
        :param kwargs: Named arguments passed to
          :meth:`~toxicbuild.common.interfaces.BaseInterface.to_dict`.
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


class NotificationInterface(BaseInterface):
    """Integration with the notifications api."""

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


class BaseHoleInterface(BaseInterface):

    # This is for the cli only. Do not use.
    _client = None

    @classmethod
    async def get_client(cls, requester):
        """Returns a client connected to master."""

        if cls._client:
            if not cls._client._connected:
                await cls._client.connect()
            return cls._client

        client_settings = get_hole_client_settings(cls.settings)
        client = await get_hole_client(requester, **client_settings)
        return client


class UserInterface(BaseHoleInterface):
    """A user created in the master"""

    def __init__(self, requester, ordered_kwargs):
        if requester is None:
            requester = self
        super().__init__(requester, ordered_kwargs)

    @classmethod
    async def get(cls, **kwargs):
        """Returns a user.

        :param requester: The user who is requesting the operation.
        :param kwargs: kwargs to get the user."""

        requester = cls._get_root_user()
        with await cls.get_client(requester) as client:
            user_dict = await client.user_get(**kwargs)
        user = cls(requester, user_dict)
        return user

    @classmethod
    def _get_root_user(cls):
        root_id = cls.settings.ROOT_USER_ID
        return cls(None, {'id': root_id})

    @classmethod
    async def authenticate(cls, username_or_email, password):
        kw = {'username_or_email': username_or_email,
              'password': password}

        with await cls.get_client(None) as client:
            user_dict = await client.user_authenticate(**kw)
        user = cls(None, user_dict)
        return user

    @classmethod
    async def change_password(cls, requester, old_password,
                              new_password):
        kw = {'username_or_email': requester.email,
              'old_password': old_password,
              'new_password': new_password}

        with await cls.get_client(requester) as client:
            await client.user_change_password(**kw)
        return True

    @classmethod
    async def request_password_reset(cls, email, reset_link):
        """Request the reset of the user's password. Sends an
        email with a link to reset the password.
        """
        subject = 'Reset password requested'

        message = "Follow the link {} to reset your password.".format(
            reset_link)

        requester = cls._get_root_user()
        kw = {'email': email,
              'subject': subject,
              'message': message}

        with await cls.get_client(requester) as client:
            await client.user_send_reset_password_email(**kw)

        return True

    @classmethod
    async def change_password_with_token(cls, token, password):
        """Changes the user password using a token. The token
        was generated when ``request_password_reset`` was called and
        a link with the token was sent to the user email.
        """

        kw = {'token': token,
              'password': password}

        requester = cls._get_root_user()

        with await cls.get_client(requester) as client:
            await client.user_change_password_with_token(**kw)

        return True

    @classmethod
    async def add(cls, email, username, password,
                  allowed_actions):
        requester = cls._get_root_user()
        kw = {'username': username,
              'email': email,
              'password': password, 'allowed_actions': allowed_actions}

        with await cls.get_client(requester) as client:
            user_dict = await client.user_add(**kw)
        user = cls(None, user_dict)
        return user

    async def delete(self):
        kw = {'id': str(self.id)}
        with await type(self).get_client(self.requester) as client:
            resp = await client.user_remove(**kw)
        return resp

    @classmethod
    async def exists(cls, **kwargs):
        """Checks if a user with some given information exists.

        :param kwargs: Named arguments to match the user"""
        requester = cls._get_root_user()
        with await cls.get_client(requester) as client:
            exists = await client.user_exists(**kwargs)

        return exists


class SlaveInterface(BaseHoleInterface):

    @classmethod
    async def add(cls, requester, name, port, token, owner,
                  use_ssl=True, validate_cert=True, on_demand=False,
                  host=None, instance_type=None, instance_confs=None):
        """Adds a new slave.

        :param name: Slave name.
        :param host: Slave host.
        :param port: Slave port.
        :param token: Authentication token.
        :param owner: The slave owner
        :param use_ssl: Indicates if the slave uses a ssl connection.
        :pram validate_cert: Should the slave certificate be validated?
        :param on_demand: Does this slave have an on-demand instance?
        :param instance_type: Type of the on-demand instance.
        :param instance_confs: Configuration parameters for the on-demand
          instance.
        """

        kw = {'slave_name': name, 'slave_host': host,
              'slave_port': port, 'slave_token': token,
              'owner_id': str(owner.id), 'use_ssl': use_ssl,
              'validate_cert': validate_cert, 'on_demand': on_demand,
              'instance_type': instance_type, 'instance_confs': instance_confs}

        with await cls.get_client(requester) as client:
            slave_dict = await client.slave_add(**kw)
        slave = cls(requester, slave_dict)
        return slave

    @classmethod
    async def get(cls, requester, **kwargs):
        """Returns a slave.

        :param requester: The user who is requesting the operation.
        :param kwargs: kwargs to get the slave."""

        cls._handle_name_or_id('slave', kwargs)
        with await cls.get_client(requester) as client:
            slave_dict = await client.slave_get(**kwargs)
        slave = cls(requester, slave_dict)
        return slave

    @classmethod
    async def list(cls, requester):
        """Lists all slaves.

        :param requester: The user who is requesting the operation."""

        with await cls.get_client(requester) as client:
            slaves = await client.slave_list()
        slave_list = [cls(requester, slave) for slave in slaves]
        return slave_list

    async def delete(self):
        """Delete a slave."""

        with await self.get_client(self.requester) as client:
            resp = await client.slave_remove(slave_name_or_id=self.id)
        return resp

    async def update(self, **kwargs):
        """Updates a slave"""

        with await self.get_client(self.requester) as client:
            resp = await client.slave_update(slave_name_or_id=self.id,
                                             **kwargs)
        return resp


class BuilderInterface(BaseHoleInterface):

    @classmethod
    async def list(cls, requester, **kwargs):
        """Lists builders already used."""

        with await cls.get_client(requester) as client:
            builders = await client.builder_list(**kwargs)

        builders_list = [cls(requester, builder) for builder in builders]
        return builders_list


class StepInterface(BaseHoleInterface):

    @classmethod
    async def get(cls, requester, uuid):
        """Returns information about a step.
        :param uuid: The uuid of the step."""

        with await cls.get_client(requester) as client:
            sdict = await client.buildstep_get(step_uuid=uuid)

        step = cls(requester, sdict)
        return step


class BuildInterface(BaseHoleInterface):
    references = {'steps': StepInterface,
                  'builder': BuilderInterface}

    def to_dict(self, *args, **kwargs):
        """Converts a build object in to a dictionary.

        :param args: Positional arguments passed to
          :meth:`~toxicbuild.common.interfaces.BaseInterface.to_dict`.
        :param kwargs: Named arguments passed to
          :meth:`~toxicbuild.common.interfaces.BaseInterface.to_dict`.
        """
        d = super().to_dict(*args, **kwargs)
        d['builder'] = d['builder'].to_dict(*args, **kwargs)
        d['steps'] = [s.to_dict(*args, **kwargs) for s in d.get('steps', [])]
        return d

    @classmethod
    async def get(cls, requester, uuid):
        """Returns information about abuild.
        :param uuid: The uuid of the build."""

        with await cls.get_client(requester) as client:
            build_dict = await client.build_get(build_uuid=uuid)

        build = cls(requester, build_dict)
        return build


class RepositoryInterface(BaseHoleInterface):

    """Interface for a repository."""

    references = {
        'slaves': SlaveInterface,
        'last_buildset': 'toxicbuild.common.interfaces.BuildSetInterface'
    }

    @classmethod
    async def add(cls, requester, name, url, owner, vcs_type,
                  update_seconds=300, slaves=None, parallel_builds=None,
                  schedule_poller=True, branches=None, external_id=None,
                  external_full_name=None, fetch_url=None, envvars=None):
        """Adds a new repository.

        :param requester: The user who is requesting the operation.
        :param name: Repository's name.
        :param url: Repository's url.
        :param owner: The repository owner
        :param vcs_type: VCS type used on the repository.
        :param update_seconds: Interval to update the repository code.
        :param slaves: List with slave names for this reporitory.
        :params parallel_builds: How many paralles builds this repository
          executes. If None, there is no limit.
        :param schedule_poller: Should this repository be scheduled for
          polling? If this repository comes from an integration
          (with github, gitlab, etc...) this should be False.
        :param branches: A list of branches configuration that trigger builds.
        :param external_id: The id of the repository in an external service.
        :param external_full_name: The full name in an external service.
        :param fetch_url: If the repository uses a differente url to fetch code
          (ie: it has an auth token url) this is the fetch_url.
        :param envvars: Environment variables that will be used in every build
          in this repository.
        """

        kw = {'repo_name': name, 'repo_url': url, 'vcs_type': vcs_type,
              'update_seconds': update_seconds,
              'parallel_builds': parallel_builds,
              'owner_id': str(owner.id),
              'schedule_poller': schedule_poller,
              'branches': branches,
              'envvars': envvars or {},
              'external_id': external_id,
              'external_full_name': external_full_name,
              'fetch_url': fetch_url}

        kw.update({'slaves': slaves or []})

        with await cls.get_client(requester) as client:
            repo_dict = await client.repo_add(**kw)

        repo = cls(requester, repo_dict)
        return repo

    @classmethod
    async def get(cls, requester, **kwargs):
        """Returns a repository.

        :param requester: The user who is requesting the operation.
        :param kwargs: kwargs to get the repository."""

        cls._handle_name_or_id('repo', kwargs)
        with await cls.get_client(requester) as client:
            repo_dict = await client.repo_get(**kwargs)
        repo = cls(requester, repo_dict)
        return repo

    @classmethod
    async def list(cls, requester, **kwargs):
        """Lists all repositories.

        :param requester: The user who is requesting the operation."""

        with await cls.get_client(requester) as client:
            repos = await client.repo_list(**kwargs)
        repo_list = [cls(requester, repo) for repo in repos]
        return repo_list

    async def delete(self):
        """Delete a repository."""

        with await self.get_client(self.requester) as client:
            resp = await client.repo_remove(repo_name_or_id=self.id)
        return resp

    async def add_slave(self, slave):
        """Adds a slave to the repository.

        :param slave: A Slave instance."""

        with await self.get_client(self.requester) as client:
            resp = await client.repo_add_slave(repo_name_or_id=self.id,
                                               slave_name_or_id=slave.id)
        return resp

    async def remove_slave(self, slave):
        """Removes a slave from the repository.

        :param slave: A Slave instance.
        """

        with await self.get_client(self.requester) as client:
            resp = await client.repo_remove_slave(
                repo_name_or_id=self.id, slave_name_or_id=slave.id)
        return resp

    async def add_branch(self, branch_name, notify_only_latest):
        """Adds a branch config to a repositoiry.

        :param branch_name: The name of the branch.
        :param notify_only_latest: If we should create builds for all
          revisions or only for the lastest one."""

        with await self.get_client(self.requester) as client:
            resp = await client.repo_add_branch(
                repo_name_or_id=self.id, branch_name=branch_name,
                notify_only_latest=notify_only_latest)

        return resp

    async def remove_branch(self, branch_name):
        """Removes a branch config from a repository.

        :param branch_name: The name of the branch."""
        with await self.get_client(self.requester) as client:
            resp = await client.repo_remove_branch(
                repo_name_or_id=self.id, branch_name=branch_name)

        return resp

    async def update(self, **kwargs):
        """Updates a slave"""
        with await self.get_client(self.requester) as client:
            resp = await client.repo_update(repo_name_or_id=self.id,
                                            **kwargs)
        return resp

    async def start_build(self, branch, builder_name_or_id=None,
                          named_tree=None):
        """Starts a (some) build(s) for a repository.

        :param branch: The name of the branch.
        :param builder_name_or_id: The name of the builder that will execute
          the build
        :param named_tree: The named_tree that will be builded. If no
          named_tree the last one will be used.
        """

        with await self.get_client(self.requester) as client:
            resp = await client.repo_start_build(
                repo_name_or_id=self.id, branch=branch,
                builder_name_or_id=builder_name_or_id,
                named_tree=named_tree)
        return resp

    def to_dict(self, *args, **kwargs):
        """Transforms a repository into a dictionary.

        :param args: Positional arguments passed to
          :meth:`~toxicbuild.common.interfaces.BaseInterface.to_dict`.
        :param kwargs: Named arguments passed to
          :meth:`~toxicbuild.common.interfaces.BaseInterface.to_dict`.
        """

        d = super().to_dict(*args, **kwargs)
        d['slaves'] = [s.to_dict(*args, **kwargs) for s in d['slaves']]
        if self.last_buildset:
            d['last_buildset'] = self.last_buildset.to_dict(*args, **kwargs)
        return d

    async def cancel_build(self, build_uuid):
        """Cancels a build from the repository.

        :param build_uuid: The uuid of the build."""

        with await self.get_client(self.requester) as client:
            resp = await client.repo_cancel_build(repo_name_or_id=self.id,
                                                  build_uuid=build_uuid)

        return resp

    async def enable(self):
        """Enables this repository."""
        with await self.get_client(self.requester) as client:
            resp = await client.repo_enable(repo_name_or_id=self.id)

        return resp

    async def disable(self):
        """Disables this repository."""
        with await self.get_client(self.requester) as client:
            resp = await client.repo_disable(repo_name_or_id=self.id)

        return resp

    async def request_code_update(self, repo_branches=None, external=None,
                                  wait_for_lock=False):
        """Request the code update of the repository.

        :param repo_branches: A dictionary with information about the branches
          to be updated. If no ``repo_branches`` all branches in the repo
          config will be updated.

          The dictionary has the following format.

          .. code-block:: python

             {'branch-name': {'notify_only_latest': True}}

        :param external: If we should update code from an external
          (not the origin) repository, `external` is the information about
          this remote repo.
        :param wait_for_lock: Indicates if we should wait for the release of
          the lock or simply return if we cannot get a lock.
        """

        with await self.get_client(self.requester) as client:
            resp = await client.repo_request_code_update(
                repo_name_or_id=self.id, repo_branches=repo_branches,
                external=external, wait_for_lock=wait_for_lock)

        return resp

    async def add_envvars(self, **envvars):
        """Adds environment variables to use in the builds of this repository.

        :param envvars: Environment variables in the format {var: val, ...}
        """

        with await self.get_client(self.requester) as client:
            resp = await client.repo_add_envvars(
                repo_name_or_id=self.id, **envvars)

        return resp

    async def rm_envvars(self, **envvars):
        """Removes environment variables from this repository.

        :param envvars: Environment variables in the format {var: val, ...}
        """

        with await self.get_client(self.requester) as client:
            resp = await client.repo_rm_envvars(
                repo_name_or_id=self.id, **envvars)

        return resp

    async def replace_envvars(self, **envvars):
        """Replaces environment variables of this repository.

        :param envvars: Environment variables in the format {var: val, ...}
        """

        with await self.get_client(self.requester) as client:
            resp = await client.repo_replace_envvars(
                repo_name_or_id=self.id, **envvars)

        return resp

    async def list_branches(self):
        """Lists the branches known by this repositor.
        """

        repo_name_or_id = self.id or self.full_name
        with await self.get_client(self.requester) as client:
            resp = await client.repo_list_branches(
                repo_name_or_id=repo_name_or_id)

        return resp


class BuildSetInterface(BaseHoleInterface):
    references = {'builds': BuildInterface,
                  'repository': RepositoryInterface}

    @classmethod
    async def list(cls, requester, repo_name_or_id=None, summary=True,
                   branch=None):
        """Lists buildsets. If ``repo_name_or_id`` only builds of this
        repsitory will be listed.

        :param repo_name: Name of a repository.
        :param summary: If True, no builds information will be returned.
        :param branch: List buildsets for this branch. If None list buildsets
          from all branches.
        """

        with await cls.get_client(requester) as client:
            buildsets = await client.buildset_list(
                repo_name_or_id=repo_name_or_id, offset=10,
                summary=summary, branch=branch)

        buildset_list = [cls(requester, buildset) for buildset in buildsets]
        return buildset_list

    def to_dict(self, *args, **kwargs):
        """Returns a dictionary based in a BuildSet object.

        :param args: Positional arguments passed to
          :meth:`~toxicbuild.common.interfaces.BaseInterface.to_dict`.
        :param kwargs: Named arguments passed to
          :meth:`~toxicbuild.common.interfaces.BaseInterface.to_dict`.
        """
        d = super().to_dict(*args, **kwargs)
        d['builds'] = [b.to_dict(*args, **kwargs) for b in d.get('builds', [])]
        d['repository'] = self.repository.to_dict(*args, **kwargs) \
            if self.repository else None
        return d

    @classmethod
    async def get(cls, requester, buildset_id):
        """Returns an instance of BuildSet.

        :param buildset_id: The id of the buildset to get.
        """

        with await cls.get_client(requester) as client:
            buildset = await client.buildset_get(buildset_id=buildset_id)

        return cls(requester, buildset)
