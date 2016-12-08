# -*- coding: utf-8 -*-

# Copyright 2015 2016 Juca Crispim <juca@poraodojuca.net>

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
import json
from toxicbuild.ui.client import get_hole_client
from toxicbuild.ui import settings


class BaseModel:
    # These references are fields that refer to other objects.
    # Note that this references are not always references on
    # database, they may be (and most are) embedded documents
    # that are simply treated as other objects.
    references = {}

    def __init__(self, **kwargs):
        # here is where we transform the dictonaries from the
        # master's response into objects that are references.
        for name, cls in self.references.items():
            if not isinstance(kwargs.get(name), (dict, cls)):
                kwargs[name] = [cls(**kw) if not isinstance(kw, cls) else kw
                                for kw in kwargs.get(name, [])]
            else:
                obj = kwargs[name]
                kwargs[name] = cls(**obj) if not isinstance(obj, cls) else obj

        for key, value in kwargs.items():
            setattr(self, key, value)

    def __eq__(self, other):
        return type(self) == type(other) and self.id == other.id

    def __hash__(self):
        return hash(self.id)

    @classmethod
    @asyncio.coroutine
    def get_client(cls):
        """Returns a client connected to master."""

        host = settings.HOLE_HOST
        port = settings.HOLE_PORT
        client = yield from get_hole_client(host, port)
        return client

    def to_dict(self):
        """Transforms a model into a dict."""

        attrs = [a for a in dir(self) if not a.startswith('_')]

        d = {}
        for attr in attrs:
            objattr = getattr(self, attr)
            if not callable(objattr) and attr != 'references':
                d[attr] = objattr

        return d

    def to_json(self):
        """Transforms a model into a json."""

        d = self.to_dict()
        return json.dumps(d)


class Slave(BaseModel):

    @classmethod
    @asyncio.coroutine
    def add(cls, name, host, port, token):
        """Adds a new slave.

        :param name: Slave name.
        :param host: Slave host.
        :param port: Slave port.
        :param token: Authentication token.
        """

        kw = {'slave_name': name, 'slave_host': host,
              'slave_port': port, 'slave_token': token}

        with (yield from cls.get_client()) as client:
            slave_dict = yield from client.slave_add(**kw)
        slave = cls(**slave_dict)
        return slave

    @classmethod
    @asyncio.coroutine
    def get(cls, **kwargs):
        """Returns a slave.

        :param kwargs: kwargs to get the slave."""

        with (yield from cls.get_client()) as client:
            slave_dict = yield from client.slave_get(**kwargs)
        slave = cls(**slave_dict)
        return slave

    @classmethod
    @asyncio.coroutine
    def list(cls):
        """Lists all slaves."""

        with (yield from cls.get_client()) as client:
            slaves = yield from client.slave_list()
        slave_list = [cls(**slave) for slave in slaves]
        return slave_list

    @asyncio.coroutine
    def delete(self):
        """Delete a slave."""

        with (yield from self.get_client()) as client:
            resp = yield from client.slave_remove(slave_name=self.name)
        return resp

    @asyncio.coroutine
    def update(self, **kwargs):
        """Updates a slave"""
        with (yield from self.get_client()) as client:
            resp = yield from client.slave_update(slave_name=self.name,
                                                  **kwargs)
        return resp


class Plugin(BaseModel):
    """A repository plugin."""

    @classmethod
    def list(cls):
        """Lists all plugins available in the master."""
        with (yield from cls.get_client()) as client:
            resp = yield from client.plugin_list()

        plugins = [cls(**p) for p in resp]
        return plugins


class Repository(BaseModel):

    """Class representing a repository."""

    references = {'slaves': Slave,
                  'plugins': Plugin}

    @classmethod
    @asyncio.coroutine
    def add(cls, name, url, vcs_type, update_seconds=300, slaves=[]):
        """Adds a new repository.

        :param name: Repository's name.
        :param url: Repository's url.
        :param vcs_type: VCS type used on the repository.
        :param update_seconds: Interval to update the repository code.
        :param slaves: List with slave names for this reporitory."""

        kw = {'repo_name': name, 'repo_url': url, 'vcs_type': vcs_type,
              'update_seconds': update_seconds}

        kw.update({'slaves': slaves})
        with (yield from cls.get_client()) as client:
            repo_dict = yield from client.repo_add(**kw)
        repo = cls(**repo_dict)
        return repo

    @classmethod
    @asyncio.coroutine
    def get(cls, **kwargs):
        """Returns a repository.

        :param kwargs: kwargs to get the repository."""

        with (yield from cls.get_client()) as client:
            repo_dict = yield from client.repo_get(**kwargs)
        repo = cls(**repo_dict)
        return repo

    @classmethod
    @asyncio.coroutine
    def list(cls):
        """Lists all repositories."""

        with (yield from cls.get_client()) as client:
            repos = yield from client.repo_list()
        repo_list = [cls(**repo) for repo in repos]
        return repo_list

    @asyncio.coroutine
    def delete(self):
        """Delete a repository."""

        with (yield from self.get_client()) as client:
            resp = yield from client.repo_remove(repo_name=self.name)
        return resp

    @asyncio.coroutine
    def add_slave(self, slave):
        """Adds a slave to the repository.

        :param slave: A Slave instance."""

        client = yield from self.get_client()
        with (yield from self.get_client()) as client:
            resp = yield from client.repo_add_slave(repo_name=self.name,
                                                    slave_name=slave.name)
        return resp

    @asyncio.coroutine
    def remove_slave(self, slave):
        """Removes a slave from the repository.

        :param slave: A Slave instance.
        """

        with (yield from self.get_client()) as client:
            resp = yield from client.repo_remove_slave(repo_name=self.name,
                                                       slave_name=slave.name)
        return resp

    @asyncio.coroutine
    def add_branch(self, branch_name, notify_only_latest):
        """Adds a branch config to a repositoiry.

        :param branch_name: The name of the branch.
        :param notify_only_latest: If we should create builds for all
          revisions or only for the lastest one."""

        with (yield from self.get_client()) as client:
            resp = yield from client.repo_add_branch(
                repo_name=self.name, branch_name=branch_name,
                notify_only_latest=notify_only_latest)

        return resp

    @asyncio.coroutine
    def remove_branch(self, branch_name):
        """Removes a branch config from a repository.

        :param branch_name: The name of the branch."""
        with (yield from self.get_client()) as client:
            resp = yield from client.repo_remove_branch(
                repo_name=self.name, branch_name=branch_name)

        return resp

    @asyncio.coroutine
    def update(self, **kwargs):
        """Updates a slave"""
        with (yield from self.get_client()) as client:
            resp = yield from client.repo_update(repo_name=self.name,
                                                 **kwargs)
        return resp

    @asyncio.coroutine
    def start_build(self, branch, builder_name=None, named_tree=None,
                    slaves=[]):
        """Starts a (some) build(s) for a repository.

        :param branch: The name of the branch.
        :param builder_name: The name of the builder that will execute
          the build
        :param named_tree: The named_tree that will be builded. If no
          named_tree the last one will be used.
        :param slaves: A list with names of slaves that will execute
          the builds. If no slave is supplied all will be used."""

        with (yield from self.get_client()) as client:
            resp = yield from client.repo_start_build(
                repo_name=self.name, branch=branch, builder_name=builder_name,
                named_tree=named_tree, slaves=slaves)
        return resp

    def to_dict(self):
        """Transforms a repository into a dictionary."""

        d = super().to_dict()
        d['slaves'] = [s.to_dict() for s in d['slaves']]
        return d

    def enable_plugin(self, plugin_name, **kwargs):
        """Enables a plugin to a repository.

        :param plugin_name: The plugin's name.
        :param kwargs: kwargs used to configure the plugin.
        """

        with (yield from self.get_client()) as client:
            resp = yield from client.repo_enable_plugin(
                repo_name=self.name, plugin_name=plugin_name, **kwargs)

        return resp

    def disable_plugin(self, **kwargs):
        """Disables a plugin from a repository.

        :param kwargs: kwargs to match the plugin."""

        with (yield from self.get_client()) as client:
            resp = yield from client.repo_disable_plugin(
                repo_name=self.name, **kwargs)

        return resp


class Builder(BaseModel):

    @classmethod
    @asyncio.coroutine
    def list(cls, **kwargs):
        """Lists builders already used."""

        with (yield from cls.get_client()) as client:
            builders = yield from client.builder_list(**kwargs)

        builders_list = [cls(**builder) for builder in builders]
        return builders_list


class Step(BaseModel):
    pass


class Build(BaseModel):
    references = {'steps': Step,
                  'builder': Builder}


class BuildSet(BaseModel):
    references = {'builds': Build}

    def __init__(self, *args, **kw):

        super().__init__(*args, **kw)

    @classmethod
    @asyncio.coroutine
    def list(cls, repo_name=None):
        """Lists buildsets. If ``repo_name`` only builds of this
        repsitory will be listed.

        :param repo_name: Name of a repository."""

        with (yield from cls.get_client()) as client:
            buildsets = yield from client.buildset_list(repo_name=repo_name,
                                                        offset=10)
        buildset_list = [cls(**buildset) for buildset in buildsets]
        return buildset_list
