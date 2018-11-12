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
import json
import traceback
from tornado.web import HTTPError
from tornado.websocket import WebSocketHandler, WebSocketError
from pyrocumulus.web.applications import PyroApplication, StaticApplication
from pyrocumulus.web.decorators import post, get, put, delete, patch
from pyrocumulus.web.handlers import PyroRequest, BasePyroHandler
from pyrocumulus.web.template import render_template
from pyrocumulus.web.urlmappers import URLSpec

from toxicbuild.core.utils import LoggerMixin, string2datetime
from toxicbuild.ui import settings
from toxicbuild.ui.connectors import StreamConnector
from toxicbuild.ui.exceptions import BadSettingsType
from toxicbuild.ui.models import (Repository, Slave, User, Notification,
                                  BuildSet, Builder, Build)
from toxicbuild.ui.utils import (format_datetime, is_datetime)


COOKIE_NAME = 'toxicui'

FULL_NAME_REGEX = '([\w\d\-]+/[\w\d\-]+)'


class ToxicRequest(PyroRequest):

    _tranlate_table = {'true': True,
                       'false': False}

    def __getitem__(self, key):
        item = self.new_request[key]
        if len(item) == 1:
            item = item[0]

        try:
            item = self._tranlate_table.get(item, item)
        except TypeError:
            pass

        return item

    def items(self):
        """Returns the request items"""
        for k in self.new_request.keys():
            yield k, self.get(k)

    def get(self, key, default=None):
        """Returns a single value for a key. If it's not present
        returns None."""
        try:
            item = self[key]
        except KeyError:
            item = default

        return item


def _create_cookie_content(user):
    userjson = json.dumps({'id': user.id, 'email': user.email,
                           'username': user.username})

    content = base64.encodebytes(userjson.encode('utf-8'))
    return content


class CookieAuthHandlerMixin(LoggerMixin):
    """A mixin that checks if the requester is logged by looking
    for a cookie."""

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    def _get_user(self):
        user = self._get_user_from_cookie()
        if not user:
            raise HTTPError(403)

        self.user = user

    async def async_prepare(self):
        self._get_user()
        await super().async_prepare()
        return True

    def _get_user_from_cookie(self):
        cookie = self.get_secure_cookie(COOKIE_NAME)
        if not cookie:
            return

        userjson = base64.decodebytes(cookie).decode('utf-8')
        return User(None, json.loads(userjson))


class TemplateHandler(BasePyroHandler):
    """
    Handler with little improved template support
    """

    def render_template(self, template, extra_context=None):
        """
        Renders a template using
        :func:`pyrocumulus.web.template.render_template`.
        """
        extra_context = extra_context or {}
        self.write(render_template(template, self.request, extra_context))

    def set_xsrf_cookie(self):  # pragma no cover
        return self.xsrf_token


class LoggedTemplateHandler(CookieAuthHandlerMixin, TemplateHandler):
    skeleton_template = 'toxictheme/skeleton.html'

    async def async_prepare(self):
        try:
            await super().async_prepare()
        except HTTPError:
            self.redirect('/login')

        self.set_xsrf_cookie()


class BaseNotLoggedTemplate(TemplateHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.body = None
        self.query = None
        self.user = None

    async def async_prepare(self):
        await super().async_prepare()
        self.query = ToxicRequest(self.request.arguments)
        if self.request.body:
            self.body = json.loads(self.request.body)

    def _set_cookie_content(self):
        content = _create_cookie_content(self.user)
        self.set_secure_cookie(COOKIE_NAME, content)


class RegisterHandler(BaseNotLoggedTemplate):

    register_template = 'toxictheme/register.html'

    @get('register')
    def show_register_page(self):
        self.set_xsrf_cookie()
        self.render_template(self.register_template, {})


class LoginHandler(BaseNotLoggedTemplate):

    login_template = 'toxictheme/login.html'

    @get('login')
    def show_login_page(self):
        self.set_xsrf_cookie()
        self.render_template(self.login_template, {})
        return ''

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

        self.redirect('/')


class ModelRestHandler(LoggerMixin, BasePyroHandler):
    """A base handler for handlers that are responsible for manipulating
    models from :mod:`~toxicbuild.ui.models`"""

    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model', None)
        self.body = None
        self.query = None
        self.user = None
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

    @patch('')
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


class UserAddRestHandler(ModelRestHandler):
    """A rest api handler to add new users.
    """

    @get('check')
    async def check_exists(self):
        exists = await self.model.exists(**self.query)
        return {'check-exists': exists}

    @post('')
    async def add(self):
        email = self.body['email']
        username = self.body['username']
        password = self.body['password']
        allowed_actions = ['add_repo', 'add_slave',
                           'remove_repo', 'remove_slave']
        r = await self.model.add(email, username, password, allowed_actions)

        # When we create a user, we set a cookie for the new user's login
        content = _create_cookie_content(r)

        self.set_secure_cookie(COOKIE_NAME, content)
        return {'user-add': r.to_dict()}


class ReadOnlyRestHandler(ModelRestHandler):

    @post('')
    @put('')
    @patch('')
    @delete('')
    def invalid(self):
        raise HTTPError(405)


class BuildSetHandler(ReadOnlyRestHandler):

    async def _list(self, repo_name):
        summary = self.query.get('summary', False)
        r = await self.model.list(
            self.user, repo_name_or_id=repo_name, summary=summary)
        items = [i.to_dict() for i in r]
        return {'items': items}

    async def _get(self, buildset_id):
        buildset = await self.model.get(self.user, buildset_id)
        return buildset.to_dict()

    @get('')
    async def list_or_get(self):
        repo_name = self.query.get('repo_name')
        buildset_id = self.query.get('buildset_id')

        if repo_name:
            r = await self._list(repo_name)
        elif buildset_id:
            r = await self._get(buildset_id)
        else:
            raise HTTPError(400)

        return r


class CookieAuthBuildSetHandler(CookieAuthHandlerMixin, BuildSetHandler):
    pass


class BuildHandler(ReadOnlyRestHandler):

    @get('')
    async def get_build(self):
        try:
            build_uuid = self.query['build_uuid']
        except KeyError:
            raise HTTPError(400)

        build = await self.model.get(self.user, build_uuid)
        return build.to_dict()


class CookieAuthBuildHandler(CookieAuthHandlerMixin, BuildHandler):
    pass


class WaterfallRestHandler(ReadOnlyRestHandler):

    @get('')
    async def get_waterfall(self):
        try:
            repo_name = self.query['repo_name']
        except KeyError:
            raise HTTPError(400)

        buildsets = await self.model.list(self.user, repo_name_or_id=repo_name,
                                          summary=False)
        builders = await self._get_builders(buildsets)
        r = {'builders': [b.to_dict() for b in builders],
             'buildsets': [b.to_dict() for b in buildsets]}
        return r

    async def _get_builders(self, buildsets):
        bids = [b.builder.id for bs in buildsets for b in bs.builds]
        builders = await Builder.list(self.user, id__in=bids)
        return builders


class CookieAuthWaterfallHandler(CookieAuthHandlerMixin, WaterfallRestHandler):
    pass


class RepositoryRestHandler(ModelRestHandler):
    """A rest api handler for repositories."""

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

    @post('enable')
    async def enable(self):
        repo = await self.model.get(self.user, **self.query)
        await repo.enable()
        return {'repo-enable': 'enabled'}

    @post('disable')
    async def disable(self):
        repo = await self.model.get(self.user, **self.query)
        await repo.disable()
        return {'repo-disable': 'disabled'}


class NotificationRestHandler(ReadOnlyRestHandler):
    """Handler for enable/disable/update notifications for
    repositories.
    """

    @post('(.*)/(.*)')
    async def enable(self, notif_name, repo_id):
        notif_name = notif_name.decode()
        repo_id = repo_id.decode()
        await Notification.enable(repo_id, notif_name, **self.body)
        return {notif_name: 'enabled'}

    @delete('(.*)/(.*)')
    async def disable(self, notif_name, repo_id):
        notif_name = notif_name.decode()
        repo_id = repo_id.decode()
        await Notification.disable(repo_id, notif_name)
        return {notif_name: 'disabled'}

    @put('(.*)/(.*)')
    async def update(self, notif_name, repo_id):
        notif_name = notif_name.decode()
        repo_id = repo_id.decode()
        await Notification.update(repo_id, notif_name, **self.body)
        return {notif_name: 'updated'}

    @get('')
    async def list(self):
        repo_id = self.query.get('repo_id')
        r = await Notification.list(repo_id)
        items = [i.to_dict() for i in r]
        return {'items': items}


class CookieAuthNotificationRestHandler(CookieAuthHandlerMixin,
                                        NotificationRestHandler):
    """Rest api handler for notifications which requires cookie auth."""


class CookieAuthRepositoryRestHandler(CookieAuthHandlerMixin,
                                      RepositoryRestHandler):
    """A rest api handler for repositories which requires cookie auth."""


class SlaveRestHandler(ModelRestHandler):
    """A rest api handler for slaves."""

    def _query_has_pk(self):
        keys = self.query.keys()
        return 'id' in keys or 'name' in keys


class CookieAuthSlaveRestHandler(CookieAuthHandlerMixin, SlaveRestHandler):
    """A rest api handler for slaves which requires cookie auth."""


class StreamHandler(CookieAuthHandlerMixin, WebSocketHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action = None
        self.repo_id = None
        self.body = None

    def prepare(self):
        self._get_user()

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
                                                'repo_added',
                                                'buildset_started',
                                                'buildset_finished'],
                                'repo-buildsets': ['buildset_started',
                                                   'buildset_finished',
                                                   'buildset_added'],
                                'builds': ['build_started', 'build_finished',
                                           'build_added', 'step_started',
                                           'step_finished', 'build_cancelled'],
                                'buildset-info': ['build_started',
                                                  'build_finished',
                                                  'buildset_added',
                                                  'buildset_started',
                                                  'buildset_finished'],
                                'waterfall-info': ['buildset_added',
                                                   'build_started',
                                                   'build_finished',
                                                   'buildset_finished',
                                                   'step_started',
                                                   'step_finished'],
                                'step-output': ['step_output_info']}

    async def _get_repo_id(self):
        if 'repo_id' in self.request.arguments.keys():
            return self.request.arguments['repo_id'][0].decode()
        try:
            repo_name = self.request.arguments.get('repo_name')[0].decode()
        except TypeError:
            return

        repo = await Repository.get(self.user, repo_name_or_id=repo_name)
        return repo.id

    async def open(self, action):
        self.action = action
        self.body = self.action_messages[self.action]
        self.repo_id = await self._get_repo_id()
        r = await StreamConnector.plug(
            self.user, self.repo_id, self.body, self.receiver)
        return r

    def receiver(self, sender, **message):
        message_type = message.get('event_type')
        msg = 'message arrived: {}'.format(message_type)
        self.log(msg, level='debug')
        if message_type not in self.action_messages.get(self.action, []):
            msg = 'leaving receiver'
            self.log(msg, level='debug')
            return
        outfn = self.events.get(message_type, self._send_raw_info)
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

        commit_date = info.get('commit_date')
        if commit_date and is_datetime(commit_date):
            info['commit_date'] = format_datetime(string2datetime(commit_date))

        buildset = info.get('buildset')
        if buildset:
            self._format_info_dt(buildset)

    def _send_raw_info(self, info):
        self._format_info_dt(info)
        self.write2sock(info)

    def on_close(self):
        self.log('connection closed', level='debug')
        StreamConnector.unplug(self.user, self.repo_id, self.body,
                               self.receiver)

    def write2sock(self, body):
        try:
            self.write_message(body)
        except WebSocketError:
            tb = traceback.format_exc()
            self.log('WebSocketError: {}'.format(tb), level='debug')


class DashboardHandler(LoggedTemplateHandler):
    main_template = 'toxictheme/main.html'
    settings_template = 'toxictheme/settings.html'
    repo_settings_template = 'toxictheme/repo_settings.html'
    slave_settings_template = 'toxictheme/slave_settings.html'
    repository_template = 'toxictheme/repository.html'
    slave_template = 'toxictheme/slave.html'
    buildset_list_template = 'toxictheme/buildset_list.html'
    waterfall_template = 'toxictheme/waterfall.html'
    build_template = 'toxictheme/build.html'
    buildset_template = 'toxictheme/buildset.html'
    notifications_template = 'toxictheme/notifications.html'

    def _get_main_template(self):
        rendered = render_template(self.main_template,
                                   self.request, {})
        return rendered

    def _get_settings_template(self, settings_type):
        github_import_url = getattr(settings, 'GITHUB_IMPORT_URL', '#')
        rendered = render_template(self.settings_template,
                                   self.request,
                                   {'github_import_url': github_import_url,
                                    'settings_type': settings_type})
        return rendered

    def _get_settings_main_template(self, settings_type):
        if settings_type == 'repositories':
            github_import_url = getattr(settings, 'GITHUB_IMPORT_URL', '#')
            context = {'github_import_url': github_import_url}
            template = self.repo_settings_template

        elif settings_type == 'slaves':
            context = {}
            template = self.slave_settings_template

        else:
            raise BadSettingsType(settings_type)

        rendered = render_template(template, self.request, context)
        return rendered

    def _get_repository_template(self, full_name=''):
        rendered = render_template(self.repository_template, self.request,
                                   {'repo_full_name': full_name})
        return rendered

    def _get_slave_template(self, full_name=''):
        rendered = render_template(self.slave_template, self.request,
                                   {'slave_full_name': full_name})
        return rendered

    def _get_buildset_list_template(self, full_name):
        rendered = render_template(self.buildset_list_template, self.request,
                                   {'repo_full_name': full_name})
        return rendered

    def _get_waterfall_template(self, full_name):
        rendered = render_template(self.waterfall_template, self.request,
                                   {'repo_name': full_name})
        return rendered

    def _get_build_template(self, build_uuid):
        rendered = render_template(self.build_template, self.request,
                                   {'build_uuid': build_uuid})
        return rendered

    def _get_buildset_template(self, buildset_id, repo_id):
        rendered = render_template(self.buildset_template, self.request,
                                   {'buildset_id': buildset_id,
                                    'repo_id': repo_id})
        return rendered

    def _get_notifications_template(self, repo_name, repo_id):
        rendered = render_template(self.notifications_template, self.request,
                                   {'repo_full_name': repo_name,
                                    'repo_id': repo_id})
        return rendered

    @get('')
    def show_main(self):
        content = self._get_main_template()
        context = {'content': content}
        self.render_template(self.skeleton_template, context)

    @get('templates/main')
    def show_main_template(self):
        content = self._get_main_template()
        self.write(content)

    @get('settings/(slaves|repositories)')
    def show_settings(self, settings_type):
        settings_type = settings_type.decode()
        content = self._get_settings_template(settings_type)
        context = {'content': content}
        self.render_template(self.skeleton_template, context)

    @get('{}/'.format(FULL_NAME_REGEX))
    def show_repo_buildset_list(self, full_name):
        full_name = full_name.decode()
        content = self._get_buildset_list_template(full_name)
        context = {'content': content}
        self.render_template(self.skeleton_template, context)

    @get('buildset/([\d\w\-]+)')
    async def show_buildset_details(self, buildset_id):
        buildset_id = buildset_id.decode()
        buildset = await BuildSet.get(self.user, buildset_id)
        repo_id = buildset.repository.id
        content = self._get_buildset_template(buildset_id, repo_id)
        context = {'content': content}
        self.render_template(self.skeleton_template, context)

    @get('{}/waterfall'.format(FULL_NAME_REGEX))
    def show_repo_waterfall(self, full_name):
        full_name = full_name.decode()
        content = self._get_waterfall_template(full_name)
        context = {'content': content}
        self.render_template(self.skeleton_template, context)

    @get('{}/settings'.format(FULL_NAME_REGEX))
    def show_repository_details(self, full_name):
        full_name = full_name.decode()
        content = self._get_repository_template(full_name)
        context = {'content': content}
        self.render_template(self.skeleton_template, context)

    @get('{}/notifications'.format(FULL_NAME_REGEX))
    async def show_repository_notifications(self, full_name):
        full_name = full_name.decode()
        repo = await Repository.get(self.user, repo_name_or_id=full_name)
        content = self._get_notifications_template(full_name, str(repo.id))
        context = {'content': content}
        self.render_template(self.skeleton_template, context)

    @get('repository/add')
    def show_repo_add(self):
        full_name = ''
        content = self._get_repository_template(full_name)
        context = {'content': content}
        self.render_template(self.skeleton_template, context)

    @get('slave/add')
    @get('slave/{}'.format(FULL_NAME_REGEX))
    def show_slave_details(self, full_name=b''):
        full_name = full_name.decode()
        content = self._get_slave_template(full_name)
        context = {'content': content}
        self.render_template(self.skeleton_template, context)

    @get('build/([\d\w\-]+)')
    def show_build_details(self, build_uuid):
        build_uuid = build_uuid.decode()
        content = self._get_build_template(build_uuid)
        context = {'content': content}
        self.render_template(self.skeleton_template, context)

    @get('templates/repo-details')
    @get('templates/repo-details/{}'.format(FULL_NAME_REGEX))
    def show_repository_details_template(self, full_name=b''):
        full_name = full_name.decode()
        content = self._get_repository_template(full_name)
        self.write(content)

    @get('templates/repo-notifications/{}'.format(FULL_NAME_REGEX))
    async def show_repository_notifications_template(self, full_name):
        full_name = full_name.decode()
        repo = await Repository.get(self.user, repo_name_or_id=full_name)
        content = self._get_notifications_template(full_name, str(repo.id))
        self.write(content)

    @get('templates/slave-details')
    def show_slave_details_template(self):
        content = self._get_slave_template()
        self.write(content)

    @get('templates/settings/(slaves|repositories)')
    def show_settings_template(self, settings_type):
        settings_type = settings_type.decode()
        content = self._get_settings_template(settings_type)
        self.write(content)

    @get('templates/settings/main/(slaves|repositories)')
    def show_settings_main_template(self, settings_type):
        settings_type = settings_type.decode()
        content = self._get_settings_main_template(settings_type)
        self.write(content)

    @get('templates/buildset-list/{}'.format(FULL_NAME_REGEX))
    def show_repo_buildset_list_template(self, full_name):
        full_name = full_name.decode()
        content = self._get_buildset_list_template(full_name)
        self.write(content)

    @get('templates/build/([\d\w\-]+)')
    def show_build_template(self, build_uuid):
        build_uuid = build_uuid.decode()
        content = self._get_build_template(build_uuid)
        self.write(content)

    @get('templates/buildset/([\d\w\-]+)')
    async def show_buildset_template(self, buildset_id):
        buildset_id = buildset_id.decode()
        buildset = await BuildSet.get(self.user, buildset_id)
        repo_id = buildset.repository.id
        content = self._get_buildset_template(buildset_id, repo_id)
        self.write(content)

    @get('templates/waterfall/{}'.format(FULL_NAME_REGEX))
    def show_repo_waterfall_template(self, full_name):
        full_name = full_name.decode()
        content = self._get_waterfall_template(full_name)
        self.write(content)


dashboard = URLSpec('/(.*)$', DashboardHandler)

login = URLSpec('/(login|logout)', LoginHandler)
register = URLSpec('/(register)', RegisterHandler)

app = PyroApplication([register, login, dashboard])

static_app = StaticApplication()

repo_kwargs = {'model': Repository}
repo_api_url = URLSpec('/api/repo/(.*)', CookieAuthRepositoryRestHandler,
                       repo_kwargs)

websocket = URLSpec('/api/socks/(.*)', StreamHandler)
slave_kwargs = {'model': Slave}
slave_api_url = URLSpec('/api/slave/(.*)', CookieAuthSlaveRestHandler,
                        slave_kwargs)
notifications_api_url = URLSpec('/api/notification/(.*)$',
                                CookieAuthNotificationRestHandler)
user_add_api = URLSpec('/api/user/(.*)$',
                       UserAddRestHandler, {'model': User})

buildset_api = URLSpec('/api/buildset/(.*)$',
                       CookieAuthBuildSetHandler, {'model': BuildSet})

build_api = URLSpec('/api/build/(.*)$',
                    CookieAuthBuildHandler, {'model': Build})

waterfall_api = URLSpec('/api/waterfall/(.*)$',
                        CookieAuthWaterfallHandler,
                        {'model': BuildSet})

api_app = PyroApplication(
    [websocket, repo_api_url, slave_api_url, notifications_api_url,
     buildset_api, user_add_api, waterfall_api, build_api])
