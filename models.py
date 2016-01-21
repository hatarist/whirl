import datetime

import tornado.options

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from tornado.options import define, options


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)

    username = Column(String(20), nullable=False, unique=True)
    password = Column(String(128), nullable=False)

    date_created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)

    messages = relationship("Message", back_populates="user")

    def __repr__(self):
        return "<User {}>".format(self.username)

    def __str__(self):
        return self.username


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="messages")
    p_type = Column(Integer, nullable=False, index=True)  # protocol.P_TYPE
    channel = Column(String(20), nullable=False, index=True)
    message = Column(String(2048), index=True)

    date_created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)

if __name__ == '__main__':
    # creates a database and schemas
    define("sqlalchemy_db", help="sqlalchemy database uri", type=str)
    tornado.options.parse_config_file('server.conf')
    # users_table = User.__table__
    # messages_table = Message.__table__
    engine = create_engine(options.sqlalchemy_db)
    Base.metadata.create_all(engine)
