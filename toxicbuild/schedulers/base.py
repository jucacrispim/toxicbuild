# -*- coding: utf-8 -*-

from twisted.internet import defer
from buildbot.schedulers.base import BaseScheduler
from toxicbuild.config import ConfigReader


# yeah, dirty and ugly. but works and i don't need to write it twice!
# propably I should replace it for a proper BuilderManager.
@defer.inlineCallbacks
def addBuildsetForChanges(instance, reason='', external_idstring=None,
                          changeids=[], builderNames=None, properties=None):
    builders = yield getBuildersForChanges(instance, changeids)
    builderNames = [b['name'] for b in builders]

    rev = yield BaseScheduler.addBuildsetForChanges(
        instance, reason, external_idstring, changeids, builderNames,
        properties)

    defer.returnValue(rev)


@defer.inlineCallbacks
def getBuildersForChanges(instance, changeids):
    lastChange = yield getLastChange(instance, changeids)
    revconf = yield instance.master.toxicdb.revisionconfig.getRevisionConfig(
        lastChange['branch'], lastChange['repository'],
        lastChange['revision'])

    config = ConfigReader(revconf.config)
    builders = config.getBuildersForBranch(lastChange['branch'])
    defer.returnValue(builders)


@defer.inlineCallbacks
def getLastChange(instance, changeids):
    changesByCodebase = {}

    def get_last_change_for_codebase(codebase):
        return max(changesByCodebase[codebase],
                   key=lambda change: change["changeid"])

    for changeid in changeids:
        chdict = yield instance.master.db.changes.getChange(changeid)
        # group change by codebase
        changesByCodebase.setdefault(chdict["codebase"], []).append(chdict)

    lastchangeid = None
    for codebase in instance.codebases:
        if codebase in changesByCodebase:
            lastchangeid = get_last_change_for_codebase(codebase)['changeid']

    lastChange = yield instance.master.db.changes.getChange(lastchangeid)
    defer.returnValue(lastChange)
