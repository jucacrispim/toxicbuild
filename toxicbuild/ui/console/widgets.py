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

from collections import deque
import os

import urwid


class ExtendedEdit(urwid.Edit):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history_file = os.path.join(os.path.expanduser('~'),
                                         '.toxiccli_history')
        self.history_limit = 100

        self.history = self._get_history()
        self._history_position = -1
        self._callbacks = {}
        self.register_callback('enter', self._add2history)
        self.register_callback('up', self._get_previous_command)
        self.register_callback('down', self._get_next_command)

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

    def register_callback(self, key, call):
        """Registers a callback to be called when a specific key
        is pressed.

        :param key: The key that triggers the callback.
        :param call: A callable that gets two params: size, key
        """

        self._callbacks[key] = call

    def unregister_callback(self, key):
        """Un-registers a callback

        :param key: The key to un-register the callback.
        """

        self._callbacks.pop(key, None)

    def _add2history(self, size, key):
        self._history_position = -1
        edit_text = self.get_edit_text().strip()
        if edit_text:
            self.append_to_history(edit_text)

        return super().keypress(size, key)

    def _get_previous_command(self, size, key):
        cmd = self.get_previous()
        self.set_edit_text(cmd)

    def _get_next_command(self, size, key):
        cmd = self.get_next()
        self.set_edit_text(cmd)

    def keypress(self, size, key):
        call = self._callbacks.get(key, super().keypress)
        return call(size, key)

    def _get_history(self):
        if not os.path.exists(self.history_file):
            history = deque()
        else:
            with open(self.history_file, 'r') as fd:
                lines = [l.strip().strip('\n') for l in fd.readlines()]
                history = deque()
                history.extend(lines)

        return history


class NotSelectable:

    def selectable(self):
        return False


class BottomAlignedListBox(urwid.ListBox):
    """A list box that align its contents to the bottom of the canvas
    by padding on top of the actual content if needed.
    """

    def render(self, *args, **kwargs):
        canvas = super().render(*args, **kwargs)

        top = self._get_top_blank_count(canvas)
        bottom = self._get_bottom_blank_count(canvas)

        # remove blank canvases added by ListBox
        canvas = urwid.canvas.CompositeCanvas(canvas)
        canvas.trim(top)
        if bottom:
            canvas.trim_end(bottom)

        # reverse top/bottom and add blank canvas again
        top, bottom = bottom, top
        canvas.pad_trim_top_bottom(top, bottom)
        return canvas

    def _get_top_blank_count(self, canvas):
        shard = canvas.shards[0]
        return self._get_blank_count(shard)

    def _get_bottom_blank_count(self, canvas):
        shard = canvas.shards[-1]
        return self._get_blank_count(shard)

    def _get_blank_count(self, shard):
        count = 0
        cnv = shard[1][0][-1]
        if isinstance(cnv, urwid.BlankCanvas):
            count = shard[0]

        return count


class NotSelectableBottomAlignedListBox(NotSelectable, BottomAlignedListBox):
    pass
