# -*- coding: utf-8 -*-
from twisted.internet import defer
from buildbot.changes.gitpoller import GitPoller as GitPollerBase
from toxicbuild.db.models import RevisionConfig

STEPS_FILE = 'toxicbuild.conf'


class GitPoller(GitPollerBase):
    def __init__(self, *args, **kwargs):
        GitPollerBase.__init__(self, *args, **kwargs)
        self.revList = []
        self.poll()

    @defer.inlineCallbacks
    def poll(self):
        # I need to do it here 'cause if I don't,
        # firt build will break.
        yield GitPollerBase.poll(self)
        for branch, rev in self.lastRev.items():
            yield self._save_revconf(rev, branch)

    @defer.inlineCallbacks
    def _process_changes(self, newRev, branch):
        yield self._save_revconf(newRev, branch)
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
        conf = yield self._dovccmd('show', ['%s:%s' % (revision, STEPS_FILE)],
                                   path=self.workdir)

        RevisionConfig.save_revconf(revision, branch, self.repourl, conf)
