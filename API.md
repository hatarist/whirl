# API Documentation

The whole interaction with the server uses WebSockets.

## Connection

To connect to the chat server, the client has to create a WebSocket connection to the `/chat/login/%NICK%` URL, where `%NICK` is a desired nickname. _(TODO) validation_.

## Data transfer

Both requests and responses are JSON objects. All objects are obligated to have a `type` key, which represents the type of the action.

### Action types:

 - `0` - channel message
 - `1` - user registration _(not implemented yet)_
 - `2` - user log in
 - `3` - user log out
 - `4` - user joining channel
 - `5` - user leaving channel
 - `6` - list users connected to the server
 - `-1` - error message _(not implemented yet)_

### Commands:

#### Log in

Key         | Type | Value
----------- | ---- | ------------
`type`      | int  | `2`
`user`      | str  | `'nickname'`

Client doesn't have to send this command after connecting to the WebSocket. 

The server broadcasts this command to everyone after the client is connected.

#### Log out

Key         | Type | Value
----------- | ---- | ------------
`type`      | int  | `3`

No additional parameters required. 

When the client sends this command, the server closes the WebSocket connection and broadcasts the remaining clients that the user is disconnected.

#### Join a channel

##### Client sends:

Key         | Type | Value
----------- | ---- | ------------
`type`      | int  | `4`
`channel`   | str  | `'#channel'`

##### Client receives:

Key         | Type | Value
----------- | ---- | ------------
`type`      | int  | `4`
`channel`   | str  | `'#channel'`
`user`      | str  | `'new_user'`

The sharp symbols at the beginning of the `channel` parameter are optional and are stripped by the server - so `django` and `#django` are the same channels.

The server notifies all users in that channel that the `user` has joined it.

#### Leave a channel

##### Client sends:

Key         | Type | Value
----------- | ---- | ------------
`type`      | int  | `5`
`channel`   | str  | `'#channel'`

##### Client receives:

Key         | Type | Value
----------- | ---- | ------------
`type`      | int  | `5`
`channel`   | str  | `'#channel'`
`user`      | str  | `'gone_user'`

Just like `join`, the sharp symbols are also stripped.

#### Send a message

##### Client sends:

Key         | Type | Value
----------- | ---- | ------------
`type`      | int  | `0`
`dest`      | str  | `'#channel'`
`message`   | str  | `'hello world`

##### Client receives:

Key         | Type | Value
----------- | ---- | ------------
`type`      | int  | `0`
`dest`      | str  | `'#channel'`
`message`   | str  | `'hello world`
`user`      | str  | `'sender'`

The server broadcasts the response message to everybody who have joined the channel the message was sent to; the server also adds a `user` parameter which contains the nickname of the sender.

#### List connected users

##### Client sends:

Key         | Type | Value
----------- | ---- | ------------
`type`      | int  | `6`

##### Client receives:

Key         | Type | Value
----------- | ---- | ------------
`type`      | int  | `6`
`users`     | arr  | `['user1', 'user2']`

As of now, this command only supports listing all the users connected to the server; it can't list users of particular channel.
