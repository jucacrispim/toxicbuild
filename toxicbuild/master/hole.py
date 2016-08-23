# -*- coding: utf-8 -*-

# Copyright 2015, 2016 Juca Crispim <juca@poraodojuca.net>

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
# In fact, boring module!

import asyncio
import inspect
import json
import traceback
from toxicbuild.core import BaseToxicProtocol
from toxicbuild.core.utils import LoggerMixin
from toxicbuild.master import (Slave, Repository, Builder,
                               BuildSet, RepositoryRevision)
from toxicbuild.master.exceptions import UIFunctionNotFound
from toxicbuild.master.signals import (step_started, step_finished,
                                       build_started, build_finished)


class UIHole(BaseToxicProtocol, LoggerMixin):

    @asyncio.coroutine
    def client_connected(self):
        data = self.data.get('body') or {}
        if self.action == 'stream':
            handler = UIStreamHandler(self)
        else:
            handler = HoleHandler(data, self.action, self)

        try:
            yield from handler.handle()
            status = 0
        except Exception:
            msg = traceback.format_exc()
            status = 1
            yield from self.send_response(code=1, body={'error': msg})
            self.close_connection()

        return status


class HoleHandler:

    """ Handles the incomming connections for the UIHole. It has the following
    methods available to the clients:

    * `repo-add`
    * `repo-get`
    * `repo-list`
    * `repo-remove`
    * `repo-update`
    * `repo-add-slave`
    * `repo-remove-slave`
    * `repo-start-build`
    * `slave-add`
    * `slave-get`
    * `slave-list`
    * `slave-remove`
    * `slave-update`
    * `buildset-list`
    * `builder-show`
    * `list-funcs`
    """

    def __init__(self, data, action, protocol):
        self.data = data
        self.action = action
        self.protocol = protocol

    @asyncio.coroutine
    def handle(self):

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

        repo_name = repo_name.strip()
        repo_url = repo_url.strip()
        slaves_info = slaves or []
        slaves = []
        for name in slaves_info:
            slave = yield from Slave.get(name=name)
            slaves.append(slave)

        repo = yield from Repository.create(repo_name, repo_url,
                                            update_seconds, vcs_type, slaves)
        repo_dict = yield from self._get_repo_dict(repo)
        return {'repo-add': repo_dict}

    @asyncio.coroutine
    def repo_get(self, repo_name=None, repo_url=None):
        """Shows information about one specific repository.
        One of ``repo_name`` or ``repo_url`` is required. """

        if not (repo_name or repo_url):
            raise TypeError("repo_name or repo_url required")

        kw = {}
        if repo_name:
            kw['name'] = repo_name

        if repo_url:
            kw['url'] = repo_url

        repo = yield from Repository.get(**kw)
        repo_dict = yield from self._get_repo_dict(repo)
        return {'repo-get': repo_dict}

    @asyncio.coroutine
    def repo_remove(self, repo_name):
        """ Removes a repository from toxicubild """

        repo = yield from Repository.get(name=repo_name)
        yield from repo.remove()
        return {'repo-remove': 'ok'}

    @asyncio.coroutine
    def repo_list(self):
        """ Lists all repositories. """

        repos = yield from Repository.objects.all().to_list()
        repo_list = []
        for repo in repos:

            repo_dict = yield from self._get_repo_dict(repo)
            repo_list.append(repo_dict)

        return {'repo-list': repo_list}

    @asyncio.coroutine
    def repo_update(self, repo_name, **kwargs):
        """ Updates repository information. """

        repo = yield from Repository.get(name=repo_name)
        [setattr(repo, k, v) for k, v in kwargs.items()]

        yield from repo.save()
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

        # Mutable stuff on method declaration. Sin!!! Take that, PyLint!

        repo = yield from Repository.get(name=repo_name)

        slaves = yield from [(yield from Slave.get(name=name))
                             for name in slaves]
        if not slaves:
            slaves = yield from repo.slaves

        if not named_tree:
            rev = yield from repo.get_latest_revision_for_branch(branch)
            named_tree = rev.commit
        else:
            rev = yield from RepositoryRevision.get(repository=repo,
                                                    branch=branch,
                                                    commit=named_tree)

        if not builder_name:
            builders = yield from self._get_builders(slaves, rev)
        else:
            blist = [(yield from Builder.get(name=builder_name,
                                             repository=repo))]
            builders = {}
            for slave in slaves:
                builders.update({slave: blist})

        builds_count = 0

        buildset = yield from BuildSet.create(repository=repo, revision=rev,
                                              save=False)
        for slave in slaves:
            yield from repo.add_builds_for_slave(buildset, slave,
                                                 builders[slave])

        return {'repo-start-build': '{} builds added'.format(builds_count)}

    @asyncio.coroutine
    def slave_add(self, slave_name, slave_host, slave_port):
        """ Adds a new slave to toxicbuild. """

        slave = yield from Slave.create(name=slave_name, host=slave_host,
                                        port=slave_port)

        slave_dict = self._get_slave_dict(slave)
        return {'slave-add': slave_dict}

    @asyncio.coroutine
    def slave_get(self, slave_name):
        """Returns information about on specific slave"""

        slave = yield from Slave.get(name=slave_name)
        slave_dict = self._get_slave_dict(slave)
        return {'slave-get': slave_dict}

    @asyncio.coroutine
    def slave_remove(self, slave_name):
        """ Removes a slave from toxicbuild. """

        slave = yield from Slave.get(name=slave_name)

        yield from slave.delete()

        return {'slave-remove': 'ok'}

    @asyncio.coroutine
    def slave_list(self):
        """ Lists all slaves. """

        slaves = yield from Slave.objects.all().to_list()
        slave_list = []

        for slave in slaves:
            slave_dict = self._get_slave_dict(slave)
            slave_list.append(slave_dict)

        return {'slave-list': slave_list}

    @asyncio.coroutine
    def slave_update(self, slave_name, **kwargs):
        """Updates infomation of a slave."""

        slave = yield from Slave.get(name=slave_name)
        [setattr(slave, k, v) for k, v in kwargs.items()]

        yield from slave.save()
        return {'slave-update': 'ok'}

    @asyncio.coroutine
    def buildset_list(self, repo_name=None, skip=0, offset=None):
        """ Lists all buildsets.

        If ``repo_name``, only builders from this repository will be listed.
        :param repo_name: Repository's name.
        :param skip: skip for buildset list.
        :param offset: offset for buildset list.
        """

        buildsets = BuildSet.objects
        if repo_name:
            repository = yield from Repository.get(name=repo_name)
            buildsets = buildsets.filter(repository=repository)

        buildsets = buildsets.order_by('-created')
        count = yield from buildsets.count()

        stop = count if not offset else skip + offset

        buildsets = buildsets[skip:stop]
        buildsets = yield from buildsets.to_list()
        buildset_list = []
        for b in buildsets:
            bdict = yield from b.to_dict(id_as_str=True)
            buildset_list.append(bdict)

        return {'buildset-list': buildset_list}

    @asyncio.coroutine
    def builder_list(self, **kwargs):
        """List builders.

        :param kwargs: Arguments to filter the list."""

        queryset = Builder.objects.filter(**kwargs)
        builders = yield from queryset.to_list()
        blist = []

        for b in builders:
            blist.append((yield from b.to_dict(id_as_str=True)))

        return {'builder-list': blist}

    @asyncio.coroutine
    def builder_show(self, repo_name, builder_name, skip=0, offset=None):
        """ Returns information about one specific builder.

        :param repo_name: The builder's repository name.
        :param builder_name. The bulider's name.
        :param skip: How many elements we should skip in the result.
        :param offset: How many results we should return."""

        kwargs = {'name': builder_name}
        repo = yield from Repository.get(name=repo_name)
        kwargs.update({'repository': repo})

        builder = yield from Builder.get(**kwargs)
        buildsets = BuildSet.objects(builds__builder=builder)
        count = yield from buildsets.count()
        stop = count if not offset else skip + offset
        buildsets = buildsets[skip:stop]
        buildsets = yield from buildsets.to_list()
        buildsets_list = []
        for buildset in buildsets:
            bdict = yield from buildset.to_dict()
            bdict['builds'] = []
            for b in (yield from buildset.get_builds_for(builder=builder)):
                build_dict = yield from b.to_dict()
                bdict['builds'].append(build_dict)

            buildsets_list.append(bdict)

        builder_dict = yield from builder.to_dict()
        builder_dict['buildsets'] = buildsets_list
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

        func_names = [n for n in dir(self) if not n.startswith('_') and
                      n not in forbiden and callable(getattr(self, n))]

        funcs = {n: getattr(self, n) for n in func_names}
        return funcs

    @asyncio.coroutine
    def _get_repo_dict(self, repo):
        """Returns a dictionary for a given repository"""
        repo_dict = json.loads(repo.to_json())
        repo_dict['id'] = str(repo.id)
        repo_dict['status'] = yield from repo.get_status()
        slaves = yield from repo.slaves
        repo_dict['slaves'] = [self._get_slave_dict(s) for s in slaves]
        return repo_dict

    def _get_slave_dict(self, slave):
        slave_dict = json.loads(slave.to_json())
        slave_dict['id'] = str(slave.id)
        return slave_dict

    @asyncio.coroutine
    def _get_builders(self, slaves, revision):
        repo = yield from revision.repository
        builders = {}
        for slave in slaves:
            builders[slave] = yield from repo.build_manager.get_builders(
                slave, revision)

        return builders


class UIStreamHandler:

    """ Handler that keeps the connection open and messages when
    builds and steps are stated or finished.
    """

    def __init__(self, protocol):
        self.protocol = protocol

        def connection_lost_cb(exc):  # pragma no cover
            self._disconnectfromsignals()

        self.protocol.connection_lost_cb = connection_lost_cb

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

    def _disconnectfromsignals(self):
        step_started.disconnect(self.step_started)
        step_finished.disconnect(self.step_finished)
        build_started.disconnect(self.build_started)
        build_finished.disconnect(self.build_finished)

    @asyncio.coroutine
    def handle(self):
        self._connect2signals()
        yield from self.protocol.send_response(code=0, body={'stream': 'ok'})

    @asyncio.coroutine
    def send_info(self, info_type, build=None, step=None):
        repo = yield from build.repository
        slave = yield from build.slave

        build = yield from build.to_dict()
        slave = json.loads(slave.to_json())
        repo = json.loads(repo.to_json())

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
