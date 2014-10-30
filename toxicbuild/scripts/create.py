# -*- coding: utf-8 -*-

import os
import jinja2
from pkg_resources import resource_filename
from twisted.internet import defer
from twisted.python import util
from buildbot.util import in_reactor
from buildbot.scripts.create_master import (makeBasedir,
                                            makePublicHtml,
                                            makeTemplatesDir, createDB)
from buildslave.scripts.create_slave import createSlave
from migrate.versioning.api import version_control, test, upgrade
import toxicbuild


@in_reactor
@defer.inlineCallbacks
def create(config):
    create_basedir(config)
    master_config = _get_master_config(config)
    yield createMaster(master_config)
    yield createToxicbuildDB(master_config)

    slave_config = _get_slave_config(config)
    createSlave(slave_config)
    if not config['quiet']:
        print('master configured at %s' % master_config['basedir'])
        print('slave configured at %s' % slave_config['basedir'])
    defer.returnValue(0)


@defer.inlineCallbacks
def createToxicbuildDB(config):
    repository = resource_filename('toxicbuild', 'migrations')
    url = config['toxicbuild-db']
    if not config['quiet']:
        verbose_url = url.replace(config['basedir'], '')
        print('creating database for toxicbuild (%s)' % verbose_url)

    version_control(url, repository)
    test(url, repository)
    yield upgrade(url, repository)


def create_basedir(config):
    pythonpath = os.path.join(config['basedir'], 'pythonpath')
    if not config['quiet']:
        print('mkdir %s' % config['basedir'])
        print('mkdir %s' % pythonpath)

    os.mkdir(config['basedir'])
    os.mkdir(pythonpath)


@defer.inlineCallbacks
def createMaster(config):  # pragma: no cover
    # copy/paste from buildbot.
    makeBasedir(config)
    makeTAC(config)
    makeSampleConfig(config)
    makePublicHtml(config)
    makeTemplatesDir(config)
    copyCustomTemplates(config)
    yield createDB(config)


def copyCustomTemplates(config):  # pragma: no cover
    templates_dir = os.path.dirname(os.path.abspath(toxicbuild.__file__))
    templates_dir = os.path.join(templates_dir, 'status')
    templates_dir = os.path.join(templates_dir, 'web')
    templates_dir = os.path.join(templates_dir, 'templates')

    destdir = os.path.join(config['basedir'], 'templates')

    templates = ['waterfall.html']
    for template in templates:
        if not config['quiet']:
            print('%s > %s' % (template, destdir))
        with open(os.path.join(templates_dir, template), 'r') as f:
            content = f.read()

        with open(os.path.join(destdir, template), 'w') as f:
            f.write(content)


def makeSampleConfig(config):  # pragma: no cover
    # copy/paste from buildbot
    source = util.sibpath(__file__, "sample.cfg")
    target = os.path.join(config['basedir'], "master.cfg")
    if not config['quiet']:
        print "creating %s" % target
    with open(source, "rt") as f:
        config_sample = f.read()
    if config['db']:
        config_sample = config_sample.replace('sqlite:///state.sqlite',
                                              config['db'])
    with open(target, "wt") as f:
        f.write(config_sample)
    os.chmod(target, 0600)


def makeTAC(config):  # pragma: no cover
    # copy/paste from buildbot
    # render buildbot_tac.tmpl using the config
    loader = jinja2.FileSystemLoader(os.path.dirname(__file__))
    env = jinja2.Environment(loader=loader, undefined=jinja2.StrictUndefined)
    env.filters['repr'] = repr
    tpl = env.get_template('buildbot_tac.tmpl')
    cxt = dict((k.replace('-', '_'), v) for k, v in config.iteritems())
    contents = tpl.render(cxt)

    tacfile = os.path.join(config['basedir'], "buildbot.tac")
    if os.path.exists(tacfile):
        with open(tacfile, "rt") as f:
            oldcontents = f.read()
        if oldcontents == contents:
            if not config['quiet']:
                print "buildbot.tac already exists and is correct"
            return
        if not config['quiet']:
            print "not touching existing buildbot.tac"
            print "creating buildbot.tac.new instead"
        tacfile += ".new"
    with open(tacfile, "wt") as f:
        f.write(contents)


def _get_master_config(config):
    master_config = {}
    master_config['basedir'] = os.path.join(config['basedir'], 'master')
    master_config['quiet'] = config['quiet']
    master_config['force'] = False
    master_config['relocatable'] = True
    master_config['no-logrotate'] = False
    master_config['config'] = 'master.cfg'
    master_config['log-size'] = "10000000"
    master_config['log-count'] = "10"
    master_config['db'] = "sqlite:///state.sqlite"
    master_config['toxicbuild-db'] = _get_toxicbuild_db_url(
        config['toxicbuild-db'], master_config['basedir'])

    return master_config


def _get_slave_config(config):
    slave_config = {}
    slave_config['basedir'] = os.path.join(config['basedir'], 'slave')
    slave_config['quiet'] = False
    slave_config['force'] = False
    slave_config['relocatable'] = True
    slave_config['no-logrotate'] = False
    slave_config['log-size'] = 10000000
    slave_config['log-count'] = 10
    slave_config['umask'] = "None"
    slave_config['usepty'] = 0
    slave_config['keepalive'] = 600
    slave_config['maxdelay'] = 300
    slave_config['allow-shutdown'] = None
    slave_config['name'] = 'easyslave'
    slave_config['passwd'] = 'dummypass'
    slave_config['host'] = 'localhost'
    slave_config['port'] = 9989

    return slave_config


def _get_toxicbuild_db_url(toxicbuild_db, basedir):
    origurl = url = toxicbuild_db

    if origurl.startswith('sqlite'):
        path = origurl.split('sqlite:///')[1]
        if not path.startswith('/'):
            url = os.path.join(basedir, path)
            url = 'sqlite:///' + url

    return url
