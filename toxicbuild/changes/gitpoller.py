# -*- coding: utf-8 -*-
from twisted.internet import defer
from buildbot.changes.gitpoller import GitPoller as GitPollerBase
from toxicbuild import master
from toxicbuild.config import ConfigReader
from toxicbuild.process.builder import BuilderManager

STEPS_FILE = 'toxicbuild.conf'
# :/
WRONG_CONFIG_TOKEN = 'BADCONF'


class GitPoller(GitPollerBase):
    def __init__(self, *args, **kwargs):
        GitPollerBase.__init__(self, *args, **kwargs)
        self.revList = []

    @defer.inlineCallbacks
    def poll(self):
        yield GitPollerBase.poll(self)
        for branch, rev in self.lastRev.items():
            conf = yield self._save_revconf(rev, branch)
            config = ConfigReader(conf)
            manager = BuilderManager(self.master, config)
            manager.updateBuilders()

    @defer.inlineCallbacks
    def _process_changes(self, newRev, branch):
        lastRev = self.lastRev.get(branch)
        yield self._make_revList(lastRev, newRev)
        for rev in self.revList:
            yield self._save_revconf(rev, branch)

        yield GitPollerBase._process_changes(self, newRev, branch)

    def _set_revList(self, revList):
        self._revList = revList

    def _get_revList(self):
        return self._revList

    revList = property(_get_revList, _set_revList)

    @defer.inlineCallbacks
    def _make_revList(self, lastRev, newRev):  # pragma: no cover
        # copy/paste from buildbot
        if lastRev:
            revListArgs = [r'--format=%H', '%s..%s' % (lastRev, newRev), '--']
            results = yield self._dovccmd('log', revListArgs,
                                          path=self.workdir)
            # process oldest change first
            self.revList = results.split()
            self.revList.reverse()
        yield self.revList

    @defer.inlineCallbacks
    def _save_revconf(self, revision, branch):

        try:
            conf = yield self._dovccmd('show',
                                       ['%s:%s' % (revision, STEPS_FILE)],
                                       path=self.workdir)
        except:
            conf = WRONG_CONFIG_TOKEN

        master.TOXICDB.revisionconfig.saveRevisionConfig(revision, branch,
                                                         self.repourl, conf)
        defer.returnValue(conf)
