# -*- coding: utf-8 -*-

from sqlalchemy.schema import MetaData
from twisted.python import log
from buildbot.test.util.db import RealDatabaseMixin
from toxicbuild.db import model


# copy/paste from buildbot, only changing model

class RealDatabaseMixin(RealDatabaseMixin):
    """
    A class that sets up a real database for testing.  This sets self.db_url to
    the URL for the database.  By default, it specifies an in-memory SQLite
    database, but if the BUILDBOT_TEST_DB_URL environment variable is set, it
    will use the specified database, being careful to clean out *all* tables in
    the database before and after the tests are run - so each test starts with
    a clean database.

    @ivar db_pool: a (real) DBThreadPool instance that can be used as desired

    @ivar db_url: the DB URL used to run these tests

    @ivar db_engine: the engine created for the test database
    """

    # Note that this class uses the production database model.  A
    # re-implementation would be virtually identical and just require extra
    # work to keep synchronized.

    # Similarly, this class uses the production DB thread pool.  This achieves
    # a few things:
    #  - affords more thorough tests for the pool
    #  - avoids repetitive implementation
    #  - cooperates better at runtime with thread-sensitive DBAPI's


    def __thd_clean_database(self, conn):
        # drop the known tables, although sometimes this misses dependencies
        try:
            model.Model.metadata.drop_all(bind=conn, checkfirst=True)
        except sa.exc.ProgrammingError:
            pass

        # see if we can find any other tables to drop
        meta = MetaData(bind=conn)
        meta.reflect()
        meta.drop_all()

    def __thd_create_tables(self, conn, table_names):
        all_table_names = set(table_names)
        ordered_tables = [ t for t in model.Model.metadata.sorted_tables
                        if t.name in all_table_names ]

        for tbl in ordered_tables:
            tbl.create(bind=conn, checkfirst=True)

    def insertTestData(self, rows):
        """Insert test data into the database for use during the test.

        @param rows: be a sequence of L{fakedb.Row} instances.  These will be
        sorted by table dependencies, so order does not matter.

        @returns: Deferred
        """
        # sort the tables by dependency
        all_table_names = set([ row.table for row in rows ])
        ordered_tables = [ t for t in model.Model.metadata.sorted_tables
                           if t.name in all_table_names ]
        def thd(conn):
            # insert into tables -- in order
            for tbl in ordered_tables:
                for row in [ r for r in rows if r.table == tbl.name ]:
                    tbl = model.Model.metadata.tables[row.table]
                    try:
                        tbl.insert(bind=conn).execute(row.values)
                    except:
                        log.msg("while inserting %s - %s" % (row, row.values))
                        raise
        return self.db_pool.do(thd)
