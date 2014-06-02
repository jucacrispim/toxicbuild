# -*- coding: utf-8 -*-

import sqlalchemy as sa
from buildbot.db import base


class Model(base.DBConnectorComponent):
    metadata = sa.MetaData()

    revisionconfig = sa.Table(
        'revision_config', metadata,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('repourl', sa.String(128)),
        sa.Column('revision', sa.String(128)),
        sa.Column('branch', sa.String(64)),
        sa.Column('config', sa.Text),
        sa.Column('timestamp', sa.TIMESTAMP),

        sa.UniqueConstraint('repourl', 'revision')
    )
