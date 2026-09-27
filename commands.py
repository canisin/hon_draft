from flask import request
from flask_socketio import emit

import sockets
import draft
import utils
import dice

commands = []

def command( command, help ):
    def decorator( function ):
        commands.append( ( command, help, function ) )
        return function
    return decorator

@command( "help", "prints help" )
def print_help( player, parameters ):
    for command, help, function in commands:
        sockets.message( "command_help", command = command, help = help ).emit( to = request.sid )

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
    sockets.message( "server_reset", player = player.id ).emit()

@command( "roll", "rolls dice" )
def roll_dice( player, expression ):
    if expression == "help":
        sockets.message( "dice_help" ).emit( to = request.sid )
        return

    expression = dice.DiceExpression.parse( expression )
    if not expression:
        sockets.message( "dice_error" ).emit( to = request.sid )
        sockets.message( "dice_help" ).emit( to = request.sid )
        return

    sockets.message( "dice_roll", player = player.id, expression = expression.to_string(), roll = expression.roll() ).emit()

def try_dispatch( player, message ):
    if message[:1] != "/": return False
    ( command, _, parameters ) = message[1:].partition( " " )
    dispatch( player, command, parameters )
    return True

def dispatch( player, command, parameters ):
    function = next( ( function for _command, help, function in commands if _command == command ), None )
    if not function:
            sockets.message( "unrecognized_command" ).emit( to = request.sid )
            return
    function( player, parameters )
