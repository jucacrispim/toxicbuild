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
from datetime import datetime
import os
from toxicbuild.core import get_vcs
from toxicbuild.core.exceptions import ExecCmdError
from toxicbuild.core.utils import(
    load_module_from_file, exec_cmd, log, datetime2string)
from toxicbuild.slave.contextmanagers import change_dir
from toxicbuild.slave.exceptions import BuilderNotFound


class BuildManager:

    """ A manager for remote build requests
    """

    def __init__(self, protocol, repo_url, vcs_type, branch, named_tree):
        self.protocol = protocol
        self.repo_url = repo_url
        self.vcs = get_vcs(vcs_type)(self.workdir)
        self.branch = branch
        self.named_tree = named_tree
        self.configfile = os.path.join(self.workdir, 'toxicbuild.conf')
        self._configmodule = None

    @property
    def configmodule(self):
        if not self._configmodule:
            self._configmodule = load_module_from_file(self.configfile)
        return self._configmodule

    @property
    def workdir(self):
        """ The directory where the source code of this repository is
        cloned into
        """
        workdir = self.repo_url.replace('/', '-').replace('@', '').replace(
            ':', '')
        return os.path.join('src', workdir)

    @asyncio.coroutine
    def update_and_checkout(self):
        """ Fetches changes on repository and checkout to ``self.named_tree``.
        If the repository was not cloned before, clones it first

        """
        if not self.vcs.workdir_exists():
            yield from self.vcs.clone(self.repo_url)

        # yield from self.vcs.fetch()

        yield from self.vcs.checkout(self.branch)
        yield from self.vcs.pull(self.branch)
        yield from self.vcs.checkout(self.named_tree)

    # the whole purpose of toxicbuild is this!
    # see the git history and look for the first versions.
    # First thing I changed on buildbot was to add the possibility
    # to load builers from a config file.
    def list_builders(self):
        """ Returns a list with all builders names for this branch
        based on toxicbuild.conf file
        """

        builders = [b['name'] for b in self.configmodule.BUILDERS
                    if (b.get('branch') == self.branch or b.get(
                        'branch')is None)]

        return builders

    def load_builder(self, name):
        """ Load a builder from toxicbuild.conf
        :param name: builder name
        """

        try:
            bdict = [b for b in self.configmodule.BUILDERS if (b.get(
                'branch') is None and b['name'] == name) or (b.get(
                    'branch') == self.branch and b['name'] == name)][0]
        except IndexError:
            msg = 'builder {} does not exist for {} branch {}'.format(
                name, self.repo_url, self.branch)
            raise BuilderNotFound(msg)

        builder = Builder(self, bdict['name'], self.workdir)

        for sdict in bdict['steps']:
            sname, command = sdict['name'], sdict['command']
            step = BuildStep(sname, command)
            builder.steps.append(step)

        return builder

    # kind of wierd place for this thing
    @asyncio.coroutine
    def send_info(self, info):
        yield from self.protocol.send_response(code=0, body=info)


class Builder:

    """ A builder executes build steps. Builders are configured in
    the toxicbuild.conf file
    """

    def __init__(self, manager, name, workdir):
        """:param manager: instance of :class:`toxicbuild.slave.BuildManager`.
        :param name: name for this builder.
        :param workdir: directory where the steps will be executed
        """
        self.manager = manager
        self.name = name
        self.workdir = workdir
        self.steps = []

    @asyncio.coroutine
    def build(self):
        build_status = None
        build_info = {'steps': [],
                      'status': 'running',
                      'started': datetime2string(datetime.now()),
                      'finished': None}

        with change_dir(self.workdir):
            self.manager.send_info(build_info)

            for step in self.steps:
                msg = 'Executing %s' % step.command
                log(msg)
                step_info = {'status': 'running',
                             'cmd': step.command,
                             'name': step.name,
                             'started': datetime2string(datetime.now()),
                             'finished': None,
                             'output': ''}

                yield from self.manager.send_info(step_info)

                step_info.update((yield from step.execute()))
                step_info.update({'finished': dtformat(datetime.now())})
                yield from self.manager.send_info(step_info)

                # here is: if build_status is something other than None
                # or success (ie failed) we don't change it anymore, the build
                # is failed anyway.
                if build_status is None or build_status == 'success':
                    build_status = step_info['status']

                build_info['steps'].append(step_info)

        build_info['status'] = build_status
        build_info['total_steps'] = len(self.steps)
        return build_info


class BuildStep:

    def __init__(self, name, cmd):
        """:param name: name for the command
        :param cmd: a string the be executed in a shell
        """
        self.name = name
        self.command = cmd

    @asyncio.coroutine
    def execute(self):
        step_status = {}
        try:
            output = yield from exec_cmd(self.command, cwd='.')
            status = 'success'
        except ExecCmdError as e:
            output = e.args[0]
            status = 'fail'

        step_status['status'] = status
        step_status['output'] = output

        return step_status
