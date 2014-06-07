# -*- coding: utf-8 -*-

from buildbot.schedulers.basic import (SingleBranchScheduler,
                                       AnyBranchScheduler)
from toxicbuild.schedulers.base import addBuildsetForChanges


class ToxicSingleBranchScheduler(SingleBranchScheduler):
    addBuildsetForChanges = addBuildsetForChanges


class ToxicAnyBranchScheduler(AnyBranchScheduler):
    addBuildsetForChanges = addBuildsetForChanges
