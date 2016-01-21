function render_date(unixtime) {
    if (typeof unixtime === 'undefined') {
        date = new Date();
    } else {
        date = new Date(unixtime * 1000);
    }
    formattedDate = '[' + ("0" + date.getHours()).slice(-2) + ":" + ("0" + date.getMinutes()).slice(-2) + '] ';
    return $("<span>").addClass("timestamp").text(formattedDate);
}

function render_message(user, message) {
    return $("<span>").addClass("message").text('<' + user + '> '+ message);
}

function render_login(user) {
    return $("<span>").addClass("notification").text(user + " has logged in");
}

function render_logout(user) {
    return $("<span>").addClass("notification").text(user + " has quit");
}

function render_join(user, channel) {
    return $("<span>").addClass("notification").text(user + " joined #" + channel);
}

function render_leave(user, channel) {
    return $("<span>").addClass("notification").text(user + " left #" + channel);
}

function render_error(message) {
    return $("<span>").addClass("error").text(message);
}

function update_user_list(users, channel) {
    if (channel) {
        $user_list = $('#chats .chat#' + channel + ' .users');
    } else {
        $user_list = $("#all_users");
    }

    $user_list.empty();
    var $users = $("<ul>").addClass("nav nav-list nav-stacked");
    $users.append($("<li>").addClass("col-header").text("Users"));
    for(var idx in users) {
        $users.append($("<li>").append($("<a>").append(users[idx])));
    };
    $user_list.append($users);
}

var P_TYPE = {
    MESSAGE: 0,
    REGISTER: 1,
    LOGIN: 2,
    LOGOUT: 3,
    JOIN: 4,
    LEAVE: 5,
    LIST: 6,
    ERROR: -1,
}

function handle_response(jsondata) {
    if (jsondata['history'] === true) {
        create_channel_tab(jsondata['channel'] || jsondata['dest']);
        print_response(jsondata, true);
        return;
    }

    switch (jsondata['type']) {
        case P_TYPE.JOIN:
            if (jsondata['user'] === window.nick) create_channel_tab(jsondata['channel']);
            break;
        case P_TYPE.LEAVE:
            if (jsondata['user'] === window.nick) destroy_channel_tab(jsondata['channel']);
            break;
        case P_TYPE.LIST:
            update_user_list(jsondata['users'], jsondata['channel']);
            return;  // don't print anything
        case P_TYPE.ERROR: {
            print_error(jsondata['message'], jsondata['time']);
            return;  // don't print anything
        }
    }

    print_response(jsondata);
}

function print_response(jsondata, is_history) {
    var element, $target;

    switch (jsondata['type']) {
        case P_TYPE.MESSAGE:
            $target = $('#chats .chat#' + jsondata['dest'] + ' .messages');
            element = render_message(jsondata['user'], jsondata['message']);
            break;
        case P_TYPE.LOGIN:
            $target = $('#chats .console .messages');
            element = render_login(jsondata['user']);
            break;
        case P_TYPE.LOGOUT:
            $target = $('#chats .console .messages');
            element = render_logout(jsondata['user']);
            break;
        case P_TYPE.JOIN:
            $target = $('#chats .chat#' + jsondata['channel'] + ' .messages');
            element = render_join(jsondata['user'], jsondata['channel']);
            break;
        case P_TYPE.LEAVE:
            $target = $('#chats .chat#' + jsondata['channel'] + ' .messages');
            element = render_leave(jsondata['user'], jsondata['channel']);
            break;
        case P_TYPE.LIST:
            update_user_list(jsondata['users']);
            return;
        case P_TYPE.ERROR: {
            $target = $('#chats .console .messages');
            element = render_error(jsondata['message'])
            break;
        }
    }

    row_class = (is_history === true) ? 'row history' : 'row';
    $target.append($('<div class="' + row_class + '">').append(render_date(jsondata['time'])).append(element));
    $target.scrollTop($target.prop("scrollHeight"));  // scroll to the bottom
}

function print_error(message, time) {
    element = render_error(message);
    $target = $('.chat.active .messages');

    $target.append($('<div class="row">').append(render_date(time).append(element)));
    $target.scrollTop($target.prop("scrollHeight"));  // scroll to the bottom
}

function channel_tab_bind() {
    $('#channels ul li a').click(function() {
        $('#input').focus();
    });
}

function channel_tab_exists(channel) {
    return $('#channels ul li a[aria-controls=' + channel + ']').length > 0;
}

function create_channel_tab(channel, focus) {
    if (channel_tab_exists(channel)) {
        return;
    }

    $tabbar = $('#channels ul');
    $tabcontainer = $('#chats');

    $tabbar.append('<li role="presentation"><a href="#' + channel + '" aria-controls="' +
                   channel + '" role="tab" data-toggle="tab">#' + channel + '</a></li>');

    $tabcontainer.append('<div class="row tab-pane chat" id="' + channel + '">' +
                         '  <div class="col-md-9 messages"></div>' +
                         '  <div class="col-md-3 users"></div>' +
                         '</div>');

    // bind focusing on a tab click
    channel_tab_bind();
    // focus on the created tab
    $tabbar.find('a[aria-controls=' + channel + ']').click();
}

function destroy_channel_tab(channel) {
    $('#channels li a[aria-controls=' + channel + ']').parent().remove();
    $('#chats .tab-pane#' + channel).remove();
}

function get_current_channel() {
    var current_channel = $('#channels .active a').attr('aria-controls');
    if (current_channel == 'server') return null;
    return current_channel;
}

function send_message(message) {
    if (message.search("/login") == 0) {

        if (typeof ws !== 'undefined' && ws.readyState !== ws.CLOSED) {
            // WS is already opened, no way we're allowing to create an another one!
            print_error("You're already logged in.");
            return;
        }

        var split = message.split(" ");
        if(split.length != 2) return;

        window.nick = split[1];

        // Create a WS connection
        ws = new WebSocket("ws://" + location.host + "/ws/login/" + window.nick);

        ws.onopen = function() {
            if ($('#chats .console .messages .row.help:first').length > 0) {
                $('#chats .console .messages .row.help:first').remove();  // Hides the helping row
            }
        };

        ws.onmessage = function(event) { 
            var jsondata = jQuery.parseJSON(event.data);
            handle_response(jsondata);
            event.preventDefault();
        }

        ws.onclose = function() {};

        return;
    } else if (message.search("/logout") == 0) {
        ws.send(generate_payload_logout());
        return;
    } else if (message.search("/join") == 0) {
        var split = message.split(" ");
        if(split.length != 2) return;
        var channel = split[1];

        if ($('#chats .console .messages .row.help:first').length > 0) {
            $('#chats .console .messages .row.help:first').remove();  // Hides the helping row
        }

        if (channel) ws.send(generate_payload_join(channel));
        return;
    } else if (message.search("/leave") == 0) {
        var split = message.split(" ");
        if(split.length > 2) return;
        if(split.length == 2) channel = split[1];
        if(split.length == 1) channel = get_current_channel();

        if (channel) ws.send(generate_payload_leave(channel));
        return;
    } else if (message.search("/list") == 0) {
        ws.send(generate_payload_list());
        return;
    }

    if (typeof ws === 'undefined') {
        print_error("Can't send a message without a connection. Please log in first.");
        return;
    }

    channel = get_current_channel();
    if (channel) return ws.send(generate_payload_message(channel, message));
}

function generate_payload_message(dest, message) {
    return JSON.stringify({
        'type': P_TYPE.MESSAGE,
        'dest': dest,
        'message': message
    });
}

function generate_payload_list() {
    return JSON.stringify({
        'type': P_TYPE.LIST
    });
}

function generate_payload_login(name) {
    return JSON.stringify({
        'type': P_TYPE.LOGIN, 'user': name
    });
}

function generate_payload_logout() {
    return JSON.stringify({
        'type': P_TYPE.LOGOUT
    });
}

function generate_payload_join(channel) {
    return JSON.stringify({
        'type': P_TYPE.JOIN, 'channel': channel
    });
}

function generate_payload_leave(channel) {
    return JSON.stringify({
        'type': P_TYPE.LEAVE, 'channel': channel
    });
}

$(function() {
    $('#channels').find('a[aria-controls=server]').click();

    $('form[name=chat]').submit(function(e) {
        send_message($('#input').val());
        $('#input').val('');
        e.preventDefault();
    });

    $('#input').keypress(function(e) {
      if (e.which == 13) {
        $('form[name=chat]').submit();
        return false;
      }
    });

    channel_tab_bind();
});
