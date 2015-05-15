# -*- coding: utf-8 -*-

# Copyright 2015 Juca Crispim <juca@poraodojuca.net>

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

import asyncio
from toxicbuild.master.signals import revision_added
from toxicbuild.core.vcs import get_vcs
from toxicbuild.core.utils import log


class Poller:

    """ Class to poll changes from a vcs, process them and notificate about
    incoming changes
    """

    def __init__(self, repository, vcs_type, workdir,
                 notify_only_latest=False):
        """:param repository: An instance of
          :class:`toxicbuild.repositories.Repository`

        :param vcs_type: Vcs type for :func:`toxicbuild.core.vcs.get_vcs`.
        :param workdir: workdir for vcs.
        """
        self.repository = repository
        self.vcs = get_vcs(vcs_type)(workdir)
        self.notify_only_latest = notify_only_latest

    @asyncio.coroutine
    def poll(self):
        """ Check for changes on repository and if there are changes, notify
        about it.
        """

        self.log('Polling changes for {}'.format(self.repository.url))

        if not self.vcs.workdir_exists():
            yield from self.vcs.clone(self.repository.url)

        if (yield from self.vcs.has_changes()):
            yield from self.process_changes()

    @asyncio.coroutine
    def process_changes(self):
        """ Process all changes since the last revision in db
        """
        dbrevisions = yield from self.repository.get_latest_revisions()

        since = dict((branch, r.commit_date) for branch, r
                     in dbrevisions.items())

        newer_revisions = yield from self.vcs.get_revisions(since=since)

        known_branches = dbrevisions.keys()

        for branch, revisions in newer_revisions.items():
            # the thing here is that if the branch is a new one
            # or is the first time its running, I don't what to get all
            # revisions, but the last one only.
            if branch not in known_branches:
                rev = revisions[0]
                revision = yield from self.repository.add_revision(branch,
                                                                   **rev)
                msg = 'Last revision for {} on branch {} added'
                self.log(msg.format(self.repository.url, branch))
                self.notify_change(revision)
                continue

            for rev in revisions:
                revision = yield from self.repository.add_revision(
                    branch, **rev)
                # the thing here is: if self.notify_only_latest, we only
                # send a signal for the most recent revision, the last
                # one of the revisions list
                if (not revisions[-1] == rev and self.notify_only_latest):
                    continue

                # not sure if the right place for this notification  is
                # here or in Repository. Who knows...
                self.notify_change(revision)

            if len(revisions):
                msg = '{} new revisions for {} on branch {} added'
                self.log(msg.format(len(revisions), self.repository.url,
                                    branch))

    def notify_change(self, revision):
        """ Notify about an incoming change
        """
        revision_added.send(self, revision=revision)

    def log(self, msg):
        log('[poller] ' + msg)
