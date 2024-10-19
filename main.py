from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit

from threading import Thread
from threading import Timer
from time import sleep
import random
from uuid import uuid4
from dotenv import load_dotenv
from os import getenv
from os import popen

load_dotenv()

pool_countdown_duration = 5
banning_countdown_duration = 5
banning_duration = 5
picking_countdown_duration = 5
picking_duration = 5

ban_count = 4
initial_pick_count = 1
later_pick_count = 2
remaining_picks = 0

revision = popen( "git rev-list --count HEAD" ).read().strip()
sha = popen( "git rev-parse --short HEAD" ).read().strip()

app = Flask( __name__ )
app.secret_key = "honzor"
socketio = SocketIO( app )

state = "lobby"

def emit_icon( icon ):
    return f"/static/images/{ icon }.png"

class Hero:
    def __init__( self, name, icon ):
        self.name = name
        self.icon = icon
        self.is_banned = False

    def emit( self ):
        return {
            "name": self.name,
            "icon": emit_icon( self.icon ),
            "is_banned": self.is_banned,
        }

null_hero = Hero( "null", "hero-none" )

class Player:
    def __init__( self, name, id ):
        self.name = name
        self.id = id
        self.hero = None
        self.team = None
        self.index = None

    def set_name( self, name ):
        self.name = name
        socketio.emit( "update-player", self.emit() )
        if self.team:
            socketio.emit( "update-slot", ( self.team.name, self.index, self.emit() ) )

    def set_team( self, team, index = None ):
        if self.team:
            socketio.emit( "update-slot", ( self.team.name, self.index, self.team.emit_null_player() ) )

        self.team = team
        self.index = index if team else None
        socketio.emit( "update-player", self.emit() )

        if self.team:
            socketio.emit( "update-slot", ( self.team.name, self.index, self.emit() ) )

    def set_hero( self, hero ):
        self.hero = hero
        socketio.emit( "update-player", self.emit() )
        if self.team:
            socketio.emit( "update-slot", ( self.team.name, self.index, self.emit() ) )

    def reset_hero( self ):
        self.set_hero( None )

    def emit( self ):
        return {
            "name": self.name,
            "id": self.id,
            "hero": self.hero.emit() if self.hero
                else self.team.emit_null_hero() if self.team
                else null_hero.emit(),
            "team": self.team.emit( without_players = True ) if self.team else observer_team.emit(),
        }

class Team:
    def __init__( self, name, icon, color ):
        self.name = name
        self.icon = icon
        self.color = color
        self.players = []

    def add_player( self, player ):
        self.players.append( player )

    def remove_player( self, player ):
        self.players.remove( player )

    def remove_players( self ):
        self.players = []

    def picking_players( self ):
        return ( player for player in self.players if not player.hero )

    def emit_null_hero( self ):
        return Hero( "null", f"hero-{ self.name }" ).emit()

    def emit_null_player( self ):
        return {
            "name": "null",
            "hero": self.emit_null_hero(),
            "team": self.emit( without_players = True ),
        }

    def emit( self, without_players = False ):
        return {
            "name": self.name,
            "icon": emit_icon( self.icon ),
            "color": self.color,
            "players": None if without_players else
                [ next( ( player.emit() for player in self.players if player.index == index ),
                    self.emit_null_player() ) for index in range( 3 ) ]
        }

players = []

def reset_players():
    for player in players:
        player.reset_hero()

observer_team = Team( "observers", "observer", "blue" )
teams = {
    "legion": Team( "legion", "team-legion", "green" ),
    "hellbourne": Team( "hellbourne", "team-hellbourne", "red" ),
}

def get_other_team( team ):
    if team == teams[ "legion" ]: return teams[ "hellbourne" ]
    if team == teams[ "hellbourne" ]: return teams[ "legion" ]

all_heroes = {
    "agi": [
        Hero( "Emerald Warden", "emerald_warden" ),
        Hero( "Moon Queen", "krixi" ),
        Hero( "Andromeda", "andromeda" ),
        Hero( "Artillery", "artillery" ),
        Hero( "Blitz", "blitz" ),
        Hero( "Night Hound", "hantumon" ),
        Hero( "Swiftblade", "hiro" ),
        Hero( "Master Of Arms", "master_of_arms" ),
        Hero( "Moira", "moira" ),
        Hero( "Monkey King", "monkey_king" ),
        Hero( "Nitro", "nitro" ),
        Hero( "Nomad", "nomad" ),
        Hero( "Sapphire", "sapphire" ),
        Hero( "Scout", "scout" ),
        Hero( "Silhouette", "silhouette" ),
        Hero( "Sir Benzington", "sir_benzington" ),
        Hero( "Tarot", "tarot" ),
        Hero( "Valkyrie", "valkyrie" ),
        Hero( "Wildsoul", "yogi" ),
        Hero( "Zephyr", "zephyr" ),
        Hero( "Arachna", "arachna" ),
        Hero( "Blood Hunter", "hunter" ),
        Hero( "Bushwack", "bushwack" ),
        Hero( "Chronos", "chronos" ),
        Hero( "Dampeer", "dampeer" ),
        Hero( "Flint Beastwood", "flint_beastwood" ),
        Hero( "Forsaken Archer", "forsaken_archer" ),
        Hero( "Grinex", "grinex" ),
        Hero( "Gunblade", "gunblade" ),
        Hero( "Shadowblade", "shadowblade" ),
        Hero( "Calamity", "calamity" ),
        Hero( "Corrupted Disciple", "corrupted_disciple" ),
        Hero( "Slither", "ebulus" ),
        Hero( "Gemini", "gemini" ),
        Hero( "Klanx", "klanx" ),
        Hero( "Riptide", "riptide" ),
        Hero( "Sand Wraith", "sand_wraith" ),
        Hero( "The Madman", "scar" ),
        Hero( "Soulstealer", "soulstealer" ),
        Hero( "Tremble", "tremble" ),
        Hero( "The Dark Lady", "vanya" ),
    ],
    "int": [
        Hero( "Aluna", "aluna" ),
        Hero( "Blacksmith", "dwarf_magi" ),
        Hero( "Bombardier", "bomb" ),
        Hero( "Ellonia", "ellonia" ),
        Hero( "Engineer", "engineer" ),
        Hero( "Midas", "midas" ),
        Hero( "Pyromancer", "pyromancer" ),
        Hero( "Rhapsody", "rhapsody" ),
        Hero( "Witch Slayer", "witch_slayer" ),
        Hero( "Bubbles", "bubbles" ),
        Hero( "Qi", "chi" ),
        Hero( "The Chipper", "chipper" ),
        Hero( "Empath", "empath" ),
        Hero( "Nymphora", "fairy" ),
        Hero( "Kinesis", "kenisis" ),
        Hero( "Thunderbringer", "kunas" ),
        Hero( "Martyr", "martyr" ),
        Hero( "Monarch", "monarch" ),
        Hero( "Oogie", "oogie" ),
        Hero( "Ophelia", "ophelia" ),
        Hero( "Pearl", "pearl" ),
        Hero( "Pollywog Priest", "pollywogpriest" ),
        Hero( "Skrap", "skrap" ),
        Hero( "Tempest", "tempest" ),
        Hero( "Vindicator", "vindicator" ),
        Hero( "Warchief", "warchief" ),
        Hero( "Defiler", "defiler" ),
        Hero( "Demented Shaman", "shaman" ),
        Hero( "Doctor Repulsor", "doctor_repulsor" ),
        Hero( "Glacius", "frosty" ),
        Hero( "Gravekeeper", "taint" ),
        Hero( "Myrmidon", "hydromancer" ),
        Hero( "Parasite", "parasite" ),
        Hero( "Plague Rider", "diseasedrider" ),
        Hero( "Revenant", "revenant" ),
        Hero( "Soul Reaper", "helldemon" ),
        Hero( "Succubus", "succubis" ),
        Hero( "Wretched Hag", "babayaga" ),
        Hero( "Artesia", "artesia" ),
        Hero( "Circe", "circe" ),
        Hero( "Fayde", "fade" ),
        Hero( "Geomancer", "geomancer" ),
        Hero( "Goldenveil", "goldenveil" ),
        Hero( "Hellbringer", "hellbringer" ),
        Hero( "Parallax", "parallax" ),
        Hero( "Prophet", "prophet" ),
        Hero( "Puppet Master", "puppetmaster" ),
        Hero( "Riftwalker", "riftmage" ),
        Hero( "Voodoo Jester", "voodoo" ),
        Hero( "Torturer", "xalynx" ),
    ],
    "str": [
        Hero( "Armadon", "armadon" ),
        Hero( "Hammerstorm", "hammerstorm" ),
        Hero( "Legionnaire", "legionnaire" ),
        Hero( "Magebane", "javaras" ),
        Hero( "Pandamonium", "panda" ),
        Hero( "Predator", "predator" ),
        Hero( "Prisoner 945", "prisoner" ),
        Hero( "Rally", "rally" ),
        Hero( "Behemoth", "behemoth" ),
        Hero( "Berzerker", "berzerker" ),
        Hero( "Drunken Master", "drunkenmaster" ),
        Hero( "Flux", "flux" ),
        Hero( "The Gladiator", "gladiator" ),
        Hero( "Ichor", "ichor" ),
        Hero( "Jeraziah", "jereziah" ),
        Hero( "Xemplar", "mimix" ),
        Hero( "Bramble", "plant" ),
        Hero( "Rampage", "rampage" ),
        Hero( "Pebbles", "rocky" ),
        Hero( "Salomon", "salomon" ),
        Hero( "Shellshock", "shellshock" ),
        Hero( "Solstice", "solstice" ),
        Hero( "Keeper of the Forest", "treant" ),
        Hero( "Tundra", "tundra" ),
        Hero( "Balphagore", "bephelgor" ),
        Hero( "Magmus", "magmar" ),
        Hero( "Maliken", "maliken" ),
        Hero( "Ravenor", "ravenor" ),
        Hero( "Amun-Ra", "ra" ),
        Hero( "Accursed", "accursed" ),
        Hero( "Adrenaline", "adrenaline" ),
        Hero( "Apex", "apex" ),
        Hero( "Cthulhuphant", "cthulhuphant" ),
        Hero( "Deadlift", "deadlift" ),
        Hero( "Deadwood", "deadwood" ),
        Hero( "Devourer", "devourer" ),
        Hero( "Lord Salforis", "dreadknight" ),
        Hero( "Electrician", "electrician" ),
        Hero( "Draconis", "flamedragon" ),
        Hero( "Gauntlet", "gauntlet" ),
        Hero( "Kane", "kane" ),
        Hero( "King Klout", "king_klout" ),
        Hero( "Kraken", "kraken" ),
        Hero( "Lodestone", "lodestone" ),
        Hero( "Moraxus", "moraxus" ),
        Hero( "Pharaoh", "mumra" ),
        Hero( "Pestilence", "pestilence" ),
        Hero( "War Beast", "wolfman" ),
    ],
}

heroes = {
    "agi": list( null_hero for _ in range( 8 ) ),
    "int": list( null_hero for _ in range( 8 ) ),
    "str": list( null_hero for _ in range( 8 ) ),
}

def set_hero( stat, index, hero ):
    heroes[ stat ][ index ] = hero
    socketio.emit( "update-hero", ( stat, index, hero.emit() ) )

def reset_heroes():
    for stat in heroes:
        for index in range( 8 ):
            set_hero( stat, index, null_hero )

def generate_heroes():
    for stat in heroes:
        for index, hero in enumerate( random.sample( all_heroes[ stat ], 8 ) ):
            set_hero( stat, index, hero )

first_ban = teams[ "legion" ]
timer = None
active_team = None

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
    global active_team
    active_team = first_ban
    set_state( "banning" )
    set_timer( banning_duration, banning_timer )

def ban_hero( player, stat, index ):
    if state != "banning":
        return

    global active_team
    if player and player.team != active_team:
        return

    hero = heroes[ stat ][ index ]
    if hero.is_banned:
        return

    hero.is_banned = True
    socketio.emit( "update-hero", ( stat, index, hero.emit() ) )
    socketio.emit( "message", f"{ player.name if player else "Fate" } has banned { hero.name }" )

    timer.cancel()

    current_ban_count = sum( 1 for stat in heroes for hero in heroes[ stat ] if hero.is_banned )
    if current_ban_count == ban_count:
        active_team = None
        set_state( "picking_countdown" )
        set_timer( picking_countdown_duration, picking_countdown_timer )
    else:
        active_team = get_other_team( active_team )
        set_timer( banning_duration, banning_timer )

def get_available_heroes():
    available_heroes = []
    for stat, stat_heroes in heroes.items():
        for index, hero in enumerate( stat_heroes ):
            if hero == null_hero:
                continue
            if hero.is_banned:
                continue
            available_heroes.append( ( stat, index ) )
    return available_heroes

def banning_timer():
    stat, index = random.choice( get_available_heroes() )
    ban_hero( None, stat, index )

def start_picking( pick_count ):
    global active_team
    global remaining_picks
    remaining_picks = min(
        pick_count,
        sum( 1 for player in active_team.picking_players() )
    )
    print( f"{ remaining_picks = }" )

    if remaining_picks == 0:
        active_team = None
        set_state( "lobby" )
        return

    set_timer( picking_duration, picking_timer )

def picking_countdown_timer():
    global active_team
    active_team = first_ban
    set_state( "picking" )
    start_picking( initial_pick_count )

def pick_hero( player, stat, index ):
    if state != "picking":
        return

    global active_team
    if player.team != active_team:
        return
    if player.has_picked():
        return

    hero = heroes[ stat ][ index ]
    if hero == null_hero:
        return
    if hero.is_banned:
        return

    player.set_hero( hero )
    set_hero( stat, index, null_hero )

    global remaining_picks
    remaining_picks -= 1
    if remaining_picks > 0:
        return

    timer.cancel()

    active_team = get_other_team( active_team )
    start_picking( later_pick_count )

def picking_timer():
    while remaining_picks > 0:
        player = next( player for player in active_team.picking_players() )
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
        players = [ player.emit() for player in players ],
        teams = { team: teams[ team ].emit() for team in teams },
        heroes = { stat: [ hero.emit() for hero in heroes[ stat ] ] for stat in heroes },
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
    emit( "message", f"Welcome to HoNDraft [.{revision}-{sha}]" )
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
    slot_player = next( ( player for player in team.players if player.index == index ), None )
    if not slot_player:
        if player.team:
            player.team.remove_player( player )
        player.set_team( team, index )
        team.add_player( player )
    elif slot_player == player:
        team.remove_player( player )
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
    elif state == "picking":
        pick_hero( player, stat, index )

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
    host = getenv( "HOST" ) or "0.0.0.0"
    port = getenv( "PORT" ) or None
    debug = getenv( "DEBUG" ) or False
    socketio.run( app, allow_unsafe_werkzeug = True, host = host, port = port, debug = debug )
