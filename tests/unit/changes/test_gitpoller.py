# -*- coding: utf-8 -*-

import unittest
from mock import Mock, patch
from toxicbuild.changes import gitpoller


class GitPollerTestCase(unittest.TestCase):
    @patch.object(gitpoller.GitPoller, 'poll', Mock())
    def setUp(self):
        self.repourl = 'git@git.nada.com'
        self.workdir = 'my-workdir'
        self.poller = gitpoller.GitPoller(
            repourl=self.repourl, workdir=self.workdir)

    @patch.object(gitpoller.GitPoller, '_dovccmd', Mock())
    @patch.object(gitpoller.master, 'TOXICDB', Mock())
    def test_save_revconf(self):
        revision = 'asf3333'
        branch = 'master'
        config = '''steps:
        - sh ./something.sh'''
        gitpoller.GitPoller._dovccmd.return_value = config

        self.poller._save_revconf(revision, branch)

        expected_save = (revision, branch, self.poller.repourl, config)
        called_save = gitpoller.master.TOXICDB.revisionconfig.\
            saveRevisionConfig.call_args[0]

        self.assertEqual(expected_save, called_save)

    @patch.object(gitpoller.GitPoller, '_save_revconf', Mock())
    @patch.object(gitpoller.GitPollerBase, '_process_changes', Mock())
    @patch.object(gitpoller.GitPoller, 'revList', [1, 2])
    def test_process_changes(self):
        newRev = '0789guio0987'
        branch = 'master'
        self.poller._process_changes(newRev, branch)

        # 3 calls. One from last rev the the other from revList
        calls = len(gitpoller.GitPoller._save_revconf.call_args_list)
        self.assertEqual(calls, 3)

    @patch.object(gitpoller.GitPollerBase, 'poll', Mock())
    @patch.object(gitpoller.GitPoller, '_save_revconf', Mock())
    def test_poll(self):
        self.poller.lastRev = {'master': 'asf90'}
        self.poller.poll()

        self.assertTrue(self.poller._save_revconf.called)

    def test_get_revList(self):
        self.poller._revList = [1, 2, 3]
        self.assertEqual(self.poller.revList, [1, 2, 3])

    def test_set_revList(self):
        self.poller.revList = ['a', 'b', 'c']
        self.assertEqual(self.poller.revList, ['a', 'b', 'c'])
