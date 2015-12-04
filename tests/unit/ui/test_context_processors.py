# -*- coding: utf-8 -*-

from unittest import TestCase, mock
from toxicbuild.ui import context_processors


class ToxicWebMainContextProcessorTest(TestCase):

    @mock.patch.object(context_processors, 'settings', mock.Mock())
    def test_get_context(self):
        context_processors.settings.HOLE_HOST = 'localhost'
        context_processors.settings.HOLE_PORT = 1234
        processor = context_processors.ToxicWebMainContextProcessor(
            mock.Mock())
        context = processor.get_context()

        self.assertIn('master_location', context.keys())
