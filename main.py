from flask import Flask, render_template, session
from flask_socketio import SocketIO

from threading import Thread
from threading import Timer
from time import sleep
from random import random

app = Flask( __name__ )
app.secret_key = "honzor"
socketio = SocketIO( app )

state = "lobby"
players = []
legion = []
hellbourne = []

def get_other_team( team ):
    if team == legion: return hellbourne
    if team == hellbourne: return legion

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
    for stat in [ "agi", "int", "str" ]:
        for index in range( 8 ):
            set_hero( stat, index, null_hero )

def generate_heroes():
    for stat, hero in [ ( "agi", rikimaru ), ( "int", blacksmith ), ( "str", armadon ) ]:
        for index in range( 8 ):
            set_hero( stat, index, hero )

first_ban = legion
timer = None
banning_team = None
picking_players = []

def set_state( new_state ):
    global state
    state = new_state
    print( f"sending new state {state} to socket" )
    socketio.emit( "state-changed", state )

def set_timer( seconds, callback ):
    global timer
    timer = Timer( seconds, callback )
    socketio.emit( "set-timer", seconds )
    timer.start()

def push_data():
    socketio.emit( "players", players )
    socketio.emit( "legion", legion )
    socketio.emit( "hellbourne", hellbourne )

def select_team( player, team ):
    if player.team != None:
        player.team.remove( player )
    player.team = team
    if team != None:
        team.append( player )

def right_click( player, hero ):
    if player.has_picked:
        return
    player.hero = hero

def reset_players():
    for player in players:
        player.has_picked = False
        player.hero = None
    push_data()

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
    push_data()

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
    push_data()

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
    if "player" not in session:
        session[ "player" ] = "Unnamed Player"
    return render_template( "home.html",
        state = state,
        legion = legion,
        hellbourne = hellbourne,
        heroes = heroes
    )

@app.route( "/test" )
def test():
    return render_template( "test.html" )

@socketio.on( "connect" )
def on_connect( auth ):
    print( "socket connected" )
    player = session[ "player" ]
    socketio.emit( "message", f"{ player } joined." )

@socketio.on( "disconnect" )
def on_disconnect():
    print( "socket disconnected" )
    player = session[ "player" ]
    socketio.emit( "message", f"{ player } left." )

@socketio.on( "start-draft" )
def on_start_draft():
    print( "received start draft request from socket" )
    start_draft()


if __name__ == "__main__":
    socketio.run( app, host = "localhost", port = 80, debug = True )
