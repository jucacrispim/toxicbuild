# -*- coding: utf-8 -*-

# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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

from asyncio import ensure_future
import base64
import json
from pyrocumulus.web.applications import PyroApplication
from pyrocumulus.web.decorators import post, get
from pyrocumulus.web.handlers import BasePyroHandler
from pyrocumulus.web.urlmappers import URLSpec
from tornado import gen
from tornado.web import HTTPError
from toxicbuild.core.utils import LoggerMixin
from toxicbuild.master.users import User
from toxicbuild.integrations import settings
from toxicbuild.integrations.github import GithubInstallation


class GithubWebhookReceiver(LoggerMixin, BasePyroHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_type = None
        self.body = None
        self.events = {'ping': self._handle_ping,
                       'push': self._handle_push,
                       'repository-create': self._handle_install_repo_added}

    async def _get_user_from_cookie(self):
        cookie = self.get_secure_cookie(settings.TOXICUI_COOKIE)
        if not cookie:
            self.log('No cookie found.', level='debug')
            return

        user_dict = json.loads(base64.decodebytes(cookie).decode('utf-8'))
        user = await User.objects.get(id=user_dict['id'])
        return user

    def prepare(self):
        super().prepare()
        self._parse_body()
        self.event_type = self._check_event_type()

    @get('hello')
    def hello(self):
        return {'code': 200, 'msg': 'Hi there!'}

    @get('auth')
    @gen.coroutine
    def authenticate(self):
        user = yield from self._get_user_from_cookie()
        if not user:
            url = '{}?redirect={}'.format(
                settings.TOXICUI_LOGIN_URL, self.request.get_full_url())
        else:
            githubapp_id = self.params.get('installation_id')
            if not githubapp_id:
                raise HTTPError(400)
            ensure_future(GithubInstallation.create(githubapp_id, user))
            url = settings.TOXICUI_URL

        return self.redirect(url)

    async def _handle_ping(self):
        msg = 'Ping received. App id {}\n'.format(self.body['app_id'])
        msg += 'zen: {}'.format(self.body['zen'])
        self.log(msg, level='debug')
        return 'Got it.'

    async def _handle_push(self):
        install_id = self.body['installation']['id']
        repo_github_id = self.body['repository']['id']
        install = await GithubInstallation.objects.get(github_id=install_id)
        ensure_future(install.update_repository(repo_github_id))
        return 'updating repo'

    async def _handle_install_repo_added(self):
        install_id = self.body['installation']['id']
        install = await GithubInstallation.objects.get(github_id=install_id)
        for repo_info in self.body['repositories_added']:
            ensure_future(install.import_repository(repo_info))

    async def _handle_install_repo_removed(self):
        install_id = self.body['installation']['id']
        install = await GithubInstallation.objects.get(github_id=install_id)
        for repo_info in self.body['repositories_removed']:
            ensure_future(install.remove_repository(repo_info['id']))

    @post('webhooks')
    async def receive_webhook(self):

        async def default_call():
            raise HTTPError(400)

        call = self.events.get(self.event_type, default_call)
        msg = await call()
        return {'code': 200, 'msg': msg}

    def _parse_body(self):
        if self.request.body:
            self.body = json.loads(self.request.body.decode())

    def _check_event_type(self):
        event_type = self.request.headers.get('X-GitHub-Event')

        if not event_type:
            msg = 'No event type\n{}'.format(self.body)
            self.log(msg, level='warning')

        action = self.body.get('action')
        if action:
            event_type = '{}-{}'.format(event_type, action)
        return event_type


url = URLSpec('/github/(.*)', GithubWebhookReceiver)
app = PyroApplication([url])
