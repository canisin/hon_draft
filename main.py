from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room

from os import getenv

import players
import teams
import heroes
import messages
import logic

app = Flask( __name__ )
app.secret_key = "honzor"
socketio = SocketIO( app )

## ROUTES ##
@app.route( "/" )
def home():
    if "name" not in session:
        session[ "name" ] = "Unnamed Player"
    if "id" not in session:
        session[ "id" ] = players.Players.generate_id()
    return render_template( "home.html",
        team_size = logic.team_size,
        pool_size = logic.pool_size,
    )

@app.route( "/name", methods = [ "POST" ] )
def name():
    print( "name request" )
    name = request.form[ "name" ]
    player = players.Players.get( session[ "id" ] )
    player.set_name( name )
    session[ "name" ] = name
    return ""

## INCOMING SOCKET EVENTS ##
@socketio.on( "connect" )
def on_connect( auth ):
    print( "socket connecting" )
    id = session[ "id" ]
    name = session[ "name" ]
    players.Players.connect( id, name, request.sid )
    print( "socket connected" )

@socketio.on( "disconnect" )
def on_disconnect():
    print( "socket disconnecting" )
    id = session[ "id" ]
    players.Players.disconnect( id )
    print( "socket disconnected" )

@socketio.on( "first-ban" )
def on_first_ban( team ):
    player = players.Players.get( session[ "id" ] )
    team = teams.Teams.get( team )
    logic.set_first_ban( player, team )

@socketio.on( "toggle-stat" )
def on_toggle_stat( stat ):
    player = players.Players.get( session[ "id" ] )
    stat = heroes.Heroes.get( stat )
    logic.toggle_stat( player, stat )

@socketio.on( "start-draft" )
def on_start_draft():
    player = players.Players.get( session[ "id" ] )
    logic.start_draft( player )

@socketio.on( "cancel-draft" )
def on_cancel_draft():
    player = players.Players.get( session[ "id" ] )
    logic.cancel_draft( player )

@socketio.on( "end-draft" )
def on_end_draft():
    player = players.Players.get( session[ "id" ] )
    logic.end_draft( player )

@socketio.on( "click-slot" )
def on_click_slot( team, index ):
    player = players.Players.get( session[ "id" ] )
    team = teams.Teams.get( team )
    logic.click_slot( player, team, index )

@socketio.on( "dibs-hero" )
def on_dibs_hero( stat, index ):
    player = players.Players.get( session[ "id" ] )
    hero = heroes.Heroes.get( stat, index )
    logic.dibs_hero( player, hero )

@socketio.on( "veto-hero" )
def on_veto_hero( stat, index ):
    player = players.Players.get( session[ "id" ] )
    hero = heroes.Heroes.get( stat, index )
    logic.veto_hero( player, hero )

@socketio.on( "ban-hero" )
def on_ban_hero( stat, index ):
    player = players.Players.get( session[ "id" ] )
    hero = heroes.Heroes.get( stat, index )
    logic.ban_hero( player, hero )

@socketio.on( "pick-hero" )
def on_pick_hero( stat, index ):
    player = players.Players.get( session[ "id" ] )
    hero = heroes.Heroes.get( stat, index )
    logic.pick_hero( player, hero )

@socketio.on( "message" )
def on_message( message ):
    print( "received message" )
    if message[:1] == "/":
        on_command( message[1:] )
        return
    player = players.Players.get( session[ "id" ] )
    messages.emit_message( f"{ player.get_formatted_name() }: { message }", team = player.team )

def on_command( command ):
    ( command, _, parameters ) = command.partition( " " )
    match command:
        case "name":
            set_name( parameters )
        case "reset":
            reset_server()
        case _:
            print( "unrecognized command" )
            messages.emit_message( "unrecognized command", to = request.sid )

def set_name( name ):
    if not name: return
    name = name[:16]
    # tell the client to make a request to set the cookie
    emit( "set-name", name )

def reset_server():
    print( "resetting server" )
    logic.reset_draft( clear_players = True )
    messages.emit_message( "<span style=\"color: red\">Server has been reset, please refresh the page.</span>" )

def update_rooms( team ):
    if team is teams.Teams.observer:
        join_room( teams.Teams.legion.name )
        join_room( teams.Teams.hellbourne.name )
        join_room( teams.Teams.observer.name )
    else:
        join_room( team.name )
        leave_room( team.get_other().name )
        leave_room( teams.Teams.observer.name )

if __name__ == "__main__":
    logic.initialize_state()

    host = getenv( "HOST" ) or "0.0.0.0"
    port = getenv( "PORT" ) or None
    debug = logic.getenv_bool( "DEBUG", False )
    socketio.run( app, allow_unsafe_werkzeug = True, host = host, port = port, debug = debug )
