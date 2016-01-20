import logging
import os

from collections import defaultdict
from enum import IntEnum

import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket

from tornado.escape import json_encode, json_decode
from tornado.options import define, options


define("port", default=8667, help="web server's port", type=int)
define("address", default='127.0.0.1', help="web server's host", type=str)
define("debug", default=False, help="debug mode", type=bool)
define("cookie_secret", default=None, help="cookie secret key", type=str)


class P_TYPE(IntEnum):
    """Message/payload types."""

    MESSAGE = 0
    REGISTER = 1
    LOGIN = 2
    LOGOUT = 3
    JOIN = 4
    LEAVE = 5
    LIST = 6
    ERROR = -1


USERS = []  # Stores the active handler instances
CHANNELS = defaultdict(list)

# Initialize predefined channels:
for channel in ('django', 'flask', 'tornado'):
    CHANNELS[channel]


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html", channels=CHANNELS)


class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self, action, nick):
        USERS.append(self)
        self.nickname = ''
        self.logged_in = False

        if action == 'login' and nick is not None:
            # The user has connected to the websocket via a custom URL.
            # Let's log the user in automagically right after connect
            # without having him/her to send an additional LOGIN request
            self.user_login(nick)

    def on_message(self, message):
        """Sends a personal/broadcast message based on the command requested."""
        payload_in = json_decode(message)

        if payload_in['type'] == P_TYPE.LOGIN:
            self.user_login(payload_in['user'])

        elif payload_in['type'] == P_TYPE.LOGOUT:
            self.close()  # Closes the WebSocket connection

        elif payload_in['type'] == P_TYPE.JOIN:
            channel = payload_in['channel'].lstrip('#')
            if self.nickname not in CHANNELS[channel]:
                CHANNELS[channel].append(self.nickname)

            self.broadcast_message(
                self.generate_payload(P_TYPE.JOIN, channel=channel),
                # send the channel message only to the people belonging to that channel
                filter_users=lambda user: user.nickname in CHANNELS[channel]
            )
        elif payload_in['type'] == P_TYPE.LEAVE:
            channel = payload_in['channel'].lstrip('#')
            if self.nickname in CHANNELS[channel]:
                CHANNELS[channel].remove(self.nickname)

            self.broadcast_message(
                self.generate_payload(P_TYPE.LEAVE, channel=channel),
                # send the channel message only to the people belonging to that channel
                filter_users=lambda user: user.nickname in CHANNELS[channel]
            )
        elif payload_in['type'] == P_TYPE.MESSAGE:
            channel = payload_in['dest']

            self.broadcast_message(
                self.generate_payload(
                    P_TYPE.MESSAGE,
                    dest=channel,
                    message=payload_in['message'],
                ),
                # send the channel message only to the people belonging to that channel
                filter_users=lambda user: user.nickname in CHANNELS[channel]
            )
        elif payload_in['type'] == P_TYPE.LIST:
            self.user_list()

    def user_login(self, nick):
        self.nickname = nick
        self.logged_in = True
        self.broadcast_message(self.generate_payload(P_TYPE.LOGIN))
        self.write_message(
            self.generate_payload(P_TYPE.LIST, users=[c.nickname for c in USERS])
        )

    def user_logout(self):
        self.broadcast_message(
            self.generate_payload(P_TYPE.LOGOUT),
            filter_users=lambda user: user != self  # exclude the user him/herself
        )
        USERS.remove(self)

    def user_in_channels(self):
        return [channel for channel, users in CHANNELS.items() if self.nickname in users]

    def user_list(self, broadcast=False):
        self.write_message(
            self.generate_payload(P_TYPE.LIST, users=[c.nickname for c in USERS])
        )

    def broadcast_message(self, payload, filter_users=None):
        """Sends a websocket message to all connected clients."""
        for c in filter(filter_users, USERS):
            if c.logged_in:
                c.write_message(payload)

    def generate_payload(self, p_type, **kwargs):
        """A simple helper function that returns a dictionary
suitable for the given message type.
It's ought to be sent to the client right after that."""

        result = {'type': p_type}

        if p_type in (P_TYPE.MESSAGE, P_TYPE.REGISTER, P_TYPE.LOGIN,
                      P_TYPE.LOGOUT, P_TYPE.JOIN, P_TYPE.LEAVE):
            result.update({'user': self.nickname})

        result.update(kwargs)
        return json_encode(result)

    def on_close(self):
        self.user_logout()


class Application(tornado.web.Application):
    def __init__(self, **kwargs):
        handlers = [
            (r"/", MainHandler),
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
