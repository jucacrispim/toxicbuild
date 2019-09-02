# -*- coding: utf-8 -*-
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

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

import asyncio
import inspect
import random
import re
import sys

import urwid

from toxicbuild.ui import translate, inutils
from toxicbuild.ui.console.commands import (RepoAddCommand,
                                            RepoListCommand,
                                            RepoCommandGroup)
from toxicbuild.ui.console.widgets import (ExtendedEdit,
                                           NotSelectableBottomAlignedListBox)


def parse_cmdline(cmdline):
    """ Parses a command line from the console.
    Returns action, args, kwargs for the command line.

    :param cmdline: Input from the user as a string.
    """

    # getting rid of the spaces around equal signs (kwargs)
    cmdline = re.sub(re.compile('(\s+|)=(\s+|)'), '=', cmdline)

    # removing quotes
    cmdline = re.sub(re.compile('(\'|")'), '', cmdline)

    action, rest = cmdline.split()[0], cmdline.split()[1:]
    cmdargs, cmdkwargs = [], {}

    for part in rest:
        if '=' in part:
            k, v = part.split('=')
            cmdkwargs.update({k: v})
        else:
            if part.isdigit():
                part = int(part)
            cmdargs.append(part)

    return action, cmdargs, cmdkwargs


class TextScreen(urwid.Text):
    def __init__(self):
        self._screen = self._get_screen()
        super().__init__(self._screen)

    def _get_screen(self):
        return ''


class WelcomeScreen(TextScreen):

    def _get_screen(self):
        welcome = self._get_welcome_text()
        hlp = self._get_help_screen()

        screen = welcome + hlp
        screen.append('\n\n\n')
        return screen

    def _get_welcome_text(self):
        # Translators: Do not translate what is inside {}
        base_txt = translate('Welcome to {toxicbuild}')
        text = [base_txt.replace('{toxicbuild}', ''), '\n']
        toxicbuild = random.choice(inutils.LOGOS)
        text += toxicbuild

        text.append('\n')
        text.append(random.choice(inutils.SENTENCES))
        text.append('\n\n')

        return text

    def _get_help_screen(self):
        # Translators: Do not translate what is inside {}
        base_txt = translate('Type {h} for help and {q} for quit')

        # all this mess to put colors on h and q... pfff
        msg0 = base_txt.split('{h}')[0]
        msg1 = base_txt.split('{h}')[1].split('{q}')[0]
        msg2 = base_txt.split('{h}')[1].split('{q}')[1]

        textstyle = [msg0, ('action-name', 'h'), msg1, ('action-name', 'q'),
                     msg2]
        return textstyle


class HelpScreen(TextScreen):

    def __init__(self, commands):
        self.commands = commands
        super().__init__()

    def _get_base_text(self):
        text = [('action-name', 'help'), ' - ']
        text.append(
            translate('Displays this help text. If `command-name` displays '
                      'the command help text')
        )
        text.append('\n')
        return text

    def _get_params_text(self):
        text = []
        params = translate('Parameters')
        text.append('  {}: '.format(params))
        text.append(('param', 'command-name'))
        text.append('\n')
        return text

    def _get_example_text(self):
        text = []
        example = translate('Example')
        text.append('  {}: '.format(example))
        text.append(('bold_green', 'help repo-add'))
        text.append('\n\n')
        return text

    def _get_quit_cmd_text(self):
        text = []
        text.append(('action-name', 'quit'))
        text.append(' - ')
        text.append(translate('Finishes the program'))
        text.append('\n')
        return text

    def _get_screen(self):
        text = self._get_base_text()
        text += self._get_params_text()
        text += self._get_example_text()
        text += self._get_quit_cmd_text()

        for command in self.commands:
            text.append(('action-name', command.get_name()))
            text.append(' - ')
            text.append(command.get_help())
            text.append('\n')

        return text


class CommandHelpScreen(TextScreen):

    def __init__(self, command):
        self.command = command
        super().__init__()

    def _get_base_text(self):
        text = [('action-name', self.command.get_name()), ' - ']
        text.append(self.command.get_help())
        text.append('\n')
        return text

    def _get_params_text(self):
        text = []
        if self.command.params:  # pragma no branch
            params = translate('Parameters')
            params = '  {}: '.format(params)
            params_len = len(params)
            text.append(params)
            text.append(('param', self.command.params[0]['name']))
            text.append('\n')
            for para in self.command.params[1:]:
                text.append(' ' * params_len)
                text.append(('param', para['name']))
                text.append('\n')

        return text

    def _get_example_text(self):
        text = []
        if self.command.example:  # pragma no branch
            example = translate('Example')
            example = '  {}: '.format(example)
            text.append(example)
            text.append(('bold_green', self.command.example))
            text.append('\n')
        return text

    def _get_screen(self):
        text = self._get_base_text()
        text += self._get_params_text()
        text += self._get_example_text()
        return text


class RepoRowScreen(TextScreen):
    """A row in the repo list"""

    def __init__(self, repo):
        self.repo = repo
        self.last_buildset = self.repo.last_buildset

        super().__init__()

    def _get_screen(self):
        try:
            commit = self.last_buildset.commit[:8]
            title = self.last_buildset.title
        except AttributeError:
            commit = ''
            title = ''

        text = [
            ('under', self.repo.full_name),
            ' - ',
            ('status-' + self.repo.status, self.repo.status),
            '\n',
            commit,
            '  ' + title,
            '\n\n',
        ]
        return text


class RepoListScreen(urwid.Pile):

    def __init__(self, repos):
        self.repos = repos
        pile = [RepoRowScreen(repo) for repo in self.repos]
        super().__init__(pile)


class MainScreen(urwid.BoxAdapter):

    def __init__(self):
        self._listbox = NotSelectableBottomAlignedListBox([
            urwid.Text('')
        ])
        super().__init__(self._listbox, height=0)

    def set_height(self, height):
        self.height = height

    def set_screen(self, widget):
        self._listbox.body = [widget]

    def get_screen(self):
        return self._listbox.body[0]

    def scroll_up(self, size=None):
        size = size or (1, self.height)
        self._listbox.keypress(size, 'up')

    def scroll_down(self, size=None):
        size = size or (1, self.height)
        self._listbox.keypress(size, 'down')


class ToxicConsole(urwid.Filler):

    PALETTE = [
        ('bold_blue', 'dark blue,bold', 'black'),
        ('bold_yellow', 'yellow,bold', 'black'),
        ('bold_white', 'white,bold', 'black'),
        ('bold_red', 'light red,bold', 'black'),
        ('bold_green', 'light green,bold', 'black'),
        ('bg', '', '', '', 'dark green', 'h0'),
        ('under', 'light green,underline', 'black'),
        ('error', 'dark red', 'black'),
        ('action-name', 'dark blue,bold', 'black'),
        ('status-running', '', '', '', 'white', 'h26'),
        ('status-fail', '', '', '', 'white', 'h160'),
        ('status-ready', '', '', '', 'white', 'h240'),
        ('status-exception', '', '', '', 'white', 'h89'),
        ('status-cancelled', '', '', '', 'h102,bold', ''),
        ('status-success', '', '', '', 'white', 'h22'),
        ('status-warning', '', '', '', 'h202,bold', ''),
        ('status-pending', '', '', '', 'h190,bold', ''),
        ('param', 'white,bold', 'black')
    ]

    def __init__(self, user):
        self.user = user
        self._prompt = 'toxicbuild> '
        self._loop = None
        self.messages = urwid.Text('')
        self.main_screen = MainScreen()
        self.div = urwid.Divider()
        self.user_input = ExtendedEdit(self._prompt)
        self.pile = urwid.Pile(
            [
                self._set_bg(self.main_screen),
                self._set_bg(self.div),
                self._set_bg(self.messages),
                self._set_bg(self.div),
                self._set_bg(self.user_input)
            ]
        )

        # 4 lines at the bottom of the screen: 2 for  divs, 1 for messages and
        # 1 for user input. Used to calculate the main screen rows.
        self._bottom_rows = 4

        self.actions = {
            'welcome-screen': self.show_welcome_screen,
            'help': self.show_help_screen,
            'h': self.show_help_screen,
            'quit': self.quit_program,
            'q': self.quit_program,
            'repo-list': self.show_repo_list,
        }

        self.commands = [
            RepoAddCommand(self.user),
            RepoListCommand(self.user),
            RepoCommandGroup(self.user)
        ]
        self._commands_table = {cmd.get_name(): cmd for cmd in self.commands}

        self._key_callbacks = {  # pragma no branch for the lambdas
            'enter': self._handle_enter_key,
            'ctrl n': lambda size, key: self.main_screen.scroll_down(size),
            'ctrl p': lambda size, key: self.main_screen.scroll_up(size),
            'ctrl down': lambda size, key: self.main_screen.scroll_down(size),
            'ctrl up': lambda size, key: self.main_screen.scroll_up(size),
        }

        super().__init__(self.pile, valign='bottom')

    def _set_bg(self, el):
        urwid.AttrMap(el, 'bg')
        return el

    @property
    def loop(self):
        if self._loop:
            return self._loop

        loop = asyncio.get_event_loop()
        evl = urwid.AsyncioEventLoop(loop=loop)
        self._loop = urwid.MainLoop(self._set_bg(self), event_loop=evl)
        return self._loop

    @property
    def screen_size(self):
        """Returns (cols, rows) for the screen size."""
        return self.loop.screen.get_cols_rows()

    @property
    def screen_cols(self):
        """Returns the number of columns in the screen.
        """

        return self.screen_size[0]

    @property
    def screen_rows(self):
        """Returns the number of rows in the screen.
        """

        return self.screen_size[1]

    def _get_main_screen_rows(self):
        return self.screen_rows - self._bottom_rows

    def run(self):
        self.loop.screen.set_terminal_properties(colors=256)
        self.loop.screen.register_palette(self.PALETTE)
        self.show_welcome_screen()
        self.loop.run()

    def _handle_enter_key(self, size, key):
        txt = self._get_input_text()
        self._clean_input_messages()
        if not txt:
            return

        f = asyncio.ensure_future(self.handle_input(txt))

        # for tests
        return f

    def keypress(self, size, key):
        super().keypress(size, key)
        call = self._key_callbacks.get(key, lambda size, key: None)
        return call(size, key)

    def _get_input_text(self):
        txt = self.user_input.get_edit_text()
        return txt

    def _clean_input_messages(self):
        self.user_input.set_edit_text('')
        self.messages.set_text('')

    async def handle_input(self, cmdline):
        cmd, args, kwargs = parse_cmdline(cmdline)
        if cmd not in self.actions:
            msg = translate('Command "{}" does not exist').format(cmdline)
            self.set_error_message(msg)
            return False

        call = self.actions[cmd]

        if not inspect.iscoroutinefunction(call):

            async def wrapper(*a, **kw):
                return call(*a, **kw)

            fn = wrapper
        else:
            fn = call

        try:
            await fn(*args, **kwargs)
        except Exception as e:
            self.set_error_message(str(e))
            return False

        return True

    def set_error_message(self, message):
        self.messages.set_text(('error', message))

    def quit_program(self):
        sys.exit(0)

    def set_main_screen(self, widget):
        rows = self._get_main_screen_rows()
        self.main_screen.set_height(rows)
        self.main_screen.set_screen(widget)

    def show_welcome_screen(self):
        screen = WelcomeScreen()
        self.set_main_screen(screen)

    def show_help_screen(self, cmd=None):
        if not cmd:
            screen = HelpScreen(self.commands)
        else:
            command = self._commands_table[cmd]
            screen = CommandHelpScreen(command)
        self.set_main_screen(screen)

    async def show_repo_list(self):
        cmd = self._commands_table['repo-list']
        repos = await cmd.execute()
        screen = RepoListScreen(repos)
        self.set_main_screen(screen)
