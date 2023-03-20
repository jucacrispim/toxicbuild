# -*- coding: utf-8 -*-
# Copyright 2019, 2023 Juca Crispim <juca@poraodojuca.net>

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

from unittest import TestCase
from unittest.mock import patch, MagicMock, AsyncMock

from toxicbuild.ui.console import screens

from tests import async_test

# urwid changes the locale and this makes a test on vcs fail
# so, changing it back here

import locale
locale.setlocale(locale.LC_ALL, 'C')


class ParseCmdLineTest(TestCase):

    def test_parse_cmdline(self):
        cmdline = 'repo-add toxicbuild git@toxicbuild.com/toxicbuild.git'
        cmdline += ' 300 git'

        expected = ('repo-add',
                    ['toxicbuild', 'git@toxicbuild.com/toxicbuild.git', 300,
                     'git'], {})

        returned = screens.parse_cmdline(cmdline)

        self.assertEqual(returned, expected)

    def test_parse_cmdline_without_args(self):
        cmdline = 'repo-list'
        expected = ('repo-list', [], {})
        returned = screens.parse_cmdline(cmdline)

        self.assertEqual(returned, expected)

    def test_parse_cmdline_with_kwargs(self):

        cmdline = 'command-name param1 param2=bla'

        expected = ('command-name', ['param1'], {'param2': 'bla'})

        returned = screens.parse_cmdline(cmdline)

        self.assertEqual(returned, expected)


class TextScreenText(TestCase):

    def setUp(self):
        self.screen = screens.TextScreen()

    def test_get_screen(self):
        self.assertIsInstance(self.screen._get_screen(), str)


class WelcomeScreenTest(TestCase):

    def test_screen(self):
        screen = screens.WelcomeScreen()
        self.assertTrue(screen._screen)


class HelpScreenTest(TestCase):

    def test_screen(self):
        screen = screens.HelpScreen([screens.RepoAddCommand(MagicMock()),
                                     screens.RepoCommandGroup(MagicMock())])
        self.assertIn('help - ', screen.text)
        self.assertIn('repo-add - ', screen.text)


class CommandHelpScreenTest(TestCase):

    def test_screen(self):
        screen = screens.CommandHelpScreen(
            screens.RepoCommandGroup(MagicMock()))
        self.assertIn('repository-name', screen.text)

    def test_screen_with_params(self):
        screen = screens.CommandHelpScreen(
            screens.RepoAddCommand(MagicMock()))
        self.assertIn('name', screen.text)
        self.assertIn('url', screen.text)
        self.assertIn('envvars', screen.text)


class MainScreen(TestCase):

    def setUp(self):
        self.screen = screens.MainScreen()

    def test_set_height(self):
        self.screen.set_height(10)
        self.assertEqual(self.screen.height, 10)

    def test_set_screen(self):
        widget = MagicMock()
        self.screen.set_screen(widget)

        self.assertEqual(self.screen._listbox.body, [widget])

    def test_get_screen(self):
        widget = MagicMock()
        self.screen.set_screen(widget)

        self.assertIs(self.screen.get_screen(), widget)

    def test_scroll_up(self):
        self.screen._listbox.keypress = MagicMock(
            spec=self.screen._listbox.keypress)
        self.screen.scroll_up()
        called = self.screen._listbox.keypress.call_args[0][1]

        self.assertEqual(called, 'up')

    def test_scroll_down(self):
        self.screen._listbox.keypress = MagicMock(
            spec=self.screen._listbox.keypress)
        self.screen.scroll_down()
        called = self.screen._listbox.keypress.call_args[0][1]

        self.assertEqual(called, 'down')


class ToxicConsoleTest(TestCase):

    def setUp(self):
        self.console = screens.ToxicConsole(MagicMock())

    def test_loop_not_none(self):
        loop = MagicMock()
        self.console._loop = loop

        self.assertIs(self.console.loop, loop)

    def test_loop(self):
        self.console._loop = None
        self.assertTrue(self.console.loop)

    def test_screen_size(self):
        self.assertIsInstance(self.console.screen_size, tuple)
        self.assertEqual(len(self.console.screen_size), 2)

    def test_screnn_cols(self):
        self.assertIsInstance(self.console.screen_cols, int)

    def test_screen_rows(self):
        self.assertIsInstance(self.console.screen_rows, int)

    @patch.object(screens.urwid, 'MainLoop', MagicMock())
    @patch.object(screens.ToxicConsole, 'show_welcome_screen', MagicMock())
    def test_run(self):
        self.console.run()
        self.assertTrue(screens.urwid.MainLoop.return_value.run.called)
        self.assertTrue(screens.ToxicConsole.show_welcome_screen.called)

    def test_set_main_screen(self):
        widget = screens.urwid.Text('A text')
        self.console.set_main_screen(widget)
        self.assertEqual(
            self.console.main_screen.original_widget.body[0].text, 'A text')

    def test_get_main_screen_rows(self):
        rows = self.console._get_main_screen_rows()
        expected = self.console.screen_rows - self.console._bottom_rows
        self.assertEqual(rows, expected)

    def test_show_welcome_screen(self):
        self.console.show_welcome_screen()
        screen = self.console.main_screen.get_screen()
        self.assertIsInstance(screen, screens.WelcomeScreen)

    def test_get_input_text(self):
        self.console.user_input.set_edit_text('ls')
        self.assertEqual(self.console._get_input_text(), 'ls')

    def test_clean_input_messages(self):
        self.console.user_input.set_edit_text('the text')
        self.console.messages.set_text('A message')
        self.console._clean_input_messages()
        self.assertFalse(self.console.user_input.get_edit_text())
        self.assertFalse(self.console.messages.text)

    def test_keypress_not_enter(self):
        r = self.console.keypress((10, 10), 'a')
        self.assertIsNone(r)

    def test_keypress_no_text(self):
        r = self.console.keypress((10, 10), 'enter')
        self.assertIsNone(r)

    @patch.object(screens.ToxicConsole, 'handle_input',
                  AsyncMock(spec=screens.ToxicConsole.handle_input))
    @async_test
    async def test_keypress(self):
        self.console.user_input.set_edit_text('bla')
        r = self.console.keypress((10, 10), 'enter')
        self.assertTrue(r)
        await r
        self.assertTrue(self.console.handle_input.called)

    def test_set_error_message(self):
        self.console.set_error_message('a message')
        self.assertEqual(self.console.messages.text, 'a message')

    @patch.object(screens.sys, 'exit', MagicMock())
    def test_quit_program(self):
        self.console.quit_program()
        self.assertTrue(screens.sys.exit.called)

    def test_show_help_screen_no_command(self):
        self.console.show_help_screen()
        screen = self.console.main_screen.get_screen()
        self.assertIsInstance(screen, screens.HelpScreen)

    def test_show_help_screen_command(self):
        self.console.show_help_screen('repo-use')
        screen = self.console.main_screen.get_screen()
        self.assertIsInstance(screen, screens.CommandHelpScreen)

    @patch.object(screens.RepoListCommand, 'execute',
                  AsyncMock(spec=screens.RepoListCommand.execute,
                            return_value=[]))
    @async_test
    async def test_show_repo_list(self):
        await self.console.show_repo_list()
        screen = self.console.main_screen.get_screen()
        self.assertIsInstance(screen, screens.RepoListScreen)

    @patch.object(screens.ToxicConsole, 'set_error_message', MagicMock())
    @async_test
    async def test_handle_input_bad_cmd(self):
        cmdline = 'a-bad'
        r = await self.console.handle_input(cmdline)
        self.assertFalse(r)
        self.assertTrue(self.console.set_error_message.called)

    @async_test
    async def test_handle_input_fn(self):
        fn_mock = MagicMock()
        self.console.actions = {'fn': fn_mock}
        cmdline = 'fn'
        r = await self.console.handle_input(cmdline)
        self.assertTrue(r)
        self.assertTrue(fn_mock.called)

    @patch.object(screens.ToxicConsole, 'set_error_message', MagicMock())
    @async_test
    async def test_handle_input_error(self):
        fn_mock = MagicMock(side_effect=Exception)
        self.console.actions = {'fn': fn_mock}
        cmdline = 'fn'
        r = await self.console.handle_input(cmdline)
        self.assertFalse(r)
        self.assertTrue(self.console.set_error_message.called)

    @async_test
    async def test_handle_input_coro(self):
        fn_mock = AsyncMock()

        async def coro(*a, **kw):
            await fn_mock()

        self.console.actions = {'fn': coro}
        cmdline = 'fn'
        r = await self.console.handle_input(cmdline)
        self.assertTrue(r)
        self.assertTrue(fn_mock.called)


class RepoRowScreenTest(TestCase):

    def test_screen_no_last_buildset(self):
        repo = MagicMock()
        repo.full_name = 'me/my-repo'
        repo.status = 'success'

        class LastBS:
            pass

        repo.last_buildset = LastBS()

        self.screen = screens.RepoRowScreen(repo)

        self.assertIn('me/my-repo', self.screen.text)

    def test_screen_last_buildset(self):
        repo = MagicMock()
        repo.full_name = 'me/my-repo'
        repo.status = 'success'

        class LastBS:
            commit = 'thesha'
            title = 'bla'

        repo.last_buildset = LastBS()

        self.screen = screens.RepoRowScreen(repo)

        self.assertIn('me/my-repo', self.screen.text)
        self.assertIn('thesha', self.screen.text)
