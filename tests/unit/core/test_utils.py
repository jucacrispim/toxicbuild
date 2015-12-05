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
import time
from unittest.mock import patch, Mock, MagicMock
import tornado
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.core import utils
from tests.unit.core import TEST_DATA_DIR


class UtilsTest(AsyncTestCase):

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_exec_cmd(self):

        # no assertions here because if no exceptions, it's ok.
        yield from utils.exec_cmd('ls', cwd='.')

    @gen_test
    def test_exec_cmd_with_error(self):

        with self.assertRaises(utils.ExecCmdError):
            # please, don't tell me you have a lsz command on your system.
            yield from utils.exec_cmd('lsz', cwd='.')

    @gen_test
    def test_exec_cmd_with_envvars(self):
        envvars = {'PATH': 'PATH:venv/bin',
                   'MYPROGRAMVAR': 'something'}

        cmd = 'echo $MYPROGRAMVAR'

        returned = yield from utils.exec_cmd(cmd, cwd='.', **envvars)

        self.assertEqual(returned, 'something')

    def test_get_envvars(self):
        envvars = {'PATH': 'PATH:venv/bin',
                   'MYPROGRAMVAR': 'something'}

        expected = {'PATH': '{}:venv/bin'.format(os.environ.get('PATH')),
                    'MYPROGRAMVAR': 'something'}

        returned = utils._get_envvars(envvars)

        self.assertEqual(returned, expected)

    def test_load_module_from_file_with_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            utils.load_module_from_file('/some/file/that/does/not/exist.conf')

    def test_load_module_from_file_with_some_error(self):
        filename = os.path.join(TEST_DATA_DIR, 'toxicbuild_error.conf')

        with self.assertRaises(utils.ConfigError):
            utils.load_module_from_file(filename)

    def test_load_module_from_file(self):
        filename = os.path.join(TEST_DATA_DIR, 'toxicbuild.conf')
        mod = utils.load_module_from_file(filename)

        self.assertEqual(mod.BLA, 'val')

    @patch.object(utils.logging, 'info', Mock())
    def test_log(self):
        utils.log('msg')
        self.assertTrue(utils.logging.info.called)

    def test_inherit_docs(self):

        class A:

            @asyncio.coroutine
            def m():
                """ some doc"""
                return True

        @utils.inherit_docs
        class B(A):

            @asyncio.coroutine
            def m():
                return False

        self.assertEqual(B.m.__doc__, A.m.__doc__)

    def test_datetime2string(self):
        dt = utils.now()
        expected = datetime.datetime.strftime(dt, '%a %b %d %H:%M:%S %Y %z')
        returned = utils.datetime2string(dt)

        self.assertEqual(returned, expected)

    def test_datetime2string_with_other_format(self):
        dt = utils.now()

        expected = datetime.datetime.strftime(dt, '%y %d')
        returned = utils.datetime2string(dt, dtformat='%y %d')

        self.assertEqual(returned, expected)

    def test_string2datetime(self):
        dt = utils.now()
        dtstr = dt.strftime('%a %b %d %H:%M:%S %Y %z')

        returned = utils.string2datetime(dtstr)
        tz = returned.utcoffset().total_seconds()
        self.assertEqual(tz, time.localtime().tm_gmtoff)

    def test_string2datetime_with_other_format(self):
        dt = utils.now()
        dtstr = dt.strftime('%a %b %z')
        returned = utils.string2datetime(dtstr, dtformat="%a %b %z")

        tz = returned.utcoffset().total_seconds()
        self.assertEqual(tz, time.localtime().tm_gmtoff)

    def test_utc2localtime(self):
        utc = datetime.datetime.now()
        local = utils.utc2localtime(utc)
        self.assertEqual(local.utcoffset().total_seconds(),
                         time.localtime().tm_gmtoff)

    def test_now(self):
        n = utils.now()
        self.assertEqual(n.utcoffset().total_seconds(),
                         time.localtime().tm_gmtoff)


class StreamUtilsTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        self.bad_data = b'\n'
        self.good_data = b'17\n{"action": "bla"}'
        giant = {'action': 'bla' * 1000}
        self.giant = str(giant).encode('utf-8')
        self.giant_data = b'3014\n' + self.giant
        self.data = b'{"action": "bla"}'

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_read_stream_without_data(self):
        reader = Mock()

        @asyncio.coroutine
        def read(limit):
            return self.bad_data
        reader.read = read

        ret = yield from utils.read_stream(reader)

        self.assertFalse(ret)

    @gen_test
    def test_read_stream_good_data(self):
        reader = Mock()

        self._rlimit = 0

        @asyncio.coroutine
        def read(limit):
            part = self.good_data[self._rlimit: limit + self._rlimit]
            self._rlimit += limit
            return part

        reader.read = read

        ret = yield from utils.read_stream(reader)

        self.assertEqual(ret, self.data)

    @gen_test
    def test_read_stream_with_giant_data(self):
        reader = Mock()

        self._rlimit = 0

        @asyncio.coroutine
        def read(limit):
            part = self.giant_data[self._rlimit: limit + self._rlimit]
            self._rlimit += limit
            return part

        reader.read = read

        ret = yield from utils.read_stream(reader)

        self.assertEqual(ret, self.giant)

    @gen_test
    def test_write_stream(self):
        writer = MagicMock()
        yield from utils.write_stream(writer, self.data.decode())

        called_arg = writer.write.call_args[0][0]

        self.assertEqual(called_arg, self.good_data)
