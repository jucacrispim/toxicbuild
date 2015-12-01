# -*- coding: utf-8 -*-

# Copyright 2015 Juca Crispim <juca@poraodojuca.net>

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

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    @asyncio.coroutine
    def get_client(cls):
        host = settings.HOLE_HOST
        port = settings.HOLE_PORT
        client = yield from get_hole_client(host, port)
        return client

    def to_dict(self):

        attrs = [a for a in dir(self) if not a.startswith('_')]

        d = {}
        for attr in attrs:
            objattr = getattr(self, attr)
            if not callable(objattr):
                d[attr] = objattr

        return d

    def to_json(self):
        d = self.to_dict()
        return json.dumps(d)


class Repository(BaseModel):

    def __init__(self, **kwargs):
        if 'slaves' in kwargs:

            slaves = [Slave(**kw) for kw in kwargs['slaves']]
            self.slaves = slaves
            del kwargs['slaves']

        super().__init__(**kwargs)

    @classmethod
    @asyncio.coroutine
    def add(cls, name, url, vcs_type, update_seconds=300, slaves=[]):
        kw = {'repo_name': name, 'repo_url': url, 'vcs_type': vcs_type,
              'update_seconds': update_seconds}

        kw.update({'slaves': slaves})
        client = yield from cls.get_client()
        repo_dict = yield from client.repo_add(**kw)
        repo = cls(**repo_dict)
        return repo

    @classmethod
    @asyncio.coroutine
    def get(cls, **kwargs):
        client = yield from cls.get_client()
        repo_dict = yield from client.repo_get(**kwargs)
        repo = cls(**repo_dict)
        return repo

    @classmethod
    @asyncio.coroutine
    def list(cls):
        client = yield from cls.get_client()
        repos = yield from client.repo_list()
        repo_list = [cls(**repo) for repo in repos]
        return repo_list

    @asyncio.coroutine
    def delete(self):
        client = yield from self.get_client()
        resp = yield from client.repo_remove(repo_name=self.name)
        return resp

    @asyncio.coroutine
    def add_slave(self, slave):
        client = yield from self.get_client()
        resp = yield from client.repo_add_slave(repo_name=self.name,
                                                slave_name=slave.name)
        return resp

    @asyncio.coroutine
    def remove_slave(self, slave):
        client = yield from self.get_client()
        resp = yield from client.repo_remove_slave()
        return resp

    @asyncio.coroutine
    def start_build(self, branch, builder_name=None, named_tree=None,
                    slaves=[]):

        client = yield from self.get_client()
        resp = yield from client.repo_start_build(repo_name=self.name,
                                                  branch=branch,
                                                  builder_name=builder_name,
                                                  named_tree=named_tree,
                                                  slaves=slaves)
        return resp


class Slave(BaseModel):

    @classmethod
    @asyncio.coroutine
    def add(cls, name, host, port):
        kw = {'slave_name': name, 'slave_host': host,
              'slave_port': port}
        client = yield from cls.get_client()
        slave_dict = yield from client.slave_add(**kw)
        slave = cls(**slave_dict)
        return slave

    @classmethod
    @asyncio.coroutine
    def get(cls, **kwargs):
        client = yield from cls.get_client()
        repo_dict = yield from client.slave_get(**kwargs)
        repo = cls(**repo_dict)
        return repo

    @classmethod
    @asyncio.coroutine
    def list(cls):
        client = yield from cls.get_client()
        slaves = yield from client.slave_list()
        slave_list = [cls(**slave) for slave in slaves]
        return slave_list

    @asyncio.coroutine
    def delete(self):
        client = yield from self.get_client()
        resp = yield from client.slave_remove(slave_name=self.name)
        return resp
