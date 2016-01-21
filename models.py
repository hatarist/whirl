import datetime

import tornado.options

from sqlalchemy import Column, Integer, String, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base

from tornado.options import define, options


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)

    username = Column(String(20), nullable=False, unique=True)
    password = Column(String(128), nullable=False)

    date_created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)

    def __repr__(self):
        return "<User {}>".format(self.username)

    def __str__(self):
        return self.username


if __name__ == '__main__':
    # creates a database and schemas
    define("sqlalchemy_db", help="sqlalchemy database uri", type=str)
    tornado.options.parse_config_file('server.conf')
    users_table = User.__table__
    engine = create_engine(options.sqlalchemy_db)
    Base.metadata.create_all(engine)
