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
from tornado import gen
from pyrocumulus.web.applications import (PyroApplication, StaticApplication)
from pyrocumulus.web.handlers import TemplateHandler, PyroRequest
from pyrocumulus.web.urlmappers import URLSpec
from toxicbuild.ui.models import Repository, Slave, BuildSet, Builder


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

        self.request.arguments = kw


class SlaveHandler(BaseModelHandler):

    def prepare(self):
        super().prepare()
        kw = {}
        kw['name'] = self.params.get('name')
        kw['host'] = self.params.get('host')
        kw['port'] = self.params.get('port')
        self.params = kw

    @gen.coroutine
    def delete(self, *args):
        self.params = {'slave_name': self.params.get('name')}
        yield super().delete(*args)

    @gen.coroutine
    def put(self, *args):
        item = yield from self.get_item(slave_name=self.params['name'])
        r = yield from item.update(**self.params)
        return r


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
                'running': 'info', 'exception': 'exception',
                'cloning': 'pending'}.get(status)


class WaterfallHandler(TemplateHandler):
    template = 'waterfall.html'

    def prepare(self):
        self.params = PyroRequest(self.request.arguments)

    @gen.coroutine
    def get(self, repo_name):
        buildsets = yield from BuildSet.list(repo_name=repo_name)
        builders = yield from self._get_builders_for_buildsets(buildsets)

        def _ordered_builds(builds):
            return sorted(
                builds, key=lambda b: builders[builders.index(b.builder)].name)

        context = {'buildsets': buildsets, 'builders': builders,
                   'ordered_builds': _ordered_builds,
                   'get_ending': self._get_ending}
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
        return sorted(builders, key=lambda b: b.name)

    def _get_ending(self, build, build_index, builders):
        i = build_index
        while build.builder != builders[i] and len(builders) > i:
            yield '</td><td>'
            i += 1
        yield ''


url = URLSpec('/$', MainHandler)
waterfall = URLSpec('/waterfall/(.*)', WaterfallHandler)
app = PyroApplication([url, waterfall])
static_app = StaticApplication()

repo_kwargs = {'model': Repository}
repo_api_url = URLSpec('/api/repo/(.*)', RepositoryHandler, repo_kwargs)

slave_kwargs = {'model': Slave}
slave_api_url = URLSpec('/api/slave/(.*)', SlaveHandler, slave_kwargs)

api_app = PyroApplication([repo_api_url, slave_api_url])
