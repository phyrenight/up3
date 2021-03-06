from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Game, Consoles
import datetime

engine = create_engine('sqlite:///gameswap.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

#Add users
user1 = User(name='Ted', email='ted@gmail.com')
session.add(user1)

user2 = User(name='ed', email='ed@gmail.com')
session.add(user2)

user3 = User(name='Paul', email='paul@gmail.com')
session.add(user3)

user4 = User(name='Tiff', email='tiff@gmail.com')
session.add(user4)


#add console

console1 = Consoles(name='Ps4')
session.add(console1)

console2 = Consoles(name='Xbox one')
session.add(console2)

console3 = Consoles(name='Wii')
session.add(console3)

console4 = Consoles(name='Xbox 360')
session.add(console4)

# add Game

game1 = Game(name='Tetris', console="Ps4",  user_name='Marc Preston')
session.add(game1)

game2 = Game(name='Gears of War 3', console='Xbox 360', description='none', user_name='Marc Preston')
session.add(game2)

game3 = Game(name='Undead Island', console='Xbox 360', description='Zombies on an island', user_name='Sam')
session.add(game3)

game4 = Game(name='Uncharted 4', console='Ps4', description='sequal to part 3', user_name='Marc Preston')
session.add(game4)

game5 = Game(name='Metroid', console='Wii', description="Samus on another adventure", user_name='Sam')
session.add(game5)

game6 = Game(name='Crazy Taxi', console='Ps4', description="Crazy mayhem dropping off passengers", user_name='Sam')
session.add(game6)

session.commit()