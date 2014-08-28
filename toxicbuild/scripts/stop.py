# -*- coding: utf-8 -*-

import os
import subprocess


def stop(config):
    slave_dir = os.path.join(config['basedir'], 'slave')
    master_dir = os.path.join(config['basedir'], 'master')
    master_cmd = ['buildbot', 'stop', master_dir]
    slave_cmd = ['buildslave', 'stop', slave_dir]
    errors = subprocess.call(master_cmd)
    if errors:
        return 1

    errors = subprocess.call(slave_cmd)
    if errors:
        return 1

    return 0
