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

# User Interface Hole: The place where master's clients can ask
# for what they need.

import asyncio
import json
from toxicbuild.core import BaseToxicProtocol
from toxicbuild.master import Slave, Repository, Build, Builder


class UIHole(BaseToxicProtocol):

    """ Protocol for user interfaces access toxicbuild master
    in a unified way.
    """

    @asyncio.coroutine
    def client_connected(self):
        data = self.data.get('body') or {}
        try:
            handler = HoleHandler(data, self.action)
            resp = yield from handler.handle()
            yield from self.send_response(code=0, body=resp)
        except Exception as e:
            yield from self.send_response(code=1, body={'message': str(e)})

        self.close_connection()


class HoleHandler:

    """ Handles the incomming connections for the UIHole. """

    def __init__(self, data, action):
        self.data = data
        self.action = action
        self.funcs = {'repo-add': self.repo_add,
                      'repo-remove': self.repo_remove,
                      'repo-list': self.repo_list,
                      'repo-update': self.repo_update,
                      'repo-add-slave': self.repo_add_slave,
                      'repo-remove-slave': self.repo_remove_slave,
                      'slave-add': self.slave_add,
                      'slave-remove': self.slave_remove,
                      'slave-list': self.slave_list,
                      'builder-list': self.builder_list,
                      'builder-show': None,
                      'list-funcs': self.list_funcs}

    @asyncio.coroutine
    def handle(self):
        func = self.funcs.get(self.action)
        if not func:
            raise

        r = yield from func()
        return r

    @asyncio.coroutine
    def repo_add(self):
        """ Adds a new repository and first_run() it. """

        url = self.data['url']
        vcs_type = self.data['vcs_type']
        update_seconds = self.data['update_seconds']
        slaves = []
        for host, port in self.data['slaves']:
            slave = yield from Slave.get(host=host, port=port)
            slaves.append(slave)

        repo = yield from Repository.create(url, update_seconds, vcs_type,
                                            slaves)
        repo.first_run()
        repo = json.loads(repo.to_json())
        return {'repo-add': repo}

    @asyncio.coroutine
    def repo_remove(self):
        url = self.data['url']

        repo = yield from Repository.get(url)
        yield repo.delete()
        return {'repo-remove': 'ok'}

    @asyncio.coroutine
    def repo_list(self):
        repos = yield Repository.objects.all().to_list()
        repo_list = []
        for repo in repos:

            repo_dict = json.loads(repo.to_json())
            repo_list.append(repo_dict)

        return {'repo-list': repo_list}

    @asyncio.coroutine
    def repo_update(self):
        repo = yield from Repository.get(self.data['url'])
        repo.vcs_type = self.data.get('vcs_type') or repo.vcs_type
        repo.update_seconds = self.data.get(
            'update_seconds') or repo.update_seconds
        yield repo.save()
        return {'repo-update': 'ok'}

    @asyncio.coroutine
    def repo_add_slave(self):
        repo = yield from Repository.get(self.data['url'])
        slave = yield from Slave.get(self.data['host'],
                                     self.data['port'])
        yield from repo.add_slave(slave)
        return {'repo-add-slave': 'ok'}

    @asyncio.coroutine
    def repo_remove_slave(self):
        repo = yield from Repository.get(self.data['url'])
        slave = yield from Slave.get(self.data['host'],
                                     self.data['port'])
        yield from repo.remove_slave(slave)
        return {'repo-remove-slave': 'ok'}

    @asyncio.coroutine
    def slave_add(self):
        host = self.data['host']
        port = self.data['port']
        slave = yield from Slave.create(host, port)

        slave_dict = json.loads(slave.to_json())
        return {'slave-add': slave_dict}

    @asyncio.coroutine
    def slave_remove(self):
        host = self.data['host']
        port = self.data['port']
        slave = yield from Slave.get(host, port)
        yield slave.delete()

        return {'slave-remove', 'ok'}

    @asyncio.coroutine
    def slave_list(self):
        slaves = yield Slave.objects.all().to_list()
        slave_list = []

        for slave in slaves:
            slave_list.append(json.loads(slave.to_json()))

        return {'slave-list': slave_list}

    @asyncio.coroutine
    def builder_list(self):
        repo_url = self.data.get('repo-url')
        builders = Builder.objects
        if repo_url:
            builders = builders.filter(repository__url=repo_url)

        builders = yield builders.to_list()

        builder_list = []

        for builder in builders:
            builder_dict = json.loads(builder.to_json())
            builder_dict['status'] = (yield Build.objects.filter(
                builder=builder).order_by('-started')[0]).status

            builder_list.append(builder_dict)

        return {'builder-list': builder_list}

    @asyncio.coroutine
    def builder_show(self):
        repo_url = self.data.get('repo-url')
        builder_name = self.data['name']
        kwargs = {'name': builder_name}
        if repo_url:
            repo = yield from Repository.get(repo_url)
            kwargs.update({'repository': repo})
        builder = yield Builder.objects.get(**kwargs)
        builder_dict = json.loads(builder.to_json())
        build_list = []
        for build in (yield Build.objects.filter(builder=builder).to_list()):
            build_dict = json.loads(build.to_json())
            build_list.append(build_dict)
        builder_dict.update({'builds': build_list})
        return {'builder-show': builder_dict}

    @asyncio.coroutine
    def list_funcs(self):
        """ Lists the functions available for user interfaces. """

        funcs = [k for k, v in self.funcs.items() if v]
        return {'funcs': funcs}


class HoleServer:

    def __init__(self, addr='127.0.0.1', port=6666):
        self.protocol = UIHole
        self.loop = asyncio.get_event_loop()
        self.addr = addr
        self.port = port

    def serve(self):

        coro = self.loop.create_server(
            self.get_protocol_instance, self.addr,  self.port)

        asyncio.async(coro)

    def get_protocol_instance(self):
        return self.protocol(self.loop)
