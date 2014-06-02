# -*- coding: utf-8 -*-

from buildbot.test.fake import fakemaster
from buildbot.test.util.connector_component import FakeDBConnector
from toxicbuild.db import model
from tests.util import db

# another copy/paste from buildbot, now only changing RealDatabaseMixin
# to use the monkey patched one.


class ConnectorComponentMixin(db.RealDatabaseMixin):
    """
    Implements a mock DBConnector object, replete with a thread pool and a DB
    model.  This includes a RealDatabaseMixin, so subclasses should not
    instantiate that class directly.  The connector appears at C{self.db}, and
    the component should be attached to it as an attribute.

    @ivar db: fake database connector
    @ivar db.pool: DB thread pool
    @ivar db.model: DB model
    """
    def setUpConnectorComponent(self, table_names=[], basedir='basedir'):
        """Set up C{self.db}, using the given db_url and basedir."""
        d = self.setUpRealDatabase(table_names=table_names, basedir=basedir)

        def finish_setup(_):
            self.db = FakeDBConnector()
            self.db.pool = self.db_pool
            self.db.model = model.Model(self.db)
            self.db.master = fakemaster.make_master()
        d.addCallback(finish_setup)
        return d

    def tearDownConnectorComponent(self):
        d = self.tearDownRealDatabase()

        def finish_cleanup(_):
            self.db_pool.shutdown()
            # break some reference loops, just for fun
            del self.db.pool
            del self.db.model
            del self.db
        d.addCallback(finish_cleanup)
        return d
