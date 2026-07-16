from flask import request
from flask_socketio import emit

import messages
import draft
import utils

def try_dispatch( player, message ):
    if message[:1] != "/": return False
    ( command, _, parameters ) = message[1:].partition( " " )
    dispatch( player, command, parameters )
    return True

def dispatch( player, command, parameters ):
    match command:
        case "name":
            set_name( parameters )
        case "reset":
            reset_server()
        case _:
            messages.emit_message( "unrecognized command", to = request.sid )

def set_name( name ):
    if not name: return
    name = name[:16]
    # tell the client to make a request to set the cookie
    emit( "set-name", name )

def reset_server():
    utils.log( "resetting server" )
    draft.reset_draft( clear_players = True )
    messages.emit_message( "<span style=\"color: red\">Server has been reset, please refresh the page.</span>" )
