from sqlalchemy import (Table, Column, Integer, String, Text, TIMESTAMP,
                        MetaData)

meta = MetaData()

revision_config = Table(
    'revision_config', meta,
    Column('id', Integer, primary_key=True),
    Column('repourl', String(128)),
    Column('revision', String(128)),
    Column('branch', String(64)),
    Column('config', Text),
    Column('timestamp', TIMESTAMP),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta.bind = migrate_engine
    revision_config.create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    meta.bind = migrate_engine
    revision_config.drop()
