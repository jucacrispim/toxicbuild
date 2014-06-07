# -*- coding: utf-8 -*-

from buildbot.db import base


class RevisionConfigConnectorComponent(base.DBConnectorComponent):

    def saveRevisionConfig(self, revision, branch, repourl, config):
        def thd(conn):
            return self._saveRevisionConfig(
                conn, revision, branch, repourl, config)

        return self.db.pool.do(thd)

    def _saveRevisionConfig(self, conn, revision, branch, repourl, config):
        # yeah, this method is silly, but there's a reason.
        # somethimes I really need to block the whole thing
        r = conn.execute(self.db.model.revisionconfig.insert(),
                         dict(revision=revision, branch=branch,
                              repourl=repourl, config=config))

        return r.inserted_primary_key[0]

    def getRevisionConfig(self, branch, repourl=None, revision=None):
        def thd(conn):
            return self._getRevisionConfig(conn, branch, repourl, revision)

        return self.db.pool.do(thd)

    def _getRevisionConfig(self, conn, branch, repourl=None, revision=None):
        # the silly thing again
        tbl = self.db.model.revisionconfig
        query = tbl.select(whereclause=(tbl.c.branch == branch))
        if repourl:
            query = query.where(tbl.c.repourl == repourl)

        if revision:
            query = query.where(tbl.c.revision == revision)
        else:
            query = query.order_by('-id')

        r = conn.execute(query)
        return r.fetchone()
