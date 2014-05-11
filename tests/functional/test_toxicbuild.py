# -*- coding: utf-8 -*-

import os
import json
import time
import unittest
import shutil
import subprocess
from webrunner import WebBrowser


class ToxicBuildTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.basedir = os.path.abspath('../toxic-test')

        cls.master_cfg_file = os.path.join(os.path.join(cls.basedir, 'master'),
                                           'master.cfg')
        cls.slave_cfg_file = os.path.join(os.path.join(cls.basedir, 'slave'),
                                          'buildbot.tac')
        cls.sampleconfig = os.path.join(
            os.path.abspath(os.path.dirname((__file__))), 'sample.cfg')

        cls.slaveconfig = os.path.join(
            os.path.abspath(os.path.dirname((__file__))), 'buildbot.tac.slave')

        cls.master_path = os.path.join(cls.basedir, 'master')
        cls.slave_path = os.path.join(cls.basedir, 'slave')

        cls.toxic_url = 'http://localhost:8020'
        cls.toxic_builder_url = cls.toxic_url + '/builders/dynamic-builder'

        cls.fakeproject = os.path.join(
            os.path.abspath(os.path.dirname((__file__))), 'fakeproject')
        cls.fakeproject_dest = os.path.join(cls.master_path, 'fakeproject')

    @classmethod
    def tearDownClass(cls):
        stop_master_cmd = ['buildbot', 'stop', '%s' % cls.master_path]
        stop_slave_cmd = ['buildslave', 'stop', '%s' % cls.slave_path]

        subprocess.call(stop_master_cmd)
        subprocess.call(stop_slave_cmd)

        try:
            subprocess.call(['rm', '-rf', '%s' % cls.basedir])
        except OSError:
            pass

    def test_1_create_new_project(self):
        # creating a new project
        create_project_cmd = [
            'export PYTHONPATH="." && ./script/toxicbuild create %s '
            % self.basedir]
        msg = ''
        success = not subprocess.call(create_project_cmd, shell=True)

        # copying master sample config for tests
        try:
            shutil.copyfile(self.sampleconfig, self.master_cfg_file)
        except shutil.Error:
            success = False
            msg += 'error on copyfile\n'

        # copying slave sample config for tests
        try:
            shutil.copyfile(self.slaveconfig, self.slave_cfg_file)
        except shutil.Error:
            success = False
            msg += 'error on copyfile\n'

        # creating test project
        try:
            shutil.copytree(self.fakeproject, self.fakeproject_dest)
        except shutil.Error:
            success = False
            msg += 'error copying fakeproject'

        init_cmd = ['cd', '%s' % self.fakeproject_dest, '&&', 'git', 'init']
        add_cmd = ['cd', '%s' % self.fakeproject_dest, '&&', 'git', 'add', '.']
        commit_cmd = ['cd', '%s' % self.fakeproject_dest, '&&',
                      'git', 'commit', '-m"test"']
        cmds = [init_cmd, add_cmd, commit_cmd]
        for cmd in cmds:
            error = os.system(' '.join(cmd))
            if error:
                success = False

        # sym link to toxicbuild
        toxicbuild_path = os.path.abspath('toxicbuild/')
        toxicbuild_link_path = os.path.abspath(os.path.join(
            os.path.join(self.basedir, 'pythonpath'), 'toxicbuild'))

        symlink_cmd = ['ln', '-s', toxicbuild_path, toxicbuild_link_path]
        success = subprocess.call(symlink_cmd) or success

        self.assertTrue(success)

    def test_2_start_toxicbuild(self):
        start_master_cmd = ['buildbot', 'start', '%s' % self.master_path]
        start_slave_cmd = ['buildslave', 'start', '%s' % self.slave_path]

        master_success = not subprocess.call(start_master_cmd)
        slave_success = not subprocess.call(start_slave_cmd)

        self.assertTrue(master_success and slave_success)

    def test_3_force_build(self):
        wb = WebBrowser()
        wb.urlopen(self.toxic_builder_url)

        # only authenticated users can force builds
        login_form = wb.current_page.forms['login']
        login_form.set_value('toxicbuild', 'username')
        login_form.set_value('toxicbuild', 'passwd')
        wb.submit_form(login_form)

        # forcing a build
        wb.urlopen(self.toxic_builder_url)
        force_form = wb.current_page.forms['force_build']
        wb.submit_form(force_form)
        # here we need to wait to build have time to be shown
        # in the web.
        time.sleep(1)
        # getting build info
        url = 'http://localhost:8020/json/builders/dynamic-builder/builds/0'
        wb.urlopen(url)

        # odd json sent by buildbot json api
        response = str(wb.current_page.soup).replace('</toxicbuild>', '')

        json_response = json.loads(response)

        self.assertEqual(len(json_response['steps']), 5)
        # asserting steps order
        self.assertEqual(json_response['steps'][-1]['name'], 'grep')
