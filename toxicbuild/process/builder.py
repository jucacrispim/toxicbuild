# -*- coding: utf-8 -*-

import copy
from twisted.python import log
from buildbot.process.builder import Builder
from buildbot.schedulers.forcesched import ForceScheduler
from toxicbuild.config import DynamicBuilderConfig


class BuilderManager:
    def __init__(self, master, config, category=None):
        self.master = master
        self.config = config
        self.category = category

    def updateBuilders(self):
        """
        Creates new builders and remove old ones based on self.config
        """

        removed = self.removeOldBuilders()
        builders = self.createNewBuilders()
        self.updateSlaves()
        return builders, removed

    def createNewBuilders(self):

        builders = {}
        for bdict in self.config.builders:
            if bdict['name'] in self.master.botmaster.builderNames:
                continue

            log.msg('builder: creating builder %s' % bdict['name'])

            force = bdict.get('forceScheduler', True)
            builder = self.createBuilderFromDict(bdict)
            builders[bdict['name']] = builder
            if force:
                self.addToForceScheduler(builder)

        builderNames = [b['name'] for b in self.config.builders]
        self.master.botmaster.builders.update(builders)
        self.master.botmaster.builderNames = self.master.botmaster.\
            builders.keys()

        return builderNames

    def updateSlaves(self):
        for s in self.master.config.slaves:
            s.updateSlave()

    def removeOldBuilders(self):
        builderNames = copy.copy(self.master.botmaster.builderNames)
        new_builders = [b['name'] for b in self.config.builders]
        removed = []
        for b in builderNames:
            if b in new_builders:
                continue

            log.msg('builder: removing builder %s' % b)
            removed.append(b)
            self.master.status.builderRemoved(b)
            self.master.botmaster.builderNames.pop(
                self.master.botmaster.builderNames.index(b))
            builder = self.master.botmaster.builders[b]
            builder.disownServiceParent()
            del self.master.botmaster.builders[b]

        return removed

    def createBuilderFromDict(self, bdict):
        builder = Builder(bdict['name'])
        keys2delete = ['steps', 'branch', 'forceScheduler', 'candies']
        for key in keys2delete:
            try:
                del bdict[key]
            except KeyError:
                pass

        if 'slavenames' not in bdict.keys():
            bdict['slavenames'] = [s.slavename for s in
                                   self.master.config.slaves]

        bconf = DynamicBuilderConfig(**bdict)
        builder.config = bconf
        builder.master = self.master
        builder.botmaster = self.master.botmaster
        builder.builder_status = self.master.status.builderAdded(
            bconf.name,
            bconf.builddir,
            bconf.category,
            bconf.description)

        builder.setServiceParent(builder.botmaster)
        return builder

    def addToForceScheduler(self, builder):
        """
        Sets the builder in all force schedulers configured
        in master
        """

        for sched in self.master.config.schedulers.values():
            if isinstance(sched, ForceScheduler):
                sched.builderNames.append(builder.name)
