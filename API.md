# API Documentation

The whole interaction with the server uses WebSockets.

## Connection

To connect to the chat server, the client has to create a WebSocket connection to the `/ws/` while being authenticated using the `/login/` form & `session` cookies.

## Data transfer

Both requests and responses are JSON objects. All objects are obligated to have a `type` key, which represents the type of the action.
Every response also has a `time` parameter, which is floating point number and contains UNIX timestamp of the moment the action was handled on the server side.

### Action types:

 - `0` - channel message
 - `1` - user registration _(not implemented yet)_
 - `2` - user log in
 - `3` - user log out
 - `4` - user joining channel
 - `5` - user leaving channel
 - `6` - list server/channel users
 - `7` - channel action
 - `-1` - error message

### Commands:

#### Log in

##### Client receives:

Key         | Type | Value        | Notes
----------- | ---- | ------------ | -----
`type`      | int  | `2`          |
`user`      | str  | `'nickname'` | 2-20 character limit

The server broadcasts this command to everyone after the client is connected.

#### Log out

##### Client sends:

Key         | Type | Value
----------- | ---- | ------------
`type`      | int  | `3`

##### Client receives:

Key         | Type | Value        | Notes
----------- | ---- | ------------ | -----
`type`      | int  | `3`          |
`user`      | str  | `'nickname'` | 2-20 character limit

No additional parameters required. 

When the client sends this command, the server closes the WebSocket connection and broadcasts the remaining clients that the user is disconnected.

#### Join a channel

##### Client sends:

Key         | Type | Value        | Notes
----------- | ---- | ------------ | -----
`type`      | int  | `4`          |
`channel`   | str  | `'#tornado'` | 2-16 character limit

##### Client receives:

Key         | Type  | Value            | Notes
----------- | ----- | ---------------- | -----
`type`      | int   | `4`              |
`time`      | float | `1453338500.966` |
`channel`   | str   | `'tornado'`      |
`user`      | str   | `'new_user'`     |
`history`   | bool  | `true`           | (optional) Flags the message as channel's history log

The sharp symbols at the beginning of the `channel` parameter are optional and are stripped by the server - so `django` and `#django` are the same channels.

The server notifies all users in that channel that the `user` has joined it.

#### Leave a channel

##### Client sends:

Key         | Type | Value
----------- | ---- | -----
`type`      | int  | `5`
`channel`   | str  | `'#tornado'`

##### Client receives:

Key         | Type  | Value            | Notes
----------- | ----- | ---------------- | -----
`type`      | int   | `5`              |
`time`      | float | `1453338500.966` |
`channel`   | str   | `'tornado'`      |
`user`      | str   | `'gone_user'`    |
`history`   | bool  | `true`           | (optional) Flags the message as channel's history log

Behaves exactly like `join`.

#### Send a message

##### Client sends:

Key         | Type | Value           | Notes
----------- | ---- | --------------- | -----
`type`      | int  | `0`             |
`channel`   | str  | `'#tornado'`    |
`message`   | str  | `'hello world'` | 1-2048 character limit

##### Client receives:

Key         | Type  | Value            | Notes
----------- | ----- | ---------------- | -----
`type`      | int   | `0`              |
`time`      | float | `1453338500.966` |
`channel`   | str   | `'tornado'`      |
`message`   | str   | `'hello world'`  |
`user`      | str   | `'sender'`       |
`history`   | bool  | `true`           | (optional) Flags the message as channel's history log

The server broadcasts the response message to everybody who have joined the channel the message was sent to; the server also adds a `user` parameter which contains the nickname of the sender.

#### Send an action

##### Client sends:

Key         | Type | Value           | Notes
----------- | ---- | --------------- | -----
`type`      | int  | `7`             |
`channel`   | str  | `'#tornado'`    |
`message`   | str  | `'ate a berry'` | 1-2048 character limit

##### Client receives:

Key         | Type  | Value            | Notes
----------- | ----- | ---------------- | -----
`type`      | int   | `7`              |
`time`      | float | `1453338500.966` |
`channel`   | str   | `'tornado'`      |
`message`   | str   | `'ate a berry'`  | Action taken on behalf of the user.
`user`      | str   | `'berry_eater'`  |
`history`   | bool  | `true`           | (optional) Flags the message as channel's history log

This behaves exactly the same as the MESSAGE command, just has a different purpose.

Command type | Message displayed
-----------: | :----------------
     message | <maintainer> friday night production deploy ftw!
     message | <nagios> SERVER IS DOWN
      action | _* maintainer screwed up_
     message | <maintainer> :(


#### List connected users

##### Client sends:

Key         | Type | Value        | Notes
----------- | ---- | ------------ | -----
`type`      | int  | `6`          |
`channel`   | str  | `'#tornado'` | (optional)

##### Client receives:

Key         | Type | Value                | Notes
----------- | ---- | -------------------- | -----
`type`      | int  | `6`                  |
`users`     | arr  | `['user1', 'user2']` |
`channel`   | str  | `'tornado'`          | (optional) and is to be sent only if it existed in the request.

If sent without a `channel` parameter, it returns all the users that are connected to the server.
Otherwise, it returns just the users that have joined the given channel.

This command is also sent by the server if anybody joins/leaves the channel to ensure the consistency of the client list.
