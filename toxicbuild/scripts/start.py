# -*- coding: utf-8 -*-

import os
import subprocess


def start(config):
    slave_dir = os.path.join(config['basedir'], 'slave')
    master_dir = os.path.join(config['basedir'], 'master')
    master_cmd = ['buildbot', 'start', master_dir]
    slave_cmd = ['buildslave', 'start', slave_dir]
    errors = subprocess.call(master_cmd)
    if errors:
        return 1

    errors = subprocess.call(slave_cmd)
    if errors:
        return 1

    return 0
