# -*- coding: utf-8 -*-

from twisted.python import log
from buildbot.process.builder import Builder
from buildbot.schedulers.forcesched import ForceScheduler
from toxicbuild.config import DynamicBuilderConfig


def createBuildersFromConfig(master, config):

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
    try:
        del bdict['steps']
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
