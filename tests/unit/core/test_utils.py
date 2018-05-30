# -*- coding: utf-8 -*-

# Copyright 2015-2018 Juca Crispim <juca@poraodojuca.net>

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
from concurrent import futures
import os
import subprocess
import time
from unittest import TestCase
from unittest.mock import patch, Mock, MagicMock
from toxicbuild.core import utils
from tests.unit.core import TEST_DATA_DIR
from tests import async_test


class UtilsTest(TestCase):

    @async_test
    def test_exec_cmd(self):
        out = yield from utils.exec_cmd('ls', cwd='.')
        self.assertTrue(out)

    @async_test
    def test_exec_cmd_with_error(self):
        with self.assertRaises(utils.ExecCmdError):
            # please, don't tell me you have a lsz command on your system.
            yield from utils.exec_cmd('lsz', cwd='.')

    @async_test
    def test_exec_cmd_with_timeout(self, *args, **kwargs):
        with self.assertRaises(asyncio.TimeoutError):
            yield from utils.exec_cmd('sleep 2', cwd='.', timeout=1)

        # wait here to avoid runtime error saying the loop is closed
        # when the process try to send its message to the caller
        time.sleep(1)

    @async_test
    def test_kill_group(self):
        cmd = 'sleep 55'
        proc = yield from utils._create_cmd_proc(cmd, cwd='.')
        try:
            f = proc.stdout.readline()
            yield from asyncio.wait_for(f, 1)
        except futures.TimeoutError:
            pass

        utils._kill_group(proc)
        procs = subprocess.check_output(['ps', 'aux']).decode()
        self.assertNotIn(cmd, procs)

    @async_test
    def test_exec_cmd_with_envvars(self):
        envvars = {'PATH': 'PATH:venv/bin',
                   'MYPROGRAMVAR': 'something'}

        cmd = 'echo $MYPROGRAMVAR'

        returned = yield from utils.exec_cmd(cmd, cwd='.', **envvars)

        self.assertEqual(returned, 'something')

    @async_test
    def test_exec_cmd_with_out_fn(self):
        envvars = {'PATH': 'PATH:venv/bin',
                   'MYPROGRAMVAR': 'something'}

        cmd = 'echo $MYPROGRAMVAR'

        lines = Mock()

        out_fn = asyncio.coroutine(lambda i, l: lines((i, l)))
        yield from utils.exec_cmd(cmd, cwd='.',
                                  out_fn=out_fn,
                                  **envvars)
        yield
        self.assertTrue(lines.called)
        self.assertTrue(isinstance(
            lines.call_args[0][0][1], str), lines.call_args)

    def test_get_envvars(self):
        envvars = {'PATH': 'PATH:venv/bin',
                   'MYPROGRAMVAR': 'something'}

        expected = {'PATH': '{}:venv/bin'.format(os.environ.get('PATH')),
                    'MYPROGRAMVAR': 'something',
                    'HOME': os.environ.get('HOME', '')}

        returned = utils._get_envvars(envvars)

        for var, val in expected.items():
            self.assertIn(var, returned)
            self.assertEqual(returned[var], val)

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

    @patch.object(utils, 'log', Mock())
    def test_logger_mixin(self):
        class MyLogger(utils.LoggerMixin):
            pass

        logger = MyLogger()
        logger.log('msg')
        msg = utils.log.call_args[0][0]
        self.assertTrue(msg.startswith('[MyLogger]'))

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

    def test_format_timedelta(self):
        td = datetime.timedelta(seconds=97)
        expected = '0:01:37'
        returned = utils.format_timedelta(td)
        self.assertEqual(expected, returned)

    def test_datetime2string(self):
        dt = utils.now()
        expected = datetime.datetime.strftime(dt, '%a %b %d %H:%M:%S %Y %z')
        returned = utils.datetime2string(dt)
        self.assertEqual(returned, expected)

    def test_datetime2string_timezone(self):
        dt = datetime.datetime.now()
        dttz = dt.replace(tzinfo=datetime.timezone(
            datetime.timedelta(seconds=0)))
        expected = datetime.datetime.strftime(dttz, '%a %b %d %H:%M:%S %Y %z')
        returned = utils.datetime2string(datetime.datetime.now())
        hour = int(returned.split(' ')[3].split(':')[0])

        self.assertEqual(hour, dt.hour)
        self.assertEqual(expected, returned)

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

    def test_localtime2utc(self):
        local = utils.now()
        utc = utils.localtime2utc(local)
        expected = local - utils.timedelta(
            seconds=local.utcoffset().total_seconds())

        self.assertEqual(utc.hour, expected.hour)
        self.assertEqual(utc.utcoffset().total_seconds(), 0)

    def test_now(self):
        n = utils.now()
        self.assertEqual(n.utcoffset().total_seconds(),
                         time.localtime().tm_gmtoff)

    @patch.object(utils, 'load_module_from_file', Mock())
    def test_get_toxicbuildconf(self):
        utils.get_toxicbuildconf('/some/dir/')
        called_conffile = utils.load_module_from_file.call_args[0][0]
        self.assertTrue(utils.load_module_from_file.called)
        self.assertEqual(called_conffile, '/some/dir/toxicbuild.conf')

    def test_list_builders_from_config(self):
        confmodule = Mock()
        slave = Mock()
        slave.name = 'myslave'
        confmodule.BUILDERS = [{'name': 'b0'},
                               {'name': 'b1', 'branches': ['other']},
                               {'name': 'b2',
                                'slaves': ['myslave'],
                                'branches': ['mast*', 'release']},
                               {'name': 'b3', 'slaves': ['otherslave']}]
        builders = utils.list_builders_from_config(confmodule, 'master', slave)
        self.assertEqual(len(builders), 2)
        self.assertNotIn({'name': 'b1', 'branch': 'other'}, builders)

    def test_list_builders_from_config_no_branch(self):
        confmodule = Mock()
        slave = Mock()
        slave.name = 'myslave'
        confmodule.BUILDERS = [{'name': 'b0'},
                               {'name': 'b1', 'branches': ['other'],
                                'slaves': ['other']},
                               {'name': 'b2',
                                'slaves': ['myslave'], 'branches': ['master']}]
        builders = utils.list_builders_from_config(confmodule, slave=slave)
        self.assertEqual(len(builders), 2)
        self.assertNotIn({'name': 'b1', 'branch': 'other',
                          'slave': 'other'}, builders)

    def test_list_builders_from_config_no_branch_no_slave(self):
        confmodule = Mock()
        slave = Mock()
        slave.name = 'myslave'
        confmodule.BUILDERS = [{'name': 'b0'},
                               {'name': 'b1', 'branches': ['other'],
                                'slaves': ['other']},
                               {'name': 'b2',
                                'slaves': ['myslave'], 'branches': ['master']}]
        builders = utils.list_builders_from_config(confmodule)
        self.assertEqual(len(builders), 3)

    def test_bcript_with_str_salt(self):
        salt = utils.bcrypt.gensalt(7).decode()
        passwd = 'somepasswd'
        encrypted = utils.bcrypt_string(passwd, salt)
        self.assertIsInstance(encrypted, str)

    def test_bcript_with_bytes_salt(self):
        salt = utils.bcrypt.gensalt(7)
        passwd = 'somepasswd'
        encrypted = utils.bcrypt_string(passwd, salt)
        self.assertIsInstance(encrypted, str)

    def test_bcript_no_salt(self):
        passwd = 'somepasswd'
        encrypted = utils.bcrypt_string(passwd)
        self.assertIsInstance(encrypted, str)

    def test_compare_bcrypt_string(self):
        passwd = 'somepasswd'
        encrypted = utils.bcrypt_string(passwd)
        self.assertTrue(utils.compare_bcrypt_string(passwd, encrypted))

    def test_create_random_string(self):
        length = 10
        random_str = utils.create_random_string(length)
        self.assertEqual(len(random_str), length)

    @patch.object(utils.os, 'chdir', Mock())
    def test_changedir(self):
        with utils.changedir('bla'):
            pass

        self.assertEqual(len(utils.os.chdir.call_args_list), 2)

    def test_match_string(self):
        filters = ['something', '*thing']
        smatch = 'something'
        smatch2 = 'otherthing'
        self.assertTrue(all([utils.match_string(smatch, filters),
                             utils.match_string(smatch2, filters)]))

    def test_match_string_not_match(self):
        filters = ['something', '*thing']
        smatch = 'somestuff'
        self.assertFalse(utils.match_string(smatch, filters))

    @patch.object(utils, '_THREAD_EXECUTOR', MagicMock())
    @async_test
    def test_run_in_thread(self):
        fn = Mock()
        yield from utils.run_in_thread(fn, 1, a=2)
        called = utils._THREAD_EXECUTOR.submit.call_args
        expected = ((fn, 1), {'a': 2})
        self.assertEqual(called, expected)


class StreamUtilsTest(TestCase):

    def setUp(self):
        super().setUp()
        self.bad_data = b'\n'
        self.good_data = b'17\n{"action": "bla"}'
        giant = {'action': 'bla' * 1000}
        self.giant = str(giant).encode('utf-8')
        self.giant_data = b'3014\n' + self.giant
        self.giant_data_with_more = self.giant_data + self.good_data
        self.data = b'{"action": "bla"}'

    @async_test
    def test_read_stream_without_data(self):
        reader = Mock()

        @asyncio.coroutine
        def read(limit):
            return self.bad_data
        reader.read = read

        ret = yield from utils.read_stream(reader)

        self.assertFalse(ret)

    @async_test
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

    @async_test
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

    @async_test
    def test_read_stream_with_good_data_in_parts(self):
        reader = Mock()

        self._rlimit = 0

        @asyncio.coroutine
        def read(limit):
            if limit != 1:
                limit = 10

            part = self.good_data[self._rlimit: limit + self._rlimit]
            self._rlimit += limit
            return part

        reader.read = read
        ret = yield from utils.read_stream(reader)

        self.assertEqual(ret, self.data)

    @async_test
    def test_read_stream_with_giant_data_with_more(self):
        reader = Mock()

        self._rlimit = 0

        @asyncio.coroutine
        def read(limit):
            part = self.giant_data_with_more[
                self._rlimit: limit + self._rlimit]
            self._rlimit += limit
            return part

        reader.read = read

        ret = yield from utils.read_stream(reader)

        self.assertEqual(ret, self.giant)

    @async_test
    def test_write_stream(self):
        writer = MagicMock()
        yield from utils.write_stream(writer, self.data.decode())

        called_arg = writer.write.call_args[0][0]

        self.assertEqual(called_arg, self.good_data)

    # @async_test
    # def test_write_step_output(self):
    #     output = {"code": 0, "body": {"output": "test_list_plugins (tests.unit.core.test_plugins.PluginTest) ... ok\n", "output_index": 254, "uuid": "3e8dd1f3-71e0-49fd-95d7-92c95f833756", "info_type": "step_output_info"}}  # noqa f501
    #     import json
    #     output = json.dumps(output)
    #     writer = MagicMock()
    #     yield from utils.write_stream(writer, output)

    #     called_arg = writer.write.call_args[0][0]
    #     import ipdb;ipdb.set_trace()
    #     called_len = int(called_arg.split('\n')[0])
    #     self.assertEqual(called_len, 204)


class MatchKeyDictTest(TestCase):

    def test_getitem(self):
        d = utils.MatchKeysDict()
        d['a'] = 1
        self.assertTrue(d['a'])

    def test_getitem_wildcard(self):
        d = utils.MatchKeysDict()
        d['a*'] = 1
        self.assertTrue(d['asdf'])

    def test_getitem_keyerror(self):
        d = utils.MatchKeysDict()
        d['a*'] = 1
        with self.assertRaises(KeyError):
            d['key']
