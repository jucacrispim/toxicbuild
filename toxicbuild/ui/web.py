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

import asyncio
from asyncio import ensure_future
import base64
import datetime
import json
import traceback

from tornado import gen
from tornado.web import HTTPError
from tornado.websocket import WebSocketHandler, WebSocketError
from pyrocumulus.web.applications import (PyroApplication, StaticApplication)
from pyrocumulus.web.decorators import post, get, put, delete
from pyrocumulus.web.handlers import (TemplateHandler, PyroRequest,
                                      BasePyroHandler)
from pyrocumulus.web.urlmappers import URLSpec

from toxicbuild.core.utils import LoggerMixin, string2datetime
from toxicbuild.ui import settings
from toxicbuild.ui.connectors import StreamConnector
from toxicbuild.ui.models import (Repository, Slave, BuildSet, Plugin,
                                  User)
from toxicbuild.ui.utils import (format_datetime, is_datetime,
                                 get_builders_for_buildsets)


COOKIE_NAME = 'toxicui'


class ToxicRequest(PyroRequest):

    def __getitem__(self, key):
        item = self.new_request[key]
        if len(item) == 1:
            item = item[0]
        return item

    def items(self):
        """Returns the request items"""
        for k, v in self.new_request.items():
            yield k, self.get(k)

    def get(self, key, default=None):
        """Returns a single value for a key. If it's not present
        returns None."""
        try:
            item = self[key]
        except KeyError:
            item = default

        return item


class LoggedTemplateHandler(TemplateHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None

    def prepare(self):
        super().prepare()
        user = self._get_user_from_cookie()
        if not user:
            self.redirect('/login')
        self.user = user

    def _get_user_from_cookie(self):
        cookie = self.get_secure_cookie(COOKIE_NAME)
        if not cookie:
            return

        userjson = base64.decodebytes(cookie).decode('utf-8')
        return User(None, json.loads(userjson))


class CookieAuthHandlerMixin(LoggerMixin, BasePyroHandler):
    """A mixin that checks if the requester is logged by looking
    for a cookie."""

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    async def async_prepare(self):
        user = self._get_user_from_cookie()
        if not user:
            raise HTTPError(403)
        self.user = user
        await super().async_prepare()
        return True

    def _get_user_from_cookie(self):
        cookie = self.get_secure_cookie(COOKIE_NAME)
        if not cookie:
            return

        userjson = base64.decodebytes(cookie).decode('utf-8')
        return User(None, json.loads(userjson))


class LoginHandler(BasePyroHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.body = None

    async def async_prepare(self):
        await super().async_prepare()
        self.body = json.loads(self.request.body)

    @post('login')
    async def do_login(self):
        """Authenticates using username and password and creates a cookie"""

        username_or_email = self.body.get('username_or_email')
        password = self.body.get('password')

        if not (username_or_email and password):
            raise HTTPError(400, 'Missing parameters for login')

        try:
            self.user = await User.authenticate(username_or_email, password)
        except Exception:
            raise HTTPError(403)

        self._set_cookie_content()
        return {'login': 'ok'}

    @get('logout')
    def do_logout(self):
        self.clear_cookie(COOKIE_NAME)
        return {'logout': 'ok'}

    def _set_cookie_content(self):
        userjson = json.dumps({'id': self.user.id, 'email': self.user.email,
                               'username': self.user.username})

        content = base64.encodebytes(userjson.encode('utf-8'))
        self.set_secure_cookie(COOKIE_NAME, content)


class ModelRestHandler(LoggerMixin, BasePyroHandler):
    """A base handler for handlers that are responsible for manipulating
    models from :mod:`~toxicbuild.ui.models`"""

    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model', None)
        self.body = None
        self.query = None
        super().__init__(*args, **kwargs)

    async def async_prepare(self):
        super().async_prepare()

        if self.request.body:  # pragma no branch
            self.body = json.loads(self.request.body)

        self.query = ToxicRequest(self.request.arguments)

    @post('')
    async def add(self):
        self.body['owner'] = self.user

        resp = await self.model.add(self.user, **self.body)

        json_resp = resp.to_json()
        return json_resp

    @get('')
    async def get_or_list(self):
        if self._query_has_pk():
            item = await self.model.get(self.user, **self.query)
            resp = item.to_json()
        else:
            items = await self.model.list(self.user, **self.query)
            r = {'items': [i.to_dict() for i in items]}
            resp = json.dumps(r)

        return resp

    @put('')
    async def update(self):
        item = await self.model.get(self.user, **self.query)
        for key, value in self.body.items():
            setattr(item, key, value)

        await item.update(**self.body)
        return item.to_json()

    @delete('')
    async def delete_item(self):
        item = await self.model.get(self.user, **self.query)
        await item.delete()
        return {'delete': 'ok'}

    def _query_has_pk(self):
        return 'id' in self.query.keys()


class RepositoryRestHandler(ModelRestHandler):
    """A rest api handler for repositories"""

    @post('add-slave')
    async def add_slave(self):
        repo = await self.model.get(self.user, **self.query)
        slave = await Slave.get(self.user, **self.body)
        await repo.add_slave(slave)
        return {'repo-add-slave': 'slave added'}

    @post('remove-slave')
    async def remove_slave(self):
        repo = await self.model.get(self.user, **self.query)
        slave = await Slave.get(self.user, **self.body)
        await repo.remove_slave(slave)
        return {'repo-remove-slave': 'slave removed'}

    @post('add-branch')
    async def add_branch(self):
        """Adds a new branch configuration to the repository."""

        repo = await self.model.get(self.user, **self.query)
        branches = self.body.get('add_branches', [])
        tasks = [ensure_future(repo.add_branch(**branch))
                 for branch in branches]

        await asyncio.gather(*tasks)
        return {'repo-add-branch': '{} branches added'.format(len(branches))}

    @post('remove-branch')
    async def remove_branch(self):
        """Removes a branch configuration from the repository."""

        repo = await self.model.get(self.user, **self.query)
        branches = self.body.get('remove_branches', [])
        tasks = [ensure_future(repo.remove_branch(branch))
                 for branch in branches]
        await asyncio.gather(*tasks)
        return {'repo-remove-branch': '{} branches removed'.format(len(
            branches))}

    @post('enable-plugin')
    async def enable_plugin(self):
        """Enables a plugin for a repository."""

        repo = await self.model.get(self.user, **self.query)
        await repo.enable_plugin(**self.body)
        return {'repo-enable-plugin': 'plugin {} enabled'.format(self.body.get(
            'plugin_name'))}

    @post('disable-plugin')
    async def disable_plugin(self):
        """Disables a plugin for a repository."""

        repo = await self.model.get(self.user, **self.query)
        await repo.disable_plugin(**self.body)
        return {'repo-disable-plugin': 'plugin {} disabled'.format(
            self.body.get('plugin_name'))}

    @get('list-plugins')
    async def list_plugins(self):
        """Lists all plugins available to a repository."""

        plugins = await Plugin.list(self.user)
        return {'items': [p.to_dict() for p in plugins]}

    @post('start-build')
    async def start_build(self):
        """Starts builds for the repository."""

        repo = await self.model.get(self.user, **self.query)
        await repo.start_build(**self.body)
        return {'repo-start-build': 'builds scheduled'}

    @post('cancel-build')
    async def cancel_build(self):
        """Cancels a build from a repository."""

        repo = await self.model.get(self.user, **self.query)
        build_uuid = self.body.get('build_uuid')
        await repo.cancel_build(build_uuid)
        return {'repo-cancel-build': 'build cancelled'}


class CookieAuthRepositoryRestHandler(CookieAuthHandlerMixin,
                                      RepositoryRestHandler):
    """A rest api handler for repositories which requires cookie auth."""


class SlaveRestHandler(ModelRestHandler):
    """A rest api handler for slaves."""


class CookieAuthSlaveRestHandler(CookieAuthHandlerMixin, SlaveRestHandler):
    """A rest api handler for slaves which requires cookie auth."""


class StreamHandler(LoggerMixin, LoggedTemplateHandler, WebSocketHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action = None
        self.repo_id = None

    def initialize(self):
        self.action = None
        self.repo_id = None
        self.events = {'repo_status_changed': self._send_raw_info,
                       'repo_added': self._send_raw_info,
                       'build_started': self._send_build_info,
                       'build_finished': self._send_build_info,
                       'build_added': self._send_build_info,
                       'build_cancelled': self._send_build_info,
                       'step_started': self._send_build_info,
                       'step_finished': self._send_build_info,
                       'step_output_info': self._send_step_output_info}
        # maps actions to message (event) types
        self.action_messages = {'repo-status': ['repo_status_changed',
                                                'repo_added'],
                                'builds': ['build_started', 'build_finished',
                                           'build_added', 'step_started',
                                           'step_finished', 'build_cancelled'],
                                'step-output': ['step_output_info']}

    def _bad_message_type_logger(self, message):
        msg = 'Bad. message type: {}'.format(message['event_type'])
        self.log(msg, level='warning')

    def _get_repo_id(self):
        repo_id = None
        keys = ['repo_id', 'repository_id']
        for key in keys:
            try:
                repo_id = self.request.arguments.get(key)[0].decode()
                break
            except TypeError:
                pass

        return repo_id

    def open(self, action):
        self.action = action
        self.repo_id = self._get_repo_id()
        f = ensure_future(StreamConnector.plug(
            self.user, self.repo_id, self.receiver))
        return f

    def receiver(self, sender, **message):
        message_type = message.get('event_type')
        msg = 'message arrived: {}'.format(message_type)
        self.log(msg, level='debug')
        if message_type not in self.action_messages.get(self.action, []):
            msg = 'leaving receiver'
            self.log(msg, level='debug')
            return
        outfn = self.events.get(message_type, self._bad_message_type_logger)
        try:
            outfn(message)
        except Exception:
            msg = traceback.format_exc()
            self.log(msg, level='error')

    def _send_step_output_info(self, info):
        """Sends information about step output to the ws client.

        :param info: Message sent by the master"""
        step_uuid = self.request.arguments.get('uuid')[0].decode()
        uuid = info.get('uuid')
        if step_uuid == uuid:
            self.write2sock(info)

    def _send_build_info(self, info):
        """Sends information about builds to the ws client.

        :param info: The message sent by the master"""

        self._format_info_dt(info)
        self.write2sock(info)

    def _format_info_dt(self, info):
        started = info.get('started')
        if started and is_datetime(started):
            info['started'] = format_datetime(string2datetime(started))

        finished = info.get('finished')
        if finished and is_datetime(finished):
            info['finished'] = format_datetime(string2datetime(finished))

        created = info.get('created')
        if created and is_datetime(created):
            info['created'] = format_datetime(string2datetime(created))

        buildset = info.get('buildset')
        if buildset:
            self._format_info_dt(buildset)

    def _send_raw_info(self, info):
        self.write2sock(info)

    def on_close(self):
        self.log('connection closed', level='debug')
        StreamConnector.unplug(self.user, self.repo_id, self.receiver)

    def write2sock(self, body):
        try:
            self.write_message(body)
        except WebSocketError:
            tb = traceback.format_exc()
            self.log('WebSocketError: {}'.format(tb), level='debug')


class MainHandler(LoggedTemplateHandler):
    main_template = 'main.html'

    @gen.coroutine
    def get(self):
        repos = yield from Repository.list(self.user)
        slaves = yield from Slave.list(self.user)
        plugins = yield from Plugin.list(self.user)

        github_import_url = self._get_settings('GITHUB_IMPORT_URL') or '#'
        context = {'repos': repos, 'slaves': slaves,
                   'get_btn_class': self._get_btn_class,
                   'plugins': plugins, 'github_import_url': github_import_url}
        self.render_template(self.main_template, context)

    def _get_settings(self, key):
        try:
            return getattr(settings, key)
        except AttributeError:
            return None

    def _get_btn_class(self, status):
        return {'success': 'success', 'fail': 'danger',
                'running': 'info', 'exception': 'exception',
                'clone-exception': 'exception', 'ready': 'success',
                'warning': 'warning', 'cloning': 'pending'}.get(status)


class WaterfallHandler(LoggedTemplateHandler):
    template = 'waterfall.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params = None

    def prepare(self):
        super().prepare()
        self.params = PyroRequest(self.request.arguments)

    @gen.coroutine
    def get(self, repo_name):
        buildsets = yield from BuildSet.list(self.user, repo_name=repo_name)
        builders = yield from self._get_builders_for_buildsets(buildsets)
        repo = yield from Repository.get(self.user, repo_name=repo_name)

        def _ordered_builds(builds):
            return sorted(
                builds, key=lambda b: builders[builders.index(b.builder)].name)

        def fmtdt(dt):  # pragma: no cover
            # when the attribute is not set, it is a empty string int the
            # template, so we simply skip it here
            if not isinstance(dt, datetime.datetime):
                return
            return format_datetime(dt)

        context = {'buildsets': buildsets, 'builders': builders,
                   'ordered_builds': _ordered_builds,
                   'get_ending': self._get_ending,
                   'repository': repo, 'fmtdt': fmtdt}
        self.render_template(self.template, context)

    @asyncio.coroutine
    def _get_builders_for_buildsets(self, buildsets):
        r = yield from get_builders_for_buildsets(self.user, buildsets)
        return r

    def _get_ending(self, build, build_index, builders):
        i = build_index
        while build.builder != builders[i] and len(builders) > i:
            tag = '</td><td class="builder-column builder-column-id-{}'
            tag += ' builder-column-index-{}">'
            yield tag.format(builders[i].id, i + 1)
            i += 1
        yield ''


url = URLSpec('/$', MainHandler)
waterfall = URLSpec('/waterfall/(.*)', WaterfallHandler)
websocket = URLSpec('/api/socks/(.*)', StreamHandler)
login = URLSpec('/(login|logout)', LoginHandler)

app = PyroApplication([url, waterfall, login, websocket])

static_app = StaticApplication()

repo_kwargs = {'model': Repository}
repo_api_url = URLSpec('/api/repo/(.*)', CookieAuthRepositoryRestHandler,
                       repo_kwargs)

slave_kwargs = {'model': Slave}
slave_api_url = URLSpec('/api/slave/(.*)', CookieAuthSlaveRestHandler,
                        slave_kwargs)

api_app = PyroApplication([repo_api_url, slave_api_url])
