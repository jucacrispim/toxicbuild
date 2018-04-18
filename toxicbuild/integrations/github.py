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
from datetime import timedelta
import time
import jwt
from mongomotor import Document
from mongomotor.fields import (StringField, DateTimeField, IntField,
                               ReferenceField, DictField)
from toxicbuild.core import requests
from toxicbuild.core.utils import (string2datetime, now, localtime2utc,
                                   LoggerMixin, utc2localtime)
from toxicbuild.integrations import settings
from toxicbuild.master.users import User
from toxicbuild.master.repository import Repository, RepositoryBranch
from toxicbuild.master.slave import Slave
from toxicbuild.integrations.exceptions import (AppDoesNotExist,
                                                BadRequestToGithubAPI)


class GithubApp(LoggerMixin, Document):
    """A GitHub App. Only one app per ToxicBuild installation."""

    private_key = settings.GITHUB_PRIVATE_KEY
    app_id = settings.GITHUB_APP_ID
    jwt_expires = DateTimeField()
    jwt_token = StringField()

    @classmethod
    async def get_app(cls):
        if await cls.app_exists():
            return await cls.objects.first()
        app = cls()
        await app.save()
        return app

    @classmethod
    async def app_exists(cls):
        app = await cls.objects.first()
        return bool(app)

    @classmethod
    async def is_expired(cls):
        app = await cls.get_app()
        if app.jwt_expires and utc2localtime(app.jwt_expires) < now():
            return True
        return False

    @classmethod
    async def get_jwt_token(cls):
        app = await cls.get_app()
        if app.jwt_token and not await cls.is_expired():
            return app.jwt_token
        return await cls.create_token()

    @classmethod
    async def set_jwt_token(cls, jwt_token):
        app = await cls.get_app()
        app.jwt_token = jwt_token
        await app.save()

    @classmethod
    async def set_expire_time(cls, exp_time):
        app = await cls.get_app()
        app.jwt_expires = exp_time
        await app.save()

    @classmethod
    def get_api_url(cls):
        return 'https://api.github.com/app'

    @classmethod
    async def _create_jwt(cls):
        exp_time = 10 * 60
        dt_expires = localtime2utc(now() + timedelta(seconds=exp_time))
        ts_now = int(now().timestamp())
        payload = {'iat': ts_now,
                   'exp': ts_now + exp_time,
                   'iss': cls.app_id}

        with open(cls.private_key) as fd:
            pk = fd.read()

        cls().log('creating jwt_token with payload {}'.format(payload))
        jwt_token = jwt.encode(payload, pk, "RS256")
        await cls.set_expire_time(dt_expires)
        await cls.set_jwt_token(jwt_token.decode())
        return jwt_token.decode()

    @classmethod
    async def create_token(cls):
        myjwt = await cls._create_jwt()
        header = {'Authorization': 'Bearer {}'.format(myjwt),
                  'Accept': 'application/vnd.github.machine-man-preview+json'}
        await requests.post(cls.get_api_url(), headers=header)
        return myjwt

    @classmethod
    async def create_installation_token(cls, installation):
        """Creates a auth token for a given github installation

        :param installation: An instance of
        :class:`~toxicbuild.master.integrations.github.GitHubInstallation`"""

        msg = 'Creating installation token for {}'.format(installation.id)
        cls().log(msg, level='debug')

        if not cls.app_id:
            raise AppDoesNotExist('You don\'t have a github application.')

        myjwt = await cls.get_jwt_token()
        header = {'Authorization': 'Bearer {}'.format(myjwt),
                  'Accept': 'application/vnd.github.machine-man-preview+json'}

        ret = await requests.post(installation.auth_token_url, headers=header)

        if ret.status != 201:
            raise BadRequestToGithubAPI(ret.status, ret.text)

        ret = ret.json()
        installation.auth_token = ret['token']
        installation.expires = string2datetime(ret['expires_at'],
                                               dtformat="%Y-%m-%dT%H:%M:%SZ")
        await installation.save()
        return installation


class GithubInstallation(LoggerMixin, Document):
    """An installation of the GitHub App. Installations have access to
    repositories and events."""

    app = GithubApp

    user = ReferenceField(User, required=True)
    # the id of the github app installation
    github_id = IntField(required=True, unique=True)
    auth_token = StringField()
    expires = DateTimeField()
    # maps github_repo_ids/repo_ids
    repositories = DictField()

    @classmethod
    async def create(cls, github_id, user):
        """Creates a new github app installation. Imports
        the repositories available to the installation.

        :param github_id: The installation id on github
        :param user: The user that owns the installation."""

        if await cls.objects.filter(github_id=github_id).first():
            msg = 'Installation {} already exists'.format(github_id)
            cls().log(msg, level='error')
            return

        msg = 'Creating installation for github_id {}'.format(github_id)
        cls().log(msg, level='debug')
        installation = cls(github_id=github_id, user=user)
        await installation.save()
        await installation.import_repositories()
        return installation

    async def update_repository(self, github_repo_id):
        """Updates a repository code.

        :param github_repo_id: The id of the repository on github.
        """

        repo_id = self.repositories[github_repo_id]
        repo = await Repository.get(id=repo_id)
        url = await self._get_auth_url(repo.url)
        if repo.fetch_url != url:
            repo.fetch_url = url
            await repo.save()
        await repo.update_code()

    @property
    def auth_token_url(self):
        """URL used to retrieve an access token for this installation."""

        return 'https://api.github.com/installations/{}/access_tokens'.format(
            self.github_id)

    @property
    def token_is_expired(self):
        n = now()
        if n > utc2localtime(self.expires):
            return True
        return False

    async def import_repositories(self):
        """Imports all repositories available to the installation."""

        msg = 'Importing repos for {}'.format(self.github_id)
        self.log(msg, level='debug')
        tasks = []
        for repo in await self.list_repos():
            t = ensure_future(self.import_repository(repo))
            tasks.append(t)

        return gather(*tasks)

    async def import_repository(self, repo_info):
        """Imports a repository from GitHub.

        :param repo_info: A dictionary with the repository information."""
        msg = 'Importing repo {}'.format(repo_info['clone_url'])
        self.log(msg, level='debug')

        branches = [
            RepositoryBranch(name='master', notify_only_latest=False),
            RepositoryBranch(name='feature-*', notify_only_latest=True),
            RepositoryBranch(name='bug-*', notify_only_latest=True)]
        slaves = await Slave.list_for_user(await self.user).to_list()
        # update_seconds=0 because it will not be scheduled in fact.
        # note the schedule_poller=False.
        # What triggers an update code is a message from github in the
        # webhook receiver.
        user = await self.user
        repo = await Repository.create(name=repo_info['name'],
                                       url=repo_info['clone_url'],
                                       owner=user,
                                       update_seconds=0,
                                       vcs_type='git',
                                       schedule_poller=False,
                                       parallel_builds=1,
                                       branches=branches,
                                       slaves=slaves)
        url = await self._get_auth_url(repo.url)
        await repo.update_code(url=url)
        self.repositories[repo_info['id']] = str(repo.id)
        return repo

    async def _get_header(self):
        if not self.auth_token or self.token_is_expired:
            await self.app.create_installation_token(self)

        header = {'Authorization': 'token {}'.format(self.auth_token),
                  'Accept': 'application/vnd.github.machine-man-preview+json'}
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
        url = 'https://api.github.com/installation/repositories'
        ret = await requests.get(url, headers=header)
        if ret.status != 200:
            raise BadRequestToGithubAPI(ret.status, ret.text, url)
        ret = ret.json()
        return ret['repositories']
