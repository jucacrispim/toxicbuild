# -*- coding: utf-8 -*-

from buildbot.test.fake import fakedb

class RevisionConfig(fakedb.Row):
    table = "revision_config"

    defaults = dict(
        id = None,
        repourl = None,
        revision = None,
        branch = None,
        config = None,
        timestamp = None,
    )

    id_column = 'id'
    required_columns = ('repourl', 'revision', 'config')
