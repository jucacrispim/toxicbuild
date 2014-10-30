# -*- coding: utf-8 -*-

import os
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
        stop_cmd = ['export', 'PYTHONPATH="."', '&&',
                    './script/toxicbuild', 'toxicstop', '%s' % cls.basedir]

        os.system(' '.join(stop_cmd))

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
        cls.toxic_builder_url = cls.toxic_url + '/builders/b1'

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
        new_brach_cmd = ['cd', '%s' % cls.fakeproject_dest, '&&', 'git',
                         'branch', 'dev']
        cmds = [init_cmd, add_cmd, commit_cmd, new_brach_cmd]
        for cmd in cmds:
            os.system(' '.join(cmd))

        # sym link to toxicbuild
        toxicbuild_path = os.path.abspath('toxicbuild/')
        toxicbuild_link_path = os.path.abspath(os.path.join(
            os.path.join(cls.basedir, 'pythonpath'), 'toxicbuild'))

        symlink_cmd = ['ln', '-s', toxicbuild_path, toxicbuild_link_path]
        os.system(' '.join(symlink_cmd))

    @classmethod
    def start(cls):
        start_cmd = [
            'export', 'PYTHONPATH="."', '&&',
            './script/toxicbuild', 'toxicstart', '%s' % cls.basedir]
        err = os.system(' '.join(start_cmd))
        if err:
            raise Exception('Error while starting toxicbuild')

    @classmethod
    def weblogin(cls):
        # login to web interface
        cls.wb = WebBrowser()
        cls.wb.urlopen(cls.toxic_url)

        login_form = cls.wb.current_page.forms['login']
        login_form.set_value('toxicbuild', 'username')
        login_form.set_value('toxicbuild', 'passwd')
        cls.wb.submit_form(login_form)

    def test_1_check_builders(self):
        time.sleep(2)
        # check if builders were created correctly
        self.wb.urlopen(self.toxic_url + '/builders')
        # checking the numbers of builders created
        table = self.wb.current_page.soup.findAll('table')[0]

        self.assertEqual(len(table.findAll('tr')), 2)

    def test_2_force_build(self):
        # forces a build
        self.wb.urlopen(self.toxic_builder_url)
        force_form = self.wb.current_page.forms['force_build']
        self.wb.submit_form(force_form)
        # getting build info
        time.sleep(2)
        url = self.toxic_url + '/builders/b1/builds/0'
        self.wb.urlopen(url)

        # getting the number of steps created
        steps = self.wb.current_page.soup.find('ol').find('li')

        self.assertEqual(len(steps), 5)

    def test_3_income_changes_with_not_config_ok_in_branch_dev(self):
        # must be create only one builder called 'Config Error!'
        cfile = os.path.join(self.fakeproject_dest, 'toxicbuild.conf')
        with open(cfile, 'r') as fd:
            content = fd.read()

        with open(cfile, 'w') as fd:
            content = content.replace('builders', '')
            fd.write(content)

        checkout_cmd = ['cd', '%s' % self.fakeproject_dest, '&&', 'git',
                        'checkout', 'dev']
        add_cmd = ['cd', '%s' % self.fakeproject_dest, '&&', 'git', 'add', '.']
        commit_cmd = ['cd', '%s' % self.fakeproject_dest,
                      '&&', 'git', 'commit', '-m"bla"']
        cmds = [checkout_cmd, add_cmd, commit_cmd]
        for cmd in cmds:
            os.system(' '.join(cmd))

        # here we need to wait to build have time to be shown
        # in the web.
        time.sleep(2)
        # getting build info
        url = self.toxic_url + '/builders/Config%20Error'
        self.wb.urlopen(url)
        self.assertTrue(self.wb.current_page)

    def test_4_remove_old_builders(self):
        # with new builders, builder 'b2' must be removed
        new_conf = """
SETTINGS = '--settings=setting_test'
builders = [{'name': 'b1',
             'branch': 'master',
             'steps': [{'name': 'list files',
                        'command': 'ls'},

                       {'name': 'grep',
                        'command': "grep -ir 'nada'"}]},

            {'name': 'b3',
             'branch': 'dev',
             'steps': [{'name': 's', 'command': 'cd'}]}]

"""
        cfile = os.path.join(self.fakeproject_dest, 'toxicbuild.conf')
        with open(cfile, 'w') as fd:
            fd.write(new_conf)

        add_cmd = ['cd', '%s' % self.fakeproject_dest, '&&', 'git', 'add', '.']
        commit_cmd = ['cd', '%s' % self.fakeproject_dest,
                      '&&', 'git', 'commit', '-m"bla"']
        cmds = [add_cmd, commit_cmd]
        for cmd in cmds:
            os.system(' '.join(cmd))

        # here we need to wait to build have time to be shown
        # in the web.
        time.sleep(2)
        # getting build info
        self.wb.urlopen(self.toxic_url + '/builders/b3')
        with self.assertRaises(Exception):
                    self.wb.urlopen(self.toxic_url + '/builders/b2')

    def test_5_custom_waterfall_template(self):
        self.wb.urlopen(self.toxic_url + '/waterfall')
        script = self.wb.current_page.soup.find('script')
        self.assertTrue(script)
