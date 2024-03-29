# -*- coding: utf-8 -*-

# Copyright 2015-2019, 2023 Juca Crispim <juca@poraodojuca.net>

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


import asyncio
import datetime
import os
import subprocess
import time
from unittest import TestCase
from unittest.mock import patch, Mock, MagicMock, AsyncMock
from toxicbuild.core import utils
from tests.unit.core import TEST_DATA_DIR
from tests import async_test


class UtilsTest(TestCase):

    @async_test
    async def test_try_readline_lf(self):
        stream = AsyncMock()
        await utils._try_readline(stream)

        assert stream.readuntil.call_args[0][0] == b'\n'

    @async_test
    async def test_try_readline_cr(self):
        stream = AsyncMock()
        stream.readuntil.side_effect = [
            utils.LimitOverrunError('msg', False), '']
        await utils._try_readline(stream)

        assert stream.readuntil.call_args[0][0] == b'\r'

    @patch.object(utils, '_try_readline', AsyncMock(
        side_effect=utils.IncompleteReadError('partial', 'exp')))
    @async_test
    async def test_readline_incomplete(self):
        stream = AsyncMock()
        r = await utils._readline(stream)

        self.assertEqual(r, 'partial')

    @patch.object(utils, '_try_readline', AsyncMock(
        side_effect=utils.LimitOverrunError('msg', 0)))
    @async_test
    async def test_readline_limit_overrun(self):
        stream = AsyncMock()
        stream._buffer = bytearray()
        stream._maybe_resume_transport = Mock()
        stream._buffer.extend(b'\nblerg')
        with self.assertRaises(ValueError):
            await utils._readline(stream)

    @patch.object(utils, '_try_readline', AsyncMock(
        side_effect=utils.LimitOverrunError('msg', 0)))
    @async_test
    async def test_readline_limit_overrun_clear(self):
        stream = AsyncMock()
        stream._buffer = bytearray()
        stream._maybe_resume_transport = Mock()
        await stream.extend(b'blerg')
        with self.assertRaises(ValueError):
            await utils._readline(stream)

    @async_test
    async def test_exec_cmd(self):
        out = await utils.exec_cmd('ls', cwd='.')
        self.assertTrue(out)

    @async_test
    async def test_exec_cmd_with_error(self):
        with self.assertRaises(utils.ExecCmdError):
            # please, don't tell me you have a lsz command on your system.
            await utils.exec_cmd('lsz', cwd='.')

    @async_test
    async def test_exec_cmd_with_timeout(self, *args, **kwargs):
        with self.assertRaises(asyncio.TimeoutError):
            await utils.exec_cmd('sleep 2', cwd='.', timeout=1)

        # wait here to avoid runtime error saying the loop is closed
        # when the process try to send its message to the caller
        time.sleep(1)

    @async_test
    async def test_kill_group(self):
        cmd = 'sleep 55'
        proc = await utils._create_cmd_proc(cmd, cwd='.')
        try:
            f = proc.stdout.readline()
            await asyncio.wait_for(f, 1)
        except asyncio.exceptions.TimeoutError:
            pass

        await utils._kill_group(proc)
        procs = subprocess.check_output(['ps', 'aux']).decode()
        self.assertNotIn(cmd, procs)

    @async_test
    async def test_exec_cmd_with_envvars(self):
        envvars = {'PATH': 'PATH:venv/bin',
                   'MYPROGRAMVAR': 'something'}

        cmd = 'echo $MYPROGRAMVAR'

        returned = await utils.exec_cmd(cmd, cwd='.', **envvars)

        self.assertEqual(returned, 'something')

    @async_test
    async def test_exec_cmd_with_out_fn(self):
        envvars = {'PATH': 'PATH:venv/bin',
                   'MYPROGRAMVAR': 'something'}

        cmd = 'echo $MYPROGRAMVAR'

        out_fn = AsyncMock()
        await utils.exec_cmd(cmd, cwd='.',
                             out_fn=out_fn,
                             **envvars)

        async def wait():
            return

        await wait()
        self.assertTrue(out_fn.called)
        self.assertTrue(isinstance(
            out_fn.call_args[0][1], str), out_fn.call_args)

    def test_get_envvars(self):
        envvars = {'PATH': 'PATH:venv/bin',
                   'MYPROGRAMVAR': 'something'}

        expected = {'PATH': '{}:venv/bin'.format(os.environ.get('PATH')),
                    'MYPROGRAMVAR': 'something',
                    'HOME': os.environ.get('HOME', '')}

        returned = utils.get_envvars(envvars)

        for var, val in expected.items():
            self.assertIn(var, returned)
            self.assertEqual(returned[var], val)

    def test_get_envvars_no_local(self):
        envvars = {'PATH': 'PATH:venv/bin',
                   'MYPROGRAMVAR': 'something'}

        expected = {'PATH': '{}:venv/bin'.format(os.environ.get('PATH')),
                    'MYPROGRAMVAR': 'something'}

        returned = utils.get_envvars(envvars, use_local_envvars=False)

        for var, val in expected.items():
            self.assertIn(var, returned)
            self.assertEqual(returned[var], val)

        self.assertEqual(len(list(returned.keys())), 2)

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

    def test_load_module_from_content(self):
        contents = 'BLA = 1'
        mod = utils.load_module_from_content(contents)
        self.assertEqual(mod.BLA, 1)

    @patch.object(utils.logger, 'setLevel', Mock())
    def test_set_loglevel(self):
        utils.set_loglevel('info')

        self.assertTrue(utils.logger.setLevel.called)

    @patch.object(utils.logger, 'info', Mock())
    def test_log(self):
        utils.log('msg')
        self.assertTrue(utils.logger.info.called)

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

            async def m():
                """ some doc"""
                return True

        @utils.inherit_docs
        class B(A):

            async def m():
                return False

        self.assertEqual(B.m.__doc__, A.m.__doc__)

    def test_format_timedelta(self):
        td = datetime.timedelta(seconds=97)
        expected = '0:01:37'
        returned = utils.format_timedelta(td)
        self.assertEqual(expected, returned)

    def test_datetime2string(self):
        dt = utils.now()
        expected = datetime.datetime.strftime(dt, '%w %m %d %H:%M:%S %Y %z')
        returned = utils.datetime2string(dt)
        self.assertEqual(returned, expected)

    def test_datetime2string_timezone(self):
        dt = datetime.datetime.now()
        dttz = dt.replace(tzinfo=datetime.timezone(
            datetime.timedelta(seconds=0)))
        expected = datetime.datetime.strftime(dttz, '%w %m %d %H:%M:%S %Y %z')
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
        dtstr = dt.strftime('%w %m %d %H:%M:%S %Y %z')

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

    def test_set_tz_info(self):
        n = datetime.datetime.now()
        ntz = utils.set_tzinfo(n, -10800)
        self.assertEqual(ntz.utcoffset().total_seconds(), -10800)

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

    def test_validation_string(self):
        secret = '1234'
        b64str = utils.create_validation_string(secret)

        self.assertTrue(utils.validate_string(b64str, secret))

    def test_validation_string_bad(self):
        secret = '1234'
        bad_secret = '123'
        b64str = utils.create_validation_string(secret)

        self.assertFalse(utils.validate_string(b64str, bad_secret))

    @patch.object(utils, 'log', Mock())
    def test_validation_string_exception(self):
        secret = '1234'
        self.assertFalse(utils.validate_string('bad-str', secret))

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
    async def test_run_in_thread(self):
        fn = Mock()
        await utils.run_in_thread(fn, 1, a=2)
        called = utils._THREAD_EXECUTOR.submit.call_args
        expected = ((fn, 1), {'a': 2})
        self.assertEqual(called, expected)

    def test_patch_source_suffixes(self):
        patcher = utils.SourceSuffixesPatcher()
        with patcher:
            patcher.patch_source_suffixes()
            self.assertEqual(
                utils.importlib._bootstrap_external.SOURCE_SUFFIXES,
                ['.py', '.conf'])

    def test_patch_pyrosettings(self):
        patcher = utils.SettingsPatcher()
        settings = Mock()
        with patcher:
            patcher.patch_pyro_settings(settings)
            import pyrocumulus
            self.assertEqual(pyrocumulus.conf.settings, settings)

        self.assertNotEqual(pyrocumulus.conf.settings, settings)

    @async_test
    async def test_read_file(self):
        filename = os.path.join(TEST_DATA_DIR, 'toxicbuild.conf')
        c = await utils.read_file(filename)
        self.assertTrue(c)


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
    async def test_read_stream_without_data(self):
        reader = Mock()

        async def read(limit):
            return self.bad_data
        reader.read = read

        ret = await utils.read_stream(reader)

        self.assertFalse(ret)

    @async_test
    async def test_read_stream_good_data(self):
        reader = Mock()

        self._rlimit = 0

        async def read(limit):
            part = self.good_data[self._rlimit: limit + self._rlimit]
            self._rlimit += limit
            return part

        reader.read = read

        ret = await utils.read_stream(reader)

        self.assertEqual(ret, self.data)

    @async_test
    async def test_read_stream_with_giant_data(self):
        reader = Mock()

        self._rlimit = 0

        async def read(limit):
            part = self.giant_data[self._rlimit: limit + self._rlimit]
            self._rlimit += limit
            return part

        reader.read = read

        ret = await utils.read_stream(reader)

        self.assertEqual(ret, self.giant)

    @async_test
    async def test_read_stream_with_good_data_in_parts(self):
        reader = Mock()

        self._rlimit = 0

        async def read(limit):
            if limit != 1:
                limit = 10

            part = self.good_data[self._rlimit: limit + self._rlimit]
            self._rlimit += limit
            return part

        reader.read = read
        ret = await utils.read_stream(reader)

        self.assertEqual(ret, self.data)

    @async_test
    async def test_read_stream_with_giant_data_with_more(self):
        reader = Mock()

        self._rlimit = 0

        async def read(limit):
            part = self.giant_data_with_more[
                self._rlimit: limit + self._rlimit]
            self._rlimit += limit
            return part

        reader.read = read

        ret = await utils.read_stream(reader)

        self.assertEqual(ret, self.giant)

    @async_test
    async def test_write_stream(self):
        writer = MagicMock(drain=AsyncMock())
        r = await utils.write_stream(writer, self.data.decode())

        called_arg = writer.write.call_args[0][0]

        self.assertEqual(called_arg, self.good_data)
        self.assertTrue(r)

    @async_test
    async def test_write_stream_no_writer(self):
        writer = None
        r = await utils.write_stream(writer, self.data.decode())
        self.assertFalse(r)

    # @async_test
    # def test_write_step_output(self):
    #     output = {"code": 0, "body": {"output": "test_list_plugins (tests.unit.core.test_plugins.PluginTest) ... ok\n", "output_index": 254, "uuid": "3e8dd1f3-71e0-49fd-95d7-92c95f833756", "info_type": "step_output_info"}}  # noqa f501
    #     import json
    #     output = json.dumps(output)
    #     writer = MagicMock()
    #     await utils.write_stream(writer, output)

    #     called_arg = writer.write.call_args[0][0]
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

    def test_get(self):
        d = utils.MatchKeysDict()
        d['a*'] = 1

        self.assertTrue(d.get('adsf'))

    def test_get_not_present(self):
        d = utils.MatchKeysDict()
        d['a*'] = 1

        self.assertIsNone(d.get('k'))
