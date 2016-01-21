import time
import re

from collections import defaultdict
from enum import IntEnum

from tornado.escape import json_encode
from tornado.websocket import WebSocketClosedError
from sqlalchemy.exc import IntegrityError

from models import Message


class P_TYPE(IntEnum):
    """Message/payload types."""
    MESSAGE = 0
    REGISTER = 1
    LOGIN = 2
    LOGOUT = 3
    JOIN = 4
    LEAVE = 5
    LIST = 6
    ACTION = 7
    ERROR = -1


class ValidationError(Exception):
    pass


def validate_username(username):
    if not re.match(r'\w{2,20}$', username):
        raise ValidationError(
            'Username should contain 2-20 characters (only letters, numbers and underscores).'
        )


def validate_channel(channel):
    if channel == 'server':
        raise ValidationError("This channel name is reserved for the system purposes.")

    if not re.match(r'\w{2,16}$', channel):
        raise ValidationError(
            'Channel should contain 2-16 characters (only letters, numbers and underscores).'
        )


def validate_message(message):
    if not re.match(r'.{1,2048}$', message):
        raise ValidationError(
            'Message should contain 1-2048 characters.'
        )


class ChatServerMixin(object):
    USERS = []
    CHANNELS = defaultdict(list)

    def write_message(self, message, **kwargs):
        """Extends the default write_message function to encode the message to JSON and
to prevent hanging while trying to send a message to a disconnected user."""
        try:
            return super(ChatServerMixin, self).write_message(json_encode(message), **kwargs)
        except WebSocketClosedError:
            pass

    def _generate_payload(self, p_type, **kwargs):
        """A simple helper function that returns a dictionary suitable for the given message type.
It's ought to be sent to the client right after that."""
        result = {
            'type': p_type,
            'time': time.time(),
        }

        if p_type in (P_TYPE.MESSAGE, P_TYPE.REGISTER, P_TYPE.LOGIN,
                      P_TYPE.LOGOUT, P_TYPE.JOIN, P_TYPE.LEAVE, P_TYPE.ACTION):
            result.update({'user': self.nickname})

        result.update(kwargs)
        return result

    def _broadcast_message(self, payload, filter_users=None):
        """Sends a websocket message to all connected clients (also filters the users if given)."""
        for c in filter(filter_users, self.USERS):
            if c.logged_in:
                c.write_message(payload)

    def _channel_message(self, channel, payload):
        """Send a websocket message to all clients within a channel."""
        self._broadcast_message(
            payload,
            filter_users=lambda user: user.nickname in self.CHANNELS[channel]
        )

    def update_history(self, channel, payload):
        user = self.get_current_user()
        message = Message(
            user_id=user.id,
            p_type=int(payload['type']),
            channel=channel,
            message=payload.get('message')
        )

        try:
            self.application.db.add(message)
            self.application.db.commit()
        except IntegrityError:
            self.application.db.rollback()

    def send_history(self, channel):
        for message in (self.application.db.query(Message)
                        .filter_by(channel=channel)
                        .order_by(Message.date_created)
                        .limit(50)):
            self.write_message({
                'time': message.date_created.timestamp(),
                'type': message.p_type,
                'channel': channel,
                'user': message.user.username,
                'message': message.message or None,
                'history': True
            })

    # API command methods
    def send_error(self, message, **kwargs):
        self.write_message(self._generate_payload(P_TYPE.ERROR, message=message, **kwargs))

    def user_login(self, username, password=None):
        try:
            validate_username(username)
        except ValidationError as e:
            self.send_error(str(e))
            return

        if password is None:
            user = self.get_current_user()
        else:
            user = self.login(username, password)

        if user:
            self.nickname = username
            self.logged_in = True
            self.write_message(self._generate_payload(P_TYPE.LOGIN, auth=True))
            self._broadcast_message(
                self._generate_payload(P_TYPE.LOGIN),
                filter_users=lambda user: user != self  # exclude the user him/herself
            )
            self.user_list()
        else:
            self.send_error("Wrong username or password.")

    def user_logout(self):
        self._broadcast_message(
            self._generate_payload(P_TYPE.LOGOUT),
            filter_users=lambda user: user != self  # exclude the user him/herself
        )

        # Remove the user from all the channels & notify the users
        for channel in [chan for chan, users in self.CHANNELS.items() if self.nickname in users]:
            self.user_leave(channel)
            self.user_list(channel=channel, broadcast=True)

        try:
            self.logged_in = False
            self.USERS.remove(self)
        except ValueError:
            pass

    # Channel-related commands

    def user_join(self, channel):
        if self.nickname in self.CHANNELS[channel]:
            self.send_error("You have already joined that channel!")
            return

        self.CHANNELS[channel].append(self.nickname)

        self.send_history(channel)

        payload = self._generate_payload(P_TYPE.JOIN, channel=channel)
        self._channel_message(channel, payload)
        self.update_history(channel, payload)

    def user_leave(self, channel):
        if self.nickname not in self.CHANNELS[channel]:
            self.send_error("You aren't present on that channel!")
            return

        payload = self._generate_payload(P_TYPE.LEAVE, channel=channel)
        self._channel_message(channel, payload)
        self.CHANNELS[channel].remove(self.nickname)
        self.update_history(channel, payload)

    def send_message(self, channel, message, msg_type=None):
        if msg_type is None:
            msg_type = P_TYPE.MESSAGE

        payload = self._generate_payload(msg_type, channel=channel, message=message)
        self._channel_message(channel, payload)
        self.update_history(channel, payload)

    def user_list(self, channel=None, broadcast=False):
        """Sends a list of connected users.
If `channel` is set, sends only a list of users in that channel.
If `broadcast` is set, also sends a list of users to everybody in that channel."""

        if channel:
            msg_func = self.write_message

            if broadcast:
                msg_func = lambda payload: self._channel_message(channel, payload)

            msg_func(
                self._generate_payload(
                    P_TYPE.LIST,
                    users=self.CHANNELS[channel],
                    channel=channel,
                )
            )
        else:
            self.write_message(
                self._generate_payload(
                    P_TYPE.LIST,
                    users=[c.nickname for c in self.USERS],
                )
            )

    def handle_command(self, payload):
        """This method handles API requests."""
        # Common parameter: `channel`
        if payload['type'] in (P_TYPE.JOIN, P_TYPE.LEAVE, P_TYPE.MESSAGE,
                               P_TYPE.ACTION, P_TYPE.LIST):
            channel = payload['channel'].lstrip('#')

            try:
                validate_channel(channel)
            except ValidationError as e:
                self.send_error(str(e))
                return

        # Common parameter: `message`
        if payload['type'] in (P_TYPE.MESSAGE, P_TYPE.ACTION):
            message = payload['message']

            try:
                validate_message(message)
            except ValidationError as e:
                self.send_error(str(e))
                return

            self.send_message(channel, message, msg_type=payload['type'])

        # Actual command handling
        if payload['type'] == P_TYPE.LOGIN:
            nickname = payload['user']
            password = payload.get('password')
            self.user_login(nickname, password=password)
        elif payload['type'] == P_TYPE.LOGOUT:
            self.user_logout()
            self.close()
        elif payload['type'] == P_TYPE.JOIN:
            self.user_join(channel)
            self.user_list(channel=channel, broadcast=True)
        elif payload['type'] == P_TYPE.LEAVE:
            self.user_leave(channel)
            self.user_list(channel=channel, broadcast=True)
        elif payload['type'] == P_TYPE.LIST:
            self.user_list(channel=channel)
