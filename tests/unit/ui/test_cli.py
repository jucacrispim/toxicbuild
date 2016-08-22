# -*- coding: utf-8 -*-

# Copyright 2015 2016 Juca Crispim <juca@poraodojuca.net>

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
import concurrent
import builtins
import unittest
from unittest.mock import MagicMock, Mock, patch
import tornado
from toxicbuild.ui import cli
from tests import async_test


# urwid changes the locale and this makes a test on vcs fail
# so, changing it back here

import locale
locale.setlocale(locale.LC_ALL, 'C')

# installing gettext so we can text the cli properly
import gettext  # flake8:  noqa
gettext.install('toxicbuild.ui', 'fakedir')


class CliCommandTest(unittest.TestCase):

    def test_parse_cmdline(self):
        cmdline = 'repo-add toxicbuild git@toxicbuild.com/toxicbuild.git'
        cmdline += ' 300 git'

        expected = ('repo-add',
                    ['toxicbuild', 'git@toxicbuild.com/toxicbuild.git', 300,
                     'git'], {})

        returned = cli.parse_cmdline(cmdline)

        self.assertEqual(returned, expected)

    def test_parse_cmdline_without_args(self):
        cmdline = 'repo-list'
        expected = ('repo-list', [], {})
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

    def test_get_next_in_the_end_of_the_list(self):
        item_a, item_b, item_c = 'a', 'b', 'c'

        self.history_edit.append_to_history(item_c)
        self.history_edit.append_to_history(item_b)
        self.history_edit.append_to_history(item_a)
        self.history_edit._history_position = 3

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
    @patch.object(cli.os.path, 'exists', Mock(return_value=True))
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

           'repo-show':
           {'parameters': [{'name': 'repo_name', 'required': False},
                           {'name': 'repo_url', 'required': False}],

            'doc': """Shows information about one specific repository.
            One of ``repo_name`` or ``repo_url`` is required. """},

           'repo-add-slave':
           {'parameters': [{'name': 'repo_name', 'required': True},
                           {'name': 'slave_name', 'required': True}],
            'doc': ' Adds a slave to a repository. '},

           'peek':
           {'parameters': [],
            'doc': 'Peeks throught the master\'s hole'}}


class ToxicCliActionsTest(unittest.TestCase):

    @patch.object(cli.ToxicCliActions, 'get_actions', Mock())
    def setUp(self):
        super().setUp()

        cli.ToxicCliActions.get_actions.return_value = ACTIONS
        self.cli_actions = cli.ToxicCliActions()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @patch.object(cli, 'get_hole_client', MagicMock())
    @async_test
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

        @asyncio.coroutine
        def lf():
            return ACTIONS

        client.list_funcs = lf

        @asyncio.coroutine
        def ghc(host, port):
            client.__enter__.return_value = client
            return client

        cli.get_hole_client = ghc

        actions = self.cli_actions.get_actions()

        self.assertEqual(actions, ACTIONS)

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

    def test_get_action_help(self):
        action_help = self.cli_actions.get_action_help('builder-list')
        short_doc = ' Lists all builders.'

        self.assertEqual(short_doc, action_help['short_doc'])

    def test_get_action_help_unknown_command(self):
        with self.assertRaises(cli.ToxicShellError):
            self.cli_actions.get_action_help('i-dont-exist')

    @async_test
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

    @classmethod
    @patch.object(cli.ToxicCliActions, 'get_client', MagicMock())
    def setUpClass(cls):
        @asyncio.coroutine
        def gc(*args, **kwargs):
            client = MagicMock()
            client.list_funcs = asyncio.coroutine(lambda *args, **kwargs: None)
            client.__enter__.return_value = client
            return client

        cli.ToxicCliActions.get_client = gc

        cls.cli = cli.ToxicCli()
        cls.cli.actions = ACTIONS
        cls.loop = asyncio.get_event_loop()

    @patch.object(cli.ToxicCli, '_format_result', Mock())
    def test_getattr(self):
        self.cli._format_builder_show()

        self.assertTrue(self.cli._format_result.called)

    def test_getattr_attribute_error(self):
        with self.assertRaises(AttributeError):
            self.cli._i_dont_exist()

    def test_getattr_with_bad_format(self):
        with self.assertRaises(AttributeError):
            self.cli._format_inexistent()

    @patch.object(cli.urwid, 'AsyncioEventLoop', Mock())
    @patch.object(cli.urwid, 'MainLoop', Mock())
    @patch.object(cli.ToxicCli, 'show_welcome_screen', Mock())
    def test_run(self):
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
        try:
            loop.run_until_complete(
                asyncio.gather(*asyncio.Task.all_tasks()))

        except concurrent.futures._base.CancelledError:
            pass

        self.assertEqual(self.cmdline, 'repo-list')

    def test_keypree_with_enter_and_no_data(self):
        self.cli.input.set_edit_text('')

        self.cmdline = None

        @asyncio.coroutine
        def exec_and_show(cmdline):
            self.cmdline = cmdline

        self.cli.execute_and_show = exec_and_show

        self.cli.keypress((10, 10), 'enter')

        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(
                asyncio.gather(*asyncio.Task.all_tasks()))
        except concurrent.futures._base.CancelledError:
            pass

        self.assertEqual(self.cmdline, None)

    def test_key_press(self):
        self.cli.input.set_edit_text('repo-add ')

        self.cmdline = None

        @asyncio.coroutine
        def exec_and_show(cmdline):
            self.cmdline = cmdline

        self.cli.execute_and_show = exec_and_show

        self.cli.keypress((10, 10), ' ')

        try:
            self.loop.run_until_complete(
                asyncio.gather(*asyncio.Task.all_tasks()))
        except concurrent.futures._base.CancelledError:
            pass

        self.assertEqual(self.cmdline, None)

    def test_execute_and_show_with_exception(self):
        @asyncio.coroutine
        def ea(cmdline):
            raise cli.ToxicShellError()

        self.cli.execute_action = ea

        self.loop.run_until_complete(self.cli.execute_and_show(''))

        self.assertEqual(self.cli.messages.get_text()[1][0][0], 'error')

    @patch.object(cli.ToxicCli, '_format_repo_list',
                  Mock(spec=cli.ToxicCli._format_repo_list, return_value=''))
    def test_execute_and_show_with_custom_format_method(self):
        @asyncio.coroutine
        def ea(cmdline):
            return 'repo-list', {}

        self.cli.execute_action = ea

        self.loop.run_until_complete(self.cli.execute_and_show(''))
        self.assertTrue(self.cli._format_repo_list.called)

    @patch.object(cli.ToxicCli, '_format_result',
                  Mock(spec=cli.ToxicCli._format_result, return_value=''))
    def test_execute_and_show_with_default_format(self):
        @asyncio.coroutine
        def ea(cmdline):
            return 'builder-show', {}

        self.cli.execute_action = ea

        self.loop.run_until_complete(self.cli.execute_and_show(''))
        self.assertTrue(self.cli._format_result.called)

    @patch.object(cli.ToxicCli, '_format_help',
                  Mock(spec=cli.ToxicCli._format_help, return_value=''))
    def test_execute_with_help(self):
        cmdline = 'help'
        self.loop.run_until_complete(self.cli.execute_and_show(cmdline))
        self.assertTrue(self.cli._format_help.called)

    @patch.object(cli.ToxicCli, 'get_action_help_screen',
                  Mock(spec=cli.ToxicCli.get_action_help_screen,
                       return_value=''))
    def test_execute_with_command_help(self):
        cmdline = 'help repo-add'
        self.loop.run_until_complete(self.cli.execute_and_show(cmdline))
        self.assertTrue(self.cli.get_action_help_screen.called)

    @patch.object(cli.ToxicCli, 'quit', Mock(spec=cli.ToxicCli.quit,
                                             return_value=''))
    def test_execute_with_quit(self):
        cmdline = 'quit'

        self.loop.run_until_complete(self.cli.execute_and_show(cmdline))
        self.assertTrue(self.cli.quit.called)

    @patch.object(cli.ToxicCli, 'peek', MagicMock(spec=cli.ToxicCli.peek))
    def test_execute_with_peek(self):
        cmdline = 'peek'

        self.loop.run_until_complete(self.cli.execute_and_show(cmdline))
        self.assertTrue(self.cli.peek.called)

    @patch.object(cli.ToxicCli, 'stop_peek', MagicMock(spec=cli.ToxicCli.peek))
    def test_execute_with_stop_peek(self):
        cmdline = 'stop-peek'

        self.loop.run_until_complete(self.cli.execute_and_show(cmdline))
        self.assertTrue(self.cli.stop_peek.called)

    @patch.object(cli.ToxicCli, 'show_welcome_screen',
                  MagicMock(spec=cli.ToxicCli.show_welcome_screen))
    def test_execute_with_show_welcome_screen(self):
        cmdline = 'welcome-screen'

        self.loop.run_until_complete(self.cli.execute_and_show(cmdline))
        self.assertTrue(self.cli.show_welcome_screen.called)

    def test_peek(self):
        client_mock = MagicMock()
        client_mock.__enter__.return_value = client_mock

        @asyncio.coroutine
        def gc():
            return client_mock

        self.cli.stop_peek()
        self.cli.get_client = gc
        self.loop.run_until_complete(self.cli.peek())

        stream_called = client_mock.request2server.call_args[0][0] == 'stream'
        self.assertTrue(stream_called)
        self.assertTrue(client_mock.get_response.called)

    def test_get_welcome_text(self):
        expected = _('Welcome to {toxicbuild}')  # noqa

        returned = self.cli._get_welcome_text()
        self.assertEqual(expected, returned)

    def test_get_help_text(self):
        expected = _('Type {h} for help and {q} for quit')  # noqa
        returned = self.cli._get_help_text()

        self.assertEqual(expected, returned)

    def test_format_help_text(self):
        text = _('Type {h} for help and {q} for quit')  # noqa
        formated = self.cli._format_help_text(text)
        self.assertIn(('action-name', 'h'), formated)
        self.assertIn(('action-name', 'q'), formated)

    def test_show_welcome_screen(self):
        self.cli._get_welcome_text = Mock(spec=self.cli._get_welcome_text,
                                          return_value='Welcome!')

        self.cli._get_help_text = Mock(spec=self.cli._get_help_text,
                                       return_value='t {h} help {q} quit')

        self.cli.main_screen.set_text = Mock(
            spec=self.cli.main_screen.set_text)
        self.cli.show_welcome_screen()

        self.assertTrue(self.cli._get_welcome_text.called)
        self.assertTrue(self.cli._get_help_text.called)
        self.assertTrue(self.cli.main_screen.set_text.called)

    def test_get_action_help_screen_full(self):
        formated_help = self.cli.get_action_help_screen('repo-add-slave')

        self.assertIn(('action-name', 'repo-add-slave'), formated_help)

    def test_get_action_help_screen_full_with_peek(self):
        # It is here to test all branches
        formated_help = self.cli.get_action_help_screen('peek')
        self.assertIn(('action-name', 'peek'), formated_help)

    def test_get_action_help_screen_full_with_builder_list(self):
        # It is here to test all branches
        formated_help = self.cli.get_action_help_screen('builder-list')
        self.assertIn(('action-name', 'builder-list'), formated_help)

    def test_get_help_screen(self):
        self.cli.get_action_help_screen = Mock(
            return_value=[], spec=self.cli.get_action_help_screen)

        self.cli.get_help_screen()
        times = len(self.cli.actions.keys())
        self.assertEqual(len(self.cli.get_action_help_screen.call_args_list),
                         times)

    def test_get_column_sizes(self):
        output = (('name', 'url', 'vcs'),
                  ('some-repo', 'git@somewhere.com', 'git'))
        expected = [9, 17, 3]

        returned = self.cli._get_column_sizes(output)

        self.assertEqual(returned, expected)

    def test_format_result(self):
        result = {'some': ['thing list']}
        returned = self.cli._format_result(result)

        self.assertEqual(str(result), returned)

    def test_format_help(self):
        result = ['some', ('styled', 'result')]

        returned = self.cli._format_help(result)

        self.assertEqual(result, returned)

    def test_format_row(self):
        sizes = [15, 17, 5]
        row = ('some-repo', 'git@somewhere.com', 'git')
        expected = 'some-repo' + (' ' * 10) + 'git@somewhere.com' + (' ' * 4)
        expected += 'git' + ' ' * 6

        formated = self.cli._format_row(sizes, row)

        self.assertEqual(formated, expected)

    def test_format_output_columns(self):
        output = (('name', 'url', 'vcs'),
                  ('some-repo', 'git@somewhere.com', 'git'))
        expected = 'name' + (' ' * 9) + 'url' + (' ' * 18) + 'vcs'
        expected += (' ' * 4) + '\n'
        expected += 'some-repo' + (' ' * 4) + 'git@somewhere.com' + (' ' * 4)
        expected += 'git' + ' ' * 6

        formated = self.cli._format_output_columns(output)

        self.assertEqual(formated.strip(), expected.strip())

    @patch.object(cli.ToxicCli, '_format_output_columns', Mock())
    def test_format_repo_list(self):
        repos = []

        self.cli._format_repo_list(repos)

        called = self.cli._format_output_columns.call_args[0][0][0]

        self.assertEqual(called, (_('name'), _('vcs')))  # noqa

    @patch.object(cli.ToxicCli, '_format_output_columns', Mock())
    def test_format_slave_list(self):
        slaves = []
        self.cli._format_slave_list(slaves)

        called = self.cli._format_output_columns.call_args[0][0][0]
        self.assertEqual(called, (_('name'), _('host'), _('port')))  # noqa

    @patch.object(cli.ToxicCli, '_format_output_columns', Mock())
    def test_format_builder_list(self):
        builders = []
        self.cli._format_builder_list(builders)

        called = self.cli._format_output_columns.call_args[0][0][0]
        self.assertEqual(called, (_('name'), _('status')))  # noqa

    def test_format_peek_with_build(self):
        response = {'body': {'steps': []}}
        self.cli._format_peek_build = Mock()

        self.cli._format_peek(response)

        self.assertTrue(self.cli._format_peek_build.called)

    def test_format_peek_with_step(self):
        response = {'body': {'command': 'ls'}}
        self.cli._format_peek_step = Mock()

        self.cli._format_peek(response)

        self.assertTrue(self.cli._format_peek_step.called)

    def test_format_peek_build_started(self):
        response = {'started': 'bla'}

        msg = self.cli._format_peek_build(response)

        self.assertEqual(msg, 'build started')

    def test_format_peek_build_finished(self):
        response = {'finished': 'bla', 'status': 'success',
                    'steps': [{'command': 'ls', 'status': 'success'}]}

        msg = self.cli._format_peek_build(response)

        expected = 'build finished with status {}'.format(response['status'])
        for step in response['steps']:
            expected += '\n step {} - {}'.format(step['command'],
                                                 step['status'])

        self.assertEqual(msg, expected)

    def test_format_peek_step_started(self):
        response = {'command': 'ls'}
        expected = _('step ls is running')  # noqa
        msg = self.cli._format_peek_step(response)

        self.assertEqual(msg, expected)

    def test_format_peek_step_finished(self):
        response = {'command': 'ls', 'finished': 'bla',
                    'status': 'fail'}
        expected = _('step ls finished with status fail')  # noqa
        msg = self.cli._format_peek_step(response)

        self.assertEqual(msg, expected)
