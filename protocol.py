import re

from collections import defaultdict
from enum import IntEnum

from tornado.escape import json_encode
from tornado.websocket import WebSocketClosedError


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


class ValidationError(Exception):
    pass


def validate_username(username):
    if not re.match(r'\w{2,20}$', username):
        raise ValidationError(
            'Username should contain 2-20 characters (only letters, numbers and underscores).'
        )


def validate_channel(channel):
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

    def write_message(self, *args, **kwargs):
        """Extends the default write_message function to prevent hanging while trying to
send a message to a disconnected user."""
        try:
            return super(ChatServerMixin, self).write_message(*args, **kwargs)
        except WebSocketClosedError:
            pass

    def _generate_payload(self, p_type, **kwargs):
        """A simple helper function that returns a dictionary suitable for the given message type.
It's ought to be sent to the client right after that."""
        result = {'type': p_type}

        if p_type in (P_TYPE.MESSAGE, P_TYPE.REGISTER, P_TYPE.LOGIN,
                      P_TYPE.LOGOUT, P_TYPE.JOIN, P_TYPE.LEAVE):
            result.update({'user': self.nickname})

        result.update(kwargs)
        return json_encode(result)

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

    def user_in_channels(self):
        return [channel for channel, users in self.CHANNELS.items() if self.nickname in users]

    # API command methods
    def send_error(self, message, **kwargs):
        self.write_message(self._generate_payload(P_TYPE.ERROR, message=message, **kwargs))

    def user_login(self, nick):
        try:
            validate_username(nick)
        except ValidationError as e:
            self.send_error(str(e))
            return

        self.nickname = nick
        self.logged_in = True
        self._broadcast_message(self._generate_payload(P_TYPE.LOGIN))
        self.user_list()

    def user_logout(self):
        self._broadcast_message(
            self._generate_payload(P_TYPE.LOGOUT),
            filter_users=lambda user: user != self  # exclude the user him/herself
        )

        channels = self.user_in_channels()

        # Remove the user from all the channels & notify the users
        for channel in channels:
            self.user_leave(channel)
            self.user_list(channel=channel, broadcast=True)

        try:
            self.USERS.remove(self)
        except ValueError:
            pass

    # Channel-related commands

    def user_join(self, channel):
        if self.nickname in self.CHANNELS[channel]:
            self.send_error("You have already joined that channel!")
            return

        self.CHANNELS[channel].append(self.nickname)

        self._channel_message(
            channel,
            self._generate_payload(P_TYPE.JOIN, channel=channel),
        )

    def user_leave(self, channel):
        if self.nickname not in self.CHANNELS[channel]:
            self.send_error("You aren't present on that channel!")
            return

        self._channel_message(
            channel,
            self._generate_payload(P_TYPE.LEAVE, channel=channel),
        )

        self.CHANNELS[channel].remove(self.nickname)

    def send_message(self, channel, message):
        self._channel_message(
            channel,
            self._generate_payload(P_TYPE.MESSAGE, dest=channel, message=message),
        )

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
        if payload['type'] == P_TYPE.LOGIN:
            nickname = payload['user']
            self.user_login(nickname)

        elif payload['type'] == P_TYPE.LOGOUT:
            self.user_logout()
            self.close()

        elif payload['type'] == P_TYPE.JOIN:
            channel = payload['channel'].lstrip('#')

            try:
                validate_channel(channel)
            except ValidationError as e:
                self.send_error(str(e))
                return

            self.user_join(channel)
            self.user_list(channel=channel, broadcast=True)

        elif payload['type'] == P_TYPE.LEAVE:
            channel = payload['channel'].lstrip('#')

            try:
                validate_channel(channel)
            except ValidationError as e:
                self.send_error(str(e))
                return

            self.user_leave(channel)
            self.user_list(channel=channel, broadcast=True)

        elif payload['type'] == P_TYPE.MESSAGE:
            channel = payload['dest'].lstrip('#')
            message = payload['message']

            try:
                validate_channel(channel)
                validate_message(message)
            except ValidationError as e:
                self.send_error(str(e))
                return

            self.send_message(channel, message)

        elif payload['type'] == P_TYPE.LIST:
            channel = payload.get('channel')

            if channel:
                channel = channel.lstrip('#')

                try:
                    validate_channel(channel)
                except ValidationError as e:
                    self.send_error(str(e))
                    return

            self.user_list(channel=channel)
