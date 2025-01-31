from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room

from threading import Thread
from threading import Timer
from time import sleep
import random
from uuid import uuid4
from dotenv import load_dotenv
from os import getenv
from os import popen

load_dotenv()

pool_countdown_duration = int( getenv( "POOL_COUNTDOWN_DURATION" ) or 5 )
banning_countdown_duration = int( getenv( "BANNING_COUNTDOWN_DURATION" ) or 10 )
banning_duration = int( getenv( "BANNING_DURATION" ) or 30 )
picking_countdown_duration = int( getenv( "PICKING_COUNTDOWN_DURATION" ) or 10 )
picking_duration = int( getenv( "PICKING_DURATION" ) or 30 )
add_test_players = getenv( "ADD_TEST_PLAYERS" ) or False

team_size = 3
pool_size = 8

ban_count = 4
initial_pick_count = 1
later_pick_count = 2

# TODO: Move to js
fate_formatted = "<span style=\"color:orange\">Fate</span>"

revision = open( "revision.txt" ).read().strip()
sha = popen( "git rev-parse --short HEAD" ).read().strip()

app = Flask( __name__ )
app.secret_key = "honzor"
socketio = SocketIO( app )

# TODO: Eventually delete
def emit_icon( icon ):
    return f"/static/images/{ icon }.png"

class Player:
    def __init__( self, name, id ):
        self.name = name
        self.id = id
        self.hero = None
        self.dibs = None
        self.team = None
        self.index = None
        self.is_disconnected = False

    def set_name( self, name ):
        self.name = name
        self.emit_update()

    def set_team( self, team, index):
        old_team = self.team
        if old_team:
            old_team.remove_player( self )
            emit_update_slot( old_team, self.index, None )
        self.team = team
        self.index = index
        team.add_player( self )
        self.update_rooms()
        self.emit_update()
        emit_update_client_team( team )
        emit_message( f"{ self.get_formatted_name( no_team = True ) } has joined { team.get_formatted_name() }." )

    def set_observer( self ):
        old_team = self.team
        if old_team:
            old_team.remove_player( self )
            emit_update_slot( old_team, self.index, None )
        self.team = None
        self.index = None
        self.update_rooms()
        self.emit_update()
        emit_update_client_team( None )
        emit_message( f"{ self.get_formatted_name( no_team = True ) } is now an observer." )

    def set_index( self, index ):
        emit_update_slot( self.team, self.index, None )
        self.index = index
        emit_update_slot( self.team, self.index, self )

    def set_disconnected( self, is_disconnected ):
        self.is_disconnected = is_disconnected
        if is_disconnected:
            emit_message( f"{ self.get_formatted_name() } has disconnected." )
        else:
            emit_message( f"{ self.get_formatted_name() } has reconnected." )
        self.emit_update()

    def click_slot( self, team, index ):
        if state != "lobby":
            return
        slot_player = team.get_player( index )
        if slot_player is None:
            if self.team == team:
                self.set_index( index )
            else:
                self.set_team( team, index )
        elif slot_player == self:
            self.set_observer()

    def set_hero( self, hero ):
        self.dibs = None
        self.hero = hero
        self.emit_update()

    def set_dibs( self, hero ):
        assert not self.hero
        self.dibs = hero
        self.emit_update()

    def check_dibs( self ):
        if not self.dibs: return
        if not self.dibs.is_available():
            self.set_dibs( None )

    def reset( self ):
        self.hero = None
        self.dibs = None
        self.emit_update()

    def update_rooms( self ):
        team = self.team
        if team:
            join_room( team.name )
            leave_room( team.get_other().name )
            leave_room( Teams.observer.name )
        else:
            leave_room( Teams.legion.name )
            leave_room( Teams.hellbourne.name )
            join_room( Teams.observer.name )

    def emit_update( self ):
        emit_update_player( self )
        if self.team:
            emit_update_slot( self.team, self.index, self )

    def emit( self ):
        return {
            "name": self.name,
            "id": self.id,
            "is_disconnected": self.is_disconnected,
            "hero": self.hero.emit() if self.hero else Hero.emit_null(),
            "team": self.team.emit() if self.team else Teams.observer.emit(),
        }

    def emit_with_dibs( self ):
        ret = self.emit()
        if self.dibs:
            ret[ "hero" ] = self.dibs.emit()
            ret[ "is_dibs" ] = True
        return ret

    def get_formatted_name( self, no_team = False ):
        return f"<span style=\"color: { "blue" if no_team or not self.team else self.team.color }\">{ self.name }</span>"

class Players:
    players = []

    def reset():
        for player in Players.players:
            if player.is_disconnected:
                Players.remove( player )
        for player in Players.players:
            player.reset()

    def check_dibs():
        for player in Players.players:
            player.check_dibs()

    def generate_id():
        return uuid4().hex

    def get( id ):
        return next( ( player for player in Players.players if player.id == id ), None )

    def connect( id, name ):
        player = Players.get( id )
        if player:
            Players.restore( player )
        else:
            player = Player( name, id )
            Players.add( player )
        return player

    def disconnect( id ):
        player = Players.get( id )
        if not player: return
        if state == "lobby":
            Players.remove( player )
        else:
            player.set_disconnected( True )

    def add( player ):
        # TODO: Deduplicate the following code
        Players.players.append( player )
        socketio.emit( "add-player", player.emit() )
        for other_player in Players.players:
            if other_player == player: continue
            emit( "add-player", other_player.emit() )
        emit_message( f"Welcome to HoNDraft! [.{revision}-{sha}]", to = request.sid )
        player.update_rooms()
        emit_message( f"{ player.get_formatted_name( no_team = True ) } joined." )

    def restore( player ):
        # TODO: Deduplicate the following code
        emit( "add-player", player.emit() )
        for other_player in Players.players:
            if other_player == player: continue
            emit( "add-player", other_player.emit() )
        emit_message( f"Welcome to HoNDraft! [.{revision}-{sha}]", to = request.sid )
        player.update_rooms()
        player.set_disconnected( False )

    def remove( player ):
        Players.players.remove( player )
        if player.team:
            player.team.remove_player( player )
            emit_update_slot( player.team, player.index, None )
        socketio.emit( "remove-player", player.id )
        if player.is_disconnected:
            emit_message( f"{ player.get_formatted_name( no_team = True ) } has been removed." )
        else:
            emit_message( f"{ player.get_formatted_name( no_team = True ) } left." )

    def rename( id, name ):
        player = Players.get( id )
        old_name = player.get_formatted_name( no_team = True )
        player.set_name( name )
        emit_message( f"{ old_name } changed name to { player.get_formatted_name( no_team = True ) }." )

    def emit():
        return [ player.emit() for player in Players.players ]

    def add_test_players():
        for team in Teams.teams:
            for index in range( team_size ):
                player = Player( f"{ team.name }_{ index }", Players.generate_id() )
                player.team = team
                player.index = index
                team.add_player( player )
                Players.players.append( player )

class Team:
    def __init__( self, name, icon, color ):
        self.name = name
        self.icon = icon
        self.color = color
        self.players = []   # TODO: Consider converting this to a map from index to player so that the player doesn't have to keep track of their index

    def get_player( self, index ):
        return next( ( player for player in self.players if player.index == index ), None )

    def is_empty( self ):
        return not self.players

    def add_player( self, player ):
        self.players.append( player )

    def remove_player( self, player ):
        self.players.remove( player )

    def picking_players( self ):
        return ( player for player in self.players if not player.hero )

    def missing_stats( self ):
        counts = { stat: 0 for stat in Heroes.stats if stat.is_enabled }
        for player in self.players:
            if not player.hero: continue
            counts[ player.hero.stat ] += 1
        min_count = min( counts.values() )
        for count in counts.values(): count -= min_count
        return [ stat for stat, count in counts.items() if count == 0 ]

    def get_other( self ):
        return Teams.get_other( self )

    # TODO: Delete
    def emit_null_player( self ):
        return {
            "name": "null",
            "hero": Hero( "null", None, f"slot-{ self.name }" ).emit(),
            "team": self.emit(),
        }

    def emit( self, with_players = False ):
        return {
            "name": self.name,
            "icon": emit_icon( self.icon ),
            "color": self.color,
            # TODO: List or map?
            "players": None if not with_players else
                [ player.emit() if ( player := self.get_player( index ) ) else None for index in range( team_size ) ]
        }

    def get_formatted_name( self ):
        return f"<span style=\"color: { self.color }\">The { self.name.capitalize() }</span>"

class Teams:
    legion = Team( "legion", "team-legion", "green" )
    hellbourne = Team( "hellbourne", "team-hellbourne", "red" )
    teams = [ legion, hellbourne ]
    observer = Team( "observers", "observer", "blue" )

    def get( team ):
        if team == "legion": return Teams.legion
        if team == "hellbourne": return Teams.hellbourne

    def get_other( team ):
        if team == Teams.legion: return Teams.hellbourne
        if team == Teams.hellbourne: return Teams.legion

    def can_draft():
        return not any( team.is_empty() for team in Teams.teams )

    def emit():
        return {
            "legion": Teams.legion.emit( with_players = True ),
            "hellbourne": Teams.hellbourne.emit( with_players = True ),
        }

class Hero:
    def __init__( self, name, stat, icon ):
        self.name = name
        self.stat = Heroes.get( stat ) if stat else None
        self.icon = icon
        self.is_banned = False
        self.is_picked = False

    def set_banned( self ):
        self.is_banned = True
        self.emit_update()

    def set_picked( self ):
        assert not self.is_banned
        self.is_picked = True
        self.emit_update()

    def emit_update( self ):
        emit_update_hero( self.stat, self.stat.index( self ), self )

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

class Stat:
    def __init__( self, name, full_name, color ):
        self.name = name
        self.full_name = full_name
        self.color = color
        self.is_enabled = True
        self.pool = []

    def toggle( self, player ):
        if state != "lobby":
            return

        self.is_enabled = not self.is_enabled
        emit_update_state()
        action = "enabled" if self.is_enabled else "disabled"
        emit_message( f"{ player.get_formatted_name() } has { action } { self.get_formatted_name() } heroes." )

    def reset( self ):
        for hero in self.pool:
            hero.reset()

        self.pool = []

        for index in range( pool_size ):
            emit_update_hero( self, index, None )

    def generate( self ):
        if not self.is_enabled: return
        for index, hero in enumerate( random.sample( all_heroes[ self.name ], pool_size ) ):
            self.pool.append( hero )
            emit_update_hero( self, index, hero )

    def get( self, index ):
        return self.pool[ index ]

    def index( self, hero ):
        return self.pool.index( hero )

    def calc_ban_count( self ):
        if not self.is_enabled: return 0
        return sum( 1 for hero in self.pool if hero.is_banned )

    def get_random( self ):
        return random.choice( [ hero for hero in self.pool if hero.is_available() ] )

    def emit( self ):
        return [ hero.emit() for hero in self.pool ] if self.pool else [ Hero.emit_null() for _ in range( pool_size ) ]

    def emit_state( self ):
        return {
            "is_enabled": self.is_enabled,
        }

    def get_formatted_name( self ):
        return f"<span style=\"color: { self.color }\">{ self.full_name.capitalize() }</span>"

class Heroes:
    agi = Stat( "agi", "agility", "green" )
    int = Stat( "int", "intelligence", "blue" )
    str = Stat( "str", "strength", "red" )
    stats = [ agi, int, str ]
    stats_dict = { stat.name: stat for stat in stats }

    def reset():
        for stat in Heroes.stats:
            stat.reset()

    def generate():
        for stat in Heroes.stats:
            stat.generate()

    def get( stat, index = None ):
        if index is None: return Heroes.stats_dict[ stat ]
        return Heroes.get( stat ).get( index )

    def calc_ban_count():
        return sum( stat.calc_ban_count() for stat in Heroes.stats )

    def get_random_ban():
        stat = random.choice( [ stat for stat in Heroes.stats if stat.is_enabled ] )
        return stat.get_random()

    def get_random_pick( team ):
        stat = random.choice( team.missing_stats() )
        return stat.get_random()

    def emit():
        return { stat.name: stat.emit() for stat in Heroes.stats }

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

## STATE ##
state = "lobby"
timer = None
first_ban = Teams.legion
active_team = None
remaining_picks = 0

if add_test_players:
    Players.add_test_players()

def emit_constants():
    return {
        "team_size": team_size,
        "pool_size": pool_size,
    }

def emit_state():
    return {
        "state": state,
        "first_ban": first_ban.name,
        "stats": { stat.name: stat.emit_state() for stat in Heroes.stats },
        "active_team": active_team.name if active_team else None,
        "remaining_picks": remaining_picks,
    }

def set_state( new_state, seconds, callback ):
    global state
    state = new_state
    emit_update_state()
    set_timer( seconds, callback )

def set_timer( seconds, callback ):
    global timer
    if timer: timer.cancel()

    if seconds == 0:
        if callback: callback()
    else:
        timer = Timer( seconds, callback )
        timer.start()

    emit_set_timer( seconds )

def set_first_ban( player, team ):
    if state != "lobby":
        return

    global first_ban
    if first_ban == team:
        return

    first_ban = team
    emit_update_state()
    emit_message( f"{ player.get_formatted_name() } has set { team.get_formatted_name() } to ban first." )

def start_draft( player ):
    if state != "lobby":
        return

    if not Teams.can_draft():
        return

    emit_message( f"{ player.get_formatted_name() } has started the draft!" )

    Heroes.reset()
    Players.reset()
    set_state( "pool_countdown", pool_countdown_duration, pool_countdown_callback )

    time_remaining = 5
    def announce_countdown():
        if state != "pool_countdown": return
        nonlocal time_remaining
        emit_message( f"Draft starting in { time_remaining } seconds.." )
        time_remaining -= 1
        if time_remaining == 0: return
        Timer( 1, announce_countdown ).start()
    announce_countdown()

def cancel_draft( player ):
    if state == "lobby":
        return
    global active_team
    active_team = None
    global remaining_picks
    remaining_picks = 0
    set_state( "lobby", 0, None )
    emit_message( f"{ player.get_formatted_name() } has cancelled the draft!" )

def pool_countdown_callback():
    Heroes.generate()
    set_state( "banning_countdown", banning_countdown_duration, banning_countdown_callback )

def dibs_hero( player, hero ):
    if state in [ "lobby", "pool_countdown" ]:
        return

    if not player.team:
        return

    if player.hero:
        return

    if hero.is_banned:
        return
    if hero.is_picked:
        return

    is_dibs = player.dibs != hero
    player.set_dibs( hero if is_dibs else None )
    emit_message(
        f"{ player.get_formatted_name() } has called dibs on { hero.name }."
        if is_dibs else
        f"{ player.get_formatted_name() } has retracted their dibs for { hero.name }.",
        team = player.team )

def banning_countdown_callback():
    global active_team
    active_team = first_ban
    set_state( "banning", banning_duration, banning_timer_callback )

def ban_hero( player, hero ):
    if state != "banning":
        return

    global active_team
    if player and player.team != active_team:
        return

    if hero.is_banned:
        return

    hero.set_banned()
    message_actor = player.get_formatted_name() if player else fate_formatted
    emit_message( f"{ message_actor } has banned { hero.name }." )

    Players.check_dibs()

    timer.cancel()

    if Heroes.calc_ban_count() == ban_count:
        active_team = None
        set_state( "picking_countdown", picking_countdown_duration, picking_countdown_callback )
    else:
        active_team = active_team.get_other()
        set_state( "banning", banning_duration, banning_timer_callback )

def banning_timer_callback():
    hero = Heroes.get_random_ban()
    ban_hero( None, hero )

def start_picking( team, pick_count ):
    global active_team
    active_team = team

    global remaining_picks
    remaining_picks = min(
        pick_count,
        sum( 1 for player in active_team.picking_players() )
    )

    if remaining_picks == 0:
        active_team = None
        set_state( "lobby", 0, None )
    else:
        set_state( "picking", picking_duration, picking_timer_callback )

def picking_countdown_callback():
    start_picking( first_ban, initial_pick_count )

def pick_hero( player, hero, is_fate = False ):
    if state != "picking":
        return

    if player.team != active_team:
        return
    if player.hero:
        return

    if not hero.is_available():
        return

    player.set_hero( hero )
    hero.set_picked()
    emit_message( 
        f"{ player.get_formatted_name() } has picked { hero.name }."
        if not is_fate else
        f"{ fate_formatted } has picked { hero.name } for { player.get_formatted_name() }."
    )

    Players.check_dibs()

    global remaining_picks
    remaining_picks -= 1
    if remaining_picks > 0:
        return

    timer.cancel()

    start_picking( active_team.get_other(), later_pick_count )

def picking_timer_callback():
    for _ in range( remaining_picks ):
        player = next( ( player for player in active_team.picking_players() if player.dibs ),
           next( player for player in active_team.picking_players() ) )
        hero = player.dibs if player.dibs else Heroes.get_random_pick( active_team )
        pick_hero( player, hero, is_fate = not player.dibs )

## ROUTES ##
@app.route( "/" )
def home():
    if "name" not in session:
        session[ "name" ] = "Unnamed Player"
    if "id" not in session:
        session[ "id" ] = Players.generate_id()
    return render_template( "home.html",
        constants = emit_constants(),
        state = emit_state(),
        players = Players.emit(),
        teams = Teams.emit(),
        heroes = Heroes.emit(),
    )

@app.route( "/name", methods = [ "POST" ] )
def name():
    print( "name request" )
    id = session[ "id" ]
    name = request.form[ "name" ]
    Players.rename( id, name )
    session[ "name" ] = name
    return ""

## INCOMING SOCKET EVENTS ##
@socketio.on( "connect" )
def on_connect( auth ):
    print( "socket connected" )
    id = session[ "id" ]
    name = session[ "name" ]
    player = Players.connect( id, name )
    emit_update_client_team( player.team )

@socketio.on( "disconnect" )
def on_disconnect():
    print( "socket disconnected" )
    id = session[ "id" ]
    Players.disconnect( id )

@socketio.on( "first-ban" )
def on_first_ban( team ):
    player = Players.get( session[ "id" ] )
    team = Teams.get( team )
    set_first_ban( player, team )

@socketio.on( "toggle-stat" )
def on_toggle_stat( stat ):
    player = Players.get( session[ "id" ] )
    stat = Heroes.get( stat )
    stat.toggle( player )

@socketio.on( "start-draft" )
def on_start_draft():
    print( "received start draft request from socket" )
    player = Players.get( session[ "id" ] )
    start_draft( player )

@socketio.on( "cancel-draft" )
def on_cancel_draft():
    player = Players.get( session[ "id" ] )
    cancel_draft( player )

@socketio.on( "click-slot" )
def on_click_slot( team, index ):
    player = Players.get( session[ "id" ] )
    team = Teams.get( team )
    player.click_slot( team, index )

@socketio.on( "dibs-hero" )
def on_dibs_hero( stat, index ):
    player = Players.get( session[ "id" ] )
    hero = Heroes.get( stat, index )
    dibs_hero( player, hero )

@socketio.on( "ban-hero" )
def on_ban_hero( stat, index ):
    player = Players.get( session[ "id" ] )
    hero = Heroes.get( stat, index )
    ban_hero( player, hero )

@socketio.on( "pick-hero" )
def on_pick_hero( stat, index ):
    player = Players.get( session[ "id" ] )
    hero = Heroes.get( stat, index )
    pick_hero( player, hero )

@socketio.on( "message" )
def on_message( message ):
    print( "received message" )
    if message[:1] == "/":
        on_command( message[1:] )
        return
    player = Players.get( session[ "id" ] )
    emit_message( f"{ player.name }: { message }", team = player.team if player.team else Teams.observer )

def on_command( message ):
    ( command, _, parameters ) = message.partition( " " )
    if command == "name":
        set_name( parameters )
        return
    print( "unrecognized command" )
    emit_message( "unrecognized command", to = request.id )

def set_name( name ):
    print( "received name change command" )
    # tell the client to make a request to set the cookie
    emit( "set-name", name )

## OUTGOING SOCKET EVENTS ##
def emit_update_state():
    print( f"sending new state { state } to socket" )
    socketio.emit( "update-state", emit_state() )

def emit_update_client_team( team ):
    emit( "update-client-team", team.name if team else None )

def emit_set_timer( seconds ):
    socketio.emit( "set-timer", seconds )

def emit_update_hero( stat, index, hero ):
    socketio.emit( "update-hero", ( stat.name, index, hero.emit() if hero else Hero.emit_null() ) )

def emit_update_slot( team, index, player ):
    if not player:
        socketio.emit( "update-slot", ( team.name, index, team.emit_null_player() ) )
    else:
        socketio.emit( "update-slot", ( team.name, index, player.emit_with_dibs() ), to = team.name )
        socketio.emit( "update-slot", ( team.name, index, player.emit_with_dibs() ), to = Teams.observer.name )
        socketio.emit( "update-slot", ( team.name, index, player.emit() ), to = team.get_other().name )

def emit_update_player( player ):
    socketio.emit( "update-player", player.emit() )

def emit_message( message, team = None, **kwargs ):
    if team == Teams.observer:
        socketio.emit( "message", message, to = Teams.observer.name, **kwargs )
    elif team:
        socketio.emit( "message", message, to = team.name, **kwargs )
        socketio.emit( "message", message, to = Teams.observer.name, **kwargs )
    else:
        socketio.emit( "message", message, **kwargs )

if __name__ == "__main__":
    host = getenv( "HOST" ) or "0.0.0.0"
    port = getenv( "PORT" ) or None
    debug = getenv( "DEBUG" ) or False
    socketio.run( app, allow_unsafe_werkzeug = True, host = host, port = port, debug = debug )
