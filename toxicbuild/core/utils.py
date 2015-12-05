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
from datetime import datetime, timezone, timedelta
import importlib
import logging
import os
from subprocess import PIPE
import sys
import time
from toxicbuild.core.exceptions import ExecCmdError, ConfigError


@asyncio.coroutine
def exec_cmd(cmd, cwd, **envvars):
    """ Executes a shell command. Raises with stderr if return code > 0
    :param cmd: command to run.
    :param cwd: Directory to execute the command.
    """

    envvars = _get_envvars(envvars)

    ret = yield from asyncio.create_subprocess_shell(
        cmd, stdout=PIPE, stderr=PIPE, cwd=cwd, env=envvars)

    stdout, stderr = yield from ret.communicate()
    if int(ret.returncode) > 0:
        output = stderr.decode().strip()
        if not output:
            output = stdout.decode().strip()
        raise ExecCmdError(output)

    return stdout.decode().strip()


def _get_envvars(envvars):
    """Returns environment variables to be used in shell. Does the
    interpolation of values using the current values from the envvar
    and the values passed as parameters. """

    newvars = {}
    for var, value in envvars.items():
        if var in value:
            current = os.environ.get(var, '')
            value = value.replace(var, current)

        newvars[var] = value

    return newvars


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


def log(msg, level='info'):
    log = getattr(logging, level)
    log(msg)


def datetime2string(dt, dtformat='%a %b %d %H:%M:%S %Y %z'):
    return datetime.strftime(dt, dtformat)


def string2datetime(dtstr, dtformat='%a %b %d %H:%M:%S %Y %z'):
    return datetime.strptime(dtstr, dtformat)


def now():
    """ Returns the localtime with timezone info. """

    off = time.localtime().tm_gmtoff
    tz = timezone(timedelta(seconds=off))
    return datetime.now(tz=tz)


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
                try:
                    parfunc = getattr(parent, name)
                except:
                    continue
                if parfunc and getattr(parfunc, '__doc__', None):
                    func.__doc__ = parfunc.__doc__
                    break
    return cls


@asyncio.coroutine
def read_stream(reader):
    """ Reads the input stream. First reads the bytes until the first \n.
    These first bytes are the length of the full message.

    :param reader: An instance of :class:`asyncio.StreamReader`
    """

    data = yield from reader.read(1)
    if not data or data == b'\n':
        raw_data = b''
    else:
        char = None
        while char != b'\n' and char != b'':
            char = yield from reader.read(1)
            data += char

        len_data = int(data)

        raw_data = yield from reader.read(1024)
        while len(raw_data) < len_data:
            raw_data += yield from reader.read(len_data)

    return raw_data


@asyncio.coroutine
def write_stream(writer, data):
    """ Writes ``data`` to output. Encodes data to utf-8 and prepend the
    lenth of the data before sending it.

    :param writer: An instance of asyncio.StreamWriter
    :param data: String data to be sent.
    """

    data = data.encode('utf-8')
    data = '{}\n'.format(len(data)).encode('utf-8') + data
    writer.write(data)
    yield from writer.drain()


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
