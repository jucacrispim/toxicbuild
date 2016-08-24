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

import asyncio
import os
import re
import shutil
from threading import Thread
from mongomotor import Document, EmbeddedDocument
from mongomotor.fields import (StringField, IntField, ReferenceField,
                               DateTimeField, ListField, BooleanField,
                               EmbeddedDocumentField)
from toxicbuild.core import utils
from toxicbuild.master.scheduler import scheduler
from toxicbuild.master.build import BuildSet, Builder, BuildManager
from toxicbuild.master.exceptions import CloneException
from toxicbuild.master.pollers import Poller
from toxicbuild.master.slave import Slave


# The thing here is: When a repository poller is scheduled, I need to
# keep track of the hashes so I can remove it from the scheduler
# when needed.
# The format is {repourl: hash} for update_code
# and {repourl-start-pending: hash} for starting pending builds
_scheduler_hashes = {}


class RepositoryBranch(EmbeddedDocument):
    # this unique does not work, you must ensure it by yourself.
    # it here just to remember that this should be unique.
    name = StringField(required=True, unique=True)
    notify_only_latest = BooleanField(default=False)


class Repository(Document, utils.LoggerMixin):
    name = StringField(required=True, unique=True)
    url = StringField(required=True, unique=True)
    update_seconds = IntField(default=300, required=True)
    vcs_type = StringField(required=True, default='git')
    branches = ListField(EmbeddedDocumentField(RepositoryBranch))
    slaves = ListField(ReferenceField(Slave))
    clone_status = StringField(choices=('cloning', 'done', 'clone-exception'),
                               default='cloning')

    def __init__(self, *args, **kwargs):
        super(Repository, self).__init__(*args, **kwargs)
        self._poller_instance = None
        self.build_manager = BuildManager(self)

    @property
    def workdir(self):
        """ The directory where the source code of this repository is
        cloned into
        """

        workdir = re.sub(re.compile('http(s|)://'), '', self.url)
        workdir = workdir.replace('/', '-').replace('@', '-').replace(':', '')
        workdir = workdir.strip()
        return os.path.join('src', workdir)

    @property
    def poller(self):
        if self._poller_instance is None:
            vcs_type = self.vcs_type
            self._poller_instance = Poller(self, vcs_type, self.workdir)

        return self._poller_instance

    @asyncio.coroutine
    def get_status(self):
        """Returns the status for the repository. The status is the
        status of the last buildset created for this repository that is
        not pending."""

        last_buildset = yield from BuildSet.objects(
            repository=self).order_by(
                '-created').first()

        clone_statuses = ['cloning', 'clone-exception']
        if not last_buildset and self.clone_status in clone_statuses:
            status = self.clone_status
        elif not last_buildset:
            status = 'idle'
        else:
            status = last_buildset.get_status()
            i = 1
            while status == BuildSet.PENDING:
                # we do not consider pending builds for the repo status
                start = i
                stop = start + 1
                last_buildset = BuildSet.objects(repository=self).order_by(
                    '-created')[start:stop]
                last_buildset = yield from last_buildset.first()

                if not last_buildset:
                    status = 'idle'
                    break

                status = last_buildset.get_status()
                i += 1
        return status

    @classmethod
    @asyncio.coroutine
    def create(cls, name, url, update_seconds, vcs_type, slaves=None,
               branches=None):
        """ Creates a new repository and schedule it. """

        slaves = slaves or []
        branches = branches or []

        repo = cls(url=url, update_seconds=update_seconds, vcs_type=vcs_type,
                   slaves=slaves, name=name, branches=branches)
        yield from repo.save()
        repo.schedule()
        return repo

    @asyncio.coroutine
    def remove(self):
        """ Removes all builds and builders and revisions related to the
        repository, removes the poller from the scheduler, removes the
        source code from the file system and then removes the repository.
        """

        builds = BuildSet.objects.filter(repository=self)
        yield from builds.delete()

        builders = Builder.objects.filter(repository=self)
        yield from builders.delete()

        revisions = RepositoryRevision.objects.filter(repository=self)
        yield from revisions.delete()

        try:
            sched_hash = _scheduler_hashes[self.url]
            scheduler.remove_by_hash(sched_hash)
            del _scheduler_hashes[self.url]

            pending_hash = _scheduler_hashes['{}-start-pending'.format(
                self.url)]
            scheduler.remove_by_hash(pending_hash)
            del _scheduler_hashes['{}-start-pending'.format(self.url)]
        except KeyError:  # pragma no cover
            # means the repository was not scheduled
            pass

        Thread(target=shutil.rmtree, args=[self.workdir]).start()

        yield from self.delete()

    @classmethod
    @asyncio.coroutine
    def get(cls, **kwargs):
        repo = yield from cls.objects.get(**kwargs)
        return repo

    @asyncio.coroutine
    def update_code(self):
        """Updates the repository's code. It is just a wrapper for
        self.poller.poll, so I can handle exceptions here."""

        try:
            yield from self.poller.poll()
            clone_status = 'done'
        except CloneException:
            clone_status = 'clone-exception'

        self.clone_status = clone_status
        yield from self.save()

    def schedule(self):
        """Schedules all needed actions for a repository. The actions are:

        * Update source code using ``self.update_code``
        * Starts builds that are pending using
          ``self.build_manager.start_pending``."""

        self.log('Scheduling {url}'.format(url=self.url))
        # we store this hashes so we can remove it from the scheduler when
        # we remove the repository.
        sched_hash = scheduler.add(self.update_code, self.update_seconds)
        _scheduler_hashes[self.url] = sched_hash
        start_pending_hash = scheduler.add(
            self.build_manager.start_pending, 120)
        _scheduler_hashes['{}-start-pending'.format(
            self.url)] = start_pending_hash

    @classmethod
    @asyncio.coroutine
    def schedule_all(cls):
        """ Schedule all repositories. """

        repos = yield from cls.objects.all().to_list()
        for repo in repos:
            repo.schedule()

    @asyncio.coroutine
    def add_slave(self, slave):
        self.slaves
        slaves = yield from self.slaves
        slaves.append(slave)
        self.slaves = slaves
        yield from self.save()
        return slave

    @asyncio.coroutine
    def remove_slave(self, slave):
        slaves = yield from self.slaves
        slaves.pop(slaves.index(slave))
        yield from self.update(set__slaves=slaves)
        return slave

    @asyncio.coroutine
    def add_or_update_branch(self, branch_name, notify_only_latest=False):
        """Adds a new branch to this repository. If the branch
        already exists updates it with a new value."""

        # this is a shitty way of doing this. What is the
        # better way?
        def get_branch(branch_name):
            for b in self.branches:
                if b.name == branch_name:
                    return b

        branch = get_branch(branch_name)
        if branch:
            branch.notify_only_latest = notify_only_latest
        else:
            branch = RepositoryBranch(name=branch_name,
                                      notify_only_latest=notify_only_latest)
            self.branches.append(branch)

        yield from self.save()

    @asyncio.coroutine
    def remove_branch(self, branch_name):
        """Removes a branch from this repository."""

        yield from self.update(pull__branches__name=branch_name)

    @asyncio.coroutine
    def get_latest_revision_for_branch(self, branch):
        """ Returns the latest revision for a given branch
        :param branch: branch name
        """
        latest = RepositoryRevision.objects.filter(
            repository=self, branch=branch).order_by('-commit_date')

        latest = yield from latest.first()

        return latest

    @asyncio.coroutine
    def get_latest_revisions(self):
        """ Returns the latest revision for all known branches
        """
        branches = yield from self.get_known_branches()
        revs = {}
        for branch in branches:
            rev = yield from self.get_latest_revision_for_branch(branch)
            revs[branch] = rev

        return revs

    @asyncio.coroutine
    def get_known_branches(self):
        """ Returns the names for the branches that already have some
        revision here.
        """
        branches = yield from RepositoryRevision.objects.filter(
            repository=self).distinct('branch')

        return branches

    @asyncio.coroutine
    def add_revision(self, branch, commit, commit_date, author, title):
        """ Adds a revision to the repository.
        :param commit: commit uuid
        :param branch: branch name
        :param commit_date: commit's date (on authors time)
        """
        revision = RepositoryRevision(repository=self, commit=commit,
                                      branch=branch, commit_date=commit_date,
                                      author=author, title=title)
        yield from revision.save()
        return revision

    @asyncio.coroutine
    def add_builds_for_slave(self, buildset, slave, builders=[]):
        yield from self.build_manager.add_builds_for_slave(
            buildset, slave, builders=[])


class RepositoryRevision(Document):
    repository = ReferenceField(Repository, required=True)
    commit = StringField(required=True)
    branch = StringField(required=True)
    author = StringField(required=True)
    title = StringField(required=True)
    commit_date = DateTimeField(required=True)

    @classmethod
    @asyncio.coroutine
    def get(cls, **kwargs):
        ret = yield from cls.objects.get(**kwargs)
        return ret
