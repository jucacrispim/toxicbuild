# -*- coding: utf-8 -*-

# Copyright 2015-2018 Juca Crispim <juca@poraodojuca.net>

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
from datetime import timedelta
import inspect
import json
import signal
import ssl
import traceback
from bson.objectid import ObjectId
from toxicbuild.core import BaseToxicProtocol
from toxicbuild.core.utils import (LoggerMixin, datetime2string,
                                   format_timedelta)
from toxicbuild.master import settings
from toxicbuild.master.build import BuildSet, Builder
from toxicbuild.master.consumers import RepositoryMessageConsumer
from toxicbuild.master.repository import Repository
from toxicbuild.master.exceptions import (UIFunctionNotFound,
                                          OwnerDoesNotExist, NotEnoughPerms)
from toxicbuild.master.exchanges import ui_notifications
from toxicbuild.master.plugins import MasterPlugin
from toxicbuild.master.slave import Slave
from toxicbuild.master.signals import (step_started, step_finished,
                                       build_started, build_finished,
                                       build_added, build_cancelled,
                                       step_output_arrived)
from toxicbuild.master.users import User, Organization


class UIHole(BaseToxicProtocol, LoggerMixin):

    encrypted_token = settings.ACCESS_TOKEN
    _shutting_down = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None

    @classmethod
    def set_shutting_down(cls):
        cls._shutting_down = True

    async def client_connected(self):

        if type(self)._shutting_down:
            self.log('Hole is shutting down. Rejecting connection',
                     level='warning')
            self.close_connection()
            return None

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
    * `repo-cancel-build`
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
            name=repo_name, url=repo_url, owner=owner,
            update_seconds=update_seconds, vcs_type=vcs_type,
            slaves=slaves, **kw)
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

    def _get_kw_for_name_or_id(self, repo_name_or_id):
        if ObjectId.is_valid(repo_name_or_id):
            kw = {'id': repo_name_or_id}
        else:
            kw = {'name': repo_name_or_id}

        return kw

    async def repo_get(self, repo_name_or_id=None, repo_url=None):
        """Shows information about one specific repository. One of
        ``repo_name`` or ``repo_url`` is required.

        :param repo_name_or_id: Repository name or ObjectId,
        :param repo_url: Repository vcs url."""

        if not (repo_name_or_id or repo_url):
            raise TypeError("repo_name or repo_url required")

        kw = {}
        if repo_name_or_id:
            kw = self._get_kw_for_name_or_id(repo_name_or_id)

        if repo_url:
            kw['url'] = repo_url

        repo = await Repository.get_for_user(self.protocol.user, **kw)
        repo_dict = await self._get_repo_dict(repo)
        return {'repo-get': repo_dict}

    async def repo_remove(self, repo_name_or_id):
        """ Removes a repository from toxicubild.

        :param repo_name_or_id: Repository name or id."""

        kw = self._get_kw_for_name_or_id(repo_name_or_id)
        repo = await Repository.get_for_user(self.protocol.user, **kw)
        await repo.remove()
        return {'repo-remove': 'ok'}

    async def repo_list(self):
        """ Lists all repositories. """

        repos = await Repository.list_for_user(self.protocol.user)
        repo_list = []
        async for repo in repos:

            repo_dict = await self._get_repo_dict(repo)
            repo_list.append(repo_dict)

        return {'repo-list': repo_list}

    async def repo_update(self, repo_name_or_id, **kwargs):
        """ Updates repository information.

        :param repo_name_or_id: Repository name or id
        :param kwargs: kwargs to update the repository"""

        if kwargs.get('slaves'):
            qs = Slave.objects(name__in=kwargs.get('slaves'))
            slaves_instances = await qs.to_list()
            kwargs['slaves'] = slaves_instances

        query_kw = self._get_kw_for_name_or_id(repo_name_or_id)
        repo = await Repository.get_for_user(self.protocol.user, **query_kw)

        for k, v in kwargs.items():
            setattr(repo, k, v)

        await repo.save()
        return {'repo-update': 'ok'}

    async def repo_add_slave(self, repo_name_or_id, slave_name_or_id):
        """ Adds a slave to a repository.

        :param repo_name_or_id: Repository name or id.
        :param slave_name_or_id: Slave name or id."""

        repo_kw = self._get_kw_for_name_or_id(repo_name_or_id)
        repo = await Repository.get_for_user(self.protocol.user, **repo_kw)
        slave_kw = self._get_kw_for_name_or_id(slave_name_or_id)
        slave = await Slave.get_for_user(self.protocol.user, **slave_kw)
        await repo.add_slave(slave)
        return {'repo-add-slave': 'ok'}

    async def repo_remove_slave(self, repo_name_or_id, slave_name_or_id):
        """ Removes a slave from a repository.

        :param repo_name_or_id: Repository name or id.
        :param slave_name_or_id: Slave name or id."""

        repo_kw = self._get_kw_for_name_or_id(repo_name_or_id)
        repo = await Repository.get_for_user(self.protocol.user, **repo_kw)
        slave_kw = self._get_kw_for_name_or_id(slave_name_or_id)
        slave = await Slave.get_for_user(self.protocol.user, **slave_kw)
        await repo.remove_slave(slave)
        return {'repo-remove-slave': 'ok'}

    async def repo_add_branch(self, repo_name_or_id, branch_name,
                              notify_only_latest=False):
        """Adds a branch to the list of branches of the repository.

        :param repo_name_or_id: Reporitory name or id.
        :param branch_name: Branch's name.
        :notify_only_latest: If True only the latest commit in the
          branch will trigger a build."""
        kw = self._get_kw_for_name_or_id(repo_name_or_id)
        repo = await Repository.get_for_user(self.protocol.user, **kw)
        await repo.add_or_update_branch(branch_name, notify_only_latest)
        return {'repo-add-branch': 'ok'}

    async def repo_remove_branch(self, repo_name_or_id, branch_name):
        """Removes a branch from the list of branches of a repository.
        :param repo_name_or_id: Repository name or id.
        :param branch_name: Branch's name."""

        kw = self._get_kw_for_name_or_id(repo_name_or_id)
        repo = await Repository.get_for_user(self.protocol.user, **kw)
        await repo.remove_branch(branch_name)
        return {'repo-remove-branch': 'ok'}

    async def repo_enable_plugin(self, repo_name_or_id, plugin_name, **kwargs):
        """Enables a plugin to a repository.

        :param repo_name_or_id: Repository name or id.
        :param plugin_name: Plugin name
        :param kwargs: kwargs passed to the plugin."""

        kw = self._get_kw_for_name_or_id(repo_name_or_id)
        repo = await Repository.get_for_user(self.protocol.user, **kw)
        await repo.enable_plugin(plugin_name, **kwargs)
        return {'repo-enable-plugin': 'ok'}

    async def repo_disable_plugin(self, repo_name_or_id, **kwargs):
        """Disables a plugin from a repository.

        :param repo_name_or_id: Repository name or id.
        :param kwargs: kwargs passed to the plugin"""

        kw = self._get_kw_for_name_or_id(repo_name_or_id)
        repo = await Repository.get_for_user(self.protocol.user, **kw)
        await repo.disable_plugin(**kwargs)
        return {'repo-disable-plugin': 'ok'}

    async def repo_start_build(self, repo_name_or_id, branch,
                               builder_name=None, named_tree=None,
                               slaves=None, builders_origin=None):
        """ Starts a(some) build(s) in a given repository. """
        slaves = slaves or []
        kw = self._get_kw_for_name_or_id(repo_name_or_id)
        repo = await Repository.get_for_user(self.protocol.user, **kw)

        slave_instances = []
        for sname in slaves:
            slave = await Slave.get(name=sname)
            slave_instances.append(slave)

        slaves = slave_instances

        await repo.start_build(branch, builder_name, named_tree, slaves=slaves,
                               builders_origin=builders_origin)
        return {'repo-start-build': 'builds added'}

    async def repo_cancel_build(self, repo_name_or_id, build_uuid):
        """Cancels  a build if possible.

        :param repo_name_or_id: The name or the id of the repository.
        :param buid_uuid: The uuid of the build to be cancelled."""

        kw = self._get_kw_for_name_or_id(repo_name_or_id)
        repo = await Repository.get_for_user(self.protocol.user, **kw)
        await repo.cancel_build(build_uuid)
        return {'repo-cancel-build': 'ok'}

    async def slave_add(self, slave_name, slave_host, slave_port, slave_token,
                        owner_id, use_ssl=True, validate_cert=True):
        """ Adds a new slave to toxicbuild.

        :param slave_name: A name for the slave,
        :param slave_host: Host where the slave is.
        :param slave_port: Port to connect to the slave
        :param slave_token: Auth token for the slave.
        :param owner_id: Slave's owner id.
        :param use_ssl: Indicates if the slave uses a ssl connection.
        :pram validate_cert: Should the slave certificate be validated?
        """

        if not self._user_is_allowed('add_slave'):
            raise NotEnoughPerms

        owner = await self._get_owner(owner_id)
        slave = await Slave.create(name=slave_name, host=slave_host,
                                   port=slave_port, token=slave_token,
                                   owner=owner, use_ssl=use_ssl,
                                   validate_cert=validate_cert)

        slave_dict = self._get_slave_dict(slave)
        return {'slave-add': slave_dict}

    async def slave_get(self, slave_name_or_id):
        """Returns information about one specific slave"""

        kw = self._get_kw_for_name_or_id(slave_name_or_id)
        slave = await Slave.get_for_user(self.protocol.user, **kw)
        slave_dict = self._get_slave_dict(slave)
        return {'slave-get': slave_dict}

    async def slave_remove(self, slave_name_or_id):
        """ Removes a slave from toxicbuild. """

        kw = self._get_kw_for_name_or_id(slave_name_or_id)
        slave = await Slave.get_for_user(self.protocol.user, **kw)

        await slave.delete()

        return {'slave-remove': 'ok'}

    async def slave_list(self):
        """ Lists all slaves. """

        slaves = await Slave.list_for_user(self.protocol.user)
        slave_list = []

        async for slave in slaves:
            slave_dict = self._get_slave_dict(slave)
            slave_list.append(slave_dict)

        return {'slave-list': slave_list}

    async def slave_update(self, slave_name_or_id, **kwargs):
        """Updates infomation of a slave."""

        kw = self._get_kw_for_name_or_id(slave_name_or_id)
        slave = await Slave.get_for_user(self.protocol.user, **kw)

        for k, v in kwargs.items():
            setattr(slave, k, v)

        await slave.save()
        return {'slave-update': 'ok'}

    async def buildset_list(self, repo_name_or_id=None, skip=0, offset=None):
        """ Lists all buildsets.

        If ``repo_name_or_id``, only builders from this repository will be
          listed.
        :param repo_name_or_id: Repository's name or id.
        :param skip: skip for buildset list.
        :param offset: offset for buildset list.
        """

        buildsets = BuildSet.objects.no_dereference()
        if repo_name_or_id:
            kw = self._get_kw_for_name_or_id(repo_name_or_id)
            repository = await Repository.get_for_user(
                self.protocol.user, **kw)
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

    async def builder_show(self, repo_name_or_id, builder_name, skip=0,
                           offset=None):
        """ Returns information about one specific builder.

        :param repo_name_or_id: The builder's repository name.
        :param builder_name: The bulider's name.
        :param skip: How many elements we should skip in the result.
        :param offset: How many results we should return.
        """

        kw = self._get_kw_for_name_or_id(repo_name_or_id)
        repo = await Repository.get_for_user(self.protocol.user, **kw)
        kwargs = {'name': builder_name}
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

    async def _get_last_buildset_info(self, repo):
        last_buildset = await repo.get_last_buildset()
        if last_buildset:
            status = last_buildset.get_status()

            started = datetime2string(last_buildset.started) \
                if last_buildset.started else ''

            totaltime = format_timedelta(
                timedelta(seconds=last_buildset.total_time)) \
                if last_buildset.started else ''

            commit_date = datetime2string(last_buildset.commit_date)

            last_buildset_dict = {
                'status': status,
                'total_time': totaltime,
                'started': started,
                'commit': last_buildset.commit,
                'commit_date': commit_date,
                'title': last_buildset.title}
        else:
            last_buildset_dict = {}

        return last_buildset_dict

    async def _get_repo_dict(self, repo):
        """Returns a dictionary for a given repository"""

        repo_dict = await repo.to_dict(id_as_str=True)
        last_buildset_dict = await self._get_last_buildset_info(repo)
        repo_dict['last_buildset'] = last_buildset_dict

        repo_dict['status'] = await repo.get_status()
        repo_dict['parallel_builds'] = repo.parallel_builds or ''
        return repo_dict

    def _get_slave_dict(self, slave):
        slave_dict = json.loads(slave.to_json())
        slave_dict['id'] = str(slave.id)
        return slave_dict


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
        await self.send_info('step_started', sender=sender, **kw)

    async def step_finished(self, sender, **kw):
        await self.send_info('step_finished', sender=sender, **kw)

    async def build_started(self, sender, **kw):
        await self.send_info('build_started', sender=sender, **kw)

    async def build_finished(self, sender, **kw):
        await self.send_info('build_finished', sender=sender, **kw)

    async def build_added(self, sender, **kw):
        await self.send_info('build_added', sender=sender, **kw)

    async def build_cancelled_fn(self, sender, **kw):
        self.log('Got build-cancelled signal', level='debug')
        await self.send_info('build_cancelled', sender=sender, **kw)

    async def _connect2signals(self):
        repos = await Repository.list_for_user(self.protocol.user)
        async for repo in repos:
            self._connect_repo(repo)
        ensure_future(self._handle_ui_notifications())

    def _connect_repo(self, repo):
        step_started.connect(self.step_started, sender=str(repo.id))
        step_finished.connect(self.step_finished, sender=str(repo.id))
        build_started.connect(self.build_started, sender=str(repo.id))
        build_finished.connect(self.build_finished, sender=str(repo.id))
        build_added.connect(self.build_added, sender=str(repo.id))
        build_cancelled.connect(self.build_cancelled_fn, sender=str(repo.id))
        step_output_arrived.connect(self.send_step_output_info,
                                    sender=str(repo.id))

    async def _handle_ui_notifications(self):
        async with await ui_notifications.consume(routing_key=str(
                self.protocol.user.id)) as consumer:

            while True:
                msg = await consumer.fetch_message()
                self.log('Got msg type {}'.format(msg.body['msg_type']))
                if msg.body['msg_type'] == 'stop_consumption':
                    await msg.acknowledge()
                    self.log('stop consumption', level='debug')
                    break
                ensure_future(self._handle_ui_message(msg))
                await msg.acknowledge()

    async def _handle_ui_message(self, msg):
        msg_type = msg.body['msg_type']
        if msg_type == 'repo_added':
            await self.check_repo_added(msg)
        elif msg_type == 'repo_status_changed':
            await self.send_repo_status_info(msg)
        else:
            msg = 'Unknown message type {}'.format(msg_type)
            self.log(msg, level='warning')

    async def check_repo_added(self, msg):
        try:
            repo = await Repository.get_for_user(self.protocol.user,
                                                 id=msg.body['id'])
        except NotEnoughPerms:
            return

        ensure_future(self.send_repo_added_info(msg))
        self._connect_repo(repo)

    def _disconnectfromsignals(self):
        self.log('Disconnecting from signals', level='debug')

        ensure_future(ui_notifications.publish(
            {'msg_type': 'stop_consumption'}, routing_key=str(
                self.protocol.user.id)))
        step_output_arrived.disconnect(self.send_step_output_info)
        step_started.disconnect(self.step_started)
        step_finished.disconnect(self.step_finished)
        build_started.disconnect(self.build_started)
        build_finished.disconnect(self.build_finished)
        build_added.disconnect(self.build_added)
        build_cancelled.disconnect(self.build_cancelled_fn)

    async def handle(self):
        await self._connect2signals()
        await self.protocol.send_response(code=0, body={'stream': 'ok'})

    async def send_info(self, info_type, sender, build=None, step=None):
        repo = await Repository.objects.get(id=sender)
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

    async def send_repo_status_info(self, message):
        """Sends a message about a repository's new status

        :param message: A message from the repo_status_changed exchange."""

        repo = await Repository.objects.get(id=message.body['repository_id'])
        rdict = await repo.to_dict(id_as_str=True)
        rdict['status'] = message.body['new_status']
        rdict['old_status'] = message.body['old_status']
        rdict['event_type'] = 'repo_status_changed'
        self.log('sending response for send_repo_status_info',
                 level='debug')

        f = ensure_future(self.send_response(code=0, body=rdict))
        return f

    async def send_repo_added_info(self, message):
        """Sends a message about a repository's creation.

        :param message: A message from the repo_added exchange."""

        rdict = message.body
        rdict['event_type'] = 'repo_added'
        self.log('sending response for send_repo_added_info',
                 level='debug')
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
        except (ConnectionResetError, AttributeError):
            self.protocol._transport.close()
            self._disconnectfromsignals()


class HoleServer(LoggerMixin):
    """A server that uses the :class:`~toxicbuild.master.hole.UIHole`
    protocol."""

    def __init__(self, addr='127.0.0.1', port=6666, loop=None, use_ssl=False,
                 **ssl_kw):
        """:param addr: Address from which the server is allowed to receive
        requests. If ``0.0.0.0``, receives requests from all addresses.
        :param port: The port for the master to listen.
        :param loop: A main loop. If none, ``asyncio.get_event_loop()``
          will be used.
        :param use_ssl: Indicates is the connection uses ssl or not.
        :param ssl_kw: Named arguments passed to
          ``ssl.SSLContext.load_cert_chain()``
        """
        self.protocol = UIHole
        self.loop = loop or asyncio.get_event_loop()
        self.addr = addr
        self.port = port
        self.use_ssl = use_ssl
        self.ssl_kw = ssl_kw
        signal.signal(signal.SIGTERM, self.sync_shutdown)

    def serve(self):
        if self.use_ssl:
            ssl_context = ssl.create_default_context(
                ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(**self.ssl_kw)
            kw = {'ssl': ssl_context}
        else:
            kw = {}

        coro = self.loop.create_server(
            self.get_protocol_instance, self.addr, self.port, **kw)

        ensure_future(coro)

    async def shutdown(self):
        self.log('Shutting down')
        self.protocol.set_shutting_down()
        RepositoryMessageConsumer.stop()
        while Repository.get_running_builds() > 0:
            self.log('Waiting for {} build to finish'.format(
                Repository.get_running_builds()))
            await asyncio.sleep(0.5)

    def sync_shutdown(self, signum=None, frame=None):
        self.loop.run_until_complete(self.shutdown())

    def get_protocol_instance(self):
        return self.protocol(self.loop)
