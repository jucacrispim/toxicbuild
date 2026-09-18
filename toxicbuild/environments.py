# -*- coding: utf-8 -*-

# Copyright 2024 Juca Crispim <juca@poraodojuca.net>

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

"""Each toxicbuild component lives on its own repository and may have
conflicting dependencies with the others. Because of that, a toxicbuild
environment has one virtualenv per component, all of them inside
``<root_dir>/venvs/<component>``.

This module knows how to create those venvs, install the component and
call the component's command line (``create``/``start``/``stop``/
``restart``) from inside the component's venv.
"""

import os
import re
import subprocess
import sys


__all__ = ['Component', 'ComponentError', 'ToxicBuildError', 'COMPONENTS',
           'CREATE_ORDER', 'START_ORDER', 'get_component', 'get_all',
           'get_token', 'get_user_id']


TOKEN_RE = re.compile(r'^TOKEN:(?P<token>.+)$', re.MULTILINE)
USER_ID_RE = re.compile(r'^USER_ID:(?P<user_id>.+)$', re.MULTILINE)


def get_token(output):
    """Extracts the access token from a component ``create`` output.

    :param output: The output of a component command.
    """
    match = TOKEN_RE.search(output or '')
    return match.group('token').strip() if match else None


def get_user_id(output):
    """Extracts the user id from a component ``create_user`` output.

    :param output: The output of a component command.
    """
    match = USER_ID_RE.search(output or '')
    return match.group('user_id').strip() if match else None


class ToxicBuildError(Exception):
    """Base exception for all toxicbuild errors."""


class ComponentError(ToxicBuildError):
    """Raised when a component command fails."""


class Component:
    """A toxicbuild component (a service) installed in its own venv.

    Subclasses must define :attr:`name`, :attr:`dist` and :attr:`entry`.
    """

    name = None
    """A short name for the component. Also the name of its workdir."""

    dist = None
    """The name of the distribution on the package index."""

    entry = None
    """The console script name for the component."""

    def __init__(self, root_dir, source='pypi', source_dir='~/mysrc'):
        """ :param root_dir: The root dir of the toxicbuild environment.
        :param source: Where to install the component from. Either 'pypi'
          or 'local'.
        :param source_dir: Base directory containing the local sources of
          the components. Only used when ``source`` is 'local'.
        """
        if self.name is None or self.dist is None or self.entry is None:
            raise NotImplementedError('name, dist and entry must be defined')

        self.root_dir = os.path.expanduser(root_dir)
        self.source = source
        self.source_dir = os.path.expanduser(source_dir)

    def __repr__(self):
        return '<{} name={}>'.format(type(self).__name__, self.name)

    @property
    def workdir(self):
        """The workdir for the component inside the environment root."""
        return os.path.join(self.root_dir, self.name)

    @property
    def venv_dir(self):
        """The directory of the component's virtualenv."""
        return os.path.join(self.root_dir, 'venvs', self.name)

    @property
    def bindir(self):
        return os.path.join(self.venv_dir, 'bin')

    @property
    def pip(self):
        return os.path.join(self.bindir, 'pip')

    @property
    def python(self):
        return os.path.join(self.bindir, 'python')

    @property
    def entrypoint(self):
        """The path of the component's console script."""
        return os.path.join(self.bindir, self.entry)

    def log(self, msg):
        print('[toxicbuild] {}'.format(msg))

    def _run(self, cmd, capture=True):
        """Runs a command. If ``capture`` the output is captured and
        returned, otherwise the command inherits the current stdio.

        Raises :class:`ComponentError` if the command fails.
        """
        self.log('running: {}'.format(' '.join(cmd)))

        if capture:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True)
            output = proc.stdout or ''
            sys.stdout.write(output)
            sys.stdout.flush()
        else:
            proc = subprocess.run(cmd)
            output = ''

        if proc.returncode != 0:
            raise ComponentError('`{}` exited with status {}'.format(
                cmd[0], proc.returncode))

        return output

    def run(self, *args):
        """Runs the component's console script with ``args``."""
        return self._run([self.entrypoint] + list(args))

    def create_venv(self):
        """Creates the virtualenv for this component if needed."""
        if os.path.exists(self.python):
            return

        self.log('creating venv for {} at {}'.format(self.name,
                                                     self.venv_dir))
        os.makedirs(os.path.dirname(self.venv_dir), exist_ok=True)
        self._run([sys.executable, '-m', 'venv', self.venv_dir])

    def install(self):
        """Creates the venv and installs the component in it."""
        self.create_venv()

        cmd = [self.pip, 'install']
        if self.source == 'local':
            cmd.append('-e')
            cmd.append(os.path.join(self.source_dir, self.dist))
        else:
            cmd.append(self.dist)

        self._run(cmd)

    def create(self):
        """Runs the component's ``create`` command.

        Returns the component's access token or ``None`` if the component
        does not create a token.
        """
        return get_token(self.run('create', self.workdir))

    def setup(self):
        """Installs the component and creates its environment. Returns
        the component's access token (if any)."""
        self.install()
        return self.create()

    def start(self, daemonize=True, loglevel=None):
        """Starts the component."""
        args = ['start', self.workdir]
        if daemonize:
            args.append('--daemonize')
        if loglevel:
            args += ['--loglevel', loglevel]

        return self._run([self.entrypoint] + args, capture=False)

    def stop(self):
        """Stops the component."""
        return self._run([self.entrypoint, 'stop', self.workdir],
                         capture=False)

    def restart(self, loglevel=None):
        """Restarts the component."""
        args = ['restart', self.workdir]
        if loglevel:
            args += ['--loglevel', loglevel]

        return self._run([self.entrypoint] + args, capture=False)


class Slave(Component):

    name = 'slave'
    dist = 'toxicslave'
    entry = 'toxicslave'


class Poller(Component):

    name = 'poller'
    dist = 'toxicpoller'
    entry = 'toxicpoller'


class Secrets(Component):

    name = 'secrets'
    dist = 'toxicsecrets'
    entry = 'toxicsecrets'


class Notifications(Component):

    name = 'notifications'
    dist = 'toxicnotifications'
    entry = 'toxicnotifications'

    def create(self):
        # the notifications `create` does not create an access token, so
        # we need a second call for it.
        self.run('create', self.workdir)
        return get_token(self.run('create_token', self.workdir))


class Master(Component):

    name = 'master'
    dist = 'toxicmaster'
    entry = 'toxicmaster'

    @property
    def conffile(self):
        return os.path.join(self.workdir, 'toxicmaster.conf')

    def create(self, secrets_token='', poller_token=''):
        """ Creates the master environment. The tokens for the
        secrets server and the poller must be passed.
        """
        output = self.run('create', self.workdir,
                          '--secrets-token', secrets_token,
                          '--poller-token', poller_token)
        return get_token(output)

    def create_user(self, email, password, superuser=True):
        """Creates a new user. Returns the user id."""
        args = ['create_user', self.conffile, '--email', email,
                '--password', password]
        if superuser:
            args.append('--superuser')

        return get_user_id(self.run(*args))

    def add_slave(self, name, host, port, token, owner, use_ssl=False,
                  validate_cert=False):
        """Adds a slave to the master installation."""
        args = ['add_slave', self.conffile, name, host, str(port), token,
                owner]
        if use_ssl:
            args.append('--use-ssl')
        if validate_cert:
            args.append('--validate-cert')

        return self.run(*args)


class Integrations(Component):

    name = 'integrations'
    dist = 'toxicintegrations'
    entry = 'toxicintegrations'

    def create(self, access_token='', output_token='', root_user_id='',
               cookie_secret=''):
        return self.run('create', self.workdir,
                        '--access-token', access_token,
                        '--output-token', output_token,
                        '--root-user-id', root_user_id,
                        '--cookie-secret', cookie_secret)


class UI(Component):

    name = 'ui'
    dist = 'toxicwebui'
    entry = 'toxicwebui'

    def create(self, access_token='', output_token='', root_user_id='',
               cookie_secret=''):
        return self.run('create', self.workdir,
                        '--access-token', access_token,
                        '--output-token', output_token,
                        '--root-user-id', root_user_id,
                        '--cookie-secret', cookie_secret)


COMPONENTS = {
    'slave': Slave,
    'poller': Poller,
    'secrets': Secrets,
    'notifications': Notifications,
    'master': Master,
    'integrations': Integrations,
    'ui': UI,
}

CREATE_ORDER = ['slave', 'poller', 'secrets', 'notifications']

START_ORDER = ['slave', 'poller', 'secrets', 'notifications', 'master',
               'integrations', 'ui']


def get_component(name, root_dir, **kwargs):
    """Returns an instance of the component called ``name``."""
    try:
        cls = COMPONENTS[name]
    except KeyError:
        raise ToxicBuildError('Unknown component {}'.format(name))

    return cls(root_dir, **kwargs)


def get_all(root_dir, **kwargs):
    """Returns a dict with all the components instances."""
    return {name: cls(root_dir, **kwargs) for name, cls in COMPONENTS.items()}
