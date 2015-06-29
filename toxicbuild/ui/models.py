# -*- coding: utf-8 -*-

import asyncio
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


class Repository(BaseModel):

    @classmethod
    @asyncio.coroutine
    def add(cls, name, url, vcs_type, update_seconds=300, slaves=[]):
        kw = {'repo_name': name, 'repo_url': url, 'vcs_type': vcs_type,
              'update_seconds': update_seconds}

        slaves = [s.name for s in slaves]

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
        resp = yield from client.repo_start_build(branch=branch,
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
