from flask import Flask, render_template
from flask_socketio import SocketIO

from threading import Thread
from threading import Timer
from time import sleep
from random import random

app = Flask( __name__ )
socketio = SocketIO( app )

state = "lobby"
players = {}
legion = { "name": "legion" }
hellbourne = { "name": "hellbourne" }
legion["other"] = hellbourne
hellbourne["other"] = legion
first_ban = legion
agi_heroes = {}
int_heroes = {}
str_heroes = {}
timer = None
banning_team = None
picking_players = {}

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
    agi_heroes = {}
    int_heroes = {}
    str_heroes = {}

def reset_players():
    for player in players:
        player.has_picked = False
        player.hero = None

def start_draft():
    if state != "lobby":
        return

    reset_heroes()
    reset_players()
    state = "pool_countdown"
    timer = Timer( 5, pool_countdown_timer )
    timer.start()

def generate_pool():
    agi_heroes = {
            { "name": "agi_hero_1" },
            { "name": "agi_hero_2" },
            { "name": "agi_hero_3" },
            { "name": "agi_hero_4" },
            { "name": "agi_hero_5" },
            { "name": "agi_hero_6" },
            { "name": "agi_hero_7" },
            { "name": "agi_hero_8" },
        }
    int_heroes = {
            { "name": "int_hero_1" },
            { "name": "int_hero_2" },
            { "name": "int_hero_3" },
            { "name": "int_hero_4" },
            { "name": "int_hero_5" },
            { "name": "int_hero_6" },
            { "name": "int_hero_7" },
            { "name": "int_hero_8" },
        }
    str_heroes = {
            { "name": "str_hero_1" },
            { "name": "str_hero_2" },
            { "name": "str_hero_3" },
            { "name": "str_hero_4" },
            { "name": "str_hero_5" },
            { "name": "str_hero_6" },
            { "name": "str_hero_7" },
            { "name": "str_hero_8" },
        }

def pool_countdown_timer():
    generate_pool()
    state = "banning_countdown"
    timer = Timer( 10, banning_countdown_timer )
    timer.start()

def banning_countdown_timer():
    banning_team = first_ban
    state = "banning"
    timer = Timer( 30, banning_timer )
    timer.start()

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
            sum( hero.is_banned for hero in agi_heroes )
          + sum( hero.is_banned for hero in int_heroes )
          + sum( hero.is_banned for hero in str_heroes )
        )

    if ban_count == 4:
        banning_team = None
        state = "picking_countdown"
        timer = Timer( 10, picking_countdown_timer )
        timer.start()
    else:
        banning_team = banning_team.other
        timer = Timer( 30, banning_timer )
        timer.start()

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
    picking_players = { first_ban[ 0 ] }
    state = "picking"
    timer = Timer( 30, picking_timer )
    timer.start()

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
    picking_team = picking_players[ 0 ].team.other
    picking_players = {}
    for player in picking_team:
        if player.has_picked:
            continue
        picking_players.append( player )
        if len( picking_players ) == 2:
            break

    if not picking_players:
        state = lobby
    else:
        timer = Timer( 30, picking_timer )
        timer.start()

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

if __name__ == "__main__":
    Thread( target = logic, daemon = True ).start()

    socketio.run( app, host = "localhost", port = 80 )
