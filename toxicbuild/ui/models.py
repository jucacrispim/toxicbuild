# -*- coding: utf-8 -*-

# Copyright 2015-2019 Juca Crispim <juca@poraodojuca.net>

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


import asyncio
from toxicbuild.common.api_models import BaseModel as BaseAPIModel
from toxicbuild.ui import settings
from toxicbuild.ui.client import get_hole_client
from toxicbuild.ui.utils import (
    get_client_settings,
)


class BaseModel(BaseAPIModel):
    # These references are fields that refer to other objects.
    # Note that this references are not always references on
    # database, they may be (and most are) embedded documents
    # that are simply treated as other objects.
    references = {}

    # This is for the cli only. Do not use.
    _client = None

    @classmethod
    @asyncio.coroutine
    def get_client(cls, requester):
        """Returns a client connected to master."""

        if cls._client:
            if not cls._client._connected:
                yield from cls._client.connect()
            return cls._client

        client_settings = get_client_settings()
        client = yield from get_hole_client(requester, **client_settings)
        return client


class User(BaseModel):
    """A user created in the master"""

    def __init__(self, requester, ordered_kwargs):
        if requester is None:
            requester = self
        super().__init__(requester, ordered_kwargs)

    @classmethod
    def _get_root_user(cls):
        root_id = settings.ROOT_USER_ID
        return cls(None, {'id': root_id})

    @classmethod
    async def authenticate(cls, username_or_email, password):
        kw = {'username_or_email': username_or_email,
              'password': password}

        with (await cls.get_client(None)) as client:
            user_dict = await client.user_authenticate(**kw)
        user = cls(None, user_dict)
        return user

    @classmethod
    async def change_password(cls, requester, old_password,
                              new_password):
        kw = {'username_or_email': requester.email,
              'old_password': old_password,
              'new_password': new_password}

        with (await cls.get_client(requester)) as client:
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

        with (await cls.get_client(requester)) as client:
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

        with (await cls.get_client(requester)) as client:
            await client.user_change_password_with_token(**kw)

        return True

    @classmethod
    async def add(cls, email, username, password,
                  allowed_actions):
        requester = cls._get_root_user()
        kw = {'username': username,
              'email': email,
              'password': password, 'allowed_actions': allowed_actions}

        with (await cls.get_client(requester)) as client:
            user_dict = await client.user_add(**kw)
        user = cls(None, user_dict)
        return user

    async def delete(self):
        kw = {'id': str(self.id)}
        with (await type(self).get_client(self.requester)) as client:
            resp = await client.user_remove(**kw)
        return resp

    @classmethod
    async def exists(cls, **kwargs):
        """Checks if a user with some given information exists.

        :param kwargs: Named arguments to match the user"""
        requester = cls._get_root_user()
        with (await cls.get_client(requester)) as client:
            exists = await client.user_exists(**kwargs)

        return exists


class Slave(BaseModel):

    @classmethod
    @asyncio.coroutine
    def add(cls, requester, name, port, token, owner,
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

        with (yield from cls.get_client(requester)) as client:
            slave_dict = yield from client.slave_add(**kw)
        slave = cls(requester, slave_dict)
        return slave

    @classmethod
    @asyncio.coroutine
    def get(cls, requester, **kwargs):
        """Returns a slave.

        :param requester: The user who is requesting the operation.
        :param kwargs: kwargs to get the slave."""

        cls._handle_name_or_id('slave', kwargs)
        with (yield from cls.get_client(requester)) as client:
            slave_dict = yield from client.slave_get(**kwargs)
        slave = cls(requester, slave_dict)
        return slave

    @classmethod
    @asyncio.coroutine
    def list(cls, requester):
        """Lists all slaves.

        :param requester: The user who is requesting the operation."""

        with (yield from cls.get_client(requester)) as client:
            slaves = yield from client.slave_list()
        slave_list = [cls(requester, slave) for slave in slaves]
        return slave_list

    @asyncio.coroutine
    def delete(self):
        """Delete a slave."""

        with (yield from self.get_client(self.requester)) as client:
            resp = yield from client.slave_remove(slave_name_or_id=self.id)
        return resp

    @asyncio.coroutine
    def update(self, **kwargs):
        """Updates a slave"""

        with (yield from self.get_client(self.requester)) as client:
            resp = yield from client.slave_update(slave_name_or_id=self.id,
                                                  **kwargs)
        return resp


class Builder(BaseModel):

    @classmethod
    @asyncio.coroutine
    def list(cls, requester, **kwargs):
        """Lists builders already used."""

        with (yield from cls.get_client(requester)) as client:
            builders = yield from client.builder_list(**kwargs)

        builders_list = [cls(requester, builder) for builder in builders]
        return builders_list


class Step(BaseModel):
    pass


class Build(BaseModel):
    references = {'steps': Step,
                  'builder': Builder}

    def to_dict(self, *args, **kwargs):
        """Converts a build object in to a dictionary.

        :param args: Positional arguments passed to
          :meth:`~toxicbuild.ui.models.BaseModel.to_dict`.
        :param kwargs: Named arguments passed to
          :meth:`~toxicbuild.ui.models.BaseModel.to_dict`.
        """
        d = super().to_dict(*args, **kwargs)
        d['builder'] = d['builder'].to_dict(*args, **kwargs)
        d['steps'] = [s.to_dict(*args, **kwargs) for s in d.get('steps', [])]
        return d

    @classmethod
    @asyncio.coroutine
    def get(cls, requester, uuid):
        """Returns information about abuild.
        :param uuid: The uuid of the build."""

        with (yield from cls.get_client(requester)) as client:
            build_dict = yield from client.build_get(build_uuid=uuid)

        build = cls(requester, build_dict)
        return build


class Repository(BaseModel):

    """Class representing a repository."""

    references = {'slaves': Slave,
                  'last_buildset': 'toxicbuild.ui.models.BuildSet'}

    @classmethod
    @asyncio.coroutine
    def add(cls, requester, name, url, owner, vcs_type, update_seconds=300,
            slaves=None, parallel_builds=None):
        """Adds a new repository.

        :param requester: The user who is requesting the operation.
        :param name: Repository's name.
        :param url: Repository's url.
        :param owner: The repository owner
        :param vcs_type: VCS type used on the repository.
        :param update_seconds: Interval to update the repository code.
        :param slaves: List with slave names for this reporitory.
        :params parallel_builds: How many paralles builds this repository
          executes. If None, there is no limit."""

        kw = {'repo_name': name, 'repo_url': url, 'vcs_type': vcs_type,
              'update_seconds': update_seconds,
              'parallel_builds': parallel_builds,
              'owner_id': str(owner.id)}

        kw.update({'slaves': slaves or []})

        with (yield from cls.get_client(requester)) as client:
            repo_dict = yield from client.repo_add(**kw)

        repo = cls(requester, repo_dict)
        return repo

    @classmethod
    @asyncio.coroutine
    def get(cls, requester, **kwargs):
        """Returns a repository.

        :param requester: The user who is requesting the operation.
        :param kwargs: kwargs to get the repository."""

        cls._handle_name_or_id('repo', kwargs)
        with (yield from cls.get_client(requester)) as client:
            repo_dict = yield from client.repo_get(**kwargs)
        repo = cls(requester, repo_dict)
        return repo

    @classmethod
    @asyncio.coroutine
    def list(cls, requester, **kwargs):
        """Lists all repositories.

        :param requester: The user who is requesting the operation."""

        with (yield from cls.get_client(requester)) as client:
            repos = yield from client.repo_list(**kwargs)
        repo_list = [cls(requester, repo) for repo in repos]
        return repo_list

    @asyncio.coroutine
    def delete(self):
        """Delete a repository."""

        with (yield from self.get_client(self.requester)) as client:
            resp = yield from client.repo_remove(repo_name_or_id=self.id)
        return resp

    @asyncio.coroutine
    def add_slave(self, slave):
        """Adds a slave to the repository.

        :param slave: A Slave instance."""

        with (yield from self.get_client(self.requester)) as client:
            resp = yield from client.repo_add_slave(repo_name_or_id=self.id,
                                                    slave_name_or_id=slave.id)
        return resp

    @asyncio.coroutine
    def remove_slave(self, slave):
        """Removes a slave from the repository.

        :param slave: A Slave instance.
        """

        with (yield from self.get_client(self.requester)) as client:
            resp = yield from client.repo_remove_slave(
                repo_name_or_id=self.id, slave_name_or_id=slave.id)
        return resp

    @asyncio.coroutine
    def add_branch(self, branch_name, notify_only_latest):
        """Adds a branch config to a repositoiry.

        :param branch_name: The name of the branch.
        :param notify_only_latest: If we should create builds for all
          revisions or only for the lastest one."""

        with (yield from self.get_client(self.requester)) as client:
            resp = yield from client.repo_add_branch(
                repo_name_or_id=self.id, branch_name=branch_name,
                notify_only_latest=notify_only_latest)

        return resp

    @asyncio.coroutine
    def remove_branch(self, branch_name):
        """Removes a branch config from a repository.

        :param branch_name: The name of the branch."""
        with (yield from self.get_client(self.requester)) as client:
            resp = yield from client.repo_remove_branch(
                repo_name_or_id=self.id, branch_name=branch_name)

        return resp

    @asyncio.coroutine
    def update(self, **kwargs):
        """Updates a slave"""
        with (yield from self.get_client(self.requester)) as client:
            resp = yield from client.repo_update(repo_name_or_id=self.id,
                                                 **kwargs)
        return resp

    @asyncio.coroutine
    def start_build(self, branch, builder_name=None, named_tree=None):
        """Starts a (some) build(s) for a repository.

        :param branch: The name of the branch.
        :param builder_name: The name of the builder that will execute
          the build
        :param named_tree: The named_tree that will be builded. If no
          named_tree the last one will be used.
        """

        with (yield from self.get_client(self.requester)) as client:
            resp = yield from client.repo_start_build(
                repo_name_or_id=self.id, branch=branch,
                builder_name=builder_name,
                named_tree=named_tree)
        return resp

    def to_dict(self, *args, **kwargs):
        """Transforms a repository into a dictionary.

        :param args: Positional arguments passed to
          :meth:`~toxicbuild.ui.models.BaseModel.to_dict`.
        :param kwargs: Named arguments passed to
          :meth:`~toxicbuild.ui.models.BaseModel.to_dict`.
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
        with await self.get_client(self.requester) as client:
            resp = await client.repo_enable(repo_name_or_id=self.id)

        return resp

    async def disable(self):
        with await self.get_client(self.requester) as client:
            resp = await client.repo_disable(repo_name_or_id=self.id)

        return resp


class BuildSet(BaseModel):
    references = {'builds': Build,
                  'repository': Repository}

    @classmethod
    @asyncio.coroutine
    def list(cls, requester, repo_name_or_id=None, summary=True):
        """Lists buildsets. If ``repo_name_or_id`` only builds of this
        repsitory will be listed.

        :param repo_name: Name of a repository.
        :param summary: If True, no builds information will be returned.
        """

        with (yield from cls.get_client(requester)) as client:
            buildsets = yield from client.buildset_list(
                repo_name_or_id=repo_name_or_id, offset=10,
                summary=summary)

        buildset_list = [cls(requester, buildset) for buildset in buildsets]
        return buildset_list

    def to_dict(self, *args, **kwargs):
        """Returns a dictionary based in a BuildSet object.

        :param args: Positional arguments passed to
          :meth:`~toxicbuild.ui.models.BaseModel.to_dict`.
        :param kwargs: Named arguments passed to
          :meth:`~toxicbuild.ui.models.BaseModel.to_dict`.
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

        with (await cls.get_client(requester)) as client:
            buildset = await client.buildset_get(buildset_id=buildset_id)

        return cls(requester, buildset)
