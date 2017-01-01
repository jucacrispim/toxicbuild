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

from abc import ABCMeta, abstractmethod
import asyncio
import os
from toxicbuild.core.exceptions import VCSError
from toxicbuild.core.utils import (exec_cmd, inherit_docs, string2datetime,
                                   datetime2string, utc2localtime,
                                   localtime2utc, LoggerMixin)


class VCS(LoggerMixin, metaclass=ABCMeta):

    """ Generic inteface to a vcs (clone, fetch, get revisions etc...).
    """
    vcsbin = None

    def __init__(self, workdir):
        """:param workdir: Directory where repository will be cloned and
        all action will happen.
        """
        self.workdir = workdir

    @asyncio.coroutine
    def exec_cmd(self, cmd, cwd=None):
        """ Executes a shell command. If ``cwd`` is None ``self.workdir``
        will be used.

        :param cwd: Directory where the command will be executed.
        """
        if cwd is None:
            cwd = self.workdir

        ret = yield from exec_cmd(cmd, cwd)
        return ret

    def workdir_exists(self):
        """ Informs if the workdir for this vcs exists
        """
        return os.path.exists(self.workdir)

    @abstractmethod  # pragma no branch
    @asyncio.coroutine
    def clone(self, url):
        """ Clones a repository into ``self.workdir``
        :param url: repository url
        """

    @abstractmethod  # pragma no branch
    @asyncio.coroutine
    def fetch(self):
        """ Fetch changes from remote repository
        """

    @abstractmethod  # pragma no branch
    @asyncio.coroutine
    def checkout(self, named_tree):
        """ Checkout to ``named_tree``
        :param named_tree: A commit, branch, tag...
        """

    @abstractmethod  # pragma no branch
    @asyncio.coroutine
    def pull(self, branch_name):
        """ Pull changes from ``branch_name`` on remote repo.

        :param branch_name: A branch name, like 'master'.
        """

    @abstractmethod  # pragma no branch
    @asyncio.coroutine
    def has_changes(self):
        """ Informs if there are new revisions in the repository
        """

    @abstractmethod  # pragma no branch
    @asyncio.coroutine
    def get_revisions(self, since={}, branches=None):
        """ Returns the revisions for ``branches`` since ``since``.
        :param since: dictionary in the format: {branch_name: since_date}.
          ``since`` is a datetime object.
        :param branches: A list of branches to look for new revisions. If
          ``branches`` is None all remote branches will be used.
        """

    @abstractmethod  # pragma no branch
    @asyncio.coroutine
    def get_revisions_for_branch(self, branch, since=None):
        """ Returns the revisions for ``branch`` since ``since``.
        If ``since`` is None, all revisions will be returned.
        :param branch: branch name
        :param since: datetime
        """

    @abstractmethod  # pragma no branch
    @asyncio.coroutine
    def get_remote_branches(self):
        """ Returns a list of the remote branches available.
        """


@inherit_docs
class Git(VCS):

    """ An interface to git version control system
    """

    vcsbin = 'git'
    # this date_format is used to ask git about revisions since
    # some date
    date_format = '%a %b %d %H:%M:%S %Y'

    @asyncio.coroutine
    def clone(self, url):

        cmd = '%s clone %s %s --recursive' % (self.vcsbin, url, self.workdir)
        # we can't go to self.workdir while we do not clone the repo
        yield from self.exec_cmd(cmd, cwd='.')

    @asyncio.coroutine
    def fetch(self):
        cmd = '%s %s' % (self.vcsbin, 'fetch')

        fetched = yield from self.exec_cmd(cmd)
        return fetched

    @asyncio.coroutine
    def checkout(self, named_tree):

        cmd = '{} checkout {}'.format(self.vcsbin, named_tree)
        yield from self.exec_cmd(cmd)

    @asyncio.coroutine
    def pull(self, branch_name):

        cmd = '{} pull --no-edit origin {}'.format(self.vcsbin, branch_name)

        ret = yield from self.exec_cmd(cmd)
        return ret

    @asyncio.coroutine
    def has_changes(self):
        ret = yield from self.fetch()
        return bool(ret)

    @asyncio.coroutine
    def update_submodule(self):
        cmd = '{} submodule init'.format(self.vcsbin)
        yield from self.exec_cmd(cmd)
        cmd = '{} submodule update'.format(self.vcsbin)
        ret = yield from self.exec_cmd(cmd)
        return ret

    @asyncio.coroutine
    def get_revisions(self, since={}, branches=None):

        # this must be called everytime so we sync our repo
        # with the remote repo and then we can see new branches
        yield from self.fetch()
        remote_branches = yield from self.get_remote_branches()
        remote_branches = branches or remote_branches
        revisions = {}
        for branch in remote_branches:
            try:
                yield from self.checkout(branch)
                yield from self.pull(branch)
                since_date = since.get(branch)

                revs = yield from self.get_revisions_for_branch(branch,
                                                                since_date)
                revisions[branch] = revs
            except Exception as e:
                msg = 'Error fetching changes. {}'.format(str(e))
                self.log(msg)

        return revisions

    @asyncio.coroutine
    def get_revisions_for_branch(self, branch, since=None):

        # hash | commit date | author | title
        cmd = '{} log --pretty=format:"%H | %ad | %an | %s" '.format(
            self.vcsbin)
        if since:
            # Here we change the time to localtime since we can't get
            # utc time in git commits unless we are using git 2.7+
            localtime = utc2localtime(since)
            date = datetime2string(localtime, self.date_format)
            self.log('get revisions for branch {} since {}'.format(branch,
                                                                   date),
                     level='debug')
            cmd += '--since="%s" ' % date

        cmd += '--date=local'
        last_revs = [r for r in (yield from self.exec_cmd(cmd)).split('\n')
                     if r]

        last_revs.reverse()
        revisions = []

        for rev in last_revs:
            rev_uuid, date, author, title = rev.split(' | ')
            date = string2datetime(date.strip(), dtformat=self.date_format)
            # Here we change the date from git, that is in localtime to
            # utc before saving to database.
            date = localtime2utc(date)
            revisions.append({'commit': rev_uuid.strip(), 'commit_date': date,
                              'author': author, 'title': title})

        # The thing here is that the first revision in the list
        # is the last one consumed on last time
        return revisions[1:]

    @asyncio.coroutine
    def get_remote_branches(self):
        yield from self.fetch()
        cmd = '%s branch -r' % self.vcsbin

        out = yield from self.exec_cmd(cmd)
        msg = 'Remote branches: {}'.format(out)
        self.log(msg, level='debug')
        remote_branches = out.split('\n')
        # master, with some shitty arrow...
        remote_branches.pop(0)
        return [b.strip().split('/')[1] for b in remote_branches]


VCS_TYPES = {'git': Git}


def get_vcs(vcs_type):
    """ Retuns a subclass of :class:`toxicbuild.core.vcs.VCS` for ``vcs_type``
    """
    vcs = VCS_TYPES.get(vcs_type)
    if not vcs:
        raise VCSError('VCS not found for {}'.format(vcs_type))
    return vcs
