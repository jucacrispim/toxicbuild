# -*- coding: utf-8 -*-

from datetime import datetime
from twisted.internet import defer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine


Base = declarative_base()
Session = sessionmaker()
engine = create_engine('sqlite:///toxicbuild.sqlite')
Session.configure(bind=engine)
session = Session()


class RevisionConfig(Base):
    __tablename__ = 'revision_config'

    id = Column(Integer, primary_key=True)
    repourl = Column(String(128))
    revision = Column(String(128))
    branch = Column(String(64))
    config = Column(Text)
    # it was supposed to be an timestamp. it's not anymore
    # but the name last. :P
    timestamp = Column(DateTime)

    @classmethod
    @defer.inlineCallbacks
    def save_revconf(cls, revision, branch, repourl, config):
        if session.query(cls).filter(
                cls.revision == revision,
                cls.branch == branch,
                cls.repourl == repourl).all():
            return

        revconf = RevisionConfig()
        revconf.repourl = repourl
        revconf.revision = revision
        revconf.config = config
        revconf.branch = branch
        revconf.timestamp = datetime.now()
        session.add(revconf)
        yield session.commit()

    @classmethod
    def get_revconf(cls, branch, repourl=None, revision=None):
        queryset = session.query(cls)
        query_args = [cls.branch == branch]
        if repourl:
            query_args.append(cls.repourl == repourl)

        revconf = None
        if revision:
            query_args.append(cls.revision == revision)
            revconf = queryset.filter(*query_args)[0]
        else:
            # the last one
            revconf = queryset.filter(*query_args).all()[-1]

        return revconf
