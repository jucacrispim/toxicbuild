# -*- coding: utf-8 -*-

# Copyright 2015 2016 Juca Crispim <juca@poraodojuca.net>

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

import traceback
from toxicbuild.core.vcs import get_vcs
from toxicbuild.core.utils import LoggerMixin, MatchKeysDict
from toxicbuild.master.exceptions import CloneException
from toxicbuild.master.signals import revision_added


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

    def is_polling(self):
        return self._is_polling

    async def poll(self):
        """ Check for changes on repository and if there are changes, notify
        about it.
        """

        with_clone = False
        try:
            if self.is_polling():
                self.log('alreay polling. leaving...'.format(
                    self.repository.url), level='debug')
                return

            self._is_polling = True
            self.log('Polling changes')

            if not self.vcs.workdir_exists():
                self.log('clonning repo')
                try:
                    await self.vcs.clone(self.repository.url)
                    with_clone = True
                except Exception as e:
                    msg = traceback.format_exc()
                    self.log(msg, level='error')
                    raise CloneException(str(e))

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
        finally:
            self._is_polling = False

        return with_clone

    async def process_changes(self):
        """ Process all changes since the last revision in db
        """
        self.log('processing changes', level='debug')

        dbrevisions = await self.repository.get_latest_revisions()

        since = dict((branch, r.commit_date) for branch, r
                     in dbrevisions.items() if r)

        repo_branches = MatchKeysDict(
            **{b.name: b for b in self.repository.branches})
        newer_revisions = await self.vcs.get_revisions(
            since=since, branches=repo_branches.keys())

        known_branches = dbrevisions.keys()

        revisions = []
        for branch, revs in newer_revisions.items():
            self.log('processing changes for branch {}'.format(branch),
                     level='debug')
            # the thing here is that if the branch is a new one
            # or is the first time its running, I don't what to get all
            # revisions, but the last one only.
            if branch not in known_branches:
                rev = revs[-1]
                revision = await self.repository.add_revision(branch,
                                                              **rev)
                msg = 'Last revision added for branch {} '
                self.log(msg.format(branch), level='debug')
                revisions.append(revision)
                continue

            notify_only_latest = repo_branches.get(branch).notify_only_latest \
                if repo_branches.get(branch) else False

            await self._process_branch_revisions(branch, revs,
                                                 notify_only_latest,
                                                 revisions)

        self.notify_change(*revisions)

    def notify_change(self, *revisions):
        """ Notify about new revisions added to the repository.

        :param revisions: A list of new revisions"""

        # returning for testing purposes
        return revision_added.send(self.repository, revisions=revisions)

    def log(self, msg, level='info'):
        msg = '[{}] {}'.format(self.repository.name, msg)
        super().log(msg, level)

    async def _process_branch_revisions(self, branch, revisions,
                                        notify_only_latest, to_notify):
        """Processes the revisions for a branch"""

        branch_revs = []
        for rev in revisions:
            revision = await self.repository.add_revision(branch, **rev)
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
