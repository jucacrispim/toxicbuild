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
from toxicbuild.integrations.github import (GithubInstallation, GithubApp,
                                            BadSignature)


class GithubWebhookReceiver(LoggerMixin, BasePyroHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_type = None
        self.body = None
        handle_repo_removed = self._handle_install_repo_removed
        handle_repo_added = self._handle_install_repo_added
        self.events = {
            'ping': self._handle_ping,
            'push': self._handle_push,
            'repository-create': self._handle_install_repo_added,
            'pull_request-opened': self._handle_pull_request_opened,
            'pull_request-synchronize': self._handle_pull_request_opened,
            'check_run-rerequested': self._handle_check_run_rerequested,
            'installation-deleted': self._handle_install_deleted,
            'installation_repositories-removed': handle_repo_removed,
            'installation_repositories-added': handle_repo_added}

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
                settings.TOXICUI_LOGIN_URL, self.request.full_url())
        else:
            githubapp_id = self.params.get('installation_id')
            if not githubapp_id:
                raise HTTPError(400)
            ensure_future(GithubInstallation.create(
                user, github_id=githubapp_id))
            url = settings.TOXICUI_URL

        return self.redirect(url)

    async def _handle_ping(self):
        msg = 'Ping received. App id {}\n'.format(self.body['app_id'])
        msg += 'zen: {}'.format(self.body['zen'])
        self.log(msg, level='debug')
        return 'Got it.'

    async def _get_install(self):
        install_id = self.body['installation']['id']
        install = await GithubInstallation.objects.get(github_id=install_id)
        return install

    async def _handle_push(self):
        repo_github_id = self.body['repository']['id']
        install = await self._get_install()
        ensure_future(install.update_repository(repo_github_id))
        return 'updating repo'

    async def _handle_install_repo_added(self):
        install = await self._get_install()
        tasks = []
        for repo_info in self.body['repositories_added']:
            t = ensure_future(self._get_and_import_repo(
                install, repo_info['full_name']))
            tasks.append(t)

        return tasks

    async def _get_and_import_repo(self, install, repo_full_name):
        repo_full_info = await install.get_repo(repo_full_name)
        await install.import_repository(repo_full_info)

    async def _handle_install_repo_removed(self):
        install = await self._get_install()
        for repo_info in self.body['repositories_removed']:
            ensure_future(install.remove_repository(repo_info['id']))

    async def _handle_pull_request_opened(self):
        # in fact, hand pull requests opened and synchronized
        install = await self._get_install()
        head = self.body['pull_request']['head']
        head_id = head['repo']['id']
        base = self.body['pull_request']['base']
        base_id = base['repo']['id']
        base_branch = base['ref']
        head_branch = head['ref']
        repo_branches = {head_branch: {'notify_only_latest': True,
                                       'builders_fallback': base_branch}}
        if not head_id == base_id:
            external = {'url': head['clone_url'],
                        'name': head['label'],
                        'branch': head['ref'],
                        'into': head['label']}
            await install.update_repository(base_id, external=external,
                                            repo_branches=repo_branches,
                                            wait_for_lock=True)
        else:
            await install.update_repository(base_id,
                                            repo_branches=repo_branches,
                                            wait_for_lock=True)

    async def _handle_check_run_rerequested(self):
        install = await self._get_install()
        check_suite = self.body['check_run']['check_suite']
        repo_id = self.body['repository']['id']
        branch = check_suite['head_branch']
        named_tree = check_suite['head_sha']
        ensure_future(install.repo_request_build(repo_id, branch, named_tree))

    async def _handle_install_deleted(self):
        install = await self._get_install()
        await install.delete()

    @post('webhooks')
    async def receive_webhook(self):

        await self._validate()

        async def default_call():
            raise HTTPError(400, 'What was that? {}'.format(self.event_type))

        call = self.events.get(self.event_type, default_call)
        self.log('event_type {} received'.format(self.event_type))
        await call()
        msg = '{} handled successfully'.format(self.event_type)
        return {'code': 200, 'msg': msg}

    async def _validate(self):
        signature = self.request.headers.get('X-Hub-Signature')
        app = await GithubApp.get_app()
        try:
            app.validate_token(signature, self.request.body)
        except BadSignature:
            raise HTTPError(403, 'Bad signature')

    def _parse_body(self):
        if self.request.body:
            self.body = json.loads(self.request.body.decode())

    def _check_event_type(self):
        event_type = self.request.headers.get('X-GitHub-Event')

        if not event_type:
            msg = 'No event type\n{}'.format(self.body)
            self.log(msg, level='warning')

        action = self.body.get('action') if self.body else None
        if action:
            event_type = '{}-{}'.format(event_type, action)
        return event_type


url = URLSpec('/github/(.*)', GithubWebhookReceiver)
app = PyroApplication([url])
