# -*- coding: utf-8 -*-
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

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

from asyncio import ensure_future, gather, sleep
import re
from mongomotor import Document, EmbeddedDocument
from mongomotor.fields import (
    StringField,
    EmbeddedDocumentListField,
    DynamicField,
    DateTimeField,
)
from toxicbuild.common.exceptions import AlreadyExists
from toxicbuild.common.interfaces import (
    NotificationInterface,
    RepositoryInterface,
    SlaveInterface,
    UserInterface,
    BaseInterface
)
from toxicbuild.core import requests
from toxicbuild.core.exceptions import ToxicClientException
from toxicbuild.core.utils import LoggerMixin, now, utc2localtime
from toxicbuild.integrations import settings
from toxicbuild.integrations.exceptions import (
    BadRepository,
    BadRequestToExternalAPI
)

BaseInterface.settings = settings


class BaseIntegrationApp(LoggerMixin, Document):
    """Base class for oauth2 applications. When integrating
    with a 3rd party service like gitlab, github or bitbucket you
    need first to create an application - called oauth client on
    bitbucket - on their side.
    """

    app_id = DynamicField(required=True)
    """The app id in the 3rd party service."""

    secret = StringField()
    """A secret generated by the 3rd party service used to create
    new installation's access token.
    """

    webhook_token = StringField()
    """The token used to sign the incomming request in the webhook. This must
    be set in the github app creation page."""

    meta = {'allow_inheritance': True}

    @classmethod
    async def create_app(cls):
        raise NotImplementedError

    async def validate_token(cls, token):
        """Validates a token sent by a 3rd party hook as request signature.
        """
        raise NotImplementedError

    @classmethod
    async def get_app(cls):
        """Returns the app instance. If it does not exist, create it."""

        app = await cls.objects.first()
        if app:
            return app

        app = await cls.create_app()
        return app


class ExternalInstallationRepository(LoggerMixin, EmbeddedDocument):
    """Information about a repository in an external service."""

    external_id = DynamicField(required=True)
    """The id of the repository in the external service."""

    repository_id = StringField(required=True)
    """The id of the repository in ToxicBuild."""

    full_name = StringField(required=True)
    """Full name of the repository in the external service."""


class BaseIntegration(LoggerMixin, Document):
    """A basic oauth2 integration with third-party services. Extend this
    one to create integrations.
    """

    APP_CLS = None

    code = StringField()
    """The code first sent by the external api. Used to generate the
    access token
    """

    user_id = StringField(required=True)
    """The id of the user who owns the installation"""

    user_name = StringField(requierd=True)
    """The name of the user who owns the installation"""

    external_user_id = DynamicField()
    """The id of the user in a 3rd party service."""

    repositories = EmbeddedDocumentListField(ExternalInstallationRepository)
    """The repositories imported from the user external service account."""

    access_token = StringField()
    """Access token used for authentication on the api."""

    refresh_token = StringField()
    """Token used to get a new access_token when it expires.
    """

    expires = DateTimeField()
    """When the access_token expires. Datetime must be UTC."""

    url_user = None
    """Used as username in a url that has authentication like user:pass@host.
    """

    notif_name = None

    meta = {'allow_inheritance': True,
            'collection': 'base_integration_installation'}

    async def list_repos(self):
        """Lists the repositories using a thrid-party api. Returns a list
        of dictionaries. Each dictionary has the following keys:
        - id
        - clone_url
        - name
        - full_name
        """
        raise NotImplementedError

    async def request_access_token(self):
        """Requests a new access token to a 3rd party service api.
        Returns a dictionary with 3 keys:

        - access_token: The token used to access the api
        - refresh_token: A token used to get a new access token
        - expires: When the access token expires. A datetime object.
        """

        raise NotImplementedError

    async def refresh_access_token(self):
        """Gets a new access token when the old one is expired
        """

        raise NotImplementedError

    async def request_user_id(self):
        """Get the user id using the 3rd party api and saves it.
        """

        raise NotImplementedError

    async def create_webhook(self, repo_external_id):
        """Creates a webhook in a 3rd party service to send information
        about events.
        """

        raise NotImplementedError

    @property
    def user(self):
        """The user who owns this installation.
        """
        return UserInterface(None, {'id': self.user_id,
                                    'name': self.user_name})

    @property
    def webhook_url(self):
        """The url for the 3rd party service to reach our application.
        """
        name = type(self).__name__.replace('Integration', '').lower()
        url = settings.INTEGRATIONS_HTTP_URL + \
            '{}/webhooks?installation_id={}'.format(name, str(self.id))
        return url

    @property
    def token_is_expired(self):
        """Informs if the installation auth token is expired."""
        n = now()
        if n > utc2localtime(self.expires):
            return True
        return False

    async def get_user_id(self):
        self.external_user_id = await self.request_user_id()
        await self.save()

    async def get_auth_url(self, url):
        """Returns the repo url with the acces token for authentication
        in the format prot://user:passwd@the-url

        :param url: The https repo url"""

        if not self.url_user:
            raise BadRequestToExternalAPI(
                'You need to set an url_user in your integration class')

        if not self.access_token:
            await self.create_access_token()

        p = re.compile(r'(\w+)://(.*)')
        protocol, url = p.match(url).groups()
        new_url = '{}://{}:{}@{}'.format(protocol,
                                         self.url_user, self.access_token, url)
        return new_url

    async def get_access_token(self):
        """ Returns an access token for authenticated acces. If the
        token does not exist creates a new one. If the token is expired
        refresh the token.
        """

        if not self.access_token:
            await self.create_access_token()
        elif self.token_is_expired:
            await self.refresh_access_token()
        return self.access_token

    async def get_headers(self):
        """Returns the header used for authenticated access to the api.
        """
        token = await self.get_access_token()
        headers = {'Authorization': 'Bearer {}'.format(token)}
        return headers

    async def create_access_token(self):
        """Creates an access token to the gitlab api.
        """
        d = await self.request_access_token()
        self.access_token = d['access_token']
        self.refresh_token = d['refresh_token']
        self.expires = d['expires']
        await self.save()

    def get_notif_config(self):
        return {'installation': str(self.id)}

    async def enable_notification(self, repo):
        """Enables a notification to a repository.

        :param repo: A repository instance."""

        conf = self.get_notif_config()
        await NotificationInterface.enable(
            str(repo.id), self.notif_name, **conf)

    async def import_repository(self, repo_info, clone=True):
        """Imports a repository from an external service.

        :param repo_info: A dictionary with the repository information.
          it MUST have the following keys:
          - id
          - name
          - full_name
          - clone_url
        """

        msg = 'Importing repo {}'.format(repo_info['clone_url'])
        self.log(msg)

        branches = [
            dict(name='master', notify_only_latest=True),
            dict(name='feature-*', notify_only_latest=True),
            dict(name='bug-*', notify_only_latest=True)]
        slaves = await SlaveInterface.list(self.user)
        slaves_names = [s.name for s in slaves]
        # update_seconds=0 because it will not be scheduled in fact.
        # note the schedule_poller=False.
        # What triggers an update code is a message from github/gitlab in the
        # webhook receiver.
        user = self.user
        fetch_url = await self.get_auth_url(repo_info['clone_url'])
        external_id = repo_info['id']
        external_full_name = repo_info['full_name']
        try:
            repo = await RepositoryInterface.add(
                user,
                name=repo_info['name'], url=repo_info['clone_url'],
                owner=user, fetch_url=fetch_url, update_seconds=0,
                vcs_type='git', schedule_poller=False, parallel_builds=1,
                branches=branches, slaves=slaves_names,
                external_id=str(external_id),
                external_full_name=external_full_name)
        except AlreadyExists:
            msg = 'Repository {}/{} already exists. Leaving.'.format(
                user.name, repo_info['name'])
            self.log(msg, level='error')
            return False

        ext_repo = ExternalInstallationRepository(
            external_id=external_id,
            repository_id=str(repo.id),
            full_name=external_full_name)
        self.repositories.append(ext_repo)
        await self.save()
        await self.enable_notification(repo)

        if clone:
            await repo.request_code_update()

        await self.post_import_hooks(external_id)
        return repo

    async def import_repositories(self):
        """Imports all repositories available to the installation."""

        user = self.user
        msg = 'Importing repos for {}'.format(user.id)
        self.log(msg, level='debug')
        repos = []
        for repo_info in await self.list_repos():
            try:
                repo = await self.import_repository(repo_info, clone=False)
            except Exception as e:
                self.log('Error importing repository {}: {}'.format(
                    repo_info['name'], str(e)), level='error')
                continue

            if repo:  # pragma no branch
                repos.append(repo)

        for chunk in self._get_import_chunks(repos):
            tasks = []
            for repo in chunk:
                await repo.request_code_update()
                t = ensure_future(self._wait_clone(repo))
                tasks.append(t)

            await gather(*tasks)

        return repos

    @classmethod
    async def create(cls, user, **kwargs):
        """Creates a new integration. Imports the repositories available
        to the installation.

        :param user: The user that owns the installation.
        :param kwargs: Named arguments passed to installation class init.
        """

        installation = await cls.objects.filter(
            user_id=str(user.id)).first()
        if not installation:
            msg = 'Creating installation for {}'.format(kwargs)
            cls.log_cls(msg)
            installation = cls(user_id=str(user.id), user_name=user.username,
                               **kwargs)
            await installation.save()
            await installation.create_access_token()
            await installation.get_user_id()

        await installation.import_repositories()
        return installation

    async def update_repository(self, external_repo_id, repo_branches=None,
                                external=None, wait_for_lock=False):
        """Updates a repository's code.

        :param external_repo_id: The id of the repository on github.
        :param repo_branches: Param to be passed to
          :meth:`~toxicbuild.master.repository.Repository.request_code_update`.
        :param external: Information about an third party repository i.e a
          commit from a pull request from another repository.
        :param wait_for_lock: Indicates if we should wait for the release of
          the lock or simply return if we cannot get a lock.
        """

        repo = await self._get_repo_by_external_id(external_repo_id)
        url = await self.get_auth_url(repo.url)
        if repo.fetch_url != url:
            repo.fetch_url = url
            await repo.update(fetch_url=repo.fetch_url)
        await repo.request_code_update(
            repo_branches=repo_branches, external=external,
            wait_for_lock=wait_for_lock)

    async def repo_request_build(self, external_repo_id, branch, named_tree):
        """Requests a new build.

        :param external_repo_id: The id of the repository in a
          external service.
        :param branch: The name of the branch to build.
        :param named_tree: The named tree to build."""

        repo = await self._get_repo_by_external_id(external_repo_id)
        await repo.start_build(branch, named_tree=named_tree)

    async def delete(self, requester, *args, **kwargs):
        """Deletes the installation from the system"""

        for install_repo in self.repositories:
            try:
                repo = await RepositoryInterface.get(
                    requester, id=install_repo.repository_id)
            except ToxicClientException:
                continue
            await repo.delete()

        r = await super().delete(*args, **kwargs)
        return r

    async def remove_repository(self, github_repo_id):
        """Removes a repository from the system.

        :param github_repo_id: The id of the repository in github."""

        repo = await self._get_repo_by_external_id(github_repo_id)
        await repo.delete()

    async def request2api(self, method, *args, statuses=None, **kwargs):
        """Does a request to a 3rd party service. Returns a response object.

        :param method: Request method.
        :param args: Args passed to the request.
        :param statuses: A list of statuses that does not raise exception.
          If None status 200 does not raise exception.
        :param kwargs: Named arguments passed to the request.
        """
        statuses = [200] if statuses is None else statuses
        fn = getattr(requests, method)
        r = await fn(*args, **kwargs)
        if r.status not in statuses:
            raise BadRequestToExternalAPI(r.status, r.text)

        return r

    async def post_import_hooks(self, repo_external_id):
        """Eexecute actions after a repository is imported. Be default
        executes ``self.create_webhook``
        """

        await self.create_webhook(repo_external_id)

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

    async def _get_repo_by_external_id(self, external_repo_id):
        for repo in self.repositories:
            if repo.external_id == external_repo_id:  # pragma no branch
                repo_inst = await RepositoryInterface.get(
                    self.user, id=repo.repository_id)
                return repo_inst

        raise BadRepository(
            'External repository {} does not exist here.'.format(
                external_repo_id))

    async def _wait_clone(self, repo):
        repo = await RepositoryInterface.get(self.user, id=repo.id)
        while repo.status == 'cloning':
            await sleep(0.5)
            repo = await RepositoryInterface.get(self.user, id=repo.id)
