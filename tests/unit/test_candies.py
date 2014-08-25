# -*- coding: utf-8 -*-

import os
import unittest
from toxicbuild import candies


class CandyTest(unittest.TestCase):
    def test_getSteps(self):
        c = candies.Candy()
        with self.assertRaises(NotImplementedError):
            c.getSteps()

    def test_getEnv(self):
        c = candies.Candy()
        with self.assertRaises(NotImplementedError):
            c.getEnv()

    def test_getCandies(self):
        docinhos = candies.Candy.getCandies()
        self.assertEqual(len(docinhos), 2)

    def test_getCandy(self):
        name = 'python-virtualenv'
        candy = candies.Candy.getCandy(name)

        self.assertTrue(candy)

    def test_getCandy_with_candy_not_found(self):
        name = 'bla'
        with self.assertRaises(candies.CandyNotFound):
            candies.Candy.getCandy(name)


class PythonVirtualenvTest(unittest.TestCase):
    def setUp(self):
        self.pyversion = '/usr/bin/python3.4'
        self.venv_path = 'py34env'
        self.candy = candies.PythonVirtualenv(venv_path=self.venv_path,
                                              pyversion=self.pyversion)

    def test_getSteps(self):
        steps = self.candy.getSteps()

        self.assertEqual(len(steps), 2)

    def test_getEnv(self):
        bin_dir = os.path.join(self.venv_path, 'bin')
        expected = {'PATH': [bin_dir, '${PATH}']}
        returned = self.candy.getEnv()

        self.assertEqual(returned, expected)

    def test_constructor_without_mandatory_args(self):
        with self.assertRaises(Exception):
            candies.PythonVirtualenv()


class GitUpdateAndCheckoutTest(unittest.TestCase):

    def setUp(self):
        self.named_tree = 'master'
        self.repourl = 'git@somewhere.com'
        self.candy = candies.GitUpdateAndCheckout(repourl=self.repourl,
                                                  named_tree=self.named_tree)

    def test_getSteps(self):
        steps = self.candy.getSteps()

        self.assertEqual(len(steps), 2)

    def test_constructor_without_mandatory_args(self):
        with self.assertRaises(Exception):
            candies.GitUpdateAndCheckout()
