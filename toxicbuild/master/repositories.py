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
import os
from mongomotor import Document
from mongomotor.fields import (StringField, IntField, ReferenceField,
                               DateTimeField)
from tornado.platform.asyncio import to_asyncio_future
from toxicbuild.master.pollers import Poller


class Repository(Document):
    url = StringField(required=True)
    update_seconds = IntField(default=300, required=True)
    vcs_type = StringField(required=True, default='git')

    def __init__(self, *args, **kwargs):
        super(Repository, self).__init__(*args, **kwargs)
        self._poller_instance = None

    @property
    def workdir(self):
        """ The directory where the source code of this repository is
        cloned into
        """
        workdir = self.url.replace('/', '-').replace('@', '').replace(':', '')
        return os.path.join('src', workdir)

    @property
    def poller(self):
        if self._poller_instance is not None:  # pragma: no cover
            return self._poller_instance

        vcs_type = self.vcs_type or 'git'
        self._poller_instance = Poller(self, vcs_type, self.workdir)
        return self._poller_instance

    @asyncio.coroutine
    def get_latest_revision_for_branch(self, branch):
        """ Returns the latest revision for a given branch
        :param branch: branch name
        """
        latest = RepositoryRevision.objects.filter(
            repository=self).order_by('-commit_date')
        latest = yield from to_asyncio_future(latest.first())
        return latest

    @asyncio.coroutine
    def get_latest_revisions(self):
        """ Returns the latest revision for all known branches
        """
        branches = yield from to_asyncio_future(
            RepositoryRevision.objects.distinct('branch'))
        revs = {}
        for branch in branches:
            rev = yield from self.get_latest_revision_for_branch(branch)
            revs[branch] = rev

        return revs

    @asyncio.coroutine
    def add_revision(self, branch, commit, commit_date):
        """ Adds a revision to the repository.
        :param commit: commit uuid
        :param branch: branch name
        :param commit_date: commit's date (on authors time)
        """
        revision = RepositoryRevision(repository=self, commit=commit,
                                      branch=branch, commit_date=commit_date)
        yield from to_asyncio_future(revision.save())
        return revision


class RepositoryRevision(Document):
    repository = ReferenceField(Repository, required=True)
    commit = StringField(required=True)
    branch = StringField(required=True)
    commit_date = DateTimeField(required=True)
