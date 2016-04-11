from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__ = 'User'
    id = Column(Integer, primary_key = True)
    name = Column(String(80), nullable = False)
    email = Column(String(80), nullable = False)
    picture = Column(String(250))


class Game(Base):
    __tablename__ = 'Game'
    name = Column(String(80), nullable = True)
    id = Column(Integer, primary_key = True)
    console = Column(String(20), nullable = True)
    user_id = Column(Integer, ForeignKey('User.id'))
    description = Column(String(250))
    picture = Column(String(250))
    user = relationship(User)

class Consoles(Base):
    __tablename__ = 'Consoles'
    name = Column(String(80), primary_key = True)

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id,
            'console': self.console,
            'user_id': self.user_id,
            'description': self.description,
            'picture': self.picture,
        }

engine = create_engine('sqlite:///gameswap.db')
Base.metadata.create_all(engine)
