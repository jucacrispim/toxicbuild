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
from tornado import gen
from pyrocumulus.web.applications import Application, StaticApplication
from pyrocumulus.web.handlers import TemplateHandler
from pyrocumulus.web.urlmappers import URLSpec
from toxicbuild.ui import settings
from toxicbuild.ui.models import Repository, Slave, Builder


class BaseModelHandler(TemplateHandler):
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
        kwargs = self.request.arguments
        resp = yield from self.get_item(**kwargs)
        json_resp = resp.to_json()
        return json_resp

    @gen.coroutine
    def post(self, *args):
        kwargs = self.request.arguments
        resp = yield from self.add(**kwargs)
        self.write(resp)

    @gen.coroutine
    def delete(self, *args):
        item = yield from self.get_item(**self.request.arguments)
        resp = yield from item.delete()
        return resp


class RepositoryHandler(BaseModelHandler):

    @gen.coroutine
    def post(self, *args):
        if'start-build' not in args:
            ret = yield super().post(*args)
            return
        ret = yield from self.start_build()
        self.write(ret)

    @asyncio.coroutine
    def start_build(self):
        item = yield from self.get_item(repo_name=self.request.arguments[
            'name'])
        del self.request.arguments['name']
        ret = yield from item.start_build(**self.request.arguments)
        return ret

    def prepare(self):
        if 'start-build' in self.request.uri:
            self._prepare_start_build()
        else:
            kw = {}
            kw['name'] = self.request.arguments.get('name', [b''])[0].decode()
            kw['url'] = self.request.arguments.get('url', [b''])[0].decode()
            kw['vcs_type'] = self.request.arguments.get('vcs_type',
                                                        [b''])[0].decode()
            kw['update_seconds'] = self.request.arguments.get(
                'update_seconds', [b''])[0].decode()
            kw['slaves'] = [s.decode() for s in
                            self.request.arguments.get('slaves', [])]
            self.request.arguments = kw

    def _prepare_start_build(self):
        kw = {}
        kw['name'] = self.request.arguments.get('name', [b''])[0].decode()
        kw['builder_name'] = self.request.arguments.get(
            'builder_name', [b''])[0].decode()
        kw['branch'] = self.request.arguments.get('branch', [b''])[0].decode()
        kw['slaves'] = [s.decode() for s in
                        self.request.arguments.get('slaves', [])]

        self.request.arguments = kw

    @gen.coroutine
    def delete(self, *args):
        name = self.request.arguments['name']
        del self.request.arguments['name']
        self.request.arguments = {'repo_name': name}

        yield super().delete(*args)


class SlaveHandler(BaseModelHandler):

    def prepare(self):
        kw = {}
        kw['name'] = self.request.arguments.get('name', [b''])[0].decode()
        kw['host'] = self.request.arguments.get('host', [b''])[0].decode()
        kw['port'] = self.request.arguments.get('port', [b''])[0].decode()
        self.request.arguments = kw

    @gen.coroutine
    def delete(self, *args):
        name = self.request.arguments['name']
        del self.request.arguments['name']
        self.request.arguments = {'slave_name': name}

        yield super().delete(*args)


class MainHandler(TemplateHandler):
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
                'running': 'info'}.get(status)


class WaterfallHandler(TemplateHandler):  # pragma no cover
    template = 'waterfall.html'

    @gen.coroutine
    def get(self):
        repo_name = self.request.arguments.get('repo')[0].decode()
        builders = yield from Builder.list(repo_name=repo_name)
        context = {'builders': builders}
        self.render_template(self.template, context)


url = URLSpec('/$', MainHandler)
waterfall = URLSpec('/waterfall$', WaterfallHandler)
app = Application(url_prefix='', extra_urls=[url, waterfall])
static_app = StaticApplication()

repo_kwargs = {'model': Repository}
repo_api_url = URLSpec('/api/repo/(.*)', RepositoryHandler, repo_kwargs)

slave_kwargs = {'model': Slave}
slave_api_url = URLSpec('/api/slave/(.*)', SlaveHandler, slave_kwargs)

api_app = Application(url_prefix='', extra_urls=[repo_api_url, slave_api_url])
