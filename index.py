from flask import Flask, flash, request, jsonify
import random
import string
from flask import session as login_session
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response, url_for, redirect, render_template
import requests
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import User, Game, Base, engine
from sqlalchemy.engine.url import URL
from config import SQLALCHEMY_DATABASE_URI

app = Flask(__name__)
app.config.from_object('config')

#engine = create_engine('sqlite:///gameswap.db')
#engine = create_engine('postgresql://catalog:catalog@localhost:5432/catalog')#SQLALCHEMY_DATABASE_URI)
Base.metadata.bind = engine
DB = sessionmaker(bind=engine)
session = DB()

CLIENT_ID = json.loads(
    open('client_secret.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Game Swap"


@app.route('/login')
def loginPage():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    """
        facebook OAuth
    """
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dump('Invalid state parameter'),401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data

    app_id = json.loads(open('fb_secrets.json', 'r').read())["web"]["app_id"]
    print app_id
    app_secret = json.loads(open('fb_secrets.json', 'r').read())['web']['app_secret']
    print app_secret 
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' %(app_id, app_secret, access_token)
    ht = httplib2.Http()
    print url
    result = ht.request(url, 'GET')[1]
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' %token
    ht = httplib2.Http()
    result = ht.request(url, 'GET')[1]


    data = json.loads(result)

    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    storeToken =  token.split("=")[1]
    login_session['access_token'] = storeToken

    url = 'https://graph.facebook.com/v2.2/me/picture?%s&redirect=0&width=200&height=200' % token
    ht = httplib2.Http()
    result = ht.request(url, 'GET')[1]
    print result
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    user_id  = getUserId(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']

    flash("Now logged in as {}".format(login_session['username']))
    return output


@app.route('/fbdisconnect')
def fbdiscon():
    """
       disconnect for facebook
    """
    facebook_id = login_session['facebook_id']
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' %(facebook_id, access_token)
    ht = httplib2.Http()
    result = ht.request(url, 'DELETE')[1]
    return "You are now logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    """
        OAuth for google
    """
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data

    try:
        oauthFlow = flow_from_clientsecrets('client_secret.json', scope='')
        oauthFlow.redirect_uri = 'postmessage'
        creds = oauthFlow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
        	json.dumps('Failed authorization upgrade.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = creds.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'  % access_token)
    ht = httplib2.Http()
    result = requests.get(url).json()
    #result = json.loads(ht.request(url, 'GET')[1])
    print result
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 501)
        response.headers['Content-Type'] = 'application/json'

    gplus_id = creds.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
        	json.dumps("Token id does not match user's token."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    if result['issued_to'] != CLIENT_ID:
        response = make_response(
           json.dumps("Token client id does not match app's id"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('You are connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    # to get gconnect to work on server add .access_token to the end of creds
    login_session['credentials'] = creds
    login_session['gplus_id'] = gplus_id

    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': creds.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    user_id = getUserId(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    
    flash("You are now logged in as {}".format(login_session['username']))

    return redirect('welcome')


def createUser(login_session):
    """
       Adds the user and user info to the database.
    """
    newUser = User(name = login_session['username'], email = login_session['email'],
    	           picture = login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id
""" delete after testing
def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user.id).one()
    return user
"""


def getUserId(email):
    """
       uses the users email to retrieve the users id
    """
    try:
        user = session.query(User).filter_by(email = email).one()
        return user.id
    except:
        return None


def get_Consoles():
    """
       Changes keyedtuple into list (Removes (u') from output so just the console names are displayed)
    """
    systems = session.query(Game.console).distinct()
    systemsList = list()
    for i in systems:
        lst = list(i)
        stri = " ".join(lst)
        systemsList.append(stri)
    return systemsList


@app.route('/gdisconnect')
def gdiscon():
    """
        google disconnect
    """
    creds = login_session.get('credentials')
    if creds is None:
        response = make_response(
        	json.dumps('You are not connected'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # note to get gdiscon to work on server take access_token  off of creds, that is below
    access_token = creds.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token%s' % (access_token)
    ht = httplib2.Http()
    result = ht.request(url, 'GET')[0]
    if result['status'] != '200':
        response = make_response(
        	json.dumps('Failed to revoke token.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/disconnect')
def disconnect():
    """
        General disconnect
    """
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdiscon()
            del login_session['gplus_id']
            del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdiscon()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully logged out.")
        return redirect(url_for('welcome'))
    else:
        flash("You are not logged in")
        return redirect(url_for('welcome'))

@app.route('/')
@app.route('/welcome')
def welcome():
    """
        home page
    """
    consoles = get_Consoles()
    return render_template('welcome.html', consoles=consoles)



@app.route('/console/<title>/Games')
def displayConsoleGames(title):
    """
        display all the games for that particular console
    """
    consoles = get_Consoles()
    console_list = session.query(Game).filter_by(console=title).all()
    return render_template('console.html', consoles=consoles, Games=console_list, console_name=title)


@app.route('/console/<console>/game/<Game_id>')
def gameInfo(console, Game_id):
    """
        display details of the game 
    """
    consoles = get_Consoles()
    usersGames = session.query(Game).filter_by(id=Game_id).one()
    try:
        if usersGames.user_name != login_session['username'] or usersGames.user_name == None:
            print usersGames.user_name
            for i in login_session:
                print login_session['username']
            return render_template('game.html', consoles=consoles, usersGames=usersGames)
        else:
            return render_template('privateGame.html', consoles=consoles, usersGames=usersGames)
    except:
        return render_template('game.html', consoles=consoles, usersGames=usersGames)

@app.route('/edit_game/<int:Game_id>', methods=['GET', 'POST'])
def editGame(Game_id):
    """
        edit games in the Game database
    """
    editGame = session.query(Game).filter_by(id=Game_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    consoles = get_Consoles()
    if editGame.user_name != login_session['username']:# to test just change editGame.user_name to editGame.id
        return "<script>function notUser(){alert('This is not your item so you cannot delete it.');}\
        </script><body onload=''>"
    if request.method == 'POST':

        if request.form['name']:
            editGame.game_name = request.form['name']
        if request.form['picture']:
            editGame.pic = request.form['picture']
        if request.form['console']:
            editGame.console = request.form['console']
        if request.form['description']:
            editGame.description = request.form['description']
        session.add(editGame)
        session.commit()
        flash('Game updated')
        return redirect(url_for('welcome'))
    else:
        return render_template('edit.html', editGame=editGame, consoles=consoles)


@app.route('/delete game/<int:Game_id>', methods=['GET', 'POST'])
def deleteGame(Game_id):
    """
       user can delete games they added from the Game database
    """
    consoles = get_Consoles()
    deleteGame = session.query(Game).filter_by(id=Game_id).one()
    title = deleteGame.game_name
    if 'username' not in login_session: 
       return('/login')
    console = deleteGame.console
    if deleteGame.user_name != login_session['username']:
        pass
    if login_session['username'] != deleteGame.user_name:
        return "<script>function notUser(){alert('This is not your item so you cannot delete it.');}\
        </script><body onload=''>"
    if request.method == "POST":
    	session.delete(deleteGame)
    	session.commit()
    	flash('{} has been deleted'.format(title))
    	return redirect(url_for('welcome'))
    else:
        return render_template('deleteGame.html', consoles=consoles, Game=deleteGame)

@app.route('/game/new', methods=['GET', 'POST'])
def newGame():
    """
        used to create a new game entry in the database for the current user.
    """
    if 'username' not in login_session:
        return redirect('/login')
    consoles = get_Consoles()
    if request.method == 'POST':
        userId = session.query(User).filter_by(name=login_session['username']).one()
        newGame = Game(game_name=str(request.form['name']), console=request.form['console'],
                        description=request.form['description'], user_name=login_session['username'],
                        user_id=userId.id)
        session.add(newGame)
        session.commit()
        flash("{} has been added".format(newGame.game_name))
        return render_template("welcome.html",consoles=consoles)
    return render_template("newgame.html", consoles=consoles)


# JSON endpoints

@app.route('/game/<int:game_id>/JSON')
def GamesJSON(game_id):
    game = session.query(Game).filter_by(id=game_id).one()
    return jsonify(game=game.serialize)

@app.route('/console/<console>/games/<int:game_id>/JSON')
def gameJSON(game_id, console):
    gameDetails = session.query(Game).filter_by(id=game_id,  console=console).one()
    return jsonify(gameDetails=gameDetails.serialize)


@app.route('/console/<console>/JSON')
def consoleGames(console):
    allGames = session.query(Game).filter_by(console=console).all()
    return jsonify(allGames= [i.serialize for i in allGames])


if __name__ == '__main__':
    app.debug = True
    app.run(host = '0.0.0.0', port = 5000)