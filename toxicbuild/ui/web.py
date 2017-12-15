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

# THIS WHOLE MODULE NEEDS TO BE RE-WRITTEN

import asyncio
from asyncio import ensure_future
import base64
import datetime
import json
import traceback

from tornado import gen
from tornado.websocket import WebSocketHandler, WebSocketError

from pyrocumulus.web.applications import (PyroApplication, StaticApplication)
from pyrocumulus.web.handlers import TemplateHandler, PyroRequest
from pyrocumulus.web.urlmappers import URLSpec

from toxicbuild.core.utils import LoggerMixin, string2datetime
from toxicbuild.ui.connectors import StreamConnector
from toxicbuild.ui.models import (Repository, Slave, BuildSet, Builder, Plugin,
                                  User)
from toxicbuild.ui.utils import format_datetime, is_datetime


COOKIE_NAME = 'toxicui'


class LoginHandler(TemplateHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None

    def get(self, action):
        if action == 'logout':
            self.clear_cookie(COOKIE_NAME)
            return self.redirect('/')

        if self.get_secure_cookie(COOKIE_NAME):
            return self.redirect('/')

        error = bool(self.params.get('error'))
        self.render_template('login.html', {'error': error})

    @gen.coroutine
    def post(self, action):
        username_or_email = self.params.get('username_or_email')
        password = self.params.get('password')

        if not (username_or_email and password):
            return self.redirect('/login?error=2')

        try:
            self.user = yield from User.authenticate(username_or_email,
                                                     password)
        except:
            return self.redirect('/login?error=1')

        self._set_cookie_content()
        self.redirect('/')

    def _set_cookie_content(self):
        userjson = json.dumps({'id': self.user.id, 'email': self.user.email,
                               'username': self.user.username})

        content = base64.encodebytes(userjson.encode('utf-8'))
        self.set_secure_cookie(COOKIE_NAME, content)


class LoggedTemplateHandler(TemplateHandler):

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


class BaseModelHandler(LoggedTemplateHandler):
    item_template = 'item.html'
    list_template = 'list.html'

    def initialize(self, *args, **kwargs):
        self.model = kwargs['model']
        del kwargs['model']
        super().initialize(*args, **kwargs)

    @asyncio.coroutine
    def get_item(self, **kwargs):
        item = yield from self.model.get(self.user, **kwargs)
        return item

    @asyncio.coroutine
    def add(self, **kwargs):
        if not kwargs.get('owner'):
            kwargs['owner'] = self.user

        resp = yield from self.model.add(self.user, **kwargs)

        json_resp = resp.to_json()
        return json_resp

    @gen.coroutine
    def get(self, *args):
        resp = yield from self.get_item(**self.params)
        json_resp = resp.to_json()
        return json_resp

    @gen.coroutine
    def post(self, *args):
        resp = yield from self.add(**self.params)
        self.write(resp)

    @gen.coroutine
    def delete(self, *args):
        item = yield from self.get_item(**self.params)
        resp = yield from item.delete()
        return resp


class RepositoryHandler(BaseModelHandler):

    @gen.coroutine
    def post(self, *args):
        if 'add-branch' in args:
            yield from self.add_branch()
            return

        elif 'remove-branch' in args:
            yield from self.remove_branch()
            return

        elif 'enable-plugin' in self.request.uri:
            yield from self.enable_plugin()
            return

        elif 'disable-plugin' in self.request.uri:
            yield from self.disable_plugin()
            return

        elif'start-build' not in args:
            yield super().post(*args)
            return

        ret = yield from self.start_build()
        self.write(ret)

    @asyncio.coroutine
    def enable_plugin(self):

        repo = yield from self.get_item(repo_name=self.params.get('name'))
        del self.params['name']
        plugin_name = self.params.get('plugin_name')
        del self.params['plugin_name']
        r = yield from repo.enable_plugin(plugin_name, **self.params)
        return r

    @asyncio.coroutine
    def disable_plugin(self):
        repo = yield from self.get_item(repo_name=self.params.get('name'))
        plugin_name = self.params.get('plugin_name')
        r = yield from repo.disable_plugin(name=plugin_name)
        return r

    @asyncio.coroutine
    def list_plugins(self):
        plugins = yield from Plugin.list()
        return plugins

    @asyncio.coroutine
    def start_build(self):
        item = yield from self.get_item(repo_name=self.params.get('name'))
        del self.params['name']
        ret = yield from item.start_build(**self.params)
        return ret

    @asyncio.coroutine
    def add_branch(self):
        item = yield from self.get_item(repo_name=self.params.get('name'))
        del self.params['name']
        notify = self.params['notify_only_latest']
        notify = True if notify == 'true' else False
        self.params['notify_only_latest'] = notify
        r = yield from item.add_branch(**self.params)
        return r

    @asyncio.coroutine
    def remove_branch(self):
        item = yield from self.get_item(repo_name=self.params.get('name'))
        del self.params['name']
        r = yield from item.remove_branch(**self.params)
        return r

    @gen.coroutine
    def prepare(self):
        super().prepare()
        if 'start-build' in self.request.uri:
            self._prepare_start_build()

        elif 'add-branch' in self.request.uri:
            kw = {'name': self.params.get('name'),
                  'branch_name': self.params.get('branch_name'),
                  'notify_only_latest': self.params.get('notify_only_latest')}
            self.params = kw

        elif 'remove-branch' in self.request.uri:
            kw = {'name': self.params.get('name'),
                  'branch_name': self.params.get('branch_name')}
            self.params = kw

        elif ('enable-plugin' in self.request.uri or
              'disable-plugin' in self.request.uri):
            yield from self._prepare_for_plugin()

        else:
            kw = {}
            kw['name'] = self.params.get('name')
            kw['url'] = self.params.get('url')
            kw['vcs_type'] = self.params.get('vcs_type')
            kw['update_seconds'] = self.params.get('update_seconds')
            kw['parallel_builds'] = self.params.get('parallel_builds')
            kw['slaves'] = self.params.getlist('slaves')
            self.params = kw

    @gen.coroutine
    def delete(self, *args):
        self.params = {'repo_name': self.params.get('name')}
        yield super().delete(*args)

    @gen.coroutine
    def put(self, *args):
        item = yield from self.get_item(repo_name=self.params['name'])
        del self.params['name']
        r = yield from item.update(**self.params)
        self.write(r)

    def _prepare_start_build(self):
        kw = {}
        kw['name'] = self.params.get('name')
        kw['builder_name'] = self.params.get('builder_name')
        kw['branch'] = self.params.get('branch')
        kw['slaves'] = self.params.getlist('slaves')
        kw['named_tree'] = self.params.get('named_tree')

        self.params = kw

    @asyncio.coroutine
    def _prepare_for_plugin(self):

        kw = {}
        plugin_name = self.params.get('plugin_name')
        plugin = yield from Plugin.get(self.user, name=plugin_name)
        for k, v in self.params.items():
            try:
                kw[k] = v[0] if getattr(plugin, k)['type'] != 'list' else [
                    i.strip() for i in v[0].split(',')]
            except (AttributeError, TypeError):
                # TypeError happens when a attribute is not a dict
                # ie, plugin pretty_name and description
                kw[k] = v[0]

        self.params = kw


class SlaveHandler(BaseModelHandler):

    def prepare(self):
        super().prepare()
        kw = {}
        kw['name'] = self.params.get('name')
        kw['host'] = self.params.get('host')
        kw['port'] = self.params.get('port')
        kw['token'] = self.params.get('token')
        self.params = kw

    @gen.coroutine
    def delete(self, *args):
        self.params = {'slave_name': self.params.get('name')}
        yield super().delete(*args)

    @gen.coroutine
    def put(self, *args):
        item = yield from self.get_item(slave_name=self.params['name'])
        yield from item.update(**self.params)


class StreamHandler(LoggerMixin, LoggedTemplateHandler, WebSocketHandler):

    def initialize(self):
        self.action = None
        self.repo_id = None
        self.events = {'repo_status_changed': self._send_repo_status_info,
                       'build_started': self._send_build_info,
                       'build_finished': self._send_build_info,
                       'build_added': self._send_build_info,
                       'step_started': self._send_build_info,
                       'step_finished': self._send_build_info,
                       'step_output_info': self._send_step_output_info}
        # maps actions to message (event) types
        self.action_messages = {'repo-status': ['repo_status_changed'],
                                'builds': ['build_started', 'build_finished',
                                           'build_added', 'step_started',
                                           'step_finished'],
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

    def _send_repo_status_info(self, info):
        self.write2sock(info)

    def on_close(self):
        StreamConnector.unplug(self.user, self.repo_id, self.receiver)

    def write2sock(self, body):
        try:
            self.write_message(body)
        except WebSocketError:
            self.log('WebSocketError', level='debug')


class MainHandler(LoggedTemplateHandler):
    main_template = 'main.html'

    @gen.coroutine
    def get(self):
        repos = yield from Repository.list(self.user)
        slaves = yield from Slave.list(self.user)
        plugins = yield from Plugin.list(self.user)

        context = {'repos': repos, 'slaves': slaves,
                   'get_btn_class': self._get_btn_class,
                   'plugins': plugins}
        self.render_template(self.main_template, context)

    def _get_btn_class(self, status):
        return {'success': 'success', 'fail': 'danger',
                'running': 'info', 'exception': 'exception',
                'clone-exception': 'exception', 'ready': 'success',
                'warning': 'warning', 'cloning': 'pending'}.get(status)


class WaterfallHandler(LoggedTemplateHandler):
    template = 'waterfall.html'

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
        builders = set()
        buildsets = buildsets or []
        for buildset in buildsets:
            for build in buildset.builds:
                builders.add(build.builder)

        # Now the thing here is: the builders here are made
        # from the response of buildset-list. It returns only
        # the builder id for builds, so now I retrieve the
        # 'full' builder using builder-list
        ids = [b.id for b in builders]
        builders = yield from Builder.list(self.user, id__in=ids)
        builders_dict = {b.id: b for b in builders}
        for buildset in buildsets:
            for build in buildset.builds:
                build.builder = builders_dict[build.builder.id]

        return sorted(builders, key=lambda b: b.name)

    def _get_ending(self, build, build_index, builders):
        i = build_index
        while build.builder != builders[i] and len(builders) > i:
            tag = '</td><td class="builder-column builder-column-id-{}'
            tag += 'builder-column-index-{}">'
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
repo_api_url = URLSpec('/api/repo/(.*)', RepositoryHandler, repo_kwargs)

slave_kwargs = {'model': Slave}
slave_api_url = URLSpec('/api/slave/(.*)', SlaveHandler, slave_kwargs)

api_app = PyroApplication([repo_api_url, slave_api_url])
