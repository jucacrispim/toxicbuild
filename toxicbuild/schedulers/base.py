# -*- coding: utf-8 -*-

from twisted.internet import defer
from buildbot.schedulers.base import BaseScheduler
from toxicbuild.config import ConfigReader
from toxicbuild.process.builder import createBuildersFromConfig


# yeah, dirty and ugly. but works and i don't need to write it twice!
# propably I should replace it for a proper BuilderManager.
@defer.inlineCallbacks
def addBuildsetForChanges(instance, reason='', external_idstring=None,
                          changeids=[], builderNames=None, properties=None):
    builderNames = yield createBuildersForCodebases(instance, changeids)

    rev = yield BaseScheduler.addBuildsetForChanges(
        instance, reason, external_idstring, changeids, builderNames,
        properties)

    defer.returnValue(rev)


@defer.inlineCallbacks
def createBuildersForCodebases(instance, changeids):
    changesByCodebase = {}

    def get_last_change_for_codebase(codebase):
        return max(changesByCodebase[codebase],
                   key=lambda change: change["changeid"])

    for changeid in changeids:
        chdict = yield instance.master.db.changes.getChange(changeid)
        # group change by codebase
        changesByCodebase.setdefault(chdict["codebase"], []).append(chdict)

    builderNames = None
    for codebase in instance.codebases:
        if codebase in changesByCodebase:
            lastchageid = get_last_change_for_codebase(codebase)['changeid']
            builderNames = yield createBuildersForCodebase(instance,
                                                           lastchageid)

    defer.returnValue(builderNames)


@defer.inlineCallbacks
def createBuildersForCodebase(instance, lastchageid):

    lastChange = yield instance.master.db.changes.getChange(lastchageid)

    toxicdb = instance.master.toxicdb
    revconf = yield toxicdb.revisionconfig.getRevisionConfig(
        lastChange['branch'], lastChange['repository'],
        lastChange['revision'])

    config = ConfigReader(revconf.config)

    builderNames = createBuildersFromConfig(instance.master, config)
    defer.returnValue(builderNames)
