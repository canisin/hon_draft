from flask import Flask, render_template
from flask_socketio import SocketIO

from threading import Thread
from threading import Timer
from time import sleep
from random import random

app = Flask( __name__ )
socketio = SocketIO( app )

state = "lobby"
players = []
legion = { "name": "legion" }
hellbourne = { "name": "hellbourne" }

def get_other_team( team ):
    if team == legion return hellbourne
    if team == hellbourne return legion

first_ban = legion
agi_heroes = []
int_heroes = []
str_heroes = []
timer = None
banning_team = None
picking_players = []

def set_state( new_state ):
    global state
    state = new_state
    print( f"sending new state {state} to socket" )
    socketio.emit( "state-changed", state )

def set_timer( seconds, callback )
    global timer
    timer = Timer( seconds, callback )
    socketio.emit( "set-timer", seconds )
    timer.start()

def push_data():
    socketio.emit( "players", players )
    socketio.emit( "legion", legion )
    socketio.emit( "hellbourne", hellbourne )
    socketio.emit( "agi-heroes", agi_heroes )
    socketio.emit( "int-heroes", int_heroes )
    socketio.emit( "str-heroes", str_heroes )

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

def reset_heroes():
    agi_heroes = []
    int_heroes = []
    str_heroes = []
    push_data()

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

def generate_pool():
    global agi_heroes, int_heroes, str_heroes
    agi_heroes = [
            { "name": "agi_hero_1" },
            { "name": "agi_hero_2" },
            { "name": "agi_hero_3" },
            { "name": "agi_hero_4" },
            { "name": "agi_hero_5" },
            { "name": "agi_hero_6" },
            { "name": "agi_hero_7" },
            { "name": "agi_hero_8" },
        ]
    int_heroes = [
            { "name": "int_hero_1" },
            { "name": "int_hero_2" },
            { "name": "int_hero_3" },
            { "name": "int_hero_4" },
            { "name": "int_hero_5" },
            { "name": "int_hero_6" },
            { "name": "int_hero_7" },
            { "name": "int_hero_8" },
        ]
    str_heroes = [
            { "name": "str_hero_1" },
            { "name": "str_hero_2" },
            { "name": "str_hero_3" },
            { "name": "str_hero_4" },
            { "name": "str_hero_5" },
            { "name": "str_hero_6" },
            { "name": "str_hero_7" },
            { "name": "str_hero_8" },
        ]
    push_data()

def pool_countdown_timer():
    generate_pool()
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
            sum( hero.is_banned for hero in agi_heroes )
          + sum( hero.is_banned for hero in int_heroes )
          + sum( hero.is_banned for hero in str_heroes )
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
    for hero in agi_heroes:
        if hero.is_banned:
            continue
        if hero.is_selected:
            continue
        available_heroes.append( hero )
    for hero in int_heroes:
        if hero.is_banned:
            continue
        if hero.is_selected:
            continue
        available_heroes.append( hero )
    for hero in str_heroes:
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

value = 0

def logic():
    print( "starting logic thread" )
    while True:
        sleep( 1 )
        update()

def update():
    global value
    value += 1

@app.route( "/" )
def home():
    return render_template( "home.html",
        state = state
    )

@app.route( "/test" )
def test():
    return render_template( "test.html" )

@socketio.on( "connect" )
def on_connect( auth ):
    print( "socket connected" )
    push_data()

@socketio.on( "disconnect" )
def on_disconnect():
    print( "socket disconnected" )

@socketio.on( "start-draft" )
def on_start_draft():
    print( "received start draft request from socket" )
    start_draft()


if __name__ == "__main__":
    # Thread( target = logic, daemon = True ).start()

    socketio.run( app, host = "localhost", port = 80, debug = True )
