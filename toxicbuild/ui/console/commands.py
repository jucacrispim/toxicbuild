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
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

from toxicbuild.common.interfaces import RepositoryInterface
from toxicbuild.ui import translate


class ConsoleCommand:

    def __init__(self, requester):
        self.requester = requester

    name = None
    help_text = None
    example = None
    params = {}

    def get_help(self):
        return self.help_text

    def get_params(self):
        return self.params

    def get_name(self):
        return self.name

    async def execute(self):
        raise NotImplementedError


class ConsoleCommandGroup(ConsoleCommand):

    commands = []

    def __init__(self, requester):
        super().__init__(requester)
        self.commands = [cls(self.requester) for cls in self.commands]


###################
# No group commands
###################


class RepoAddCommand(ConsoleCommand):

    name = 'repo-add'
    help_text = translate('Add a new repository to the system')
    example = 'repo-add my-repo https://host/my-repo.git parallel_builds=1'
    params = [
        {
            'name': 'name',
            'help': 'The repository name',
            'required': True,
        },
        {
            'name': 'url',
            'help': 'The url to clone/update the repository',
            'required': True,
        },
        {
            'name': 'slaves',
            'help': 'A list of slave names to enable to the repo.',
            'required': False,
        },
        {
            'name': 'parallel_builds',
            'help': 'The number of parallel builds allowed.',
            'required': False,
        },
        {
            'name': 'envvars',
            'help': 'Environmnet variables for the repo.',
            'required': False
        },
        {
            'name': 'branches',
            'help': 'List of branch configurations.',
            'required': False,
        }
    ]


class RepoListCommand(ConsoleCommand):

    name = 'repo-list'
    help_text = translate('List the repositories')

    async def execute(self):
        repos = await RepositoryInterface.list(self.requester)
        return repos


#####################
# Repo group commands
#####################

class RepoShowCommand(ConsoleCommand):

    name = 'repo-show'
    help_text = 'Display the repository information'


class RepoRemoveCommand(ConsoleCommand):

    name = 'repo-remove'
    help_text = 'Remove the slave from the system'


class RepoAddSlaveCommand(ConsoleCommand):

    name = 'repo-add-slave'
    help_text = 'Add a slave to the list of available slaves in this \
repository.'
    params = [
        {
            'name': 'slave-name',
            'help': 'The name of a slave',
            'required': True,
        }
    ]


class RepoRmSlaveCommand(ConsoleCommand):

    name = 'repo-rm-slave'
    help_text = 'Remove a slave from the available slaves list.'
    params = [
        {
            'name': 'slave-name',
            'help': 'The name of a slave',
            'required': True,
        }
    ]


class RepoAddBranchCommand(ConsoleCommand):

    name = 'repo-add-branch'
    help_text = 'Add a branch config to the repository'
    params = [
        {
            'name': 'branch-name',
            'help': 'The branch name. Wildcars are allowed',
            'required': True
        },
        {
            'name': 'notify_only_latest',
            'help': 'If we should create builds for all revisions or only \
for the lastest one.',
            'required': True,
        }
    ]


class RepoRmBranchCommand(ConsoleCommand):

    name = 'repo-rm-branch'
    help_text = 'Remove a branch config from the repository'
    params = [
        {
            'name': 'branch-name',
            'help': 'The branch name. Wildcars are allowed',
            'required': True
        }
    ]


class RepoUpdateCommand(ConsoleCommand):

    name = 'repo-update'
    help_text = 'Update the repository information'


class RepoStartBuildCommand(ConsoleCommand):

    name = 'repo-start-build'
    help_text = 'Start a/some build(s) in the repository.'
    params = [
        {
            'name': 'branch',
            'help': 'A branch name',
            'required': True,
        },
        {
            'name': 'builder-name',
            'help': 'A builder name',
            'required': False,
        },
        {
            'name': 'named_tree',
            'help': 'A commit sha or tag',
            'required': False,
        }
    ]


class RepoCancelBuildCommand(ConsoleCommand):

    name = 'repo-cancel-build'
    help_text = 'Cancel a pending build'
    params = [
        {
            'name': 'build-number',
            'required': True,
        }
    ]


class RepoEnableCommand(ConsoleCommand):

    name = 'repo-enable'
    help_text = 'Enable the repository'


class RepoDisableCommand(ConsoleCommand):

    name = 'repo-disable'
    help_text = 'Disable the repository'


class RepoAddEnvvarsCommand(ConsoleCommand):

    name = 'repo-add-envvars'
    help_text = 'Add envvars to the repository'
    params = [
        {
            'name': 'envvars',
            'help': 'Environment variables in the format VAR=val',
            'required': True
        }
    ]


class RepoRmEnvvarsCommand(ConsoleCommand):

    name = 'repo-rm-envvars'
    help_text = 'Remove envvars from the repository',
    params = [
        {
            'name': 'envvars',
            'help': 'Environment variables names\' list',
            'required': True,
        }
    ]


class RepoReplaceEnvvarsCommand(ConsoleCommand):

    name = 'repo-replace-envvars'
    help_text = 'Replace the repository\'s envvars'
    params = [
        {
            'name': 'envvars',
            'help': 'Environment variables in the format VAR=val',
            'required': True
        }
    ]


class RepoCommandGroup(ConsoleCommandGroup):

    name = 'repo-use'
    help_text = translate('Interact with a repository')
    example = 'repo-use me/my-repo'
    params = [
        {
            'name': 'repository-name',
            'help': translate('The full name of a repository'),
            'required': True,
        }
    ]

    commands = [
        RepoShowCommand,
        RepoRemoveCommand,
        RepoUpdateCommand,
        RepoEnableCommand,
        RepoDisableCommand,
        RepoAddSlaveCommand,
        RepoRmSlaveCommand,
        RepoAddBranchCommand,
        RepoRmBranchCommand,
        RepoAddEnvvarsCommand,
        RepoRmEnvvarsCommand,
        RepoReplaceEnvvarsCommand,
        RepoStartBuildCommand,
        RepoCancelBuildCommand,
    ]
