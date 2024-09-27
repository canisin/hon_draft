from flask import Flask
from flask_socketio import SocketIO

from threading import Thread
from threading import Timer
from time import sleep

app = Flask( __name__ )
socketio = SocketIO( app )

state = "lobby"
players = {}
legion = {}
hellbourne = {}
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
    agi_heroes = { "agi_hero_1", "agi_hero_2", "agi_hero_3", "agi_hero_4"
                   "agi_hero_5", "agi_hero_6", "agi_hero_7", "agi_hero_8" }
    int_heroes = { "int_hero_1", "int_hero_2", "int_hero_3", "int_hero_4"
                   "int_hero_5", "int_hero_6", "int_hero_7", "int_hero_8" }
    str_heroes = { "str_hero_1", "str_hero_2", "str_hero_3", "str_hero_4"
                   "str_hero_5", "str_hero_6", "str_hero_7", "str_hero_8" }

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

    hero.is_banned = True
    timer.cancel()

    ban_count = 0
    for hero in agi_heroes:
        if hero.is_banned:
            ban_count += 1
    for hero in int_heroes:
        if hero.is_banned:
            ban_count += 1
    for hero in str_heroes:
        if hero.is_banned:
            ban_count += 1

    if ban_count == 4:
        banning_team = None
        state = "picking_countdown"
        timer = Timer( 10, picking_countdown_timer )
        timer.start()
    else:
        banning_team = !banning_team
        timer = Timer( 30, banning_timer )
        timer.start()

def banning_timer():
    ban_hero( banning_team[ 0 ], random_hero )

def picking_countdown_timer():
    picking_players = { first_ban[ 0 ] }
    state = "picking"
    timer = Timer( 30, picking_timer )
    timer.start()

def pick_hero( player, hero ):
    if state != "picking"
        return
    if player not in picking_players:
        return
    if player.has_picked:
        return

    player.hero = hero
    player.has_picked = True

    # check if all picking players have picked a hero
    for player in picking_players:
        if !player.has_picked:
            return

    timer.cancel()
    picking_team = !picking_players[ 0 ].team
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
    return f"Hello world! { state[ "value" ] }"

if __name__ == "__main__":
    Thread( target = logic, daemon = True ).start()

    socketio.run( app, host = "localhost", port = 80 )
