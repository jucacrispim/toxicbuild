# -*- coding: utf-8 -*-

# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

from asyncio import ensure_future
import base64
import json
from pyrocumulus.web.applications import PyroApplication
from pyrocumulus.web.decorators import post, get
from pyrocumulus.web.handlers import BasePyroHandler, PyroRequest
from pyrocumulus.web.urlmappers import URLSpec
from tornado import gen
from tornado.web import HTTPError
from toxicbuild.core.utils import LoggerMixin, validate_string
from toxicbuild.master.users import User
from toxicbuild.integrations import settings
from toxicbuild.integrations.github import (GithubInstallation, GithubApp,
                                            BadSignature)
from toxicbuild.integrations.gitlab import GitLabInstallation


class BaseWebhookReceiver(LoggerMixin, BasePyroHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_type = None
        self.params = None
        self.body = None
        self.events = {}

    async def _get_user_from_cookie(self):
        cookie = self.get_secure_cookie(settings.TOXICUI_COOKIE)
        if not cookie:
            self.log('No cookie found.', level='debug')
            return

        user_dict = json.loads(base64.decodebytes(cookie).decode('utf-8'))
        user = await User.objects.get(id=user_dict['id'])
        return user

    def _parse_body(self):
        if self.request.body:
            self.body = json.loads(self.request.body.decode())

    def check_event_type(self):
        raise NotImplementedError

    async def validate_webhook(self):
        raise NotImplementedError

    async def get_install(self):
        raise NotImplementedError

    def prepare(self):
        self.params = PyroRequest(self.request.arguments)
        self._parse_body()
        self.event_type = self.check_event_type()

    @get('hello')
    def hello(self):
        return {'code': 200, 'msg': 'Hi there!'}

    @post('webhooks')
    async def receive_webhook(self):

        await self.validate_webhook()

        async def default_call():
            raise HTTPError(400, 'What was that? {}'.format(self.event_type))

        call = self.events.get(self.event_type, default_call)
        self.log('event_type {} received'.format(self.event_type))
        await call()
        msg = '{} handled successfully'.format(self.event_type)
        return {'code': 200, 'msg': msg}

    def create_installation(self, user):
        raise NotImplementedError

    def get_repo_external_id(self):
        raise NotImplementedError

    async def handle_push(self):
        external_id = self.get_repo_external_id()
        install = await self.get_install()
        ensure_future(install.update_repository(external_id))
        return 'updating repo'

    def get_pull_request_source(self):
        raise NotImplementedError

    def get_pull_request_target(self):
        raise NotImplementedError

    async def handle_pull_request(self):
        install = await self.get_install()
        source = self.get_pull_request_source()
        target = self.get_pull_request_target()

        repo_branches = {source['branch']: {
            'notify_only_latest': True,
            'builders_fallback': target['branch']}
        }
        if source['id'] != target['id']:
            external = {'url': source['url'],
                        'name': source['name'],
                        'branch': source['branch'],
                        'into': target['branch']}

            await install.update_repository(target['id'], external=external,
                                            repo_branches=repo_branches,
                                            wait_for_lock=True)
        else:
            await install.update_repository(target['id'],
                                            repo_branches=repo_branches,
                                            wait_for_lock=True)

    @get('setup')
    @gen.coroutine
    def setup(self):
        user = yield from self._get_user_from_cookie()
        if not user:
            url = '{}?redirect={}'.format(
                settings.TOXICUI_LOGIN_URL, self.request.full_url())
        else:
            self.create_installation(user)
            url = settings.TOXICUI_URL

        return self.redirect(url)


class GithubWebhookReceiver(BaseWebhookReceiver):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        handle_repo_removed = self._handle_install_repo_removed
        handle_repo_added = self._handle_install_repo_added
        self.events = {
            'ping': self._handle_ping,
            'push': self.handle_push,
            'repository-create': self._handle_install_repo_added,
            'pull_request-opened': self.handle_pull_request,
            'pull_request-synchronize': self.handle_pull_request,
            'check_run-rerequested': self._handle_check_run_rerequested,
            'installation-deleted': self._handle_install_deleted,
            'installation_repositories-removed': handle_repo_removed,
            'installation_repositories-added': handle_repo_added}

    def create_installation(self, user):
        githubapp_id = self.params.get('installation_id')
        if not githubapp_id:
            raise HTTPError(400)

        ensure_future(GithubInstallation.create(
            user, github_id=githubapp_id))

    async def _handle_ping(self):  # pragma no cover
        msg = 'Ping received. App id {}\n'.format(self.body['app_id'])
        msg += 'zen: {}'.format(self.body['zen'])
        self.log(msg, level='debug')
        return 'Got it.'

    async def get_install(self):
        install_id = self.body['installation']['id']
        install = await GithubInstallation.objects.get(github_id=install_id)
        return install

    def get_repo_external_id(self):
        repo_github_id = self.body['repository']['id']
        return repo_github_id

    async def _handle_install_repo_added(self):
        install = await self.get_install()
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
        install = await self.get_install()
        for repo_info in self.body['repositories_removed']:
            ensure_future(install.remove_repository(repo_info['id']))

    def get_pull_request_source(self):
        head = self.body['pull_request']['head']
        source = {'id': head['repo']['id'],
                  'url': head['clone_url'],
                  'name': head['label'],
                  'branch': head['ref']}
        return source

    def get_pull_request_target(self):
        base = self.body['pull_request']['base']
        source = {'id': base['repo']['id'],
                  'branch': base['ref']}
        return source

    async def _handle_check_run_rerequested(self):
        install = await self.get_install()
        check_suite = self.body['check_run']['check_suite']
        repo_id = self.body['repository']['id']
        branch = check_suite['head_branch']
        named_tree = check_suite['head_sha']
        ensure_future(install.repo_request_build(repo_id, branch, named_tree))

    async def _handle_install_deleted(self):
        install = await self.get_install()
        await install.delete()

    async def validate_webhook(self):
        signature = self.request.headers.get('X-Hub-Signature')
        app = await GithubApp.get_app()
        try:
            app.validate_token(signature, self.request.body)
        except BadSignature:
            raise HTTPError(403, 'Bad signature')

    def check_event_type(self):
        event_type = self.request.headers.get('X-GitHub-Event')

        if not event_type:
            msg = 'No event type\n{}'.format(self.body)
            self.log(msg, level='warning')

        action = self.body.get('action') if self.body else None
        if action:
            event_type = '{}-{}'.format(event_type, action)
        return event_type


class GitlabWebhookReceiver(BaseWebhookReceiver):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events = {'push': self.handle_push,
                       'merge_request': self.handle_pull_request}

    def check_event_type(self):
        body = self.body or {}
        return body.get('object_kind')

    def state_is_valid(self):
        """Checks if the state hash sent by gitlab is valid.
        """

        state = self.params.get('state')
        if not state:
            raise HTTPError(400)

        secret = settings.TORNADO_OPTS['cookie_secret']

        return validate_string(state, secret)

    def create_installation(self, user):
        code = self.params.get('code')
        if not code:
            raise HTTPError(400)

        if not self.state_is_valid():
            raise HTTPError(400)

        ensure_future(GitLabInstallation.create(user, code=code))

    async def get_install(self):
        install_id = self.params.get('installation_id')
        install = await GitLabInstallation.objects.get(id=install_id)
        return install

    def get_repo_external_id(self):
        return self.body['project']['id']

    async def validate_webhook(self):
        secret = self.request.headers.get('X-Gitlab-Token')

        if secret != settings.GITLAB_WEBHOOK_TOKEN:
            raise HTTPError(403)
        return True

    def get_pull_request_source(self):
        attrs = self.body['object_attributes']
        return {'name': attrs['source']['name'],
                'id': attrs['source_project_id'],
                'branch': attrs['source_branch'],
                'url': attrs['source']['git_http_url']}

    def get_pull_request_target(self):
        attrs = self.body['object_attributes']
        return {'name': attrs['target']['name'],
                'id': attrs['target_project_id'],
                'branch': attrs['target_branch'],
                'url': attrs['target']['git_http_url']}


gh_url = URLSpec('/github/(.*)', GithubWebhookReceiver)
gl_url = URLSpec('/gitlab/(.*)', GitlabWebhookReceiver)
app = PyroApplication([gh_url, gl_url])
