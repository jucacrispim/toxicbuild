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

import asyncio
try:
    from asyncio import ensure_future
except ImportError:  # pragma no cover
    from asyncio import async as ensure_future

from tornado import gen
from tornado.websocket import WebSocketHandler, WebSocketError
from pyrocumulus.web.applications import (PyroApplication, StaticApplication)
from pyrocumulus.web.handlers import TemplateHandler, PyroRequest
from pyrocumulus.web.urlmappers import URLSpec
from toxicbuild.core.utils import bcrypt_string, LoggerMixin
from toxicbuild.ui import settings
from toxicbuild.ui.client import get_hole_client
from toxicbuild.ui.exceptions import BadActionError
from toxicbuild.ui.models import Repository, Slave, BuildSet, Builder


COOKIE_NAME = 'toxicui'


class LoginHandler(TemplateHandler):

    def get(self, action):
        if action == 'logout':
            self.clear_cookie(COOKIE_NAME)
            return self.redirect('/')

        if self.get_secure_cookie(COOKIE_NAME):
            return self.redirect('/')

        error = bool(self.params.get('error'))
        self.render_template('login.html', {'error': error})

    def post(self, action):
        if not self.params.get('username') == settings.USERNAME:
            return self.redirect('/login?error=1')

        salt = settings.BCRYPT_SALT
        passwd = settings.PASSWORD
        if not bcrypt_string(self.params.get('password'), salt) == passwd:
            return self.redirect('/login?error=1')

        self.set_secure_cookie(COOKIE_NAME, 'SAUCIFUFU!')
        self.redirect('/')


class LoggedTemplateHandler(TemplateHandler):

    def prepare(self):
        super().prepare()
        cookie = self.get_secure_cookie(COOKIE_NAME)
        if not cookie:
            self.redirect('/login')


class BaseModelHandler(LoggedTemplateHandler):
    item_template = 'item.html'
    list_template = 'list.html'

    def initialize(self, *args, **kwargs):
        self.model = kwargs['model']
        del kwargs['model']
        super().initialize(*args, **kwargs)

    @asyncio.coroutine
    def get_item(self, **kwargs):
        item = yield from self.model.get(**kwargs)
        return item

    @asyncio.coroutine
    def add(self, **kwargs):
        resp = yield from self.model.add(**kwargs)

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

        elif'start-build' not in args:
            yield super().post(*args)
            return

        ret = yield from self.start_build()
        self.write(ret)

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

        else:
            kw = {}
            kw['name'] = self.params.get('name')
            kw['url'] = self.params.get('url')
            kw['vcs_type'] = self.params.get('vcs_type')
            kw['update_seconds'] = self.params.get('update_seconds')
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


class StreamHandler(LoggerMixin, WebSocketHandler):

    def initialize(self):
        self.client = None

    def open(self, action):
        if action == 'repo-status':
            events = ['repo_status_changed']
            out_fn = self._send_repo_status_info

        elif action == 'builds':
            events = ['build_started', 'build_finished', 'build_added',
                      'step_started', 'step_finished']
            out_fn = self._send_build_info

        elif action == 'step-output':
            events = ['step_output_info']
            out_fn = self._send_step_output_info

        else:
            msg = 'Action {} is not known'.format(action)
            raise BadActionError(msg)

        ensure_future(self.listen2event(*events, out_fn=out_fn))

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

        repository_id = self.request.arguments[
            'repository_id'][0].decode()

        repo = info.get('repository', {})

        if not repo or (repo and repository_id == repo.get('id')):
            self.write2sock(info)

    def _send_repo_status_info(self, info):
        self.write2sock(info)

    @asyncio.coroutine
    def get_stream_client(self):
        """Return a client already connected to the master and
        listening the stream."""

        host = settings.HOLE_HOST
        port = settings.HOLE_PORT
        client = yield from get_hole_client(host, port)
        yield from client.connect2stream()
        return client

    @asyncio.coroutine
    def listen2event(self, *event_types, out_fn):
        """Creates a connection to the master and sends a messge to
        the ws client when an event of event_type is sent by the mater.

        :param event_types: A list of the events that will be handled by
          this connection.
        :para out_fn: A function that receives the message sent by the
          master if the message has the right event_type
        """

        self.client = yield from self.get_stream_client()
        while self.client._connected:
            response = yield from self.client.get_response()
            body = response.get('body', {})

            if not body:
                self.log('Bad data: closing connection', level='debug')
                self.client.disconnect()
                break

            master_event_type = body.get('event_type')

            if master_event_type in event_types:
                out_fn(body)

    def on_close(self):
        self.client.disconnect()

    def write2sock(self, body):
        try:
            self.write_message(body)
        except WebSocketError:
            self.log('WebSocketError: closing connection',
                     level='debug')
            self.client.disconnect()


class MainHandler(LoggedTemplateHandler):
    main_template = 'main.html'

    @gen.coroutine
    def get(self):
        repos = yield from Repository.list()
        slaves = yield from Slave.list()

        context = {'repos': repos, 'slaves': slaves,
                   'get_btn_class': self._get_btn_class}
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
        buildsets = yield from BuildSet.list(repo_name=repo_name)
        builders = yield from self._get_builders_for_buildsets(buildsets)
        repo = yield from Repository.get(repo_name=repo_name)

        def _ordered_builds(builds):
            return sorted(
                builds, key=lambda b: builders[builders.index(b.builder)].name)

        context = {'buildsets': buildsets, 'builders': builders,
                   'ordered_builds': _ordered_builds,
                   'get_ending': self._get_ending,
                   'repository': repo}
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
        builders = yield from Builder.list(id__in=ids)
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
