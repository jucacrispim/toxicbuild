# -*- coding: utf-8 -*-

# Copyright 2019, 2023 Juca Crispim <juca@poraodojuca.net>

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
from toxicbuild.core.vcs import get_vcs
from toxicbuild.core.utils import (
    LoggerMixin,
    MatchKeysDict,
    datetime2string,
    read_file
)
from toxicbuild.poller import settings


class Poller(LoggerMixin):

    """ Class to poll changes from a vcs, process them and notify about
    incoming changes
    """

    def __init__(self, repo_id, url, branches_conf, since, known_branches,
                 vcs_type, conffile='toxicbuild.yml'):
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
        :param conffile: The name of the build config file.
        """
        self.repo_id = repo_id
        self.url = url
        self.branches_conf = branches_conf
        self.known_branches = known_branches
        self.since = since
        self.vcs_type = vcs_type
        self.vcs = get_vcs(self.vcs_type)(self.workdir)
        self.external_info = None
        self.local_branch = False
        self.conffile = conffile
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

        self.log('external polling in {}'.format(external_url), level='debug')

        await self.vcs.import_external_branch(external_url, external_name,
                                              external_branch, into)
        self.branches_conf = {into: {'notify_only_latest': True}}
        self.external_info = {'name': external_name, 'url': external_url,
                              'branch': external_branch, 'into': into}
        # The trick here is that we import an external branch into a
        # local branch
        self.local_branch = True
        r = await self.poll()
        return r

    async def poll(self):
        """ Check for changes in a repository
        """

        ret = {'with_clone': False,
               'error': None,
               'revisions': [],
               'locked': False,
               'clone_error': False,
               'clone_status': 'ready'}

        try:
            lock = await self.lock.acquire_write(timeout=0.2)
        except exc.TimeoutError:
            self.log('Repo {} already polling'.format(self.repo_id),
                     level='warning')
            ret['locked'] = True
            return ret

        async with lock:
            self.log('Polling with url {}'.format(self.url))

            if not self.vcs.workdir_exists():
                self.log('clonning repo')
                try:
                    await self.vcs.clone(self.url)
                    ret['with_clone'] = True
                except Exception:
                    msg = traceback.format_exc()
                    self.log(msg, level='error')
                    ret['clone_error'] = True
                    ret['error'] = msg
                    ret['clone_status'] = 'clone-exception'
                    return ret

            # here we change the remote url if needed. eg: a new token
            # is beeing used to authenticate, so a new url is used.
            await self.vcs.try_set_remote(self.url)

            try:
                revs = await self.process_changes()
                ret['revisions'] = revs
            except Exception:
                # shit happends
                msg = traceback.format_exc()
                self.log(msg, level='error')
                ret['error'] = msg
                # but the show must go on

        return ret

    async def process_changes(self):
        """ Process all changes since the last revision in db
        """
        self.log(f'processing changes for branches {self.branches_conf}',
                 level='debug')

        repo_branches = MatchKeysDict(
            **{name: conf for name, conf in self.branches_conf.items()})

        branches = repo_branches.keys()

        if self.local_branch:
            newer_revisions = await self.vcs.get_local_revisions(
                since=self.since, branches=branches)

        else:
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

        self.log('Processing changes done!', level='debug')
        return revisions

    async def _process_branch_revisions(self, branch, revisions,
                                        notify_only_latest, builders_fallback,
                                        to_notify):
        """Processes the revisions for a branch"""

        branch_revs = []
        for rev in revisions:
            if (not revisions[-1] == rev and notify_only_latest):
                continue

            rev['branch'] = branch
            rev['external'] = self.external_info
            rev['builders_fallback'] = builders_fallback
            rev['commit_date'] = datetime2string(rev['commit_date'])
            rev['config'] = await self._get_config(rev['commit'])

            to_notify.append(rev)
            # branch_revs just for logging
            branch_revs.append(rev)

        msg = '{} new revisions for {} on branch {} added'
        self.log(msg.format(len(branch_revs), self.url,
                            branch))

    async def _get_config(self, commit):
        await self.vcs.checkout(commit)
        path = os.path.join(self.vcs.workdir, self.conffile)
        try:
            config = await read_file(path)
        except FileNotFoundError:
            r = ''
        else:
            r = config

        return r
