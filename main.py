from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit

from threading import Thread
from threading import Timer
from time import sleep
import random
from uuid import uuid4
import json

pool_countdown_duration = 5
banning_countdown_duration = 5
banning_duration = 5
picking_duration = 5

app = Flask( __name__ )
app.secret_key = "honzor"
socketio = SocketIO( app )

state = "lobby"

class Hero:
    def __init__( self, name, icon ):
        self.name = name
        self.icon = icon
        self.is_banned = False

null_hero = Hero( "null", "/static/images/hero-none.png" )
null_hero_legion = Hero( "null", "/static/images/hero-legion.png" )
null_hero_hellbourne = Hero( "null", "/static/images/hero-hellbourne.png" )

class Player:
    def __init__( self, name, id ):
        self.name = name
        self.id = id
        self.set_team_impl( None )

    def set_team_impl( self, team, index = None ):
        self.team = team
        self.index = index if team else None
        self.icon = team.icon if team else "/static/images/observer.png"
        self.color = team.color if team else "blue"
        self.hero = team.null_hero if team else None

    def set_name( self, name ):
        self.name = name
        socketio.emit( "update-player", self.emit() )
        if self.team:
            socketio.emit( "update-slot", ( self.team.name, self.index, self.emit() ) )

    def set_team( self, team, index = None ):
        self.set_team_impl( team, index )
        socketio.emit( "update-player", self.emit() )

    def set_hero( self, hero ):
        self.hero = hero
        socketio.emit( "update-player", self.emit() )

    def reset_hero( self ):
        self.set_hero( self.team.null_hero if self.team else None )

    def to_json( self ):
        return json.dumps( self, default = vars )

    def emit( self ):
        return {
            "name": self.name,
            "id": self.id,
            "icon": self.icon,
            "color": self.color,
            "hero": vars( self.hero ) if self.hero else None,
        }

class Team:
    def __init__( self, name ):
        self.name = name
        self.icon = f"static/images/team-{ name }.png"
        self.color = "green" if name == "legion" else "red"
        self.null_hero = Hero( "null", f"/static/images/hero-{ name }.png" )
        self.null_player = Player( "null", None )
        self.null_player.set_team( self )
        self.players = list( self.null_player for _ in range( 3 ) )

    def set_slot( self, index, player ):
        self.players[ index ] = player
        socketio.emit( "update-slot", ( self.name, index, player.emit() ) )

    def reset_slot( self, index ):
        self.set_slot( index, self.null_player )

    def reset_slots( self ):
        for index in range( 3 ):
            self.reset_slot( index )

players = []

def reset_players():
    for player in players:
        player.reset_hero()

teams = {
    "legion": Team( "legion" ),
    "hellbourne": Team( "hellbourne" ),
}

def get_other_team( team ):
    if team == teams[ "legion" ]: return teams[ "hellbourne" ]
    if team == teams[ "hellbourne" ]: return teams[ "legion" ]

rikimaru = Hero( "Rikimaru", "/static/images/heroes/hantumon.png" )
blacksmith = Hero( "Blacksmith", "/static/images/heroes/dwarf_magi.png" )
armadon = Hero( "Armadon", "/static/images/heroes/armadon.png" )

heroes = {
    "agi": list( null_hero for _ in range( 8 ) ),
    "int": list( null_hero for _ in range( 8 ) ),
    "str": list( null_hero for _ in range( 8 ) ),
}

def set_hero( stat, index, hero ):
    heroes[ stat ][ index ] = hero
    socketio.emit( "update-hero", ( stat, index, vars( hero ) ) )

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
    set_timer( pool_countdown_duration, pool_countdown_timer )

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
    set_timer( banning_countdown_duration, banning_countdown_timer )

def banning_countdown_timer():
    global banning_team
    banning_team = first_ban
    set_state( "banning" )
    set_timer( banning_duration, banning_timer )

def ban_hero( player, stat, index ):
    if state != "banning":
        return

    global banning_team
    if player and player not in banning_team.players:
        return

    hero = heroes[ stat ][ index ]
    if hero.is_banned:
        return

    hero.is_banned = True
    socketio.emit( "update-hero", ( stat, index, vars( hero ) ) )
    socketio.emit( "message", f"{ player.name if player else "Fate" } has banned { hero.name }" )

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
        set_timer( banning_duration, banning_timer )

def get_available_heroes():
    available_heroes = []
    for stat, stat_heroes in heroes.items():
        for index, hero in enumerate( stat_heroes ):
            if hero.is_banned:
                continue
            available_heroes.append( ( stat, index ) )
    return available_heroes

def banning_timer():
    stat, index = random.choice( get_available_heroes() )
    ban_hero( None, stat, index )

def picking_countdown_timer():
    global picking_players
    picking_players = [ first_ban[ 0 ] ]
    set_state( "picking" )
    set_timer( picking_duration, picking_timer )

def pick_hero( player, stat, index ):
    if state != "picking":
        return

    global picking_players
    if player not in picking_players:
        return
    if player.has_picked:
        return

    hero = heroes[ stat ][ index ]
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

    global picking_team
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
        set_timer( picking_duration, picking_timer )

def picking_timer():
    for player in picking_players:
        if player.has_picked:
            continue
        stat, index = random.choice( get_available_heroes() )
        pick_hero( player, stat, index )

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
    socketio.emit( "add-player", player.emit() )
    socketio.emit( "message", f"{ player.name } joined.", include_self = False )
    for other_player in players:
        if other_player == player: continue
        emit( "add-player", other_player.emit() )
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
    team = teams[ team ]
    slot = team.players[ index ]
    if slot == team.null_player:
        if player.team:
            player.team.reset_slot( player.index )
        player.set_team( team, index )
        team.set_slot( index, player )
    elif slot == player:
        team.reset_slot( index )
        player.set_team( None )
    else:
        return
    socketio.emit( "message", f"{ player.name } is now playing in { player.team.name } at position { player.index }."
        if player.team else f"{ player.name } is now an observer." )

@socketio.on( "click-hero" )
def click_hero( stat, index ):
    player = find_player()
    if state == "banning":
        ban_hero( player, stat, index )

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
