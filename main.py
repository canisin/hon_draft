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

team_size = 3
pool_size = 8

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
        self.is_picked = False

    def reset( self ):
        self.is_banned = False
        self.is_picked = False

    def is_available( self ):
        return not self.is_banned and not self.is_picked

    def emit( self ):
        if self.is_picked: emit_null()
        return {
            "name": self.name,
            "icon": emit_icon( self.icon ),
            "is_banned": self.is_banned,
        }

    def emit_null():
        return {
            "name": "null",
            "icon": emit_icon( "hero-none" ),
            "is_banned": False,
        }

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
                else Hero.emit_null(),
            "team": self.team.emit() if self.team else Teams.emit_observer(),
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

    def get_other( self ):
        return Teams.get_other( self )

    def emit_null_hero( self ):
        return Hero( "null", f"hero-{ self.name }" ).emit()

    def emit_null_player( self ):
        return {
            "name": "null",
            "hero": self.emit_null_hero(),
            "team": self.emit(),
        }

    def emit( self, with_players = False ):
        return {
            "name": self.name,
            "icon": emit_icon( self.icon ),
            "color": self.color,
            "players": None if not with_players else
                [ next( ( player.emit() for player in self.players if player.index == index ),
                    self.emit_null_player() ) for index in range( team_size ) ]
        }

players = []

def reset_players():
    for player in players:
        player.reset_hero()

class Teams:
    legion = Team( "legion", "team-legion", "green" )
    hellbourne = Team( "hellbourne", "team-hellbourne", "red" )

    def get( team ):
        if team == "legion": return Teams.legion
        if team == "hellbourne": return Teams.hellbourne

    def get_other( team ):
        if team == Teams.legion: return Teams.hellbourne
        if team == Teams.hellbourne: return Teams.legion

    def emit():
        return {
            "legion": Teams.legion.emit( with_players = True ),
            "hellbourne": Teams.hellbourne.emit( with_players = True ),
        }

    def emit_observer():
        return Team( "observers", "observer", "blue" ).emit()

all_heroes = {
    "agi": [
        Hero( "Emerald Warden", "heroes/emerald_warden" ),
        Hero( "Moon Queen", "heroes/krixi" ),
        Hero( "Andromeda", "heroes/andromeda" ),
        Hero( "Artillery", "heroes/artillery" ),
        Hero( "Blitz", "heroes/blitz" ),
        Hero( "Night Hound", "heroes/hantumon" ),
        Hero( "Swiftblade", "heroes/hiro" ),
        Hero( "Master Of Arms", "heroes/master_of_arms" ),
        Hero( "Moira", "heroes/moira" ),
        Hero( "Monkey King", "heroes/monkey_king" ),
        Hero( "Nitro", "heroes/nitro" ),
        Hero( "Nomad", "heroes/nomad" ),
        Hero( "Sapphire", "heroes/sapphire" ),
        Hero( "Scout", "heroes/scout" ),
        Hero( "Silhouette", "heroes/silhouette" ),
        Hero( "Sir Benzington", "heroes/sir_benzington" ),
        Hero( "Tarot", "heroes/tarot" ),
        Hero( "Valkyrie", "heroes/valkyrie" ),
        Hero( "Wildsoul", "heroes/yogi" ),
        Hero( "Zephyr", "heroes/zephyr" ),
        Hero( "Arachna", "heroes/arachna" ),
        Hero( "Blood Hunter", "heroes/hunter" ),
        Hero( "Bushwack", "heroes/bushwack" ),
        Hero( "Chronos", "heroes/chronos" ),
        Hero( "Dampeer", "heroes/dampeer" ),
        Hero( "Flint Beastwood", "heroes/flint_beastwood" ),
        Hero( "Forsaken Archer", "heroes/forsaken_archer" ),
        Hero( "Grinex", "heroes/grinex" ),
        Hero( "Gunblade", "heroes/gunblade" ),
        Hero( "Shadowblade", "heroes/shadowblade" ),
        Hero( "Calamity", "heroes/calamity" ),
        Hero( "Corrupted Disciple", "heroes/corrupted_disciple" ),
        Hero( "Slither", "heroes/ebulus" ),
        Hero( "Gemini", "heroes/gemini" ),
        Hero( "Klanx", "heroes/klanx" ),
        Hero( "Riptide", "heroes/riptide" ),
        Hero( "Sand Wraith", "heroes/sand_wraith" ),
        Hero( "The Madman", "heroes/scar" ),
        Hero( "Soulstealer", "heroes/soulstealer" ),
        Hero( "Tremble", "heroes/tremble" ),
        Hero( "The Dark Lady", "heroes/vanya" ),
    ],
    "int": [
        Hero( "Aluna", "heroes/aluna" ),
        Hero( "Blacksmith", "heroes/dwarf_magi" ),
        Hero( "Bombardier", "heroes/bomb" ),
        Hero( "Ellonia", "heroes/ellonia" ),
        Hero( "Engineer", "heroes/engineer" ),
        Hero( "Midas", "heroes/midas" ),
        Hero( "Pyromancer", "heroes/pyromancer" ),
        Hero( "Rhapsody", "heroes/rhapsody" ),
        Hero( "Witch Slayer", "heroes/witch_slayer" ),
        Hero( "Bubbles", "heroes/bubbles" ),
        Hero( "Qi", "heroes/chi" ),
        Hero( "The Chipper", "heroes/chipper" ),
        Hero( "Empath", "heroes/empath" ),
        Hero( "Nymphora", "heroes/fairy" ),
        Hero( "Kinesis", "heroes/kenisis" ),
        Hero( "Thunderbringer", "heroes/kunas" ),
        Hero( "Martyr", "heroes/martyr" ),
        Hero( "Monarch", "heroes/monarch" ),
        Hero( "Oogie", "heroes/oogie" ),
        Hero( "Ophelia", "heroes/ophelia" ),
        Hero( "Pearl", "heroes/pearl" ),
        Hero( "Pollywog Priest", "heroes/pollywogpriest" ),
        Hero( "Skrap", "heroes/skrap" ),
        Hero( "Tempest", "heroes/tempest" ),
        Hero( "Vindicator", "heroes/vindicator" ),
        Hero( "Warchief", "heroes/warchief" ),
        Hero( "Defiler", "heroes/defiler" ),
        Hero( "Demented Shaman", "heroes/shaman" ),
        Hero( "Doctor Repulsor", "heroes/doctor_repulsor" ),
        Hero( "Glacius", "heroes/frosty" ),
        Hero( "Gravekeeper", "heroes/taint" ),
        Hero( "Myrmidon", "heroes/hydromancer" ),
        Hero( "Parasite", "heroes/parasite" ),
        Hero( "Plague Rider", "heroes/diseasedrider" ),
        Hero( "Revenant", "heroes/revenant" ),
        Hero( "Soul Reaper", "heroes/helldemon" ),
        Hero( "Succubus", "heroes/succubis" ),
        Hero( "Wretched Hag", "heroes/babayaga" ),
        Hero( "Artesia", "heroes/artesia" ),
        Hero( "Circe", "heroes/circe" ),
        Hero( "Fayde", "heroes/fade" ),
        Hero( "Geomancer", "heroes/geomancer" ),
        Hero( "Goldenveil", "heroes/goldenveil" ),
        Hero( "Hellbringer", "heroes/hellbringer" ),
        Hero( "Parallax", "heroes/parallax" ),
        Hero( "Prophet", "heroes/prophet" ),
        Hero( "Puppet Master", "heroes/puppetmaster" ),
        Hero( "Riftwalker", "heroes/riftmage" ),
        Hero( "Voodoo Jester", "heroes/voodoo" ),
        Hero( "Torturer", "heroes/xalynx" ),
    ],
    "str": [
        Hero( "Armadon", "heroes/armadon" ),
        Hero( "Hammerstorm", "heroes/hammerstorm" ),
        Hero( "Legionnaire", "heroes/legionnaire" ),
        Hero( "Magebane", "heroes/javaras" ),
        Hero( "Pandamonium", "heroes/panda" ),
        Hero( "Predator", "heroes/predator" ),
        Hero( "Prisoner 945", "heroes/prisoner" ),
        Hero( "Rally", "heroes/rally" ),
        Hero( "Behemoth", "heroes/behemoth" ),
        Hero( "Berzerker", "heroes/berzerker" ),
        Hero( "Drunken Master", "heroes/drunkenmaster" ),
        Hero( "Flux", "heroes/flux" ),
        Hero( "The Gladiator", "heroes/gladiator" ),
        Hero( "Ichor", "heroes/ichor" ),
        Hero( "Jeraziah", "heroes/jereziah" ),
        Hero( "Xemplar", "heroes/mimix" ),
        Hero( "Bramble", "heroes/plant" ),
        Hero( "Rampage", "heroes/rampage" ),
        Hero( "Pebbles", "heroes/rocky" ),
        Hero( "Salomon", "heroes/salomon" ),
        Hero( "Shellshock", "heroes/shellshock" ),
        Hero( "Solstice", "heroes/solstice" ),
        Hero( "Keeper of the Forest", "heroes/treant" ),
        Hero( "Tundra", "heroes/tundra" ),
        Hero( "Balphagore", "heroes/bephelgor" ),
        Hero( "Magmus", "heroes/magmar" ),
        Hero( "Maliken", "heroes/maliken" ),
        Hero( "Ravenor", "heroes/ravenor" ),
        Hero( "Amun-Ra", "heroes/ra" ),
        Hero( "Accursed", "heroes/accursed" ),
        Hero( "Adrenaline", "heroes/adrenaline" ),
        Hero( "Apex", "heroes/apex" ),
        Hero( "Cthulhuphant", "heroes/cthulhuphant" ),
        Hero( "Deadlift", "heroes/deadlift" ),
        Hero( "Deadwood", "heroes/deadwood" ),
        Hero( "Devourer", "heroes/devourer" ),
        Hero( "Lord Salforis", "heroes/dreadknight" ),
        Hero( "Electrician", "heroes/electrician" ),
        Hero( "Draconis", "heroes/flamedragon" ),
        Hero( "Gauntlet", "heroes/gauntlet" ),
        Hero( "Kane", "heroes/kane" ),
        Hero( "King Klout", "heroes/king_klout" ),
        Hero( "Kraken", "heroes/kraken" ),
        Hero( "Lodestone", "heroes/lodestone" ),
        Hero( "Moraxus", "heroes/moraxus" ),
        Hero( "Pharaoh", "heroes/mumra" ),
        Hero( "Pestilence", "heroes/pestilence" ),
        Hero( "War Beast", "heroes/wolfman" ),
    ],
}

class Stat:
    def __init__( self, stat ):
        self.stat = stat
        self.heroes = all_heroes[ stat ]
        self.pool = []

    def reset( self ):
        for hero in self.heroes:
            hero.reset()

        self.pool = []

        for index in range( pool_size ):
            socketio.emit( "update-hero", ( self.stat, index, Hero.emit_null() ) )

    def generate( self ):
        for index, hero in enumerate( random.sample( self.heroes, pool_size ) ):
            self.pool.append( hero )
            socketio.emit( "update-hero", ( self.stat, index, hero.emit() ) )

    def get( self, index ):
        return self.pool[ index ]

    def calc_ban_count( self ):
        return sum( 1 for hero in self.pool if hero.is_banned )

    def get_random( self ):
        return random.choice( [ ( self.stat, index ) for index, hero in enumerate( self.pool ) if hero.is_available() ] )

    def emit( self ):
        return [ hero.emit() for hero in self.pool ] if self.pool else [ Hero.emit_null() for _ in range( pool_size ) ]

class Heroes:
    stats = [ Stat( stat ) for stat in all_heroes ]

    def reset():
        for stat in Heroes.stats:
            stat.reset()

    def generate():
        for stat in Heroes.stats:
            stat.generate()

    def get( stat, index ):
        return next( stat_iter for stat_iter in Heroes.stats if stat_iter.stat == stat ).get( index )

    def calc_ban_count():
        return sum( stat.calc_ban_count() for stat in Heroes.stats )

    def get_random():
        return random.choice( Heroes.stats ).get_random()

    def emit():
        return { stat.stat: stat.emit() for stat in Heroes.stats }

first_ban = Teams.legion
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

    Heroes.reset()
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
    Heroes.generate()
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

    hero = Heroes.get( stat, index )
    if hero.is_banned:
        return

    hero.is_banned = True
    socketio.emit( "update-hero", ( stat, index, hero.emit() ) )
    socketio.emit( "message", f"{ player.name if player else "Fate" } has banned { hero.name }" )

    timer.cancel()

    if Heroes.calc_ban_count() == ban_count:
        active_team = None
        set_state( "picking_countdown" )
        set_timer( picking_countdown_duration, picking_countdown_timer )
    else:
        active_team = active_team.get_other()
        set_timer( banning_duration, banning_timer )

def banning_timer():
    stat, index = Heroes.get_random()
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
    if player.hero:
        return

    hero = Heroes.get( stat, index )
    if not hero.is_available():
        return

    player.set_hero( hero )
    hero.is_picked = True

    global remaining_picks
    remaining_picks -= 1
    if remaining_picks > 0:
        return

    timer.cancel()

    active_team = active_team.get_other()
    start_picking( later_pick_count )

def picking_timer():
    while remaining_picks > 0:
        player = next( player for player in active_team.picking_players() )
        stat, index = Heroes.get_random()
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
        teams = Teams.emit(),
        heroes = Heroes.emit(),
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
    team = Teams.get( team )
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
