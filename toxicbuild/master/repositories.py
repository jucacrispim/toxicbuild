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
import re
import shutil
from threading import Thread
from mongomotor import Document
from mongomotor.fields import (StringField, IntField, ReferenceField,
                               DateTimeField, ListField, BooleanField)
from tornado.platform.asyncio import to_asyncio_future
from toxicbuild.core import utils
from toxicbuild.master.scheduler import scheduler
from toxicbuild.master.build import Slave, Build, Builder, BuildManager
from toxicbuild.master.pollers import Poller


# The thing here is: When a repository poller is scheduled, I need to
# keep track of the hashes so I can remove it from the scheduler
# when needed.
# The format is {repourl: hash}
_scheduler_hashes = {}


class Repository(Document):
    name = StringField(required=True, unique=True)
    url = StringField(required=True, unique=True)
    update_seconds = IntField(default=300, required=True)
    vcs_type = StringField(required=True, default='git')
    slaves = ListField(ReferenceField(Slave))
    notify_only_latest = BooleanField(default=False)

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
            self._poller_instance = Poller(
                self, vcs_type, self.workdir,
                notify_only_latest=self.notify_only_latest)

        return self._poller_instance

    @asyncio.coroutine
    def get_status(self):
        is_running = (yield from to_asyncio_future(Build.objects.filter(
            repository=self, status='running').count())) > 0

        if is_running:
            status = 'running'
        else:
            try:
                status = (yield from to_asyncio_future(Build.objects.filter(
                    repository=self).order_by('-started').first())).status
            except AttributeError:
                # ugly mongomotor error for no first thing
                status = ''

        return status

    @classmethod
    @asyncio.coroutine
    def create(cls, name, url, update_seconds, vcs_type, slaves=None):
        """ Creates a new repository and schedule it. """
        slaves = slaves or []

        repo = cls(url=url, update_seconds=update_seconds, vcs_type=vcs_type,
                   slaves=slaves, name=name)
        yield from to_asyncio_future(repo.save())
        repo.schedule()
        return repo

    @asyncio.coroutine
    def remove(self):
        """ Removes all builds and builders and revisions related to the
        repository, removes the poller from the scheduler, removes the
        source code from the file system and then removes the repository.
        """

        builds = Build.objects.filter(repository=self)
        yield from to_asyncio_future(builds.delete())

        builders = Builder.objects.filter(repository=self)
        yield from to_asyncio_future(builders.delete())

        revisions = RepositoryRevision.objects.filter(repository=self)
        yield from to_asyncio_future(revisions.delete())

        try:
            sched_hash = _scheduler_hashes[self.url]
            scheduler.remove_by_hash(sched_hash)
        except KeyError:  # pragma no cover
            # means the repository was not scheduled
            pass

        Thread(target=shutil.rmtree, args=[self.workdir]).start()

        yield from to_asyncio_future(self.delete())

    @classmethod
    @asyncio.coroutine
    def get(cls, **kwargs):
        repo = yield from to_asyncio_future(cls.objects.get(**kwargs))
        return repo

    def schedule(self):
        """ Adds self.poller.poll() to the scheduler. """

        self.log('Scheduling {url}'.format(url=self.url))
        sched_hash = scheduler.add(self.poller.poll, self.update_seconds)
        _scheduler_hashes[self.url] = sched_hash

    @classmethod
    @asyncio.coroutine
    def schedule_all(cls):
        """ Schedule all repositories. """

        repos = yield from to_asyncio_future(cls.objects.all().to_list())
        for repo in repos:
            repo.schedule()

    @asyncio.coroutine
    def add_slave(self, slave):
        self.slaves.append(slave)
        yield from to_asyncio_future(self.save())
        return slave

    @asyncio.coroutine
    def remove_slave(self, slave):
        self.slaves.pop(self.slaves.index(slave))
        yield from to_asyncio_future(self.save())
        return slave

    @asyncio.coroutine
    def get_latest_revision_for_branch(self, branch):
        """ Returns the latest revision for a given branch
        :param branch: branch name
        """
        latest = RepositoryRevision.objects.filter(
            repository=self, branch=branch).order_by('-commit_date')

        try:
            latest = yield from to_asyncio_future(latest.first())
        except AttributeError:
            # when first is None
            latest = None

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
        branches = yield from to_asyncio_future(
            RepositoryRevision.objects.distinct('branch'))

        return branches

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

    @asyncio.coroutine
    def add_build(self, **kwargs):
        yield from self.build_manager.add_build(**kwargs)

    def log(self, msg):
        msg = '[{}] - {}'.format(type(self).__name__, msg)
        utils.log(msg)


class RepositoryRevision(Document):
    repository = ReferenceField(Repository, required=True)
    commit = StringField(required=True)
    branch = StringField(required=True)
    commit_date = DateTimeField(required=True)

    @classmethod
    @asyncio.coroutine
    def get(cls, **kwargs):
        ret = yield from to_asyncio_future(cls.objects.get(**kwargs))
        return ret
