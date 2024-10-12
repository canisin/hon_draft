from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit

from threading import Thread
from threading import Timer
from time import sleep
from random import random
from uuid import uuid4
import json

app = Flask( __name__ )
app.secret_key = "honzor"
socketio = SocketIO( app )

state = "lobby"

class Player:
    def __init__( self, name, id ):
        self.name = name
        self.id = id
        self.team = None
        self.index = None

    def set_name( self, name ):
        self.name = name
        socketio.emit( "update-player", vars( self ) )

    def set_team( self, team, index = None ):
        self.team = team
        self.index = index if team else None
        socketio.emit( "update-player", vars( self ) )

    def to_json( self ):
        return json.dumps( self, default = vars )

null_player = Player( "null", 0 )

players = []
teams = {
    "legion": list( null_player for _ in range( 3 ) ),
    "hellbourne": list( null_player for _ in range( 3 ) ),
}

def get_other_team( team ):
    if team == legion: return hellbourne
    if team == hellbourne: return legion

def set_slot( team, index, player ):
    teams[ team ][ index ] = player
    socketio.emit( "update-slot", ( team, index, vars( player ) ) )

def reset_teams():
    for team in teams:
        for index in range( 3 ):
            set_slot( team, index, null_player )

class Hero:
    def __init__( self, name, icon ):
        self.name = name
        self.icon = icon

null_hero = Hero( "null", "h0" )
rikimaru = Hero( "Rikimaru", "heroes/14" )
blacksmith = Hero( "Blacksmith", "heroes/7" )
armadon = Hero( "Armadon", "heroes/2" )
heroes = {
    "agi": list( null_hero for _ in range( 8 ) ),
    "int": list( null_hero for _ in range( 8 ) ),
    "str": list( null_hero for _ in range( 8 ) ),
}

def set_hero( stat, index, hero ):
    heroes[ stat ][ index ] = hero
    socketio.emit( "update-hero", {
        "stat": stat,
        "index": index,
        "hero": vars( hero ) } )

def reset_heroes():
    for stat in heroes:
        for index in range( 8 ):
            set_hero( stat, index, null_hero )

def generate_heroes():
    for stat, hero in [ ( "agi", rikimaru ), ( "int", blacksmith ), ( "str", armadon ) ]:
        for index in range( 8 ):
            set_hero( stat, index, hero )

first_ban = teams[ "legion" ]
timer = None
banning_team = None
picking_players = []

def set_state( new_state ):
    global state
    state = new_state
    print( f"sending new state { state } to socket" )
    socketio.emit( "state-changed", state )

def set_timer( seconds, callback ):
    global timer
    timer = Timer( seconds, callback )
    socketio.emit( "set-timer", seconds )
    timer.start()

def start_draft():
    if state != "lobby":
        return

    reset_heroes()
    reset_players()
    set_state( "pool_countdown" )
    set_timer( 5, pool_countdown_timer )

    time_remaining = 5
    def announce_countdown():
        nonlocal time_remaining
        socketio.emit( "message", f"Draft starting in { time_remaining } seconds.." )
        time_remaining -= 1
        if time_remaining == 0: return
        Timer( 1, announce_countdown ).start()
    announce_countdown()

def pool_countdown_timer():
    generate_heroes()
    set_state( "banning_countdown" )
    set_timer( 10, banning_countdown_timer )

def banning_countdown_timer():
    global banning_team
    banning_team = first_ban
    set_state( "banning" )
    set_timer( 30, banning_timer )

def ban_hero( player, hero ):
    if state != "banning":
        return
    if player != banning_team[ 0 ]:
        return
    if hero.is_banned:
        return

    hero.is_banned = True
    timer.cancel()

    ban_count = (
            sum( hero.is_banned for hero in heroes[ "agi" ] )
          + sum( hero.is_banned for hero in heroes[ "int" ] )
          + sum( hero.is_banned for hero in heroes[ "str" ] )
        )

    if ban_count == 4:
        banning_team = None
        set_state( "picking_countdown" )
        set_timer( 10, picking_countdown_timer )
    else:
        banning_team = get_other_team( banning_team )
        set_timer( 30, banning_timer )

# make this more python
def get_available_heroes():
    available_heroes = {}
    for hero in heroes[ "agi" ]:
        if hero.is_banned:
            continue
        if hero.is_selected:
            continue
        available_heroes.append( hero )
    for hero in heroes[ "int" ]:
        if hero.is_banned:
            continue
        if hero.is_selected:
            continue
        available_heroes.append( hero )
    for hero in heroes[ "str" ]:
        if hero.is_banned:
            continue
        if hero.is_selected:
            continue
        available_heroes.append( hero )
    return available_heroes

def banning_timer():
    random_hero = random.choice( get_available_heroes )
    ban_hero( banning_team[ 0 ], random_hero )

def picking_countdown_timer():
    global picking_players
    picking_players = [ first_ban[ 0 ] ]
    set_state( "picking" )
    set_timer( 30, picking_timer )

def pick_hero( player, hero ):
    if state != "picking":
        return
    if player not in picking_players:
        return
    if player.has_picked:
        return
    if hero.is_banned:
        return
    if hero.is_selected:
        return

    player.hero = hero
    player.has_picked = True
    hero.is_selected = True

    # check if all picking players have picked a hero
    for player in picking_players:
        if not player.has_picked:
            return

    timer.cancel()
    picking_team = get_other_team( picking_players[ 0 ].team )
    picking_players = []
    for player in picking_team:
        if player.has_picked:
            continue
        picking_players.append( player )
        if len( picking_players ) == 2:
            break

    if not picking_players:
        set_state( "lobby" )
    else:
        set_timer( 30, picking_timer )

def picking_timer():
    for player in picking_players:
        if player.has_picked:
            continue
        random_hero = random.choice( get_available_heroes )
        pick_hero( player, random_hero )

@app.route( "/" )
def home():
    if "name" not in session:
        session[ "name" ] = "Unnamed Player"
    if "id" not in session:
        session[ "id" ] = uuid4().hex
    return render_template( "home.html",
        state = state,
        players = players,
        teams = teams,
        heroes = heroes
    )

def find_player():
    global players
    for player in players:
        if player.id == session[ "id" ]:
            return player

@socketio.on( "connect" )
def on_connect( auth ):
    global players
    print( "socket connected" )
    if find_player(): return
    player = Player( session[ "name" ], session[ "id" ] )
    players.append( player )
    socketio.emit( "add-player", vars( player ) )
    socketio.emit( "message", f"{ player.name } joined.", include_self = False )
    for other_player in players:
        if other_player == player: continue
        emit( "add-player", vars( other_player ) )
    emit( "message", "You joined." )

@socketio.on( "disconnect" )
def on_disconnect():
    global players
    print( "socket disconnected" )
    player = find_player()
    if not player: return
    players.remove( player )
    socketio.emit( "remove-player", player.id )
    socketio.emit( "message", f"{ player.name } left." )

@socketio.on( "start-draft" )
def on_start_draft():
    print( "received start draft request from socket" )
    start_draft()

@socketio.on( "click-slot" )
def click_slot( team, index ):
    if state != "lobby":
        return
    player = find_player()
    slot = teams[ team ][ index ]
    if slot == null_player:
        if player.team:
            set_slot( player.team, player.index, null_player )
        set_slot( team, index, player )
        player.set_team( team, index )
    elif slot == player:
        set_slot( team, index, null_player )
        player.set_team( None )
    else:
        return
    socketio.emit( "message", f"{ player.name } is now playing in { player.team } at position { player.index }."
        if player.team else f"{ player.name } is now an observer." )

@socketio.on( "click-hero" )
def click_hero( stat, index ):
    ...

@socketio.on( "right-click-hero" )
def right_click_hero( stat, index ):
    ...

@socketio.on( "message" )
def on_message( message ):
    print( "received message" )
    if message[:1] == "/":
        on_command( message[1:] )
        return
    player = find_player()
    socketio.emit( "message", f"{ player.name }: { message }" )

def on_command( message ):
    ( command, _, parameters ) = message.partition( " " )
    if command == "name":
        set_name( parameters )
        return
    print( "unrecognized command" )
    emit( "message", "unrecognized command" )

def set_name( name ):
    print( "received name change command" )
    # tell the client to make a request to set the cookie
    emit( "set-name", name )

@app.route( "/name", methods = [ "POST" ] )
def name():
    print( "name request" )
    player = find_player()
    name = request.form[ "name" ]
    old_name = player.name
    player.set_name( name )
    socketio.emit( "message", f"{ old_name } changed name to { player.name }" )
    session[ "name" ] = name
    return ""

if __name__ == "__main__":
    socketio.run( app, host = "localhost", port = 80, debug = True )
