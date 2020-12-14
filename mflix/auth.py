from mflix.mflix import app
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
from mflix.db import get_user, add_user
import flask_login
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt(app)

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

'''
Makes a class that makes user loading easy with flask_login
'''
class User(flask_login.UserMixin):
    pass

'''
Given MongoDB user data, create a user.
Assumes name and email are valid
'''
def create_user_object(userdata):
    user = User()
    user.id = userdata["email"]
    user.email = userdata["email"]
    user.name = userdata["name"]
    user.first_name = user.name.split(" ", 1)[0]
    return user

@login_manager.user_loader
def user_loader(email):
    userdata = get_user(email)
    if not userdata:
        return

    return create_user_object(userdata)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return redirect(url_for('login'))

    email = request.form['email']
    name = request.form['name']
    pw = request.form['password']

    if len(pw) < 8:
        return render_template('login.html',
            signuperror="Make sure that your password is at least 8 characters!")
    if pw != request.form['confirmpassword']:
        return render_template('login.html',
            signuperror="Make sure that the passwords you enter match!")

    insertionresult = add_user(name, email, 
        bcrypt.generate_password_hash(pw.encode('utf8')).decode("utf-8"))
    if 'error' in insertionresult:
        return render_template('login.html',
            signuperror=insertionresult["error"])

    userdata = get_user(email)
    if not userdata:
        return render_template('login.html',
            signuperror="There's something wrong on our end. Please try again later!")

    user = create_user_object(userdata)
    flask_login.login_user(user)
    return redirect(url_for('show_movies'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form['email']
    pw = request.form['password']

    userdata = get_user(email)
    if not userdata:
        return render_template('login.html', loginerror="Make sure your email is correct.")
    if not bcrypt.check_password_hash(userdata['pw'], pw):
        return render_template('login.html', loginerror="Make sure your password is correct.")

    user = create_user_object(userdata)
    flask_login.login_user(user)
    return redirect(url_for('show_movies'))

@app.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect(url_for('show_movies'))

@app.route('/profile')
@flask_login.login_required
def profile():
    return render_template('profile.html')

@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('splashpage.html')
