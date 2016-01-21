import logging
import os

import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket

from tornado.options import define, options
from tornado.escape import json_decode

from protocol import ChatServerMixin


define("port", default=8667, help="web server's port", type=int)
define("address", default='127.0.0.1', help="web server's host", type=str)
define("debug", default=False, help="debug mode", type=bool)
define("cookie_secret", default=None, help="cookie secret key", type=str)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")


class ChatSocketHandler(ChatServerMixin, tornado.websocket.WebSocketHandler):
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
            (r"/", MainHandler),
            (r"/chat", ChatSocketHandler),
            (r"/chat/(.*)/(.*)", ChatSocketHandler),
            # e.g.:  /chat/login/vasya - connects successfully and automatically logs the vasya in.
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
        )
        settings.update(kwargs)
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
