import hashlib
import logging
import os

import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket

from tornado.options import define, options
from tornado.escape import json_decode
from tornado.web import URLSpec as url

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import IntegrityError

from models import User
from protocol import ChatServerMixin, validate_username, ValidationError


define("port", help="web server's port", type=int)
define("address", help="web server's host", type=str)
define("debug", help="debug mode", type=bool)
define("cookie_secret", help="cookie secret key", type=str)
define("hash_salt", help="password hashing salt", type=str)
define("sqlalchemy_db", help="sqlalchemy database uri", type=str)


class AuthHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        user_id = self.get_secure_cookie('session')
        if not user_id:
            return None

        return self.application.db.query(User).get(int(user_id))


class IndexHandler(AuthHandler):
    name = 'index'

    def get(self):
        self.render("index.html")


class ChatHandler(AuthHandler):
    name = 'chat'

    def get(self):
        self.render("chat.html")


class LoginHandler(AuthHandler):
    name = 'login'

    def get(self):
        self.render("login.html")

    def post(self):
        username = self.get_argument('username')
        password = self.get_argument('password')

        password_hash = hashlib.sha256((password + options.hash_salt).encode('utf-8')).hexdigest()
        user = (self.application.db.query(User)
                .filter_by(username=username, password=password_hash)
                .one_or_none())

        if user:
            self.set_secure_cookie('session', str(user.id))
            self.redirect(self.reverse_url('chat'))
        else:
            self.render("login.html", success=False, message="Wrong username or password.")


class LogoutHandler(AuthHandler):
    name = 'logout'

    def get(self):
        self.set_secure_cookie('session', '')
        self.redirect(self.reverse_url('index'))


class RegisterHandler(AuthHandler):
    name = 'register'

    def get(self):
        self.render("register.html")

    def post(self):
        username = self.get_argument('username')
        password = self.get_argument('password')
        password_confirm = self.get_argument('password_confirm')

        try:
            validate_username(username)
        except ValidationError as e:
            self.render("register.html", success=False, message=(str(e)))

        if password != password_confirm:
            self.render("register.html", success=False, message="Passwords mismatch.")

        password_hash = hashlib.sha256((password + options.hash_salt).encode('utf-8')).hexdigest()

        try:
            user = User(username=username, password=password_hash)
            self.application.db.add(user)
            self.application.db.commit()
        except IntegrityError:
            self.render("register.html", success=False, message="Username is already taken.")

        self.render("login.html", success=True)


class ChatSocketHandler(ChatServerMixin, AuthHandler, tornado.websocket.WebSocketHandler):
    def open(self, action, nick):
        self.USERS.append(self)
        self.nickname = ''
        self.logged_in = False

        if action == 'login' and nick is not None:
            # The user has connected to the websocket via a custom URL.
            # Let's log the user in automagically right after connect
            # without having him/her to send an additional LOGIN request
            self.user_login(nick)

    def on_message(self, message):
        """Sends a personal/broadcast message based on the command requested."""
        self.handle_command(json_decode(message))

    def on_close(self):
        """Logs the user out when WebSocket connection closes."""
        self.user_logout()


class Application(tornado.web.Application):
    def __init__(self, **kwargs):
        handlers = [
            url(r"/", IndexHandler, name=IndexHandler.name),
            url(r"/register/", RegisterHandler, name=RegisterHandler.name),
            url(r"/login/", LoginHandler, name=LoginHandler.name),
            url(r"/logout/", LogoutHandler, name=LogoutHandler.name),
            url(r"/chat/", ChatHandler, name=ChatHandler.name),
            url(r"/ws/", ChatSocketHandler, name='ws'),
            url(r"/ws/(.*)/(.*)", ChatSocketHandler, name='ws-login'),
            # e.g.:  /ws/login/vasya - connects successfully and automatically logs the vasya in.
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
        )
        settings.update(kwargs)

        engine = create_engine(options.sqlalchemy_db, echo=False)
        self.db = scoped_session(sessionmaker(bind=engine))
        super(Application, self).__init__(handlers, **settings)


def main():
    tornado.options.parse_config_file('server.conf')
    app = Application(
        cookie_secret=options.cookie_secret,
        debug=options.debug,
    )
    app.listen(options.port, options.address)
    logging.info('Started a server at http://{address}:{port}/'.format(
        address=options.address, port=options.port
    ))
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
