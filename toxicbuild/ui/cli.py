# -*- coding: utf-8 -*-

# Copyright 2015, 2017 Juca Crispim <juca@poraodojuca.net>

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

# Messy! Have fun trying to debug it. I had. :P
# It's just for fun, if you want to implement another ui to toxicubuild
# you should take a look at toxicbuild.ui.models instead of interacting
# directly with master.hole as is done in ToxicCliAction - or you could
# use it directly, that's your code!

import asyncio
from collections import deque
import os
import random
import re
import traceback
import urwid
from toxicbuild.core.exceptions import ToxicClientException
from toxicbuild.ui import inutils
from toxicbuild.ui.client import get_hole_client
from toxicbuild.ui.models import User, BuildSet, BaseModel
from toxicbuild.ui.utils import get_builders_for_buildsets


class ToxicShellError(Exception):
    pass


def parse_cmdline(cmdline):
    """ Parses a command line from toxicshell.
    Returns action, args, kwargs for the command line.

    :param cmdline: Input from the user as a string."""

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


def validate_input(command_params, user_args, user_kwargs):
    """ Validates args and kwargs from the user input against
    the args and kwargs of a known command.

    :param command_params: Known parameters for the command.
    :param user_args: Argument list submitted by the user.
    :param user_kwargs: Keyword arguments submitted by the user.
    """

    command_args = [arg['name'] for arg in command_params if arg['required']]
    command_kwargs = {arg['name']: arg['default'] for arg in command_params
                      if arg['name'] not in command_args}

    # validate this can be tricky, so lets python do the job.
    # and how I could not figure out how to create a function based on a
    # function signature in a proper way I'm using this ugly eval thing.

    args = ', '.join(command_args)
    kwargs = ', '.join(['{}={}'.format(k, v)
                        for k, v in command_kwargs.items()])

    sig = ', '.join([args, kwargs]) if (args or kwargs) else ' '
    sig = sig.strip().strip(',')

    # take that, pylint!
    f = eval('lambda {}: None'.format(sig))  # pylint: disable=eval-used

    try:
        f(*user_args, **user_kwargs)
    except Exception as e:
        raise ToxicShellError(str(e))


def get_kwargs(command_params, args):
    """ Return kwargs for ``args`` based on ``command_params``.
    ``command_params`` are the known parameters for a command, those
    sent by list-funcs."""
    # pylint: disable=undefined-variable
    kwargs = {}
    for i, arg in enumerate(args):
        try:
            kwargs.update({command_params[i]['name']: arg})
        except IndexError:
            msg = _('Bad args for command')
            raise ToxicShellError(msg)

    return kwargs


class HistoryEditMixin:

    def __init__(self, *args, **kwargs):
        # super here so it works in cooperation
        super().__init__(*args, **kwargs)
        self.history_file = os.path.join(os.path.expanduser('~'),
                                         '.toxiccli_history')
        self.history_limit = 100

        self.history = self._get_history()
        self._history_position = -1

    def append_to_history(self, item):
        # If you type the same command repeatedly we will not store
        # all these times on history.
        item = item.strip().strip('\n')
        if (not item or (self.history and item == self.history[-1])):
            return

        if len(self.history) < self.history_limit:
            self.history.append(item)
        else:
            self.history[-1] = item

    def save_history(self):
        with open(self.history_file, 'w') as fd:
            fd.write('\n'.join(self.history))

    def get_previous(self):
        prev = self.history[self._history_position]
        self._history_position -= 1
        if abs(self._history_position) > len(self.history):
            self._history_position = -1
        return prev

    def get_next(self):
        self._history_position += 1
        if self._history_position >= len(self.history):
            self._history_position = 0
        n = self.history[self._history_position]
        return n

    def keypress(self, size, key):
        if key == 'enter':
            self._history_position = -1
            edit_text = self.get_edit_text().strip()
            if edit_text:
                self.append_to_history(edit_text)

            return super().keypress(size, key)

        elif key not in ('up', 'down') or not self.history:
            return super().keypress(size, key)

        if key == 'up':
            cmd = self.get_previous()
        else:
            # down
            cmd = self.get_next()

        self.set_edit_text(cmd)

    def _get_history(self):
        if not os.path.exists(self.history_file):
            history = deque()
        else:
            with open(self.history_file, 'r') as fd:
                lines = [l.strip().strip('\n') for l in fd.readlines()]
                history = deque()
                history.extend(lines)

        return history


class HistoryEdit(HistoryEditMixin, urwid.Edit):
    pass


class ToxicCliActions:

    def __init__(self, username_or_email, password, *args,
                 host='localhost', port=6666, token=None,
                 use_ssl=True, validate_cert=True, loop=None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.username_or_email = username_or_email
        self.password = password
        self.host = host
        self.port = port
        self.token = token
        self.user = None
        self.use_ssl = use_ssl
        self.validate_cert = validate_cert
        self._loop = loop or asyncio.get_event_loop()
        self.actions = self.get_actions()

    async def authenticate(self):
        kw = {'username_or_email': self.username_or_email,
              'password': self.password}

        client = await self.get_client()
        try:
            user_dict = await client.user_authenticate(**kw)
            self.user = User(None, user_dict)
        finally:
            client.disconnect()

    @asyncio.coroutine
    def get_client(self):
        """ Returns a client connected to a toxicbuild master"""

        client = yield from get_hole_client(self.user, self.host, self.port,
                                            hole_token=self.token,
                                            use_ssl=self.use_ssl,
                                            validate_cert=self.validate_cert)
        return client

    def get_actions(self):
        """ Asks the server for which actions are available. """

        if not self.user:
            self._loop.run_until_complete(self.authenticate())

        with self._loop.run_until_complete(self.get_client()) as client:
            actions = self._loop.run_until_complete(client.list_funcs())
        return actions

    def get_action_from_command_line(self, cmdline):
        """ Returns `cmdname` and `cmdkwargs`. """
        # pylint: disable=undefined-variable

        cmd, cmdargs, cmdkwargs = parse_cmdline(cmdline)

        try:
            sig = self.actions[cmd]
        except KeyError:
            msg = _(  # noqa E821
                'Command "{}" does not exist').format(cmd)
            raise ToxicShellError(msg)

        known_params = sig['parameters']

        cmdkwargs.update(get_kwargs(known_params, cmdargs))
        return cmd, cmdkwargs

    def get_action_help(self, action_name):
        # pylint: disable=undefined-variable
        try:
            action_sig = self.actions[action_name]
        except KeyError:
            msg = _(  # noqa E821
                'Command "{}" does not exist').format(action_name)
            raise ToxicShellError(msg)

        action_help = {}
        action_help['short_doc'] = action_sig['doc'].splitlines()[0]

        action_help['doc'] = action_sig['doc']
        action_help['parameters'] = action_sig['parameters']
        return action_help

    @asyncio.coroutine
    def execute_action(self, cmdline):
        """ Execute some action based on the ``cmdline`` inputted by
        the user."""

        action, cmdkwargs = self.get_action_from_command_line(cmdline)

        with (yield from self.get_client()) as client:
            response = yield from client.request2server(action, cmdkwargs)
        return action, response


class Waterfall:
    """A class to show the buildset waterfall."""

    def __init__(self, client, repo_name, cli):
        """param client: A client connected to the master
        :param repo_name: The name of the repository
        :param cli: An instance of toxiccli."""

        self.client = client
        self.repo_name = repo_name
        self.cli = cli

    async def show_waterfall(self):

        BaseModel._client = self.client
        try:
            buildsets = await BuildSet.list(self.client.user,
                                            repo_name_or_id=self.repo_name)
            builders = await get_builders_for_buildsets(
                self.client.user, buildsets)
            return self._format_waterfall(builders, buildsets)
        finally:
            BaseModel._client = None

    def peek_callback(self, response):
        if isinstance(response, str):
            return False
        event = response['body'].get('event_type')
        self.cli.messages.set_text('got event {}'.format(event))
        if event in ['build_added', 'buid_started',
                     'build_finished']:
            self.cli.stop_peek()
            asyncio.ensure_future(self.show_waterfall())
            return True
        return False

    def _get_ordered_builds(self, builds, builders):
        if not builds:
            return []
        ordered_builds = []
        i = 0
        for b in builders:
            try:
                build = builds[i]
            except IndexError:
                ordered_builds.append('')
            else:
                if b.name != build.builder.name:
                    ordered_builds.append('')
                else:
                    ordered_builds.append(build)
                    i += 1

        return ordered_builds

    def _format_waterfall(self, builders, buildsets):
        output = [['buildsets'] + [b.name for b in builders]]
        output += [[''] + ['' for b in builders]]
        max_builds = max([len(b.builds) for b in buildsets])
        for buildset in buildsets:
            row = [buildset.commit[:8]]

            builds = self._get_ordered_builds(buildset.builds, builders)
            for i in range(max_builds):
                try:
                    build = builds[i]
                    if build:
                        row += ['Build {}'.format(build.status)]
                    else:
                        row += ['']
                except IndexError:  # pragma no cover
                    row += ['']
            output += [row]

        self._write_screen(output)

    def _write_screen(self, output):
        asyncio.ensure_future(self.cli.peek(format_fn=self.peek_callback))
        output = self.cli._format_output_columns(
            output, post_item_formatter=self.post_item_formatter,
            post_row_formatter=self.post_row_formatter)
        self.cli.main_screen.set_text(output)

    def post_item_formatter(self, item):
        # giving color to build status
        try:
            msg0, msg1 = item.split('Build')[0], item.split('Build')[1]
        except IndexError:
            return item
        status = msg1.strip()
        statuses = {'running': 'status-running',
                    'exception': 'status-exception',
                    'cancelled': 'status-cancelled',
                    'fail': 'status-fail',
                    'pending': 'status-pending',
                    'success': 'status-success',
                    'warning': 'status-warning'}
        color = statuses.get(status) or 'none'
        msg0 += 'Build'
        textstyle = ('none', msg0), (color, msg1)
        return textstyle

    def post_row_formatter(self, row):
        new_row = []
        itemstr = ''
        for item in row:
            if isinstance(item, str):
                itemstr += item
            else:
                if itemstr:  # pragma no branch
                    new_row.append(itemstr)
                    itemstr = ''
                new_row.append(item[0])
                new_row.append(item[1])

        return new_row or [''.join(row)]


class ToxicCli(ToxicCliActions, urwid.Filler):

    # urwid, great library!

    def __init__(self, username_or_email, password, host='localhost',
                 port=6666, token=None, use_ssl=True, validate_cert=True):

        self.prompt = 'toxicbuild> '
        self.input = HistoryEdit(self.prompt)
        self.messages = urwid.Text('')
        self.main_screen = urwid.Text('')
        self.div = urwid.Divider()
        self.loop = asyncio.get_event_loop()
        self.pile = urwid.Pile([self.main_screen, self.div, self.messages,
                                self.div, self.input])
        super().__init__(username_or_email, password, self.pile,
                         valign='bottom',
                         host=host, port=port,
                         token=token,
                         use_ssl=use_ssl, validate_cert=validate_cert)

        self._stop_peek = False
        self._peek_output = []
        self._exiting = False

    def __getattr__(self, attrname):
        if attrname.startswith('_format'):
            action = attrname.replace('_format_', '').replace('_', '-')

            if action in self.actions.keys():
                return self._format_result
        raise AttributeError(attrname)

    def run(self):
        palette = [('bold_blue', 'dark blue,bold', ''),
                   ('bold_yellow', 'yellow,bold', ''),
                   ('bold_white', 'white,bold', ''),
                   ('bold_red', 'dark red,bold', ''),
                   ('error', 'dark red', ''),
                   ('action-name', 'dark blue,bold', ''),
                   ('status-running', 'light cyan,bold', ''),
                   ('status-fail', 'light red,bold', ''),
                   ('status-exception', '', '', '', 'h89,bold', ''),
                   ('status-cancelled', '', '', '', 'h102,bold', ''),
                   ('status-success', '', '', '', 'h22,bold', ''),
                   ('status-warning', '', '', '', 'h202,bold', ''),
                   ('status-pending', '', '', '', 'h190,bold', ''),
                   ('param', 'white,bold', '')]

        self.show_welcome_screen()
        evl = urwid.AsyncioEventLoop(loop=self.loop)
        loop = urwid.MainLoop(self, event_loop=evl)
        loop.screen.set_terminal_properties(colors=256)
        loop.screen.register_palette(palette)
        loop.run()

    def quit(self):
        self._exiting = True
        self.input.save_history()
        raise urwid.ExitMainLoop()

    def keypress(self, size, key):
        super().keypress(size, key)
        if key != 'enter':
            return

        input_text = self.input.text.split(self.prompt)[1].strip()
        self.input.set_edit_text('')
        self.messages.set_text('')
        if not input_text:
            return
        f = asyncio.ensure_future(self.execute_and_show(input_text))
        # for tests
        return f

    @asyncio.coroutine
    def execute_and_show(self, cmdline):
        """ Executes an action requested by the user and show
        its output. """

        # A bunch of ugly stuff, I know!
        if cmdline in ['help', 'h']:
            action, response = 'help', self.get_help_screen()
        elif cmdline.startswith('help'):
            action, response = 'help', self.get_action_help_screen(
                cmdline.split(' ')[1], full=True)
        elif cmdline in ['quit', 'q']:
            # return just for tests
            return self.quit()
        elif cmdline == 'peek':
            asyncio.ensure_future(self.peek())
            return

        elif cmdline == 'stop-peek':
            self.stop_peek()
            self.messages.set_text('stopped!')
            return
        elif cmdline == 'welcome-screen':
            self.show_welcome_screen()
            return
        elif cmdline.startswith('waterfall'):
            asyncio.ensure_future(self.show_waterfall(cmdline))
            return
        else:
            try:
                action, response = yield from self.execute_action(cmdline)
            except (ToxicShellError, ToxicClientException) as e:
                self.messages.set_text(('error', str(e)))
                return

        meth_name = '_format_' + action.replace('-', '_')
        format_meth = getattr(self, meth_name)
        response = format_meth(response)

        self.main_screen.set_text(response)

    @asyncio.coroutine
    def peek(self, format_fn=None):
        """Peeks throught the master's hole."""

        with (yield from self.get_client()) as client:

            response = yield from client.request2server('stream', {})
            if not format_fn:
                self.main_screen.set_text(self._format_result(response))
            else:
                format_fn(response)

            while True:
                try:
                    response = yield from client.get_response()
                    if self._stop_peek:
                        client.diconnect()
                        break

                    if not format_fn:
                        self.main_screen.set_text(  # pragma no cover
                            self._format_peek(response))
                    else:
                        format_fn(response)
                except Exception:  # pragma no cover
                    tb = traceback.format_exc()
                    self.messages.set_text(('error', str(tb)))

        self._stop_peek = False

    def stop_peek(self):
        self._stop_peek = True

    # from here to eternity are the methods that write the screens
    # or methods related to that.
    def show_welcome_screen(self):
        """ Displays the welcome screen for toxiccli.
        """

        welcome = self._get_welcome_text()
        welcome = welcome.replace('{toxicbuild}', '')

        text = [welcome, '\n']

        toxicbuild = random.choice(inutils.LOGOS)
        text += toxicbuild

        text.append('\n')
        text.append(random.choice(inutils.SENTENCES))
        text.append('\n\n')

        help_text = self._get_help_text()

        formated_help = self._format_help_text(help_text)

        text += formated_help

        text.append('\n\n\n')

        self.main_screen.set_text(text)

    async def show_waterfall(self, cmdline):
        _, args, _ = parse_cmdline(cmdline)
        try:
            repo_name = args[0]
        except IndexError:
            self.messages.set_text(('error', 'repo_name required'))
            return False
        client = await self.get_client()
        waterfall = Waterfall(client, repo_name, self)
        asyncio.ensure_future(waterfall.show_waterfall())
        return True

    def get_action_help_screen(self, action, full=True):
        """ Returns a list already formated to be displayed by
        ``self.main_screen`` as the help for a command.
        """

        action_help = self.get_action_help(action)
        text = [('action-name', action), ' - ',
                '%s' % action_help['short_doc']]

        if full:
            params = _('Parameters')  # pylint: disable=undefined-variable
            required = _('Required')  # pylint: disable=undefined-variable

            text += [action_help['doc'], '\n']

            if action_help['parameters']:
                text.append('%s: ' % params)

                for i, param in enumerate(action_help['parameters']):
                    name = param['name']
                    lineinit = ' ' * len(params + ': ') if i != 0 else ''
                    text += [lineinit, ('param', name), ' ']
                    if param['required']:
                        text += [('required', required), '\n']
        text.append('\n')
        return text

    def get_help_screen(self, command_name=None):
        # pylint: disable=undefined-variable
        text = [('action-name', 'help'), ' - ']

        text.append(_('Displays this help text.'))  # noqa F821

        params = _('Parameters')  # noqa F821
        text += ['\n%s: ' % params, ('param', 'command-name\n\n')]
        text += [('action-name', 'quit'), ' - ']

        text.append(_('Finishes the program'))  # noqa F821
        text.append('\n')

        ordered_actions = sorted(self.actions.keys())

        for action in ordered_actions:
            text += self.get_action_help_screen(action, full=False)

        return text

    def _get_welcome_text(self):
        # pylint: disable=undefined-variable
        # Translators: Do not translate what is inside {}
        return _('Welcome to {toxicbuild}')

    def _get_help_text(self):
        # pylint: disable=undefined-variable
        # Translators: Do not translate what is inside {}
        return _('Type {h} for help and {q} for quit')

    def _format_help_text(self, text):
        # all this mess to put colors on h and q... pfff
        msg0, msg1 = text.split('{h}')[0], text.split('{h}')[1].split('{q}')[0]
        msg2 = text.split('{h}')[1].split('{q}')[1]

        textstyle = [msg0, ('action-name', 'h'), msg1, ('action-name', 'q'),
                     msg2]
        return textstyle

    def _get_column_sizes(self, output):
        """ Returns a list with the max sizes of for the columns
        of the output. ``output`` is a tuple of tuples, like this:
        `(('a_thing' 'other_thing'), ('value', 'valueb')...)` and returns
        `[7, 11]`.

        """

        sizes = [len(max(c, key=lambda x: len(str(x)))) for c in zip(*output)]
        return sizes

    def _format_result(self, result):
        return str(result)

    def _format_help(self, result):
        return result

    def _format_row(self, sizes, row, post_item_formatter=lambda x: x):
        formated_row = []
        for i, item in enumerate(row):
            item = str(item)
            size = sizes[i]
            itemstr = item + ' ' * (size - len(item)) + ' ' * 4
            formated_row.append(post_item_formatter(itemstr))

        return formated_row

    def _format_output_columns(self, output,
                               post_item_formatter=lambda x: x,
                               post_row_formatter=lambda x: x):
        sizes = self._get_column_sizes(output)
        formated_output = []

        for row in output:
            try:
                row = self._format_row(sizes, row, post_item_formatter)
                new_row = post_row_formatter(row)
                for item in new_row:
                    formated_output.append(item)
            except IndexError:
                formated_output.append('')

            formated_output.append('\n')

        return formated_output

    def _format_repo_list(self, repos):
        # pylint: disable=undefined-variable
        output = [(_('name'), _('vcs'))]  # noqa F821
        output += [(r['name'], r['vcs_type']) for r in repos]
        return self._format_output_columns(output)

    def _format_slave_list(self, slaves):
        # pylint: disable=undefined-variable
        output = [(_('name'), _('host'), _('port'))]  # noqa F821
        output += [(s['name'], s['host'], s['port']) for s in slaves]
        return self._format_output_columns(output)

    def _format_builder_list(self, builders):
        # pylint: disable=undefined-variable

        output = [(_('name'), _('status'))]  # noqa F821
        output += [(b['name'], b['status'])
                   for b in builders]
        return self._format_output_columns(output)

    def _format_peek(self, response):
        response = response['body']

        if response['event_type'] in ['build_started', 'build_finished']:
            msg = self._format_peek_build(response)

        elif response['event_type'] in ['step_started', 'step_finished']:
            msg = self._format_peek_step(response)
        else:  # pragma no cover
            msg = ''

        self._peek_output.append(msg)
        return '\n'.join(self._peek_output)

    def _format_peek_build(self, response):
        if response.get('finished'):
            msg = 'build finished with status {}'.format(
                response['status'])

            for step in response['steps']:
                msg += '\n step {} - {}'.format(step['command'],
                                                step['status'])
        else:
            msg = 'build started'

        return msg

    def _format_peek_step(self, response):
        if response.get('finished'):
            # Translators: Do not translate what is inside {}
            msg = _(  # pylint: disable=undefined-variable
                'step {step} finished with status {status}')
            msg = msg.format(step=response['command'],
                             status=response['status'])
        else:
            # Translators: Do not translate what is inside {}
            msg = _(  # pylint: disable=undefined-variable
                'step {step} is running')
            msg = msg.format(step=response['command'])

        return msg
