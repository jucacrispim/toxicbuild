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

import traceback
import os

from aiozk import exc
from toxicbuild.common.coordination import Lock
from toxicbuild.common.exchanges import (
    revisions_added,
)
from toxicbuild.core.vcs import get_vcs
from toxicbuild.core.utils import LoggerMixin, MatchKeysDict, datetime2string
from toxicbuild.poller import settings
from toxicbuild.poller.exceptions import CloneException


class Poller(LoggerMixin):

    """ Class to poll changes from a vcs, process them and notify about
    incoming changes
    """

    def __init__(self, repo_id, url, branches_conf, since, known_branches,
                 vcs_type):
        """Constructor for Poller.

        :param repo_id: The id of the repository that will update or clone
          code.
        :param url: A repository url.
        :param branches_conf: The branch configuration of the repository.
        :param since: A dict in the format {'branch-name': commit_dt} with
          the date of the last known commit for the branch.
        :param known_branches: A list of branches that already have
          a revision.
        :param vcs_type: Vcs type for :func:`toxicbuild.core.vcs.get_vcs`.
        """
        self.repo_id = repo_id
        self.url = url
        self.branches_conf = branches_conf
        self.known_branches = known_branches
        self.since = since
        self.vcs_type = vcs_type
        self.vcs = get_vcs(self.vcs_type)(self.workdir)
        self._external_info = None
        self._lock = None

    @property
    def lock(self):
        if self._lock:
            return self._lock

        self._lock = Lock('poller-{}'.format(str(self.repo_id)))
        return self._lock

    @property
    def workdir(self):
        base_dir = settings.SOURCE_CODE_DIR
        return os.path.join(base_dir, str(self.repo_id))

    async def external_poll(self, external_url, external_name,
                            external_branch, into):
        """Fetches the changes from a external (not the origin) repository
        into a local branch.

        :param external_url: The url of the external remote repository.
        :param external_name: The name to identify the external repo.
        :param external_branch: The name of the branch in the external repo.
        :param into: The name of the local branch."""

        await self.vcs.import_external_branch(external_url, external_name,
                                              external_branch, into)
        self.branches_conf = {into: {'notify_only_latest': True}}
        self._external_info = {'name': external_name, 'url': external_url,
                               'branch': external_branch, 'into': into}
        await self.poll()

    async def poll(self):
        """ Check for changes in a repository and if there are changes, notify
        about it.
        """

        with_clone = False

        try:
            lock = await self.lock.acquire_write(timeout=0.2)
        except exc.TimeoutError:
            # Already polling for the repository
            return None

        async with lock:
            self.log('Polling with url {}'.format(self.url))

            if not self.vcs.workdir_exists():
                self.log('clonning repo')
                try:
                    await self.vcs.clone(self.url)
                    with_clone = True
                except Exception as e:
                    msg = traceback.format_exc()
                    self.log(msg, level='error')
                    raise CloneException(str(e))

            # here we change the remote url if needed. eg: a new token
            # is beeing used to authenticate, so a new url is used.
            await self.vcs.try_set_remote(self.url)

            # for git.
            # remove no branch when hg is implemented
            if hasattr(self.vcs, 'update_submodule'):  # pragma no branch
                self.log('updating submodule', level='debug')
                await self.vcs.update_submodule()

            try:
                await self.process_changes()
            except Exception as e:

                # shit happends
                msg = traceback.format_exc()
                self.log(msg, level='error')
                # but the show must go on

        return with_clone

    async def process_changes(self):
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

        repo_branches = MatchKeysDict(
            **{name: conf for name, conf in self.branches_conf.items()})

        branches = repo_branches.keys()

        newer_revisions = await self.vcs.get_revisions(
            since=self.since, branches=branches)

        revisions = []
        for branch, revs in newer_revisions.items():
            self.log('processing changes for branch {}'.format(branch),
                     level='debug')
            # the thing here is that if the branch is a new one
            # or is the first time its running, I don't want to get all
            # revisions, but the last one only.
            if branch not in self.known_branches:
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

        msg = {'repository_id': str(self.repo_id),
               'revisions': revisions}

        self.log('publishing on revisions_added', level='debug')
        await revisions_added.publish(msg)

    def log(self, msg, level='info'):
        msg = '[{}] {}'.format(self.repo_id, msg)
        super().log(msg, level)

    async def _process_branch_revisions(self, branch, revisions,
                                        notify_only_latest, builders_fallback,
                                        to_notify):
        """Processes the revisions for a branch"""

        branch_revs = []
        for rev in revisions:
            if (not revisions[-1] == rev and notify_only_latest):
                continue

            rev['branch'] = branch
            rev['external'] = self._external_info
            rev['builders_fallback'] = builders_fallback
            rev['commit_date'] = datetime2string(rev['commit_date'])

            to_notify.append(rev)
            # branch_revs just for logging
            branch_revs.append(rev)

        msg = '{} new revisions for {} on branch {} added'
        self.log(msg.format(len(branch_revs), self.url,
                            branch))
