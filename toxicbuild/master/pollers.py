# -*- coding: utf-8 -*-

# Copyright 2015-2018 Juca Crispim <juca@poraodojuca.net>

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

from functools import partial
import traceback
from toxicbuild.core.vcs import get_vcs
from toxicbuild.core.utils import LoggerMixin, MatchKeysDict
from toxicbuild.master.consumers import BaseConsumer
from toxicbuild.master.exceptions import CloneException
from toxicbuild.master.exchanges import revisions_added
from toxicbuild.master.exchanges import update_code, poll_status
from toxicbuild.master.repository import Repository


class Poller(LoggerMixin):

    """ Class to poll changes from a vcs, process them and notificate about
    incoming changes
    """

    def __init__(self, repository, vcs_type, workdir):
        """:param repository: An instance of
          :class:`toxicbuild.repositories.Repository`

        :param vcs_type: Vcs type for :func:`toxicbuild.core.vcs.get_vcs`.
        :param workdir: workdir for vcs.
        """
        self.repository = repository
        self.vcs = get_vcs(vcs_type)(workdir)
        self._is_polling = False
        self._external_info = None

    def is_polling(self):
        return self._is_polling

    async def external_poll(self, external_url, external_name,
                            external_branch, into):
        """Fetches the changes of a external (not the origin) repository
        into a local branch.

        :param external_url: The url of the external remote repository.
        :param external_name: The name to identiry the external repo.
        :param external_branch: The name of the branch in the external repo.
        :param into: The name of the local repository."""

        await self.vcs.import_external_branch(external_url, external_name,
                                              external_branch, into)
        repo_branches = {into: True}
        self._external_info = {'name': external_name, 'url': external_url,
                               'branch': external_branch, 'into': into}
        await self.poll(repo_branches)

    async def poll(self, repo_branches=None):
        """ Check for changes on repository and if there are changes, notify
        about it.

        :param repo_branches: Param to be passed to
          :meth:`~toxicbuild.master.pollers.Poller.process_changes`.
        """

        with_clone = False

        async with await self.repository.toxicbuild_conf_lock.acquire_write():
            if self.is_polling():
                self.log('{} alreay polling. leaving...'.format(
                    self.repository.url), level='debug')
                return

            url = self.repository.get_url()
            self.log('Polling with url {}'.format(url))
            self._is_polling = True

            if not self.vcs.workdir_exists():
                self.log('clonning repo')
                try:
                    await self.vcs.clone(url)
                    with_clone = True
                except Exception as e:
                    msg = traceback.format_exc()
                    self.log(msg, level='error')
                    raise CloneException(str(e))

            # here we change the remote url if needed. eg: a new token
            # is beeing used to authenticate, so a new url is used.
            await self.vcs.try_set_remote(url)

            # for git.
            # remove no branch when hg is implemented
            if hasattr(self.vcs, 'update_submodule'):  # pragma no branch
                self.log('updating submodule', level='debug')
                await self.vcs.update_submodule()

            try:
                await self.process_changes(repo_branches)
            except Exception as e:
                # shit happends
                msg = traceback.format_exc()
                self.log(msg, level='error')
                # but the show must go on

        return with_clone

    async def process_changes(self, repo_branches=None):
        """ Process all changes since the last revision in db

        :param repo_branches: The branches to look for incomming changes. If no
          branches, all branches in repo config will be used. It is a
          dictionary with the following format:

          .. code block:: python

             # builders_fallback is the builders_fallback to
             # :class:`~toxicbuild.master.repository.RepositoryRevision`
             {'branch-name': {'notify_only_latest': True
                              'builders_fallback': 'branch-name'}}

        """
        self.log('processing changes', level='debug')

        dbrevisions = await self.repository.get_latest_revisions()

        since = dict((branch, r.commit_date) for branch, r
                     in dbrevisions.items() if r)

        if not repo_branches:
            repo_branches = MatchKeysDict(
                **{b.name: {'notify_only_latest': b.notify_only_latest}
                   for b in self.repository.branches})

        branches = repo_branches.keys()

        newer_revisions = await self.vcs.get_revisions(
            since=since, branches=branches)

        known_branches = dbrevisions.keys()

        revisions = []
        for branch, revs in newer_revisions.items():
            self.log('processing changes for branch {}'.format(branch),
                     level='debug')
            # the thing here is that if the branch is a new one
            # or is the first time its running, I don't want to get all
            # revisions, but the last one only.
            if branch not in known_branches:
                revs = [revs[-1]]

            notify_only_latest = repo_branches.get(
                branch, {}).get('notify_only_latest') \
                if repo_branches.get(branch) is not None else True

            builders_fallback = repo_branches.get(
                branch, {}).get('builders_fallback') \
                if repo_branches.get(branch) is not None else ''

            await self._process_branch_revisions(branch, revs,
                                                 notify_only_latest,
                                                 builders_fallback,
                                                 revisions)

        if revisions:
            await self.notify_change(*revisions)

        self.log('Processing changes done!', level='debug')

    async def notify_change(self, *revisions):
        """ Notify about new revisions added to the repository.

        :param revisions: A list of new revisions"""

        msg = {'repository_id': str(self.repository.id),
               'revisions_ids': [str(r.id) for r in revisions]}

        self.log('publishing on revisions_added', level='debug')
        await revisions_added.publish(msg)

    def log(self, msg, level='info'):
        msg = '[{}] {}'.format(self.repository.name, msg)
        super().log(msg, level)

    async def _process_branch_revisions(self, branch, revisions,
                                        notify_only_latest, builders_fallback,
                                        to_notify):
        """Processes the revisions for a branch"""

        branch_revs = []
        for rev in revisions:
            revision = await self.repository.add_revision(
                branch, external=self._external_info,
                builders_fallback=builders_fallback, **rev)
            # the thing here is: if notify_only_latest, we only
            # add the most recent revision, the last one of the revisions
            # list to the revisionset
            if (not revisions[-1] == rev and notify_only_latest):
                continue

            to_notify.append(revision)
            # branch_revs just for logging
            branch_revs.append(revision)

        if branch_revs:
            msg = '{} new revisions for {} on branch {} added'
            self.log(msg.format(len(branch_revs), self.repository.url,
                                branch))


class PollerServer(BaseConsumer):
    """A server for pollers. Uses Rabbitmq to publish/consume messages from
    the master"""

    def __init__(self, loop=None):
        exchange = update_code
        msg_callback = self._handler_counter
        super().__init__(exchange, msg_callback, loop=loop)

    async def _handler_counter(self, msg):
        self._running_tasks += 1
        rmsg = {'with_clone': False,
                'clone_status': 'clone-exception'}
        repo_id = msg.body['repo_id']
        try:
            r = await self.handle_update_request(msg)
            rmsg.update(r)
        finally:
            await poll_status.publish(rmsg, routing_key=repo_id)
            self._running_tasks -= 1

    async def handle_update_request(self, msg):
        """Handle an update code request sent by the master."""

        body = msg.body
        repo_id = body['repo_id']
        repo = await Repository.get(id=repo_id)
        vcs_type = body['vcs_type']
        external = body.get('external')
        poller = Poller(repo, vcs_type, repo.workdir)
        if external:
            external_url = external.get('url')
            external_name = external.get('name')
            external_branch = external.get('branch')
            into = external.get('into')
            pollfn = partial(poller.external_poll, external_url, external_name,
                             external_branch, into)
        else:
            repo_branches = body.get('repo_branches')
            pollfn = partial(poller.poll, repo_branches)
        try:
            with_clone = await pollfn()
            clone_status = 'ready'
        except Exception:
            tb = traceback.format_exc()
            self.log(tb, level='error')
            with_clone = False
            clone_status = 'clone-exception'

        msg = {'with_clone': with_clone,
               'clone_status': clone_status}

        return msg
