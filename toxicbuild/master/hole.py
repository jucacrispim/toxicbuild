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

# Welcome to the strange land of the user interface hole,
# the place where master's clients can ask for what they need...
# ... e onde tudo pode acontecer...

import asyncio
import inspect
import json
from tornado.platform.asyncio import to_asyncio_future
from toxicbuild.core import BaseToxicProtocol
from toxicbuild.core.utils import log
from toxicbuild.master import (Slave, Repository, Build, Builder,
                               RepositoryRevision)
from toxicbuild.master.exceptions import UIFunctionNotFound
from toxicbuild.master.signals import (step_started, step_finished,
                                       build_started, build_finished)


class UIHole(BaseToxicProtocol):

    @asyncio.coroutine
    def client_connected(self):
        data = self.data.get('body') or {}
        if self.action == 'stream':
            handler = UIStreamHandler(self)
        else:
            handler = HoleHandler(data, self.action, self)

        try:
            yield from handler.handle()
        except Exception as e:
            msg = str(e)
            yield from self.send_response(code=1, body={'error': msg})
            self.close_connection()


class HoleHandler:

    """ Handles the incomming connections for the UIHole. It has the following
    methods available to the clients:

    * `repo-add`
    * `repo-list`
    * `repo-remove`
    * `repo-update`
    * `repo-add-slave`
    * `repo-remove-slave`
    * `repo-start-build`
    * `slave-add`
    * `slave-list`
    * `slave-remove`
    * `builder-list`
    * `builder-show`
    * `list-funcs`
    """

    def __init__(self, data, action, protocol):
        self.data = data
        self.action = action
        self.protocol = protocol

    @asyncio.coroutine
    def handle(self):
        self.log('Executing {}'.format(self.action))

        attrname = self.action.replace('-', '_')
        if attrname not in self._get_action_methods():
            raise UIFunctionNotFound(self.action)

        func = getattr(self, attrname)
        r = func(**self.data)
        if asyncio.coroutines.iscoroutine(r):
            r = yield from r

        yield from self.protocol.send_response(code=0, body=r)
        self.protocol.close_connection()

    def _get_method_signature(self, method):
        sig = inspect.signature(method)
        doc = method.__doc__ or ''
        siginfo = {'doc': doc, 'parameters': []}

        for name, param in sig.parameters.items():
            pinfo = {'name': name}
            required = '=' not in str(param)
            pinfo['required'] = required
            if not required:
                default = param.default
                pinfo['default'] = default

            siginfo['parameters'].append(pinfo)

        return siginfo

    @asyncio.coroutine
    def repo_add(self, repo_name, repo_url, update_seconds, vcs_type,
                 slaves=None):
        """ Adds a new repository and first_run() it. """

        slaves_info = slaves or []
        slaves = []
        for name in slaves_info:
            slave = yield from Slave.get(name=name)
            slaves.append(slave)

        repo = yield from Repository.create(repo_name, repo_url,
                                            update_seconds, vcs_type, slaves)
        repo = json.loads(repo.to_json())
        return {'repo-add': repo}

    @asyncio.coroutine
    def repo_remove(self, repo_name):
        """ Removes a repository from toxicubild """

        repo = yield from Repository.get(name=repo_name)
        yield from repo.remove()
        return {'repo-remove': 'ok'}

    @asyncio.coroutine
    def repo_list(self):
        """ Lists all repositories. """

        repos = yield from to_asyncio_future(
            Repository.objects.all().to_list())
        repo_list = []
        for repo in repos:

            repo_dict = json.loads(repo.to_json())
            repo_list.append(repo_dict)

        return {'repo-list': repo_list}

    @asyncio.coroutine
    def repo_update(self, repo_name, **kwargs):
        """ Updates repository information. """

        repo = yield from Repository.get(name=repo_name)
        [setattr(repo, k, v) for k, v in kwargs.items()]

        yield from to_asyncio_future(repo.save())
        return {'repo-update': 'ok'}

    @asyncio.coroutine
    def repo_add_slave(self, repo_name, slave_name):
        """ Adds a slave to a repository. """

        repo = yield from Repository.get(name=repo_name)
        slave = yield from Slave.get(name=slave_name)
        yield from repo.add_slave(slave)
        return {'repo-add-slave': 'ok'}

    @asyncio.coroutine
    def repo_remove_slave(self, repo_name, slave_name):
        """ Removes a slave from toxicbuild. """

        repo = yield from Repository.get(name=repo_name)

        slave = yield from Slave.get(name=slave_name)
        yield from repo.remove_slave(slave)
        return {'repo-remove-slave': 'ok'}

    @asyncio.coroutine
    def repo_start_build(self, repo_name, branch, builder_name=None,
                         named_tree=None, slaves=[]):
        """ Starts a(some) build(s) in a given repository. """

        # Mutable stuff on method declaration Sin!!! Take that, PyLint!

        repo = yield from Repository.get(name=repo_name)

        slaves = yield from [(yield from Slave.get(name=name))
                             for name in slaves]
        slaves = slaves or repo.slaves

        if not named_tree:
            rev = yield from repo.get_latest_revision_for_branch(branch)
            named_tree = rev.commit
        else:
            rev = RepositoryRevision.objects.get(repository=repo,
                                                 branch=branch,
                                                 commit=named_tree)

        if not builder_name:
            builders = yield from self._get_builders(slaves, rev)
        else:
            blist = [(yield from Builder.get(name=builder_name))]
            builders = {}
            for slave in slaves:
                builders.update({slave: blist})

        builds_count = 0

        for slave in slaves:
            for builder in builders[slave]:
                builds_count += 1
                yield from repo.add_build(builder=builder, branch=branch,
                                          slave=slave,
                                          named_tree=named_tree)

        return {'repo-start-build': '{} builds added'.format(builds_count)}

    @asyncio.coroutine
    def slave_add(self, slave_name, slave_host, slave_port):
        """ Adds a new slave to toxicbuild. """

        slave = yield from Slave.create(name=slave_name, host=slave_host,
                                        port=slave_port)

        slave_dict = json.loads(slave.to_json())
        return {'slave-add': slave_dict}

    @asyncio.coroutine
    def slave_remove(self, slave_name):
        """ Removes a slave from toxicbuild. """

        slave = yield from Slave.get(name=slave_name)

        yield from to_asyncio_future(slave.delete())

        return {'slave-remove': 'ok'}

    @asyncio.coroutine
    def slave_list(self):
        """ Lists all slaves. """

        slaves = yield from to_asyncio_future(
            Slave.objects.all().to_list())
        slave_list = []

        for slave in slaves:
            slave_list.append(json.loads(slave.to_json()))

        return {'slave-list': slave_list}

    @asyncio.coroutine
    def builder_list(self, repo_name=None):
        """ Lists all builders.

        If ``repo_name``, only builders from this repository will be listed.
        """

        builders = Builder.objects
        if repo_name:
            repository = yield from Repository.get(name=repo_name)
            builders = builders.filter(repository=repository)

        builders = yield from to_asyncio_future(builders.to_list())

        builder_list = []

        for builder in builders:
            builder_dict = json.loads(builder.to_json())
            builder_dict['status'] = (yield from to_asyncio_future(
                Build.objects.filter(builder=builder).
                order_by('-started')[0])).status

            builder_list.append(builder_dict)

        return {'builder-list': builder_list}

    @asyncio.coroutine
    def builder_show(self, repo_name, builder_name):
        """ Returns information about one specific builder. """

        kwargs = {'name': builder_name}
        repo = yield from Repository.get(name=repo_name)
        kwargs.update({'repository': repo})

        builder = yield from Builder.get(**kwargs)
        builder_dict = json.loads(builder.to_json())

        build_list = []
        builds = yield from to_asyncio_future(
            Build.objects.filter(builder=builder).to_list())

        for build in builds:
            build_dict = json.loads(build.to_json())
            build_list.append(build_dict)

        builder_dict.update({'builds': build_list})
        return {'builder-show': builder_dict}

    def list_funcs(self):
        """ Lists the functions available for user interfaces. """

        funcs = self._get_action_methods()

        funcs = {n.replace('_', '-'): self._get_method_signature(m)
                 for n, m in funcs.items()}

        return {'list-funcs': funcs}

    def _get_action_methods(self):
        """ Returns the methods that are avaliable as actions for users. """
        forbiden = ['handle', 'protocol', 'log']

        func_names = [n for n in dir(self) if not n.startswith('_')
                      and n not in forbiden and callable(getattr(self, n))]

        funcs = {n: getattr(self, n) for n in func_names}
        return funcs

    @asyncio.coroutine
    def _get_builders(self, slaves, revision):

        # slave: [builders]
        builders = {}
        for slave in slaves:
            builders[slave] = (yield from slave.list_builders(revision))

        return builders

    def log(self, msg):
        msg = '[{}] {}'.format(type(self).__name__, msg)
        log(msg)


class UIStreamHandler:

    """ Handler that keeps the connection open and messages when
    builds and steps are stated or finished.
    """

    def __init__(self, protocol):
        self.protocol = protocol

    def __getattr__(self, attrname):
        _signals = ['step_started', 'step_finished',
                    'build_started', 'build_finished']

        if attrname in _signals:
            def wrapper(*args, **kw):
                return self.send_info(attrname, **kw)

            return wrapper

        raise AttributeError

    def _connect2signals(self):

        step_started.connect(self.step_started, weak=False)
        step_finished.connect(self.step_finished, weak=False)
        build_started.connect(self.build_started, weak=False)
        build_finished.connect(self.build_finished, weak=False)

    @asyncio.coroutine
    def handle(self):
        self._connect2signals()
        yield from self.protocol.send_response(code=0, body={'stream': 'ok'})

    @asyncio.coroutine
    def send_info(self, info_type, build=None, step=None):
        builder = yield from to_asyncio_future(build.builder)
        repo = yield from to_asyncio_future(build.repository)
        slave = yield from to_asyncio_future(build.slave)

        build = json.loads(build.to_json())
        builder = json.loads(builder.to_json())
        slave = json.loads(slave.to_json())
        repo = json.loads(repo.to_json())

        build['builder'] = builder
        build['slave'] = slave
        build['repository'] = repo

        if step:
            step = json.loads(step.to_json())
            step['build'] = build
            info = step
        else:
            info = build

        final_info = {'type': info_type}
        final_info.update(info)

        f = asyncio.async(self.protocol.send_response(code=0, body=final_info))
        return f


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
