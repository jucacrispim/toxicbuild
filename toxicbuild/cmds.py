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

"""Command line for the toxicbuild orchestrator.

Every toxicbuild component lives on its own repository, so they may have
conflicting dependencies. Because of that, ``toxicbuild setup`` installs
each component in its own virtualenv (see
:mod:`toxicbuild.environments`) and the orchestration is done by calling
the components' console scripts from inside their venvs.
"""

import os
from secrets import token_urlsafe
import shutil

from mando import Program
from toxicbuild.environments import get_all, CREATE_ORDER, START_ORDER


DEFAULT_USER_EMAIL = 'root@toxicbuild.local'
DEFAULT_USER_PASSWORD = 'toxicroot'

SLAVE_NAME = 'local-slave'
SLAVE_HOST = 'localhost'
SLAVE_PORT = 7777

program = Program()
command = program.command
arg = program.arg

main = program


def _get_components(root_dir, source='pypi', source_dir='~/mysrc',
                    components=None):
    """Returns the components instances to work with. If ``components``
    is not given, all the components are returned.
    """
    all_comps = get_all(root_dir, source=source, source_dir=source_dir)
    if not components:
        return all_comps

    names = [c.strip() for c in components.split(',') if c.strip()]
    return {name: all_comps[name] for name in names}


@command
def setup(root_dir, source='pypi', source_dir='~/mysrc', user_email=None,
          user_password=None, components=None, reset=False):
    """ Creates a new toxicbuild environment.

    Each component is installed in its own virtualenv under
    ``<root_dir>/venvs/<component>`` and its workdir is created inside
    ``<root_dir>``.

    :param root_dir: Root directory for the toxicbuild environment.
    :param --source: Where to install the components from. Either 'pypi'
      (default) or 'local'.
    :param --source-dir: Base directory containing the local sources of
      the components. Only used with ``--source=local``.
    :param --user-email: Email for the super user. Defaults to
      ``root@toxicbuild.local``
    :param --user-password: Password for the super user. Defaults to
      ``toxicroot``
    :param --components: A comma separated list of the components to
      setup. If not given, all the components are setup.
    :param --reset: Removes ``root_dir`` (venvs and workdirs) before
      creating the environment. The databases are not touched.
    """

    root_dir = os.path.expanduser(root_dir)
    source_dir = os.path.expanduser(source_dir)

    if reset:
        print('Removing `{}`'.format(root_dir))
        shutil.rmtree(root_dir, ignore_errors=True)

    os.makedirs(root_dir, exist_ok=True)

    comps = _get_components(root_dir, source, source_dir, components)

    user_email = user_email or DEFAULT_USER_EMAIL
    user_password = user_password or DEFAULT_USER_PASSWORD

    print('Creating toxicbuild environment on `{}`'.format(root_dir))

    tokens = {}

    # first the components that create their own token
    for name in CREATE_ORDER:
        comp = comps.get(name)
        if comp is None:
            continue

        tokens[name] = comp.setup()

    # now the master, which needs the secrets and poller tokens
    master = comps.get('master')
    if master is not None:
        master.install()
        tokens['master'] = master.create(
            secrets_token=tokens.get('secrets') or '',
            poller_token=tokens.get('poller') or '')

    # a super user to access the master and a local slave
    user_id = None
    if master is not None:
        user_id = master.create_user(user_email, user_password)

        if tokens.get('slave'):
            master.add_slave(SLAVE_NAME, SLAVE_HOST, SLAVE_PORT,
                             tokens['slave'], user_id)

    # and finally the components that connect to the master and the
    # notifications api
    cookie_secret = token_urlsafe()

    for name in ('integrations', 'ui'):
        comp = comps.get(name)
        if comp is None:
            continue

        comp.install()
        comp.create(access_token=tokens.get('master') or '',
                    output_token=tokens.get('notifications') or '',
                    root_user_id=user_id or '',
                    cookie_secret=cookie_secret)

    print('Environment on `{}` created.'.format(root_dir))
    print('Done!')


@command
def start(root_dir, loglevel=None, components=None):
    """ Starts all the toxicbuild components in ``root_dir``.

    :param root_dir: Root directory of the toxicbuild environment.
    :param --loglevel: Level for logging messages.
    :param --components: A comma separated list of the components to
      start. If not given, all the components are started.
    """

    comps = _get_components(root_dir, components=components)

    for name in START_ORDER:
        comp = comps.get(name)
        if comp is not None:
            comp.start(loglevel=loglevel)


@command
def stop(root_dir, components=None):
    """ Stops all the toxicbuild components in ``root_dir``.

    :param root_dir: Root directory of the toxicbuild environment.
    :param --components: A comma separated list of the components to
      stop. If not given, all the components are stopped.
    """

    comps = _get_components(root_dir, components=components)

    for name in reversed(START_ORDER):
        comp = comps.get(name)
        if comp is not None:
            comp.stop()


@command
def restart(root_dir, loglevel=None, components=None):
    """ Restarts all the toxicbuild components in ``root_dir``.

    :param root_dir: Root directory of the toxicbuild environment.
    :param --loglevel: Level for logging messages.
    :param --components: A comma separated list of the components to
      restart. If not given, all the components are restarted.
    """

    comps = _get_components(root_dir, components=components)

    for name in reversed(START_ORDER):
        comp = comps.get(name)
        if comp is not None:
            comp.restart(loglevel=loglevel)


if __name__ == '__main__':  # pragma no cover
    main()
