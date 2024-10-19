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
    def __init__( self, name, stat, icon ):
        self.name = name
        self.stat = stat
        self.icon = icon
        self.is_banned = False
        self.is_picked = False

    def set_banned( self ):
        self.is_banned = True
        self.push_update()

    def set_picked( self ):
        assert not self.is_banned
        self.is_picked = True
        self.push_update()

    def push_update( self ):
        index = Heroes.stats_dict[ self.stat ].pool.index( self )
        socketio.emit( "update-hero", ( self.stat, index, self.emit() ) )

    def reset( self ):
        self.is_banned = False
        self.is_picked = False

    def is_available( self ):
        return not self.is_banned and not self.is_picked

    def emit( self ):
        if self.is_picked: return Hero.emit_null()
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
        self.dibs = None
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
        self.push_update()

    def set_hero( self, hero ):
        self.dibs = None
        self.hero = hero
        self.push_update()

    def set_dibs( self, hero ):
        assert not self.hero
        self.dibs = hero
        self.push_update()

    def check_dibs( self ):
        if not self.dibs: return
        if not self.dibs.is_available():
            self.set_dibs( None )

    def reset( self ):
        self.hero = None
        self.dibs = None
        self.push_update()

    def push_update( self ):
        socketio.emit( "update-player", self.emit() )
        if self.team:
            socketio.emit( "update-slot", ( self.team.name, self.index, self.emit() ) )

    def emit( self ):
        return {
            "name": self.name,
            "id": self.id,
            "hero": self.hero.emit() if self.hero
                else self.dibs.emit() if self.dibs
                else self.team.emit_null_hero() if self.team
                else Hero.emit_null(),
            "is_dibs": self.dibs is not None,
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
        return Hero( "null", None, f"hero-{ self.name }" ).emit()

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
        player.reset()

def check_dibs():
    for player in players:
        player.check_dibs()

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
        Hero( "Emerald Warden", "agi", "heroes/emerald_warden" ),
        Hero( "Moon Queen", "agi", "heroes/krixi" ),
        Hero( "Andromeda", "agi", "heroes/andromeda" ),
        Hero( "Artillery", "agi", "heroes/artillery" ),
        Hero( "Blitz", "agi", "heroes/blitz" ),
        Hero( "Night Hound", "agi", "heroes/hantumon" ),
        Hero( "Swiftblade", "agi", "heroes/hiro" ),
        Hero( "Master Of Arms", "agi", "heroes/master_of_arms" ),
        Hero( "Moira", "agi", "heroes/moira" ),
        Hero( "Monkey King", "agi", "heroes/monkey_king" ),
        Hero( "Nitro", "agi", "heroes/nitro" ),
        Hero( "Nomad", "agi", "heroes/nomad" ),
        Hero( "Sapphire", "agi", "heroes/sapphire" ),
        Hero( "Scout", "agi", "heroes/scout" ),
        Hero( "Silhouette", "agi", "heroes/silhouette" ),
        Hero( "Sir Benzington", "agi", "heroes/sir_benzington" ),
        Hero( "Tarot", "agi", "heroes/tarot" ),
        Hero( "Valkyrie", "agi", "heroes/valkyrie" ),
        Hero( "Wildsoul", "agi", "heroes/yogi" ),
        Hero( "Zephyr", "agi", "heroes/zephyr" ),
        Hero( "Arachna", "agi", "heroes/arachna" ),
        Hero( "Blood Hunter", "agi", "heroes/hunter" ),
        Hero( "Bushwack", "agi", "heroes/bushwack" ),
        Hero( "Chronos", "agi", "heroes/chronos" ),
        Hero( "Dampeer", "agi", "heroes/dampeer" ),
        Hero( "Flint Beastwood", "agi", "heroes/flint_beastwood" ),
        Hero( "Forsaken Archer", "agi", "heroes/forsaken_archer" ),
        Hero( "Grinex", "agi", "heroes/grinex" ),
        Hero( "Gunblade", "agi", "heroes/gunblade" ),
        Hero( "Shadowblade", "agi", "heroes/shadowblade" ),
        Hero( "Calamity", "agi", "heroes/calamity" ),
        Hero( "Corrupted Disciple", "agi", "heroes/corrupted_disciple" ),
        Hero( "Slither", "agi", "heroes/ebulus" ),
        Hero( "Gemini", "agi", "heroes/gemini" ),
        Hero( "Klanx", "agi", "heroes/klanx" ),
        Hero( "Riptide", "agi", "heroes/riptide" ),
        Hero( "Sand Wraith", "agi", "heroes/sand_wraith" ),
        Hero( "The Madman", "agi", "heroes/scar" ),
        Hero( "Soulstealer", "agi", "heroes/soulstealer" ),
        Hero( "Tremble", "agi", "heroes/tremble" ),
        Hero( "The Dark Lady", "agi", "heroes/vanya" ),
    ],
    "int": [
        Hero( "Aluna", "int", "heroes/aluna" ),
        Hero( "Blacksmith", "int", "heroes/dwarf_magi" ),
        Hero( "Bombardier", "int", "heroes/bomb" ),
        Hero( "Ellonia", "int", "heroes/ellonia" ),
        Hero( "Engineer", "int", "heroes/engineer" ),
        Hero( "Midas", "int", "heroes/midas" ),
        Hero( "Pyromancer", "int", "heroes/pyromancer" ),
        Hero( "Rhapsody", "int", "heroes/rhapsody" ),
        Hero( "Witch Slayer", "int", "heroes/witch_slayer" ),
        Hero( "Bubbles", "int", "heroes/bubbles" ),
        Hero( "Qi", "int", "heroes/chi" ),
        Hero( "The Chipper", "int", "heroes/chipper" ),
        Hero( "Empath", "int", "heroes/empath" ),
        Hero( "Nymphora", "int", "heroes/fairy" ),
        Hero( "Kinesis", "int", "heroes/kenisis" ),
        Hero( "Thunderbringer", "int", "heroes/kunas" ),
        Hero( "Martyr", "int", "heroes/martyr" ),
        Hero( "Monarch", "int", "heroes/monarch" ),
        Hero( "Oogie", "int", "heroes/oogie" ),
        Hero( "Ophelia", "int", "heroes/ophelia" ),
        Hero( "Pearl", "int", "heroes/pearl" ),
        Hero( "Pollywog Priest", "int", "heroes/pollywogpriest" ),
        Hero( "Skrap", "int", "heroes/skrap" ),
        Hero( "Tempest", "int", "heroes/tempest" ),
        Hero( "Vindicator", "int", "heroes/vindicator" ),
        Hero( "Warchief", "int", "heroes/warchief" ),
        Hero( "Defiler", "int", "heroes/defiler" ),
        Hero( "Demented Shaman", "int", "heroes/shaman" ),
        Hero( "Doctor Repulsor", "int", "heroes/doctor_repulsor" ),
        Hero( "Glacius", "int", "heroes/frosty" ),
        Hero( "Gravekeeper", "int", "heroes/taint" ),
        Hero( "Myrmidon", "int", "heroes/hydromancer" ),
        Hero( "Parasite", "int", "heroes/parasite" ),
        Hero( "Plague Rider", "int", "heroes/diseasedrider" ),
        Hero( "Revenant", "int", "heroes/revenant" ),
        Hero( "Soul Reaper", "int", "heroes/helldemon" ),
        Hero( "Succubus", "int", "heroes/succubis" ),
        Hero( "Wretched Hag", "int", "heroes/babayaga" ),
        Hero( "Artesia", "int", "heroes/artesia" ),
        Hero( "Circe", "int", "heroes/circe" ),
        Hero( "Fayde", "int", "heroes/fade" ),
        Hero( "Geomancer", "int", "heroes/geomancer" ),
        Hero( "Goldenveil", "int", "heroes/goldenveil" ),
        Hero( "Hellbringer", "int", "heroes/hellbringer" ),
        Hero( "Parallax", "int", "heroes/parallax" ),
        Hero( "Prophet", "int", "heroes/prophet" ),
        Hero( "Puppet Master", "int", "heroes/puppetmaster" ),
        Hero( "Riftwalker", "int", "heroes/riftmage" ),
        Hero( "Voodoo Jester", "int", "heroes/voodoo" ),
        Hero( "Torturer", "int", "heroes/xalynx" ),
    ],
    "str": [
        Hero( "Armadon", "str", "heroes/armadon" ),
        Hero( "Hammerstorm", "str", "heroes/hammerstorm" ),
        Hero( "Legionnaire", "str", "heroes/legionnaire" ),
        Hero( "Magebane", "str", "heroes/javaras" ),
        Hero( "Pandamonium", "str", "heroes/panda" ),
        Hero( "Predator", "str", "heroes/predator" ),
        Hero( "Prisoner 945", "str", "heroes/prisoner" ),
        Hero( "Rally", "str", "heroes/rally" ),
        Hero( "Behemoth", "str", "heroes/behemoth" ),
        Hero( "Berzerker", "str", "heroes/berzerker" ),
        Hero( "Drunken Master", "str", "heroes/drunkenmaster" ),
        Hero( "Flux", "str", "heroes/flux" ),
        Hero( "The Gladiator", "str", "heroes/gladiator" ),
        Hero( "Ichor", "str", "heroes/ichor" ),
        Hero( "Jeraziah", "str", "heroes/jereziah" ),
        Hero( "Xemplar", "str", "heroes/mimix" ),
        Hero( "Bramble", "str", "heroes/plant" ),
        Hero( "Rampage", "str", "heroes/rampage" ),
        Hero( "Pebbles", "str", "heroes/rocky" ),
        Hero( "Salomon", "str", "heroes/salomon" ),
        Hero( "Shellshock", "str", "heroes/shellshock" ),
        Hero( "Solstice", "str", "heroes/solstice" ),
        Hero( "Keeper of the Forest", "str", "heroes/treant" ),
        Hero( "Tundra", "str", "heroes/tundra" ),
        Hero( "Balphagore", "str", "heroes/bephelgor" ),
        Hero( "Magmus", "str", "heroes/magmar" ),
        Hero( "Maliken", "str", "heroes/maliken" ),
        Hero( "Ravenor", "str", "heroes/ravenor" ),
        Hero( "Amun-Ra", "str", "heroes/ra" ),
        Hero( "Accursed", "str", "heroes/accursed" ),
        Hero( "Adrenaline", "str", "heroes/adrenaline" ),
        Hero( "Apex", "str", "heroes/apex" ),
        Hero( "Cthulhuphant", "str", "heroes/cthulhuphant" ),
        Hero( "Deadlift", "str", "heroes/deadlift" ),
        Hero( "Deadwood", "str", "heroes/deadwood" ),
        Hero( "Devourer", "str", "heroes/devourer" ),
        Hero( "Lord Salforis", "str", "heroes/dreadknight" ),
        Hero( "Electrician", "str", "heroes/electrician" ),
        Hero( "Draconis", "str", "heroes/flamedragon" ),
        Hero( "Gauntlet", "str", "heroes/gauntlet" ),
        Hero( "Kane", "str", "heroes/kane" ),
        Hero( "King Klout", "str", "heroes/king_klout" ),
        Hero( "Kraken", "str", "heroes/kraken" ),
        Hero( "Lodestone", "str", "heroes/lodestone" ),
        Hero( "Moraxus", "str", "heroes/moraxus" ),
        Hero( "Pharaoh", "str", "heroes/mumra" ),
        Hero( "Pestilence", "str", "heroes/pestilence" ),
        Hero( "War Beast", "str", "heroes/wolfman" ),
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
            socketio.emit( "update-hero", ( self.stat, index, Hero.emit_null() ) )

    def generate( self ):
        for index, hero in enumerate( random.sample( self.heroes, pool_size ) ):
            self.pool.append( hero )
            hero.push_update()

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
    stats_dict = { stat.stat: stat for stat in stats }

    def reset():
        for stat in Heroes.stats:
            stat.reset()

    def generate():
        for stat in Heroes.stats:
            stat.generate()

    def get( stat, index ):
        return Heroes.stats_dict[ stat ].get( index )

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

    hero.set_banned()
    socketio.emit( "message", f"{ player.name if player else "Fate" } has banned { hero.name }" )

    check_dibs()

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

def pick_hero( player, stat, index, is_fate = False ):
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
    hero.set_picked()
    socketio.emit( "message", 
        f"{ player.name } has picked { hero.name }"
        if not is_fate else
        f"Fate has picked { hero.name } for { player.name }"
    )

    check_dibs()

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
        pick_hero( player, stat, index, is_fate = True )

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
