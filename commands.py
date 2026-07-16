from flask import request
from flask_socketio import emit

import messages
import draft
import utils

class Command:
    def __init__( self, command, help ):
        self.command = command
        self.help = help

    def connect( self, func ):
        self.func = func

    def execute( self, player, parameters ):
        self.func( player, parameters )

commands = []

def command_decorator( command, help ):
    command = Command( command, help )
    commands.append( command )
    return command.connect

@command_decorator( "help", "prints help" )
def print_help( player, parameters ):
    for command in commands:
        messages.emit_message( f"<span style=\"font-family: monspace, monospace; color: blue\">/{ command.command }</span>: { command.help }", to = request.sid )

@command_decorator( "name", "sets player name" )
def set_name( player, name ):
    if not name: return
    name = name[:16]
    # tell the client to make a request to set the cookie
    emit( "set-name", name )

@command_decorator( "reset", "resets the server" )
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
    command = next( c for c in commands if c.command == command )
    if not command:
            messages.emit_message( "<span style=\"color: red\">Unrecognized command</span>", to = request.sid )
            return
    command.execute( player, parameters )
