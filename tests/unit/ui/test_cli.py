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
import builtins
import unittest
from unittest.mock import MagicMock, Mock, patch
import tornado
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.ui import cli

# urwid changes the locale and this makes a test on vcs fail
# so, changing it back here

import locale
locale.setlocale(locale.LC_ALL, 'C')


class CliCommandTest(unittest.TestCase):

    def test_parse_cmdline(self):
        cmdline = 'repo-add toxicbuild git@toxicbuild.com/toxicbuild.git'
        cmdline += ' 300 git'

        expected = ('repo-add',
                    ['toxicbuild', 'git@toxicbuild.com/toxicbuild.git', 300,
                     'git'], {})

        returned = cli.parse_cmdline(cmdline)

        self.assertEqual(returned, expected)

    def test_parse_cmdline_with_kwargs(self):

        cmdline = 'command-name param1 param2=bla'

        expected = ('command-name', ['param1'], {'param2': 'bla'})

        returned = cli.parse_cmdline(cmdline)

        self.assertEqual(returned, expected)

    def test_validate_input(self):
        command_args = [{'name': 'a', 'required': True},
                        {'name': 'b', 'required': False, 'default': 0}]
        user_args = ['a_value']
        user_kwargs = {'b': 1}

        # no exception, ok
        cli.validate_input(command_args, user_args, user_kwargs)

    def test_validate_input_without_non_required_param(self):

        command_args = [{'name': 'a', 'required': True},
                        {'name': 'b', 'required': False, 'default': 0}]
        user_args = ['a_value']
        user_kwargs = {}

        # no exception, ok
        cli.validate_input(command_args, user_args, user_kwargs)

    def test_validate_input_without_required_param(self):
        command_args = [{'name': 'a', 'required': True},
                        {'name': 'b', 'required': False, 'default': 0}]
        user_args = []
        user_kwargs = {'b': 1}

        with self.assertRaises(cli.ToxicShellError):
            cli.validate_input(command_args, user_args, user_kwargs)

    def test_get_kwargs(self):
        command_args = [{'name': 'a', 'required': True},
                        {'name': 'b', 'required': False, 'default': 0}]
        args = [1]

        kwargs = cli.get_kwargs(command_args, args)

        self.assertEqual(kwargs['a'], 1)


class HistoryEditTest(unittest.TestCase):

    @patch.object(cli.HistoryEdit, '_get_history', Mock(return_value=[]))
    def setUp(self):
        self.history_edit = cli.HistoryEdit('prompt: ')
        self.history_edit.history = []

    def test_append_to_history(self):
        item = 'bla'

        self.history_edit.append_to_history(item)

        self.assertEqual(self.history_edit.history[0], item)

    def test_append_to_history_with_same_item(self):
        item = 'bla'
        self.history_edit.append_to_history(item)
        self.history_edit.append_to_history(item)

        self.assertEqual(len(self.history_edit.history), 1)

    def test_append_to_history_limit(self):
        self.history_edit.history_limit = 5

        for i in range(10):
            self.history_edit.append_to_history(str(i))

        self.assertEqual(len(self.history_edit.history), 5)

    @patch.object(builtins, 'open', MagicMock())
    def test_save_to_history(self):
        self.history_edit.history = ['some', 'thing']

        self.history_edit.save_history()

        fd_mock = builtins.open.return_value.__enter__.return_value
        history_content = fd_mock.write.call_args[0][0]
        self.assertEqual(history_content, '\n'.join(self.history_edit.history))

    def test_get_previous(self):
        item_a, item_b, item_c = 'a', 'b', 'c'
        self.history_edit.append_to_history(item_a)
        self.history_edit.append_to_history(item_b)
        self.history_edit.append_to_history(item_c)

        previous = self.history_edit.get_previous()

        self.assertEqual(item_c, previous)

    def test_get_previous_on_last(self):
        # Ensure that you can round throught the queue

        item_a, item_b, item_c = 'a', 'b', 'c'
        self.history_edit.append_to_history(item_c)
        self.history_edit.append_to_history(item_b)
        self.history_edit.append_to_history(item_a)

        self.history_edit.get_previous()
        self.history_edit.get_previous()
        self.history_edit.get_previous()

        previous = self.history_edit.get_previous()

        self.assertEqual(previous, item_a)

    def test_get_next(self):
        item_a, item_b, item_c = 'a', 'b', 'c'

        self.history_edit.append_to_history(item_c)
        self.history_edit.append_to_history(item_b)
        self.history_edit.append_to_history(item_a)

        next_item = self.history_edit.get_next()

        self.assertEqual(next_item, item_c)

    def test_keypress_with_enter(self):
        self.history_edit.get_edit_text = Mock(return_value='some text')
        self.history_edit.keypress((10,), 'enter')

        self.assertTrue('some text' in self.history_edit.history)

    def test_keypress_with_up(self):
        self.history_edit.append_to_history('something')
        self.history_edit.set_edit_text = Mock(
            spec=self.history_edit.set_edit_text)

        self.history_edit.keypress((10,), 'up')

        cmd = self.history_edit.set_edit_text.call_args[0][0]

        self.assertEqual(cmd, 'something')

    def test_keypress_with_down(self):
        self.history_edit.append_to_history('onething')
        self.history_edit.append_to_history('otherthing')

        self.history_edit.set_edit_text = Mock(
            spec=self.history_edit.set_edit_text)

        self.history_edit.keypress((10,), 'down')

        cmd = self.history_edit.set_edit_text.call_args[0][0]

        self.assertEqual(cmd, 'onething')

    def test_keypress_with_other_key(self):
        # no exceptions, ok
        ret = self.history_edit.keypress((10,), 'a')

        # urwid returns None when it handles some keypress
        self.assertIsNone(ret)

    def test_get_history_without_history_file(self):
        self.history_edit.history_file = 'file-that-does-not-exist'
        history = self.history_edit._get_history()
        self.assertEqual(len(history), 0)

    @patch.object(builtins, 'open', MagicMock(spec=builtins.open))
    def test_get_history_with_history_file(self):
        fd = builtins.open.return_value.__enter__.return_value
        fd.readlines.return_value = ['one item', 'two items', 'bla bla bla']

        history = self.history_edit._get_history()

        self.assertEqual(len(history), 3)


ACTIONS = {'builder-show':
           {'parameters': [{'name': 'repo_name', 'required': True},
                               {'name': 'builder_name', 'required': True}],
            'doc': ' Returns information about one specific builder. '},

           'list-funcs':
           {'parameters': [],
            'doc': ' Lists the functions available for user interfaces. '},

               'repo-remove': {'parameters':
                               [{'name': 'repo_name', 'required': True}],
                               'doc':
                               ' Removes a repository from toxicubild '},

           'repo-update':
           {'parameters': [{'name': 'repo_name', 'required': True},
                           {'name': 'kwargs', 'required': True}],
            'doc': ' Updates repository information. '},

           'repo-list':
           {'parameters': [],
            'doc': ' Lists all repositories. '},

           'repo-remove-slave':
           {'parameters': [{'name': 'repo_name', 'required': True},
                           {'name': 'slave_name', 'required': True}],
            'doc': ' Removes a slave from toxicbuild. '},

           'slave-remove':
           {'parameters': [{'name': 'slave_name', 'required': True}],
            'doc': ' Removes a slave from toxicbuild. '},

           'repo-start-build':
           {'parameters': [{'name': 'repo_name', 'required': True},
                           {'name': 'branch', 'required': True},
                           {'name': 'builder_name',
                            'default': None, 'required': False},
                           {'name': 'named_tree',
                            'default': None, 'required': False},
                           {'name': 'slaves', 'default': [],
                            'required': False}],
            'doc': ' Starts a(some) build(s) in a given repository. '},

           'slave-list':
           {'parameters': [], 'doc': ' Lists all slaves. '},

           'slave-add':
           {'parameters': [{'name': 'slave_name', 'required': True},
                           {'name': 'slave_host', 'required': True},
                           {'name': 'slave_port', 'required': True}],
            'doc': ' Adds a new slave to toxicbuild. '},

           'builder-list':
           {'parameters': [{'name': 'repo_name', 'default': None,
                            'required': False}],
            'doc': ' Lists all builders.\n\n        If ``repo_name``, only builders from this repository will be listed.\n        '},  # noqa

           'repo-add':
           {'parameters': [{'name': 'repo_name', 'required': True},
                           {'name': 'repo_url', 'required': True},
                           {'name': 'update_seconds', 'required': True},
                           {'name': 'vcs_type', 'required': True},
                           {'name': 'slaves', 'default': None,
                            'required': False}],
            'doc': ' Adds a new repository and first_run() it. '},

           'repo-add-slave':
           {'parameters': [{'name': 'repo_name', 'required': True},
                           {'name': 'slave_name', 'required': True}],
            'doc': ' Adds a slave to a repository. '}}


class ToxicCliActionsTest(AsyncTestCase):

    @patch.object(cli.ToxicCliActions, 'get_actions', Mock())
    def setUp(self):
        super().setUp()

        cli.ToxicCliActions.get_actions.return_value = ACTIONS
        self.cli_actions = cli.ToxicCliActions()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @patch.object(cli, 'get_hole_client', MagicMock())
    @gen_test
    def test_get_client(self):
        client = MagicMock()

        @asyncio.coroutine
        def ghc(host, port):
            client.__enter__.return_value = client
            return client

        cli.get_hole_client = ghc

        returned = yield from self.cli_actions.get_client()

        self.assertTrue(returned, client)

    @patch.object(cli, 'get_hole_client', MagicMock())
    def test_get_actions(self):
        client = MagicMock()
        list_funcs = MagicMock()

        @asyncio.coroutine
        def lf():
            list_funcs()

        client.list_funcs = lf

        @asyncio.coroutine
        def ghc(host, port):
            client.__enter__.return_value = client
            return client

        cli.get_hole_client = ghc

        self.cli_actions.get_actions()

        self.assertTrue(list_funcs.called)

    def test_get_action_from_command_line(self):
        cmdline = 'repo-add toxicbuild git@toxicbuild.org 300 git'
        cmd, cmdkwargs = self.cli_actions.get_action_from_command_line(
            cmdline)

        expected_kwargs = {'repo_name': 'toxicbuild',
                           'repo_url': 'git@toxicbuild.org',
                           'update_seconds': 300,
                           'vcs_type': 'git'}

        self.assertEqual(cmd, 'repo-add')
        self.assertEqual(expected_kwargs, cmdkwargs)

    def test_get_action_from_command_line_with_unknown_command(self):
        cmdline = 'i-dont-exist param1'

        with self.assertRaises(cli.ToxicShellError):
            self.cli_actions.get_action_from_command_line(cmdline)

    @gen_test
    def test_execute_action(self):
        client = MagicMock()
        request2server = MagicMock()

        @asyncio.coroutine
        def r2s(action, cmdkwargs):
            request2server()

        client.request2server = r2s

        @asyncio.coroutine
        def ghc(host, port):
            client.__enter__.return_value = client
            return client

        cli.get_hole_client = ghc

        cmdline = 'repo-list'
        yield from self.cli_actions.execute_action(cmdline)

        self.assertTrue(request2server.called)


class ToxicCliTest(unittest.TestCase):

    @patch.object(cli.ToxicCliActions, 'get_client', MagicMock())
    def setUp(self):
        @asyncio.coroutine
        def gc(*args, **kwargs):
            client = MagicMock()
            client.list_funcs = asyncio.coroutine(lambda *args, **kwargs: None)
            client.__enter__.return_value = client
            return client

        cli.ToxicCliActions.get_client = gc

        self.cli = cli.ToxicCli()
        self.cli.actions = ACTIONS
        self.loop = asyncio.get_event_loop()

    def test_getattr(self):
        self.cli._format_result = Mock()

        self.cli._format_builder_show()

        self.assertTrue(self.cli._format_result.called)

    @patch.object(cli.urwid, 'AsyncioEventLoop', Mock())
    @patch.object(cli.urwid, 'MainLoop', Mock())
    def test_run(self):
        self.cli.show_welcome_screen = Mock()

        self.cli.run()

        self.assertTrue(self.cli.show_welcome_screen.called)
        self.assertTrue(cli.urwid.AsyncioEventLoop.called)
        self.assertTrue(cli.urwid.MainLoop.called)

    def test_quit(self):
        self.cli.input.save_history = Mock()
        with self.assertRaises(cli.urwid.ExitMainLoop):
            self.cli.quit()

    def test_keypress_with_enter(self):
        self.cli.input.set_edit_text('repo-list')

        self.cmdline = None

        @asyncio.coroutine
        def exec_and_show(cmdline):
            self.cmdline = cmdline

        self.cli.execute_and_show = exec_and_show

        self.cli.keypress((10, 10), 'enter')

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*asyncio.Task.all_tasks()))

        self.assertEqual(self.cmdline, 'repo-list')

    def test_key_press(self):
        self.cli.input.set_edit_text('repo-add ')

        self.cmdline = None

        @asyncio.coroutine
        def exec_and_show(cmdline):
            self.cmdline = cmdline

        self.cli.execute_and_show = exec_and_show

        self.cli.keypress((10, 10), ' ')

        self.loop.run_until_complete(asyncio.gather(*asyncio.Task.all_tasks()))

        self.assertEqual(self.cmdline, None)

    def test_execute_and_show_with_exception(self):
        @asyncio.coroutine
        def ea(cmdline):
            raise cli.ToxicShellError()

        self.cli.execute_action = ea

        self.loop.run_until_complete(self.cli.execute_and_show(''))

        self.assertEqual(self.cli.messages.get_text()[1][0][0], 'error')

    def test_execute_and_show_with_custom_format_method(self):
        @asyncio.coroutine
        def ea(cmdline):
            return 'help', {}

        self.cli.execute_action = ea
        self.cli._format_help = Mock(spec=self.cli._format_help,
                                     return_value='')

        self.loop.run_until_complete(self.cli.execute_and_show(''))
        self.assertTrue(self.cli._format_help.called)

    def test_execute_and_show_with_default_format(self):
        @asyncio.coroutine
        def ea(cmdline):
            return 'builder-show', {}

        self.cli.execute_action = ea
        self.cli._format_result = Mock(spec=self.cli._format_result,
                                       return_value='')

        self.loop.run_until_complete(self.cli.execute_and_show(''))
        self.assertTrue(self.cli._format_result.called)
