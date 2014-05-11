# -*- coding: utf-8 -*-

import unittest
from mock import Mock, patch
from toxicbuild.db import models


class RevisionConfigTestCase(unittest.TestCase):

    @patch.object(models, 'session', Mock())
    def test_save_revconf(self):
        models.session.query.return_value.filter.return_value\
                                                .all.return_value = []
        models.RevisionConfig.save_revconf('098af',  'master', 'git@somewhere',
                                           '[steps]\n  - python setup.py test')

        called = models.session.add.call_args[0][0]

        self.assertTrue(isinstance(called, models.RevisionConfig))

    @patch.object(models, 'session', Mock())
    def test_save_revconf_with_duplicate(self):
        models.RevisionConfig.save_revconf('098af',  'master', 'git@somewhere',
                                           '[steps]\n  - python setup.py test')

        self.assertFalse(models.session.add.called)

    @patch.object(models, 'session', Mock())
    def test_get_revconf_with_revision(self):
        models.session.query.return_value.filter.return_value = [Mock()]
        revision = 'saf090'
        branch = 'master'
        repourl = 'git@somewhere'

        models.RevisionConfig.get_revconf(branch, repourl, revision)

        called = models.session.query.return_value.filter.call_args[0][-1]

        self.assertEqual(
            str(called), str(models.RevisionConfig.revision == revision))

    @patch.object(models, 'session', Mock())
    def test_get_revconf_without_revision(self):
        models.session.query.return_value.filter.return_value.\
            all.return_value = [Mock()]
        branch = 'master'
        repourl = 'git@somewhere'

        models.RevisionConfig.get_revconf(branch, repourl)
        called = models.session.query.return_value.filter.call_args[0][-1]
        self.assertEqual(
            str(called), str(models.RevisionConfig.repourl == repourl))

    @patch.object(models, 'session', Mock())
    def test_get_revconf_without_repourl(self):
        models.session.query.return_value.filter.return_value.\
            all.return_value = [Mock()]
        branch = 'master'
        models.RevisionConfig.get_revconf(branch)

        called = models.session.query.return_value.filter.call_args[0][-1]

        self.assertEqual(
            str(called), str(models.RevisionConfig.branch == branch))
