from flask import request
from flask_socketio import emit

import messages
import draft
import utils

commands = []

def command( command, help ):
    def decorator( function ):
        commands.append( ( command, help, function ) )
        return function
    return decorator

@command( "help", "prints help" )
def print_help( player, parameters ):
    for command, help, function in commands:
        messages.emit_message( f"<span style=\"font-family: monspace, monospace; color: blue\">/{ command }</span>: { help }", to = request.sid )

@command( "name", "sets player name" )
def set_name( player, name ):
    if not name: return
    name = name[:16]
    # tell the client to make a request to set the cookie
    emit( "set-name", name )

@command( "reset", "resets the server" )
def reset_server( player, parameters ):
    utils.log( "resetting server" )
    draft.reset_draft( clear_players = True )
    messages.emit_message( f"<span style=\"color: red\">{ player.get_formatted_name() } has reset the server, please refresh the page.</span>" )

def try_dispatch( player, message ):
    if message[:1] != "/": return False
    ( command, _, parameters ) = message[1:].partition( " " )
    dispatch( player, command, parameters )
    return True

def dispatch( player, command, parameters ):
    function = next( function for _command, help, function in commands if _command == command )
    if not function:
            messages.emit_message( "<span style=\"color: red\">Unrecognized command</span>", to = request.sid )
            return
    function( player, parameters )
