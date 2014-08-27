# -*- coding: utf-8 -*-

import unittest
from pkg_resources import resource_filename
from mock import Mock, patch
from toxicbuild.scripts import create


class CreateTestCase(unittest.TestCase):
    def test_get_master_config(self):
        config = {'basedir': 'some/dir',
                  'quiet': False,
                  'toxicbuild-db': 'sqlite:///toxicbuild.db'}
        expected = {'basedir': 'some/dir/master',
                    'quiet': False,
                    'force': False,
                    'relocatable': True,
                    'no-logrotate': False,
                    'config': 'master.cfg',
                    'log-size': "10000000",
                    'log-count': "10",
                    'db': "sqlite:///state.sqlite",
                    'toxicbuild-db': 'sqlite:///some/dir/master/toxicbuild.db'}

        returned = create._get_master_config(config)

        self.assertEqual(expected, returned)

    def test_get_slave_config(self):
        config = {'basedir': 'some/dir',
                  'quiet': False,
                  'toxicbuild-db': 'sqlite:///toxicbuild.db'}
        expected = {'basedir': 'some/dir/slave',
                    'quiet': False,
                    'force': False,
                    'relocatable': True,
                    'no-logrotate': False,
                    'umask': 'None',
                    'log-size': 10000000,
                    'log-count': 10,
                    'keepalive': 600,
                    'maxdelay': 300,
                    'allow-shutdown': None,
                    'usepty': 0,
                    'name': 'easyslave',
                    'host': 'localhost',
                    'port': 9989,
                    'passwd': 'dummypass'}

        returned = create._get_slave_config(config)

        self.assertEqual(expected, returned)

    def test_get_toxicbuild_db_url(self):
        toxicbuild_db = 'sqlite:///toxicbuild.db'
        basedir = 'some/dir'
        expected = 'sqlite:///some/dir/toxicbuild.db'

        returned = create._get_toxicbuild_db_url(toxicbuild_db, basedir)

        self.assertEqual(expected, returned)

    def test_get_toxicbuild_db_url_with_absolute_path(self):
        toxicbuild_db = 'sqlite:////abs/path/toxicbuild.db'
        basedir = 'some/dir',
        expected = 'sqlite:////abs/path/toxicbuild.db'
        returned = create._get_toxicbuild_db_url(toxicbuild_db, basedir)

        self.assertEqual(expected, returned)

    def test_get_toxicbuild_db_url_with_no_sqlite_url(self):
        toxicbuild_db = 'mysql:///my@somewhere'
        basedir = 'some/dir',
        expected = 'mysql:///my@somewhere'
        returned = create._get_toxicbuild_db_url(toxicbuild_db, basedir)

        self.assertEqual(expected, returned)

    @patch.object(create, 'version_control', Mock())
    @patch.object(create, 'test', Mock())
    @patch.object(create, 'upgrade', Mock())
    def test_createToxicbuildDB(self):
        config = {'basedir': 'some/dir',
                  'toxicbuild-db': 'sqlite:///toxicbuild.db',
                  'quiet': False}
        repo = resource_filename('toxicbuild', 'migrations')
        url = 'sqlite:///toxicbuild.db'

        create.createToxicbuildDB(config)

        called = create.upgrade.call_args[0]
        expected = (url, repo)

        self.assertEqual(called, expected)

    @patch.object(create, 'createMaster', Mock())
    @patch.object(create, 'createSlave', Mock())
    @patch.object(create, 'createToxicbuildDB', Mock())
    @patch.object(create.os, 'mkdir', Mock())
    def test_create(self):
        config = {'basedir': 'some/dir',
                  'toxicbuild-db': 'sqlite:///toxicbuild.db',
                  'quiet': False}

        create.create(config)

        everything_was_called = (create.createMaster.called and
                                 create.createToxicbuildDB.called and
                                 create.createSlave.called)

        self.assertTrue(everything_was_called)
