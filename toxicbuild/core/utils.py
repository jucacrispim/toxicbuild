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
import importlib
import os
import resource
from subprocess import PIPE
import sys
from toxicbuild.core.exceptions import ExecCmdError, ConfigError


@asyncio.coroutine
def exec_cmd(cmd, cwd):
    """ Executes a shell command. Raises with stderr if return code > 0
    :param cmd: command to run.
    :param cwd: Directory to execute the command.
    """
    ret = yield from asyncio.create_subprocess_shell(
        cmd, stdout=PIPE, stderr=PIPE, cwd=cwd)
    stdout, stderr = yield from ret.communicate()
    if int(ret.returncode) > 0:
        raise ExecCmdError(stderr.decode().strip())

    return stdout.decode().strip()


def load_module_from_file(filename):
    """ Load a module from a source file
    :param filename: full path for file to be loaded.
    """
    fname, extension = filename.rsplit('.', 1)
    fname = fname.rsplit(os.sep, 1)[-1]
    source_file = importlib.machinery.SourceFileLoader(fname, filename)

    try:
        module = source_file.load_module()
    except FileNotFoundError:
        err_msg = 'Config file "%s" does not exist!' % (filename)
        raise FileNotFoundError(err_msg)
    except Exception as e:
        err_msg = 'There is something wrong with your file. '
        err_msg += 'The original exception was:\n{}'.format(e.args[0])
        raise ConfigError(err_msg)

    return module


def log(msg, output=sys.stdout):
    output.write('{}\n'.format(msg))


# inherit_docs thanks to Raymond Hettinger on stackoverflow
# stackoverflow.com/questions/8100166/inheriting-methods-docstrings-in-python
def inherit_docs(cls):
    """ Inherit docstrings from base classes' methods.
    Can be used as a decorator

    :param cls: Class that will inherit docstrings from its parents.
    """
    for name, func in vars(cls).items():
        if not func.__doc__:
            for parent in cls.__bases__:
                parfunc = getattr(parent, name)
                if parfunc and getattr(parfunc, '__doc__', None):
                    func.__doc__ = parfunc.__doc__
                    break
    return cls


# Sorry, but not willing to test  a daemonizer.
def daemonize(call, cargs, ckwargs, stdout, stderr,
              workdir, pidfile):  # pragma: no cover
    """ Run a callable as a daemon

    :param call: a callable.
    :param cargs: args to ``call``.
    :param ckwargs: kwargs to ``call``.
    :param stdout: daemon's stdout.
    :param stderr: daemon's stderr.
    :param workdir: daemon's workdir
    :param pidfile: pidfile's path
    """
    _create_daemon(stdout, stderr, workdir)
    pid = os.getpid()
    with open(pidfile, 'w') as f:
        f.write(str(pid))

    call(*cargs, **ckwargs)


def _create_daemon(stdout, stderr, workdir):  # pragma: no cover
    _fork_off_and_die()
    os.setsid()
    _fork_off_and_die()
    os.umask(0)
    os.chdir(workdir)
    _redirect_file_descriptors(stdout, stderr)


def _fork_off_and_die():  # pragma: no cover
    pid = os.fork()
    if pid != 0:
        sys.exit(0)


def _redirect_file_descriptors(stdout, stderr):  # pragma: no cover
    for fd in sys.stdout, sys.stderr:
        fd.flush()

    sys.stdout = open(stdout, 'a', 1)
    sys.stderr = open(stderr, 'a', 1)
