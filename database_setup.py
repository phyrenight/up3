from sqlalchemy import Column, ForeignKey, Integer, String, ForeignKeyConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
import config



Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    email = Column(String(80), nullable=False)
    picture = Column(String(250))

class Game(Base):
    __tablename__ = 'Game'
    id = Column(Integer, primary_key=True)
    game_name = Column(String(80), nullable=True)
    console = Column(String(20), nullable=True)
    user_name = Column(String(80),nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'),nullable=False)
    description = Column(String(250))
    picture = Column(String(250))
    __table_args__ = (ForeignKeyConstraint([user_id],['user.id']), {})
    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id,
            'console': self.console,
            'user_name': self.user_name,
            'description': self.description,
            'picture': self.picture,
        }

engine = create_engine('postgresql://cata:cata@localhost:5432/cata')
#Base.metadata.create_all(engine)
