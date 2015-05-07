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
import datetime
import os
from toxicbuild.core.exceptions import VCSError, ImpossibillityError
from toxicbuild.core.utils import exec_cmd, log, inherit_docs


class VCS:

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

    def log(self, msg):
        vcsmsg = '{}: {}'.format(self.vcsbin, msg)
        log(vcsmsg)

    @asyncio.coroutine
    def clone(self, url):  # pragma: no cover
        """ Clones a repository into ``self.workdir``
        :param url: repository url
        """
        raise NotImplementedError

    @asyncio.coroutine
    def fetch(self):  # pragma: no cover
        """ Fetch changes from remote repository
        """
        raise NotImplementedError

    @asyncio.coroutine
    def checkout(self, named_tree):  # pragma: no cover
        """ Checkout to ``named_tree``
        :param named_tree: A commit, branch, tag...
        """
        raise NotImplementedError

    @asyncio.coroutine
    def pull(self, branch_name):  # pragma: no cover
        """ Pull changes from ``branch_name`` on remote repo.

        :param branch_name: A branch name, like 'master'.
        """

        raise NotImplementedError

    @asyncio.coroutine
    def has_changes(self):  # pragma: no cover
        """ Informs if has changes on repository
        """
        raise NotImplementedError

    @asyncio.coroutine
    def get_revisions(self, since={}):  # pragma: no cover
        """ Returns the revisions for all branches since ``since``.
        :param since: dictionary in the format: {branch_name: since_date}.
          ``since`` is a datetime object.
        """
        # do not change since dict or satan will catch you.
        raise NotImplementedError

    @asyncio.coroutine
    def get_revisions_for_branch(self, branch, since=None):  # pragma: no cover
        """ Returns the revisions for ``branch`` since ``since``.
        If ``since`` is None, all revisions will be returned.
        :param branch: branch name
        :param since: datetime
        """
        raise NotImplementedError

    @asyncio.coroutine
    def get_remote_branches(self):  # pragma: no cover
        """ Returns a list of the remote branches available.
        """
        raise NotImplementedError

    def commit(self):  # pragma: no cover
        """ Not a chance. It's not made to change your repository
        """
        msg = 'Not a chance. You can\'t change anything here.'
        raise ImpossibillityError(msg)


@inherit_docs
class Git(VCS):

    """ An interface to git version control system
    """

    vcsbin = 'git'
    # this date_format is used to ask git about revisions since
    # some date
    date_format = '%a %b %d %H:%M:%S %Y %z'

    @asyncio.coroutine
    def clone(self, url):
        self.log('cloning {} into {}'.format(url, self.workdir))

        cmd = '%s clone %s %s' % (self.vcsbin, url, self.workdir)
        # we can't go to self.workdir while we do not clone the repo
        yield from self.exec_cmd(cmd, cwd='.')

    @asyncio.coroutine
    def fetch(self):
        self.log('fetching changes for {}'.format(self.workdir))

        cmd = '%s %s origin' % (self.vcsbin, 'fetch')
        fetched = yield from self.exec_cmd(cmd)
        return fetched

    @asyncio.coroutine
    def checkout(self, named_tree):

        self.log('checking out {} to {}'.format(self.workdir, named_tree))

        cmd = '{} checkout {}'.format(self.vcsbin, named_tree)
        yield from self.exec_cmd(cmd)

    @asyncio.coroutine
    def pull(self, branch_name):

        self.log('pulling changes from {} brach {}'.format(self.workdir,
                                                           branch_name))
        cmd = '{} pull --no-edit origin {}'.format(self.vcsbin, branch_name)

        yield from self.exec_cmd(cmd)

    @asyncio.coroutine
    def get_revisions(self, since={}):

        remote_branches = yield from self.get_remote_branches()
        revisions = {}
        for branch in remote_branches:
            since_date = since.get(branch)

            revs = yield from self.get_revisions_for_branch(branch, since_date)
            revisions[branch] = revs

        return revisions

    @asyncio.coroutine
    def get_revisions_for_branch(self, branch, since=None):

        self.log('getting revisions for {} on branch {}'.format(self.workdir,
                                                                branch))

        cmd = '{} log --pretty=format:"%H | %ad" '.format(self.vcsbin)
        if since:
            date = datetime.datetime.strftime(since, self.date_format)
            cmd += '--since="%s"' % date

        last_revs = [r for r in (yield from self.exec_cmd(cmd)).split('\n')
                     if r]
        last_revs.reverse()
        revisions = []

        for rev in last_revs:
            rev_uuid, date = rev.split('|')
            date = datetime.datetime.strptime(date.strip(), self.date_format)
            revisions.append({'commit': rev_uuid.strip(), 'commit_date': date})

        return revisions

    @asyncio.coroutine
    def get_remote_branches(self):
        self.log('getting remote branches for {}'.format(self.workdir))

        cmd = '%s branch -r' % self.vcsbin

        remote_branches = yield from self.exec_cmd(cmd)
        return remote_branches.split('\n')

    @asyncio.coroutine
    def has_changes(self):
        fetched = yield from self.fetch()
        return bool(fetched)


VCS_TYPES = {'git': Git}


def get_vcs(vcs_type):
    """ Retuns a subclass of :class:`toxicbuild.core.vcs.VCS` for ``vcs_type``
    """
    vcs = VCS_TYPES.get(vcs_type)
    if not vcs:
        raise VCSError('VCS not found for {}'.format(vcs_type))
    return vcs
