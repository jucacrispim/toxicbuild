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
        cls.setClassAttrs()
        cls.create()
        cls.start()
        cls.weblogin()

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

    @classmethod
    def setClassAttrs(cls):
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
    def create(cls):
        # creating a new project
        create_project_cmd = [
            'export PYTHONPATH="." && ./script/toxicbuild create %s '
            % cls.basedir]

        subprocess.call(create_project_cmd, shell=True)
        # copying master sample config for tests
        shutil.copyfile(cls.sampleconfig, cls.master_cfg_file)

        # copying slave sample config for tests
        shutil.copyfile(cls.slaveconfig, cls.slave_cfg_file)

        # creating test project
        shutil.copytree(cls.fakeproject, cls.fakeproject_dest)

        init_cmd = ['cd', '%s' % cls.fakeproject_dest, '&&', 'git', 'init']
        add_cmd = ['cd', '%s' % cls.fakeproject_dest, '&&', 'git', 'add', '.']
        commit_cmd = ['cd', '%s' % cls.fakeproject_dest, '&&',
                      'git', 'commit', '-m"test"']
        cmds = [init_cmd, add_cmd, commit_cmd]
        for cmd in cmds:
            os.system(' '.join(cmd))

        # sym link to toxicbuild
        toxicbuild_path = os.path.abspath('toxicbuild/')
        toxicbuild_link_path = os.path.abspath(os.path.join(
            os.path.join(cls.basedir, 'pythonpath'), 'toxicbuild'))

        symlink_cmd = ['ln', '-s', toxicbuild_path, toxicbuild_link_path]
        subprocess.call(symlink_cmd)

    @classmethod
    def start(cls):
        start_master_cmd = ['buildbot', 'start', '%s' % cls.master_path]
        start_slave_cmd = ['buildslave', 'start', '%s' % cls.slave_path]

        subprocess.call(start_master_cmd)
        subprocess.call(start_slave_cmd)

    @classmethod
    def weblogin(cls):
        # login to web interface
        cls.wb = WebBrowser()
        cls.wb.urlopen(cls.toxic_builder_url)

        login_form = cls.wb.current_page.forms['login']
        login_form.set_value('toxicbuild', 'username')
        login_form.set_value('toxicbuild', 'passwd')
        cls.wb.submit_form(login_form)
        cls.wb.urlopen(cls.toxic_builder_url)
        force_form = cls.wb.current_page.forms['force_build']

    def test_1_force_build(self):

        # forcing a build
        self.wb.urlopen(self.toxic_builder_url)
        force_form = self.wb.current_page.forms['force_build']
        self.wb.submit_form(force_form)
        # here we need to wait to build have time to be shown
        # in the web.
        time.sleep(1)
        # getting build info
        url = 'http://localhost:8020/json/builders/dynamic-builder/builds/0'
        self.wb.urlopen(url)

        response = str(self.wb.current_page._web_doc)

        json_response = json.loads(response)

        self.assertEqual(len(json_response['steps']), 5)
        # asserting steps order
        self.assertEqual(json_response['steps'][-1]['name'], 'grep')

    def test_2_income_changes_with_not_config_ok(self):
        # build must be marked as Exception
        # broken config file
        cfile = os.path.join(self.fakeproject_dest, 'toxicbuild.conf')
        with open(cfile, 'r') as fd:
            content = fd.read()

        with open(cfile, 'w') as fd:
            content = content.replace('steps', '')
            fd.write(content)

        add_cmd = ['cd', '%s' % self.fakeproject_dest, '&&', 'git', 'add', '.']
        commit_cmd = ['cd', '%s' % self.fakeproject_dest, '&&', 'git', 'commit',
                      '-m"bla"']
        cmds = [add_cmd, commit_cmd]
        for cmd in cmds:
            os.system(' '.join(cmd))

        # here we need to wait to build have time to be shown
        # in the web.
        time.sleep(3)
        # getting build info
        url = 'http://localhost:8020/json/builders/dynamic-builder/builds/1'
        self.wb.urlopen(url)

        response = str(self.wb.current_page._web_doc)

        json_response = json.loads(response)

        self.assertEqual(len(json_response['steps']), 1)
        # asserting steps order
        self.assertEqual(json_response['steps'][-1]['name'], 'bomb!')
