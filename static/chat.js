function render_date() {
    var date = new Date();
    var formattedDate = '[' + ("0" + date.getHours()).slice(-2) + ":" + ("0" + date.getMinutes()).slice(-2) + '] ';
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

function render_join(user) {
    return $("<span>").addClass("notification").text(user + " joined the only chat room");
}

function render_leave(user) {
    return $("<span>").addClass("notification").text(user + " left the only chat room");
}

function render_error(message) {
    return $("<span>").addClass("error").text(message);
}

function update_user_list(users) {
    $("#all_users").empty();
    var $users = $("<ul>").addClass("nav nav-list");
    $users.append($("<li>").addClass("col-header").text("Users"));
    for(var idx in users) {
        $users.append($("<li>").append(users[idx]));
    };
    $("#all_users").append($users);
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

function print_response(jsondata) {
    var element, $target;
    if(jsondata['type'] == P_TYPE.MESSAGE) {
        $target = $('#chat_log');
        element = render_message(jsondata['user'], jsondata['message']);
    } else if(jsondata['type'] == P_TYPE.LOGIN) {
        $target = $('#console_log');
        element = render_login(jsondata['user']);
    } else if(jsondata['type'] == P_TYPE.LOGOUT) {
        $target = $('#console_log');
        element = render_logout(jsondata['user']);
    } else if(jsondata['type'] == P_TYPE.JOIN) {
        $target = $('#chat_log');
        element = render_join(jsondata['user']);
    } else if(jsondata['type'] == P_TYPE.LEAVE) {
        $target = $('#chat_log');
        element = render_leave(jsondata['user']);
    } else if(jsondata['type'] == P_TYPE.LIST) {
        update_user_list(jsondata['users']);
        return;
    } else if(jsondata['type'] == P_TYPE.ERROR) {
        $target = $('#console_log');
        element = render_error(jsondata['message'])
    }

    $target.append($("<div>").addClass("row").append(render_date()).append(element));
}

function print_error(message) {
    element = render_error(message);
    $('#console_log').append($("<div>").addClass("row").append(render_date()).append(element));
}

function send_message(message) {
    if (message.search("/login") == 0) {

        if (typeof ws !== 'undefined') {
            // WS is already opened, no way we're allowing to create an another one!
            print_error("You're already logged in.");
            return;
        }

        var split = message.split(" ");
        if(split.length != 2) {
            return;
        }
        var nick = split[1];

        // Create a WS connection
        ws = new WebSocket("ws://" + location.host + "/chat/login/" + nick);

        ws.onopen = function() {
            $('#console_log .row:first').remove();  // Hides the helping row
        };

        ws.onmessage = function(event) { 
            var jsondata = jQuery.parseJSON(event.data);
            print_response(jsondata);
            event.preventDefault();
        }

        ws.onclose = function() {};

        return;
    }

    if (typeof ws === 'undefined') {
        print_error("Can't send a message without a connection. Please log in first.");
        return;
    }

    $('#chat-menu').click();
    $("#input").focus();
    return ws.send(generate_payload_message(message));
}

function generate_payload_message(message) {
    return JSON.stringify({
        'type': P_TYPE.MESSAGE,
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

$(function() {
    $('#input').focus();

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

    $(".nav a").click(function(e) {
       $(".nav .active").removeClass("active");
       $(this).parent().addClass("active");
       $('#input').focus();
    });
    
    $("#console-menu").click(function(e) {
        $("#console-content").show();
        $("#chat-content").hide();
    });

    $("#chat-menu").click(function(e) {
        $("#console-content").hide();
        $("#chat-content").show();
    });
});
