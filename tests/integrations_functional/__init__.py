# -*- coding: utf-8 -*-

import os
import sys
from tests.functional import (start_all as start_all_base,
                              stop_all as stop_all_base)
from tests.webui.environment import start_webui, stop_webui
from toxicbuild.integrations import create_settings

PYVERSION = ''.join([str(n) for n in sys.version_info[:2]])
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
SOURCE_DIR = os.path.join(DATA_DIR, '..', '..', '..')
SCRIPTS_DIR = os.path.join(SOURCE_DIR, 'scripts')
INTEGRATIONS_ROOT_DIR = os.path.join(DATA_DIR, 'integrations')

toxicintegrations_conf = os.environ.get('TOXICINTEGRATIONS_SETTINGS')
if not toxicintegrations_conf:
    toxicintegrations_conf = os.path.join(INTEGRATIONS_ROOT_DIR,
                                          'toxicintegrations.conf')
    os.environ['TOXICINTEGRATIONS_SETTINGS'] = toxicintegrations_conf


create_settings()


def start_integrations():
    toxicintegrations_conf = os.environ.get('TOXICINTEGRATIONS_SETTINGS')
    pidfile = 'toxicintegrations{}.pid'.format(PYVERSION)
    toxicintegrations_cmd = os.path.join(SCRIPTS_DIR, 'toxicintegrations')
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&', 'python',
           toxicintegrations_cmd, 'start', INTEGRATIONS_ROOT_DIR,
           '--daemonize', '--pidfile', pidfile, '--loglevel', 'debug']

    if toxicintegrations_conf:
        cmd += ['-c', toxicintegrations_conf]

    os.system(' '.join(cmd))


def stop_integrations():

    toxicintegrations_cmd = os.path.join(SCRIPTS_DIR, 'toxicintegrations')
    pidfile = 'toxicintegrations{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           'python', toxicintegrations_cmd, 'stop', INTEGRATIONS_ROOT_DIR,
           '--pidfile', pidfile]

    os.system(' '.join(cmd))


def start_all():
    start_all_base()
    start_webui()
    start_integrations()


def stop_all():
    stop_all_base()
    stop_webui()
    stop_integrations()
