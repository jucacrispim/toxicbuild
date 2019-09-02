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

import builtins
from unittest import TestCase
from unittest.mock import patch, Mock, MagicMock

import urwid

from toxicbuild.ui.console import widgets


class ExtendedEditTest(TestCase):

    @patch.object(
        widgets.ExtendedEdit, '_get_history',
        Mock(return_value=[], spec=widgets.ExtendedEdit._get_history))
    def setUp(self):
        self.edit = widgets.ExtendedEdit('prompt: ')
        self.edit.history = []

    def test_append_to_history(self):
        item = 'bla'

        self.edit.append_to_history(item)

        self.assertEqual(self.edit.history[0], item)

    def test_append_to_history_with_same_item(self):
        item = 'bla'
        self.edit.append_to_history(item)
        self.edit.append_to_history(item)

        self.assertEqual(len(self.edit.history), 1)

    def test_append_to_history_limit(self):
        self.edit.history_limit = 5

        for i in range(10):
            self.edit.append_to_history(str(i))

        self.assertEqual(len(self.edit.history), 5)

    @patch.object(builtins, 'open', MagicMock())
    def test_save_to_history(self):
        self.edit.history = ['some', 'thing']

        self.edit.save_history()

        fd_mock = builtins.open.return_value.__enter__.return_value
        history_content = fd_mock.write.call_args[0][0]
        self.assertEqual(history_content, '\n'.join(self.edit.history))

    def test_get_previous(self):
        item_a, item_b, item_c = 'a', 'b', 'c'
        self.edit.append_to_history(item_a)
        self.edit.append_to_history(item_b)
        self.edit.append_to_history(item_c)

        previous = self.edit.get_previous()

        self.assertEqual(item_c, previous)

    def test_get_previous_on_last(self):
        # Ensure that you can round throught the queue

        item_a, item_b, item_c = 'a', 'b', 'c'
        self.edit.append_to_history(item_c)
        self.edit.append_to_history(item_b)
        self.edit.append_to_history(item_a)

        self.edit.get_previous()
        self.edit.get_previous()
        self.edit.get_previous()

        previous = self.edit.get_previous()

        self.assertEqual(previous, item_a)

    def test_get_next(self):
        item_a, item_b, item_c = 'a', 'b', 'c'

        self.edit.append_to_history(item_c)
        self.edit.append_to_history(item_b)
        self.edit.append_to_history(item_a)

        next_item = self.edit.get_next()

        self.assertEqual(next_item, item_c)

    def test_get_next_in_the_end_of_the_list(self):
        item_a, item_b, item_c = 'a', 'b', 'c'

        self.edit.append_to_history(item_c)
        self.edit.append_to_history(item_b)
        self.edit.append_to_history(item_a)
        self.edit._history_position = 3

        next_item = self.edit.get_next()

        self.assertEqual(next_item, item_c)

    def test_register_callback(self):
        call = MagicMock()
        self.edit.register_callback('a', call)
        self.assertIs(self.edit._callbacks['a'], call)

    def test_unregister_callback(self):
        call = MagicMock()
        self.edit.register_callback('a', call)
        self.edit.unregister_callback('a')
        self.assertIsNone(self.edit._callbacks.get('a'))

    def test_keypress_with_enter(self):
        self.edit.get_edit_text = Mock(return_value='some text')
        self.edit.keypress((10,), 'enter')

        self.assertTrue('some text' in self.edit.history)

    def test_keypress_with_up(self):
        self.edit.append_to_history('something-previous')
        self.edit.set_edit_text = Mock(
            spec=self.edit.set_edit_text)

        self.edit.keypress((10,), 'up')

        cmd = self.edit.set_edit_text.call_args[0][0]

        self.assertEqual(cmd, 'something-previous')

    def test_keypress_with_down(self):
        self.edit.append_to_history('onething')
        self.edit.append_to_history('otherthing')

        self.edit.set_edit_text = Mock(
            spec=self.edit.set_edit_text)

        self.edit.keypress((10,), 'down')

        cmd = self.edit.set_edit_text.call_args[0][0]

        self.assertEqual(cmd, 'onething')

    def test_keypress_with_other_key(self):
        # no exceptions, ok
        ret = self.edit.keypress((10,), 'a')

        # urwid returns None when it handles some keypress
        self.assertIsNone(ret)

    def test_get_history_without_history_file(self):
        self.edit.history_file = 'file-that-does-not-exist'
        history = self.edit._get_history()
        self.assertEqual(len(history), 0)

    @patch.object(builtins, 'open', MagicMock(spec=builtins.open))
    @patch.object(widgets.os.path, 'exists', Mock(return_value=True))
    def test_get_history_with_history_file(self):

        fd = builtins.open.return_value.__enter__.return_value
        fd.readlines.return_value = ['one item', 'two items', 'bla bla bla']

        history = self.edit._get_history()

        self.assertEqual(len(history), 3)


class BottomAlignedListBoxTest(TestCase):

    def setUp(self):
        self.widget = widgets.BottomAlignedListBox([urwid.Text('')])

    def test_get_top_blank_count(self):
        w = urwid.Text('')
        canvas = urwid.canvas.CompositeCanvas(w.render((1,)))
        canvas.pad_trim_top_bottom(2, 0)

        count = self.widget._get_top_blank_count(canvas)

        self.assertEqual(count, 2)

    def test_get_bottom_blank_count(self):
        w = urwid.Text('')
        canvas = urwid.canvas.CompositeCanvas(w.render((1,)))
        canvas.pad_trim_top_bottom(0, 2)

        count = self.widget._get_bottom_blank_count(canvas)

        self.assertEqual(count, 2)

    def test_render(self):
        canvas = self.widget.render((40, 4))

        count = self.widget._get_top_blank_count(canvas)

        # Canvas was rendered with 4 rows. 1 from the text and 3 blanks
        self.assertEqual(count, 3)

    def test_render_dont_trim_bottom(self):
        canvas = self.widget.render((40, 1))

        tcount = self.widget._get_top_blank_count(canvas)
        bcount = self.widget._get_bottom_blank_count(canvas)

        self.assertEqual(tcount, 0)
        self.assertEqual(bcount, 0)
