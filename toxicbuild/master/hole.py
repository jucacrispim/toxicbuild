# -*- coding: utf-8 -*-

# Copyright 2015-2017 Juca Crispim <juca@poraodojuca.net>

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
from asyncio import ensure_future
import inspect
import json
import traceback
from toxicbuild.core import BaseToxicProtocol
from toxicbuild.core.utils import LoggerMixin
from toxicbuild.master import settings
from toxicbuild.master.build import BuildSet, Builder
from toxicbuild.master.repository import Repository, RepositoryRevision
from toxicbuild.master.exceptions import (UIFunctionNotFound,
                                          OwnerDoesNotExist, NotEnoughPerms)
from toxicbuild.master.plugins import MasterPlugin
from toxicbuild.master.slave import Slave
from toxicbuild.master.signals import (step_started, step_finished,
                                       build_started, build_finished,
                                       repo_status_changed, build_added,
                                       step_output_arrived, repo_added)
from toxicbuild.master.users import User, Organization


class UIHole(BaseToxicProtocol, LoggerMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None

    salt = settings.BCRYPT_SALT
    encrypted_token = settings.ACCESS_TOKEN

    async def client_connected(self):

        data = self.data.get('body') or {}

        if self.action != 'user-authenticate':
            # when we are authenticating we don't need (and we can't have)
            # a requester user, so we only try to get it when we are not
            # authenticating.
            try:
                user_id = self.data.get('user_id', '')
                if not user_id:
                    raise User.DoesNotExist
                self.user = await User.objects.get(id=user_id)
            except User.DoesNotExist:
                msg = 'User {} does not exist'.format(user_id)
                self.log(msg, level='warning')
                status = 2
                await self.send_response(code=status, body={'error': msg})
                self.close_connection()
                return status

        if self.action == 'stream':
            handler = UIStreamHandler(self)
        else:
            handler = HoleHandler(data, self.action, self)

        try:
            await handler.handle()
            status = 0

        except NotEnoughPerms:
            msg = 'User {} does not have enough permissions.'.format(
                str(self.user.id))
            self.log(msg, level='warning')
            status = 3
            await self.send_response(code=status, body={'error': msg})
        except Exception:
            msg = traceback.format_exc()
            status = 1
            await self.send_response(code=1, body={'error': msg})
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
    * `repo-add-branch`
    * `repo-remove-branch`
    * `repo-enable-plugin`
    * `repo-disable-plugin`
    * `repo-start-build`
    * `slave-add`
    * `slave-get`
    * `slave-list`
    * `slave-remove`
    * `slave-update`
    * `plugins-list`
    * `plugin-get`
    * `buildset-list`
    * `builder-show`
    * `list-funcs`
    * `user-add`
    * `user-remove`
    * `user-authenticate`
    """

    def __init__(self, data, action, protocol):
        self.data = data
        self.action = action
        self.protocol = protocol

    async def handle(self):

        attrname = self.action.replace('-', '_')
        if attrname not in self._get_action_methods():
            raise UIFunctionNotFound(self.action)

        func = getattr(self, attrname)
        r = func(**self.data)
        if asyncio.coroutines.iscoroutine(r):
            r = await r

        await self.protocol.send_response(code=0, body=r)
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

    def _user_is_allowed(self, what):
        if self.protocol.user.is_superuser or \
           what in self.protocol.user.allowed_actions:
            return True
        return False

    async def user_add(self, email, password, allowed_actions, username=None):
        """Adds a new user.

        :param email: User email.
        :param password: User password
        :param allowed_actions: What the user can do.
        :param username: Username for the user."""

        if not self._user_is_allowed('add_user'):
            raise NotEnoughPerms

        user = User(email=email, allowed_actions=allowed_actions,
                    username=username)
        user.set_password(password)
        await user.save()
        return {'user-add': {'id': str(user.id), 'username': user.username,
                             'email': user.email}}

    async def user_remove(self, **kwargs):
        """Removes a user from the system."""

        if not self._user_is_allowed('remove_user'):
            raise NotEnoughPerms

        user = await User.objects.get(**kwargs)
        await user.delete()
        return {'user-remove': 'ok'}

    async def user_authenticate(self, username_or_email, password):
        """Authenticates an user. Returns user.to_dict() is
        authenticated. Raises ``InvalidCredentials`` if a user with
        this credentials does not exist.

        :param username_or_email: Username or email to use to authenticate.
        :param password: Not encrypted password."""

        user = await User.authenticate(username_or_email, password)
        return {'user-authenticate': user.to_dict()}

    async def repo_add(self, repo_name, repo_url, owner_id,
                       update_seconds, vcs_type, slaves=None,
                       parallel_builds=None):
        """ Adds a new repository and first_run() it.

        :param repo_name: Repository name
        :param repo_url: Repository vcs url
        :param owner_id: Id of the repository's owner.
        :param update_seconds: Time to poll for changes
        :param vcs_type: Type of vcs being used.
        :param slaves: A list of slave names.
        :params parallel_builds: How many parallel builds this repository
          executes. If None, there is no limit."""

        if not self._user_is_allowed('add_repo'):
            raise NotEnoughPerms

        repo_name = repo_name.strip()
        repo_url = repo_url.strip()
        slaves_info = slaves or []
        slaves = []
        for name in slaves_info:
            slave = await Slave.get(name=name)
            slaves.append(slave)

        kw = {}
        if parallel_builds:
            kw['parallel_builds'] = parallel_builds

        owner = await self._get_owner(owner_id)

        repo = await Repository.create(
            repo_name, repo_url, owner, update_seconds, vcs_type,
            slaves, **kw)
        repo_dict = await self._get_repo_dict(repo)
        return {'repo-add': repo_dict}

    async def _get_owner(self, owner_id):
        owner_types = [User, Organization]
        for owner_type in owner_types:
            try:
                owner = await owner_type.objects.get(id=owner_id)
                return owner
            except owner_type.DoesNotExist:
                pass

        msg = 'The owner {} does not exist'.format(owner_id)
        raise OwnerDoesNotExist(msg)

    async def repo_get(self, repo_name=None, repo_url=None):
        """Shows information about one specific repository. One of
        ``repo_name`` or ``repo_url`` is required.

        :param repo_name: Repository name,
        :param repo_url: Repository vcs url."""

        if not (repo_name or repo_url):
            raise TypeError("repo_name or repo_url required")

        kw = {}
        if repo_name:
            kw['name'] = repo_name

        if repo_url:
            kw['url'] = repo_url

        repo = await Repository.get_for_user(self.protocol.user, **kw)
        repo_dict = await self._get_repo_dict(repo)
        return {'repo-get': repo_dict}

    async def repo_remove(self, repo_name):
        """ Removes a repository from toxicubild.

        :param repo_name: Repository name."""

        repo = await Repository.get_for_user(self.protocol.user,
                                             name=repo_name)
        await repo.remove()
        return {'repo-remove': 'ok'}

    async def repo_list(self):
        """ Lists all repositories. """

        repos = Repository.list_for_user(self.protocol.user)
        repo_list = []
        async for repo in repos:

            repo_dict = await self._get_repo_dict(repo)
            repo_list.append(repo_dict)

        return {'repo-list': repo_list}

    async def repo_update(self, repo_name, **kwargs):
        """ Updates repository information.

        :param repo_name: Repository name
        :param kwargs: kwargs to update the repository"""

        if kwargs.get('slaves'):
            qs = Slave.objects(name__in=kwargs.get('slaves'))
            slaves_instances = await qs.to_list()
            kwargs['slaves'] = slaves_instances

        repo = await Repository.get_for_user(self.protocol.user,
                                             name=repo_name)
        [setattr(repo, k, v) for k, v in kwargs.items()]

        await repo.save()
        return {'repo-update': 'ok'}

    async def repo_add_slave(self, repo_name, slave_name):
        """ Adds a slave to a repository.

        :param repo_name: Repository name.
        :param slave_name: Slave name."""

        repo = await Repository.get_for_user(self.protocol.user,
                                             name=repo_name)
        slave = await Slave.get_for_user(self.protocol.user,
                                         name=slave_name)
        await repo.add_slave(slave)
        return {'repo-add-slave': 'ok'}

    async def repo_remove_slave(self, repo_name, slave_name):
        """ Removes a slave from toxicbuild. """

        repo = await Repository.get_for_user(self.protocol.user,
                                             name=repo_name)

        slave = await Slave.get_for_user(self.protocol.user,
                                         name=slave_name)
        await repo.remove_slave(slave)
        return {'repo-remove-slave': 'ok'}

    async def repo_add_branch(self, repo_name, branch_name,
                              notify_only_latest=False):
        """Adds a branch to the list of branches of the repository.

        :param repo_name: Reporitory name
        :param branch_name: Branch's name
        :notify_only_latest: If True only the latest commit in the
          branch will trigger a build."""
        repo = await Repository.get_for_user(self.protocol.user,
                                             name=repo_name)
        await repo.add_or_update_branch(branch_name, notify_only_latest)
        return {'repo-add-branch': 'ok'}

    async def repo_remove_branch(self, repo_name, branch_name):
        """Removes a branch from the list of branches of a repository.
        :param repo_name: Repository name
        :param branch_name: Branch's name."""

        repo = await Repository.get_for_user(self.protocol.user,
                                             name=repo_name)
        await repo.remove_branch(branch_name)
        return {'repo-remove-branch': 'ok'}

    async def repo_enable_plugin(self, repo_name, plugin_name, **kwargs):
        """Enables a plugin to a repository.

        :param repo_name: Repository name.
        :param plugin_name: Plugin name
        :param kwargs: kwargs passed to the plugin."""

        repo = await Repository.get_for_user(self.protocol.user,
                                             name=repo_name)
        await repo.enable_plugin(plugin_name, **kwargs)
        return {'repo-enable-plugin': 'ok'}

    async def repo_disable_plugin(self, repo_name, **kwargs):
        """Disables a plugin from a repository.

        :param repo_name: Repository name.
        :param kwargs: kwargs passed to the plugin"""

        repo = await Repository.get_for_user(self.protocol.user,
                                             name=repo_name)
        await repo.disable_plugin(**kwargs)
        return {'repo-disable-plugin': 'ok'}

    async def repo_start_build(self, repo_name, branch, builder_name=None,
                               named_tree=None, slaves=[]):
        """ Starts a(some) build(s) in a given repository. """
        # Mutable stuff on method declaration. Sin!!! Take that, PyLint!

        repo = await Repository.get_for_user(self.protocol.user,
                                             name=repo_name)

        slave_instances = []
        for sname in slaves:
            slave = await Slave.get(name=sname)
            slave_instances.append(slave)

        slaves = slave_instances

        if not slaves:
            slaves = await repo.slaves

        if not named_tree:
            rev = await repo.get_latest_revision_for_branch(branch)
            named_tree = rev.commit
        else:
            rev = await RepositoryRevision.get(repository=repo,
                                               branch=branch,
                                               commit=named_tree)

        if not builder_name:
            builders = await self._get_builders(slaves, rev)
        else:
            blist = [(await Builder.get(name=builder_name,
                                        repository=repo))]
            builders = {}
            for slave in slaves:
                builders.update({slave: blist})

        builds_count = 0

        buildset = await BuildSet.create(repository=repo, revision=rev,
                                         save=False)
        for slave in slaves:
            await repo.add_builds_for_slave(buildset, slave,
                                            builders[slave])

        return {'repo-start-build': '{} builds added'.format(builds_count)}

    async def slave_add(self, slave_name, slave_host, slave_port, slave_token,
                        owner_id):
        """ Adds a new slave to toxicbuild.

        :param slave_name: A name for the slave,
        :param slave_host: Host where the slave is.
        :param slave_port: Port to connect to the slave
        :param slave_token: Auth token for the slave.
        :param owner_id: Slave's owner id."""

        if not self._user_is_allowed('add_slave'):
            raise NotEnoughPerms

        owner = await self._get_owner(owner_id)
        slave = await Slave.create(name=slave_name, host=slave_host,
                                   port=slave_port, token=slave_token,
                                   owner=owner)

        slave_dict = self._get_slave_dict(slave)
        return {'slave-add': slave_dict}

    async def slave_get(self, slave_name):
        """Returns information about one specific slave"""

        slave = await Slave.get_for_user(self.protocol.user,
                                         name=slave_name)
        slave_dict = self._get_slave_dict(slave)
        return {'slave-get': slave_dict}

    async def slave_remove(self, slave_name):
        """ Removes a slave from toxicbuild. """

        slave = await Slave.get_for_user(self.protocol.user,
                                         name=slave_name)

        await slave.delete()

        return {'slave-remove': 'ok'}

    async def slave_list(self):
        """ Lists all slaves. """

        slaves = Slave.list_for_user(self.protocol.user)
        slave_list = []

        async for slave in slaves:
            slave_dict = self._get_slave_dict(slave)
            slave_list.append(slave_dict)

        return {'slave-list': slave_list}

    async def slave_update(self, slave_name, **kwargs):
        """Updates infomation of a slave."""

        slave = await Slave.get_for_user(self.protocol.user, name=slave_name)
        [setattr(slave, k, v) for k, v in kwargs.items()]

        await slave.save()
        return {'slave-update': 'ok'}

    async def buildset_list(self, repo_name=None, skip=0, offset=None):
        """ Lists all buildsets.

        If ``repo_name``, only builders from this repository will be listed.
        :param repo_name: Repository's name.
        :param skip: skip for buildset list.
        :param offset: offset for buildset list.
        """

        buildsets = BuildSet.objects.no_dereference()
        if repo_name:
            repository = await Repository.get_for_user(
                self.protocol.user, name=repo_name)
            buildsets = buildsets.filter(repository=repository)

        buildsets = buildsets.order_by('-created')
        count = await buildsets.count()

        stop = count if not offset else skip + offset

        buildsets = buildsets[skip:stop]
        buildset_list = []
        buildsets = await buildsets.to_list()
        for b in buildsets:
            bdict = b.to_dict(id_as_str=True)
            buildset_list.append(bdict)

        return {'buildset-list': buildset_list}

    async def builder_list(self, **kwargs):
        """List builders.

        :param kwargs: Arguments to filter the list."""

        queryset = Builder.objects.filter(**kwargs)
        builders = await queryset.to_list()
        blist = []

        for b in builders:
            blist.append((await b.to_dict(id_as_str=True)))

        return {'builder-list': blist}

    def plugins_list(self):
        """Lists all plugins available to the master."""

        plugins = MasterPlugin.list_plugins()
        plugins_schemas = [p.get_schema(to_serialize=True) for p in plugins]
        return {'plugins-list': plugins_schemas}

    def plugin_get(self, **kwargs):
        """Returns a specific plugin."""

        name = kwargs.get('name')
        plugin = MasterPlugin.get_plugin(name=name)
        return {'plugin-get': plugin.get_schema(to_serialize=True)}

    async def builder_show(self, repo_name, builder_name, skip=0, offset=None):
        """ Returns information about one specific builder.

        :param repo_name: The builder's repository name.
        :param builder_name: The bulider's name.
        :param skip: How many elements we should skip in the result.
        :param offset: How many results we should return.
        """

        kwargs = {'name': builder_name}
        repo = await Repository.get_for_user(self.protocol.user,
                                             name=repo_name)
        kwargs.update({'repository': repo})

        builder = await Builder.get(**kwargs)
        buildsets = BuildSet.objects(builds__builder=builder)
        count = await buildsets.count()
        stop = count if not offset else skip + offset
        buildsets = buildsets[skip:stop]
        buildsets = await buildsets.to_list()
        buildsets_list = []
        for buildset in buildsets:
            bdict = buildset.to_dict()
            bdict['builds'] = []
            for b in (await buildset.get_builds_for(builder=builder)):
                build_dict = b.to_dict()
                bdict['builds'].append(build_dict)

            buildsets_list.append(bdict)

        builder_dict = await builder.to_dict()
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

    async def _get_repo_dict(self, repo):
        """Returns a dictionary for a given repository"""

        repo_dict = json.loads(repo.to_json())
        repo_dict['id'] = str(repo.id)
        repo_dict['status'] = await repo.get_status()
        slaves = await repo.slaves
        repo_dict['slaves'] = [self._get_slave_dict(s) for s in slaves]
        repo_dict['parallel_builds'] = repo.parallel_builds or ''
        for p in repo_dict['plugins']:
            p['name'] = p['_name']

        return repo_dict

    def _get_slave_dict(self, slave):
        slave_dict = json.loads(slave.to_json())
        slave_dict['id'] = str(slave.id)
        return slave_dict

    async def _get_builders(self, slaves, revision):
        repo = await revision.repository
        builders = {}
        for slave in slaves:
            builders[slave] = await repo.build_manager.get_builders(
                slave, revision)

        return builders


class UIStreamHandler(LoggerMixin):

    """ Handler that keeps the connection open and messages when
    builds and steps are stated or finished.
    """

    def __init__(self, protocol):
        self.protocol = protocol

        def connection_lost_cb(exc):  # pragma no cover
            self._disconnectfromsignals()

        self.protocol.connection_lost_cb = connection_lost_cb

    async def step_started(self, sender, **kw):
        await self.send_info('step_started', **kw)

    async def step_finished(self, sender, **kw):
        await self.send_info('step_finished', **kw)

    async def build_started(self, sender, **kw):
        await self.send_info('build_started', **kw)

    async def build_finished(self, sender, **kw):
        await self.send_info('build_finished', **kw)

    async def build_added(self, sender, **kw):
        await self.send_info('build_added', **kw)

    async def _connect2signals(self):
        repos = Repository.list_for_user(self.protocol.user)
        async for repo in repos:
            self._connect_repo(repo)
        repo_added.connect(self.check_repo_added)

    def _connect_repo(self, repo):
        step_started.connect(self.step_started, sender=str(repo.id))
        step_finished.connect(self.step_finished, sender=str(repo.id))
        build_started.connect(self.build_started, sender=str(repo.id))
        build_finished.connect(self.build_finished, sender=str(repo.id))
        repo_status_changed.connect(self.send_repo_status_info,
                                    sender=str(repo.id))
        build_added.connect(self.build_added, sender=str(repo.id))
        step_output_arrived.connect(self.send_step_output_info,
                                    sender=str(repo.id))

    async def check_repo_added(self, sender, **kw):
        try:
            repo = await Repository.get_for_user(self.protocol.user,
                                                 id=sender)
        except NotEnoughPerms:
            return

        self._connect_repo(repo)

    def _disconnectfromsignals(self):
        step_output_arrived.disconnect(self.send_step_output_info)
        step_started.disconnect(self.step_started)
        step_finished.disconnect(self.step_finished)
        build_started.disconnect(self.build_started)
        build_finished.disconnect(self.build_finished)
        repo_status_changed.disconnect(self.send_repo_status_info)
        build_added.disconnect(self.build_added)
        repo_added.disconnect(self.check_repo_added)

    async def handle(self):
        await self._connect2signals()
        await self.protocol.send_response(code=0, body={'stream': 'ok'})

    async def send_info(self, info_type, build=None, step=None):
        repo = await build.repository
        slave = await build.slave

        build_dict = build.to_dict(id_as_str=True)
        slave = slave.to_dict(id_as_str=True)
        repo = await repo.to_dict(id_as_str=True)
        buildset = await build.get_buildset()

        build_dict['slave'] = slave
        build_dict['repository'] = repo
        build_dict['buildset'] = buildset.to_dict(id_as_str=True)

        if step:
            step = step.to_dict()
            step['build'] = build_dict
            info = step
        else:
            info = build_dict

        final_info = {'event_type': info_type}
        final_info.update(info)

        f = ensure_future(self.send_response(code=0, body=final_info))

        return f

    async def send_repo_status_info(self, repo_id, old_status, new_status):
        """Called by the signal ``repo_status_changed``

        :param repo_id: Id of the repository that had its status changed.
        :param old_status: The old status of the repository
        :param new_status: The new status of the repostiory."""

        repo = await Repository.get(id=repo_id)
        rdict = await repo.to_dict(id_as_str=True)
        rdict['status'] = new_status
        rdict['old_status'] = old_status
        rdict['event_type'] = 'repo_status_changed'
        f = ensure_future(self.send_response(code=0, body=rdict))
        return f

    def send_step_output_info(self, repo, step_info):
        """Called by the signal ``step_output_arrived``.

        :param repo: The repository that is building something.
        :param step_info: The information about the step output."""

        step_info['event_type'] = 'step_output_info'
        f = ensure_future(self.send_response(code=0, body=step_info))
        return f

    async def send_response(self, code, body):
        try:
            await self.protocol.send_response(code=code, body=body)
        except ConnectionResetError:
            self.protocol._transport.close()
            self._disconnectfromsignals()


class HoleServer:

    def __init__(self, addr='127.0.0.1', port=6666):
        self.protocol = UIHole
        self.loop = asyncio.get_event_loop()
        self.addr = addr
        self.port = port

    def serve(self):

        coro = self.loop.create_server(
            self.get_protocol_instance, self.addr,  self.port)

        ensure_future(coro)

    def get_protocol_instance(self):
        return self.protocol(self.loop)
