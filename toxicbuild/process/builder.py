# -*- coding: utf-8 -*-

import copy
from twisted.python import log
from buildbot.process.builder import Builder
from buildbot.schedulers.forcesched import ForceScheduler
from toxicbuild.config import DynamicBuilderConfig


def createBuildersFromConfig(master, config):

    builderNames = copy.copy(master.botmaster.builderNames)
    new_builders = [b['name'] for b in config.builders]
    for b in builderNames:
        if b in new_builders:
            continue

        log.msg('builder: removing builder %s' % b)
        master.status.builderRemoved(b)
        master.botmaster.builderNames.pop(
            master.botmaster.builderNames.index(b))
        builder = master.botmaster.builders[b]
        builder.disownServiceParent()
        del master.botmaster.builders[b]

    builders = {}
    for bdict in config.builders:
        if bdict['name'] in master.botmaster.builderNames:
            continue

        log.msg('builder: creating builder %s' % bdict['name'])

        builder = createBuilderFromDict(master, bdict)
        builders[bdict['name']] = builder
        setInForceScheduler(master, builder)

    builderNames = [b['name'] for b in config.builders]
    master.botmaster.builders.update(builders)
    master.botmaster.builderNames = master.botmaster.builders.keys()

    for s in master.config.slaves:
        s.updateSlave()

    return builderNames


def createBuilderFromDict(master, bdict):
    builder = Builder(bdict['name'])
    for key in ['steps', 'branch']:
        try:
            del bdict[key]
        except KeyError:
            pass

    if 'slavenames' not in bdict.keys():
        bdict['slavenames'] = [s.slavename for s in
                               master.config.slaves]

    bconf = DynamicBuilderConfig(**bdict)
    builder.config = bconf
    builder.master = master
    builder.botmaster = master.botmaster
    builder.builder_status = master.status.builderAdded(
        bconf.name,
        bconf.builddir,
        bconf.category,
        bconf.description)

    builder.setServiceParent(builder.botmaster)
    return builder


def setInForceScheduler(master, builder):
    """
    Sets the builder in all force schedulers configured
    in master
    """

    for sched in master.config.schedulers.values():
        if isinstance(sched, ForceScheduler):
            sched.builderNames.append(builder.name)
