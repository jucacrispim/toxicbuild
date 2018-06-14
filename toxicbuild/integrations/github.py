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

from asyncio import ensure_future, gather
from collections import defaultdict
from datetime import timedelta
import hashlib
import hmac
import json
import jwt
from mongomotor import Document, EmbeddedDocument
from mongomotor.fields import (StringField, DateTimeField, IntField,
                               ReferenceField, EmbeddedDocumentListField)
from toxicbuild.core import requests
from toxicbuild.core.utils import (string2datetime, now, localtime2utc,
                                   LoggerMixin, utc2localtime,
                                   datetime2string)
from toxicbuild.integrations import settings
from toxicbuild.master.build import BuildSet
from toxicbuild.master.plugins import MasterPlugin
from toxicbuild.master.repository import Repository, RepositoryBranch
from toxicbuild.master.slave import Slave
from toxicbuild.master.users import User
from toxicbuild.integrations.exceptions import (BadRequestToGithubAPI,
                                                BadRepository, BadSignature)

__doc__ = """This module implements the integration with Github. It is
a `GithubApp <https://developer.github.com/apps/>`_  that reacts to events
sent by github webhooks and informs about build statuses using
`checks <https://developer.github.com/v3/checks/>`_.

Usage:
``````

.. code-block:: python

    # When a new installation is created on github we must create a
    # installation here.

    install = await GithubInstallation.create(github_install_id, user)

    # When a push happens or a pull request is created or synchronized
    # we update the code here.

    await install.update_repository(github_repo_id)

    # When a check is rerequested we request a build
    await install.repo_request_build(github_repo_id, branch, named_tree)

For information on how to setup the integration, see
:ref:`github-integration-config`"""


class GithubApp(LoggerMixin, Document):
    """A GitHub App. Only one app per ToxicBuild installation."""

    private_key = StringField(required=True)
    """The private key you generated in github."""

    app_id = IntField(required=True)
    """The id of the app in github."""

    jwt_expires = DateTimeField()
    """When auth token for the github api. expires. It must be in UTC"""

    jwt_token = StringField()
    """The auth token for the github api."""

    webhook_token = StringField()
    """The token used to sign the incomming request in the webhook. This must
    be set in the github app creation page."""

    @classmethod
    async def get_app(cls):
        """Returns the app instance. If it does not exist, create it."""

        if await cls.app_exists():
            return await cls.objects.first()

        with open(settings.GITHUB_PRIVATE_KEY) as fd:
            pk = fd.read()

        webhook_token = settings.GITHUB_WEBHOOK_TOKEN
        app = cls(private_key=pk, webhook_token=webhook_token)
        app.app_id = settings.GITHUB_APP_ID
        await app.save()
        return app

    @classmethod
    async def app_exists(cls):
        """Informs if a github app already exists in the system."""

        app = await cls.objects.first()
        return bool(app)

    def validate_token(self, signature, data):
        """Validates the incomming data in the webhook, sent by github."""

        sig = 'sha1=' + hmac.new(self.webhook_token.encode(), data,
                                 digestmod=hashlib.sha1).hexdigest()
        sig = sig.encode()
        if isinstance(signature, str):
            signature = signature.encode()

        eq = hmac.compare_digest(sig, signature)
        if not eq:
            raise BadSignature
        return True

    async def is_expired(self):
        """Informs if the jwt token is expired."""

        if self.jwt_expires and utc2localtime(self.jwt_expires) < now():
            return True
        return False

    async def get_jwt_token(self):
        """Returns the jwt token for authentication on the github api."""

        if self.jwt_token and not await self.is_expired():
            return self.jwt_token
        return await self.create_token()

    async def set_jwt_token(self, jwt_token):
        """Sets the jwt auth token."""

        self.jwt_token = jwt_token
        await self.save()

    async def set_expire_time(self, exp_time):
        """Sets the expire time for the jwt token"""
        self.jwt_expires = exp_time
        await self.save()

    def get_api_url(self):
        """Returns the url for the github app api."""

        return settings.GITHUB_API_URL + 'app'

    async def _create_jwt(self):
        exp_time = 10 * 59
        n = now()
        dt_expires = localtime2utc(n + timedelta(seconds=exp_time))
        ts_now = int(localtime2utc(n).timestamp())
        payload = {'iat': ts_now,
                   'exp': ts_now + exp_time,
                   'iss': self.app_id}

        self.log('creating jwt_token with payload {}'.format(payload),
                 level='debug')
        jwt_token = jwt.encode(payload, self.private_key, "RS256")
        await self.set_expire_time(dt_expires)
        await self.set_jwt_token(jwt_token.decode())
        return jwt_token.decode()

    async def create_token(self):
        """Creates a new token for the github api."""

        myjwt = await self._create_jwt()
        header = {'Authorization': 'Bearer {}'.format(myjwt),
                  'Accept': 'application/vnd.github.machine-man-preview+json'}
        await requests.post(self.get_api_url(), headers=header)
        return myjwt

    @classmethod
    async def create_installation_token(cls, installation):
        """Creates a auth token for a given github installation

        :param installation: An instance of
          :class:`~toxicbuild.master.integrations.github.GitHubInstallation`
        """

        app = await cls.get_app()
        msg = 'Creating installation token for {}'.format(installation.id)
        app.log(msg, level='debug')

        myjwt = await app.get_jwt_token()
        header = {'Authorization': 'Bearer {}'.format(myjwt),
                  'Accept': 'application/vnd.github.machine-man-preview+json'}

        ret = await requests.post(installation.auth_token_url, headers=header)

        if ret.status != 201:
            raise BadRequestToGithubAPI(ret.status, ret.text)

        ret = ret.json()
        installation.auth_token = ret['token']
        expires_at = ret['expires_at'].replace('Z', '+0000')
        installation.expires = string2datetime(expires_at,
                                               dtformat="%Y-%m-%dT%H:%M:%S%z")
        await installation.save()
        return installation


GithubApp.ensure_indexes()


class GithubInstallationRepository(LoggerMixin, EmbeddedDocument):
    """External (github) information about a repository."""

    github_id = IntField(required=True)
    """The id of the repository on github."""

    repository_id = StringField(required=True)
    """The id of the repository on ToxicBuild."""

    full_name = StringField(required=True)
    """Full name of the repository on github."""


class GithubInstallation(LoggerMixin, Document):
    """An installation of the GitHub App. Installations have access to
    repositories and events."""

    app = GithubApp

    user = ReferenceField(User, required=True)
    """A reference to the :class:`~toxicbuild.master.users.User` that owns
      the installation"""

    # the id of the github app installation
    github_id = IntField(required=True, unique=True)
    auth_token = StringField()
    expires = DateTimeField()
    repositories = EmbeddedDocumentListField(GithubInstallationRepository)

    @classmethod
    async def create(cls, github_id, user):
        """Creates a new github app installation. Imports the repositories
        available to the installation.

        :param github_id: The installation id on github
        :param user: The user that owns the installation."""

        if await cls.objects.filter(github_id=github_id).first():
            msg = 'Installation {} already exists'.format(github_id)
            cls.log_cls(msg, level='error')
            return

        msg = 'Creating installation for github_id {}'.format(github_id)
        cls().log(msg, level='debug')
        installation = cls(github_id=github_id, user=user)
        await installation.save()
        await installation.import_repositories()
        return installation

    async def _get_repo_by_github_id(self, github_repo_id):
        for repo in self.repositories:
            if repo.github_id == github_repo_id:
                repo_inst = await Repository.objects.get(id=repo.repository_id)
                return repo_inst

        raise BadRepository('Github repository {} does not exist here.'.format(
            github_repo_id))

    async def update_repository(self, github_repo_id, repo_branches=None,
                                external=None, wait_for_lock=False):
        """Updates a repository code.

        :param github_repo_id: The id of the repository on github.
        :param repo_branches: Param to be passed to
          :meth:`~toxicbuild.master.repository.Repository.update_code`.
        :param external: Information about an external repository.
        :param wait_for_lock: Indicates if we should wait for the release of
          the lock or simply return if we cannot get a lock.
        """

        repo = await self._get_repo_by_github_id(github_repo_id)
        url = await self._get_auth_url(repo.url)
        if repo.fetch_url != url:
            repo.fetch_url = url
            await repo.save()
        await repo.update_code(repo_branches=repo_branches, external=external,
                               wait_for_lock=wait_for_lock)

    @property
    def auth_token_url(self):
        """URL used to retrieve an access token for this installation."""

        url = settings.GITHUB_API_URL
        return url + 'installations/{}/access_tokens'.format(self.github_id)

    @property
    def token_is_expired(self):
        """Informs if the installation auth token is expired."""
        n = now()
        if n > utc2localtime(self.expires):
            return True
        return False

    async def import_repositories(self):
        """Imports all repositories available to the installation."""

        msg = 'Importing repos for {}'.format(self.github_id)
        self.log(msg, level='debug')
        repos = []
        for repo_info in await self.list_repos():
            repo = await self.import_repository(repo_info, clone=False)
            repos.append(repo)

        for chunk in self._get_import_chunks(repos):
            tasks = []
            for repo in chunk:
                t = ensure_future(repo.update_code())
                tasks.append(t)

            await gather(*tasks)

        return repos

    def _get_import_chunks(self, repos):

        try:
            parallel_imports = settings.PARALLEL_IMPORTS
        except AttributeError:
            parallel_imports = None

        if not parallel_imports:
            yield repos
            return

        for i in range(0, len(repos), parallel_imports):
            yield repos[i:i + parallel_imports]

    async def import_repository(self, repo_info, clone=True):
        """Imports a repository from GitHub.

        :param repo_info: A dictionary with the repository information."""

        msg = 'Importing repo {}'.format(repo_info['clone_url'])
        self.log(msg, level='debug')

        branches = [
            RepositoryBranch(name='master', notify_only_latest=True),
            RepositoryBranch(name='feature-*', notify_only_latest=True),
            RepositoryBranch(name='bug-*', notify_only_latest=True)]
        slaves = await Slave.list_for_user(await self.user)
        slaves = await slaves.to_list()
        # update_seconds=0 because it will not be scheduled in fact.
        # note the schedule_poller=False.
        # What triggers an update code is a message from github in the
        # webhook receiver.
        user = await self.user
        fetch_url = await self._get_auth_url(repo_info['clone_url'])
        repo = await Repository.create(name=repo_info['name'],
                                       url=repo_info['clone_url'],
                                       owner=user,
                                       fetch_url=fetch_url,
                                       update_seconds=0,
                                       vcs_type='git',
                                       schedule_poller=False,
                                       parallel_builds=1,
                                       branches=branches,
                                       slaves=slaves)
        gh_repo = GithubInstallationRepository(
            github_id=repo_info['id'],
            repository_id=str(repo.id),
            full_name=repo_info['full_name'])
        self.repositories.append(gh_repo)
        await self.save()
        await repo.enable_plugin('github-check-run', installation=self)

        if clone:
            await repo.update_code()
        return repo

    async def remove_repository(self, github_repo_id):
        """Removes a repository from the system.

        :param github_repo_id: The id of the repository in github."""

        repo = await self._get_repo_by_github_id(github_repo_id)
        await repo.request_removal()

    async def _get_header(
            self, accept='application/vnd.github.machine-man-preview+json'):

        if not self.auth_token or self.token_is_expired:
            await self.app.create_installation_token(self)

        header = {'Authorization': 'token {}'.format(self.auth_token),
                  'Accept': accept}
        return header

    async def _get_auth_url(self, url):
        """Returns the repo url with the acces token for authentication.

        :param url: The https repo url"""

        if not self.auth_token or self.token_is_expired:
            await self.app.create_installation_token(self)

        new_url = url.replace('https://', '')
        new_url = '{}x-access-token:{}@{}'.format('https://',
                                                  self.auth_token, new_url)
        return new_url

    async def list_repos(self):
        """Lists all respositories available to an installation.
        Returns a list of dictionaries with repositories' information"""

        header = await self._get_header()
        url = settings.GITHUB_API_URL + 'installation/repositories'
        ret = await requests.get(url, headers=header)
        if ret.status != 200:
            raise BadRequestToGithubAPI(ret.status, ret.text, url)
        ret = ret.json()
        return ret['repositories']

    async def repo_request_build(self, github_repo_id, branch, named_tree):
        """Requests a new build.

        :param github_repo_id: The id of the repository in github.
        :param branch: The name of the branch to build.
        :param named_tree: The named tree to build."""

        repo = await self._get_repo_by_github_id(github_repo_id)
        await repo.request_build(branch, named_tree=named_tree)

    async def delete(self, *args, **kwargs):
        """Deletes the installation from the system"""

        for install_repo in self.repositories:
            try:
                repo = await Repository.objects.get(
                    id=install_repo.repository_id)
            except Repository.DoesNotExist:
                continue
            await repo.request_removal()

        r = await super().delete(*args, **kwargs)
        return r

    async def get_repo(self, repo_full_name):
        """Get the repository (if available to the installation) from
        the github api.

        :param github_repo_id: The full name of the repository on github."""

        header = await self._get_header()
        url = settings.GITHUB_API_URL + 'repos/{}'.format(repo_full_name)
        ret = await requests.get(url, headers=header)
        if ret.status != 200:
            raise BadRequestToGithubAPI(ret.status, ret.text, url)
        return ret.json()


GithubInstallation.ensure_indexes()


class GithubCheckRun(MasterPlugin):
    """A plugin that creates a check run reacting to a buildset that
    was added, started or finished."""

    type = 'notification'
    """The type of the plugin. This is a notification plugin."""

    name = 'github-check-run'
    """The name of the plugin"""

    events = ['buildset-added', 'buildset-started', 'buildset-finished']
    """Events that trigger the plugin."""

    no_list = True

    run_name = 'ToxicBuild CI'
    """The name displayed on github."""

    installation = ReferenceField(GithubInstallation)
    """The :class:`~toxicbuild.integrations.github.GithubInstallation`
      that owns the plugin"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sender = None

    async def _get_repo_full_name(self, repo):
        full_name = None

        installation = await self.installation

        for inst_repo in installation.repositories:
            if str(repo.id) == inst_repo.repository_id:
                full_name = inst_repo.full_name
                break

        if not full_name:
            raise BadRepository

        return full_name

    async def run(self, sender, info):
        """Runs the plugin.

        :param sender: The :class:`~toxicbuild.master.repository.Repository`
          that is running the plugin.
        :param info: The information that is being sent."""

        self.log('Sending notification to github for buildset {}'.format(
            info['id']), level='info')
        self.log('Info is: {}'.format(info), level='debug')

        self.sender = sender

        status = info['status']
        status_tb = defaultdict(lambda: 'completed')
        status_tb.update({'pending': 'queued',
                          'running': 'in_progress'})
        run_status = status_tb[status]

        conclusion_tb = defaultdict(lambda: 'failure')
        conclusion_tb.update({'success': 'success'})
        conclusion = conclusion_tb[status]

        buildset = await BuildSet.objects.get(id=info['id'])
        await self._send_message(buildset, run_status, conclusion)

    def _get_payload(self, buildset, run_status, conclusion):

        payload = {'name': self.run_name,
                   'head_branch': buildset.branch,
                   'head_sha': buildset.commit,
                   'status': run_status}

        if buildset.started:
            started_at = datetime2string(buildset.started,
                                         dtformat="%Y-%m-%dT%H:%M:%S%z")
            started_at = started_at.replace('+0000', 'Z')
            payload.update({'started_at': started_at})

        if run_status == 'completed':
            completed_at = datetime2string(buildset.finished,
                                           dtformat="%Y-%m-%dT%H:%M:%S%z")
            completed_at = completed_at.replace('+0000', 'Z')
            payload.update(
                {'completed_at': completed_at,
                 'conclusion': conclusion})

        return payload

    async def _send_message(self, buildset, run_status, conclusion):
        self.log('sending check run to github', level='debug')
        repo = await buildset.repository
        full_name = await self._get_repo_full_name(repo)
        install = await self.installation
        url = settings.GITHUB_API_URL + '/repos/{}/check-runs'.format(
            full_name)
        payload = self._get_payload(buildset, run_status, conclusion)
        header = await install._get_header(
            accept='application/vnd.github.antiope-preview+json')
        data = json.dumps(payload)
        r = await requests.post(url, headers=header, data=data)
        self.log(r.text, level='debug')
