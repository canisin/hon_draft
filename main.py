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

all_heroes = {
    "agi": [
        Hero( "Emerald Warden", "/static/images/heroes/emerald_warden.png" ),
        Hero( "Moon Queen", "/static/images/heroes/krixi.png" ),
        Hero( "Andromeda", "/static/images/heroes/andromeda.png" ),
        Hero( "Artillery", "/static/images/heroes/artillery.png" ),
        Hero( "Blitz", "/static/images/heroes/blitz.png" ),
        Hero( "Night Hound", "/static/images/heroes/hantumon.png" ),
        Hero( "Swiftblade", "/static/images/heroes/hiro.png" ),
        Hero( "Master Of Arms", "/static/images/heroes/master_of_arms.png" ),
        Hero( "Moira", "/static/images/heroes/moira.png" ),
        Hero( "Monkey King", "/static/images/heroes/monkey_king.png" ),
        Hero( "Nitro", "/static/images/heroes/nitro.png" ),
        Hero( "Nomad", "/static/images/heroes/nomad.png" ),
        Hero( "Sapphire", "/static/images/heroes/sapphire.png" ),
        Hero( "Scout", "/static/images/heroes/scout.png" ),
        Hero( "Silhouette", "/static/images/heroes/silhouette.png" ),
        Hero( "Sir Benzington", "/static/images/heroes/sir_benzington.png" ),
        Hero( "Tarot", "/static/images/heroes/tarot.png" ),
        Hero( "Valkyrie", "/static/images/heroes/valkyrie.png" ),
        Hero( "Wildsoul", "/static/images/heroes/yogi.png" ),
        Hero( "Zephyr", "/static/images/heroes/zephyr.png" ),
        Hero( "Arachna", "/static/images/heroes/arachna.png" ),
        Hero( "Blood Hunter", "/static/images/heroes/hunter.png" ),
        Hero( "Bushwack", "/static/images/heroes/bushwack.png" ),
        Hero( "Chronos", "/static/images/heroes/chronos.png" ),
        Hero( "Dampeer", "/static/images/heroes/dampeer.png" ),
        Hero( "Flint Beastwood", "/static/images/heroes/flint_beastwood.png" ),
        Hero( "Forsaken Archer", "/static/images/heroes/forsaken_archer.png" ),
        Hero( "Grinex", "/static/images/heroes/grinex.png" ),
        Hero( "Gunblade", "/static/images/heroes/gunblade.png" ),
        Hero( "Shadowblade", "/static/images/heroes/shadowblade.png" ),
        Hero( "Calamity", "/static/images/heroes/calamity.png" ),
        Hero( "Corrupted Disciple", "/static/images/heroes/corrupted_disciple.png" ),
        Hero( "Slither", "/static/images/heroes/ebulus.png" ),
        Hero( "Gemini", "/static/images/heroes/gemini.png" ),
        Hero( "Klanx", "/static/images/heroes/klanx.png" ),
        Hero( "Riptide", "/static/images/heroes/riptide.png" ),
        Hero( "Sand Wraith", "/static/images/heroes/sand_wraith.png" ),
        Hero( "The Madman", "/static/images/heroes/scar.png" ),
        Hero( "Soulstealer", "/static/images/heroes/soulstealer.png" ),
        Hero( "Tremble", "/static/images/heroes/tremble.png" ),
        Hero( "The Dark Lady", "/static/images/heroes/vanya.png" ),
    ],
    "int": [
        Hero( "Aluna", "/static/images/heroes/aluna.png" ),
        Hero( "Blacksmith", "/static/images/heroes/dwarf_magi.png" ),
        Hero( "Bombardier", "/static/images/heroes/bomb.png" ),
        Hero( "Ellonia", "/static/images/heroes/ellonia.png" ),
        Hero( "Engineer", "/static/images/heroes/engineer.png" ),
        Hero( "Midas", "/static/images/heroes/midas.png" ),
        Hero( "Pyromancer", "/static/images/heroes/pyromancer.png" ),
        Hero( "Rhapsody", "/static/images/heroes/rhapsody.png" ),
        Hero( "Witch Slayer", "/static/images/heroes/witch_slayer.png" ),
        Hero( "Bubbles", "/static/images/heroes/bubbles.png" ),
        Hero( "Qi", "/static/images/heroes/chi.png" ),
        Hero( "The Chipper", "/static/images/heroes/chipper.png" ),
        Hero( "Empath", "/static/images/heroes/empath.png" ),
        Hero( "Nymphora", "/static/images/heroes/fairy.png" ),
        Hero( "Kinesis", "/static/images/heroes/kenisis.png" ),
        Hero( "Thunderbringer", "/static/images/heroes/kunas.png" ),
        Hero( "Martyr", "/static/images/heroes/martyr.png" ),
        Hero( "Monarch", "/static/images/heroes/monarch.png" ),
        Hero( "Oogie", "/static/images/heroes/oogie.png" ),
        Hero( "Ophelia", "/static/images/heroes/ophelia.png" ),
        Hero( "Pearl", "/static/images/heroes/pearl.png" ),
        Hero( "Pollywog Priest", "/static/images/heroes/pollywogpriest.png" ),
        Hero( "Skrap", "/static/images/heroes/skrap.png" ),
        Hero( "Tempest", "/static/images/heroes/tempest.png" ),
        Hero( "Vindicator", "/static/images/heroes/vindicator.png" ),
        Hero( "Warchief", "/static/images/heroes/warchief.png" ),
        Hero( "Defiler", "/static/images/heroes/defiler.png" ),
        Hero( "Demented Shaman", "/static/images/heroes/shaman.png" ),
        Hero( "Doctor Repulsor", "/static/images/heroes/doctor_repulsor.png" ),
        Hero( "Glacius", "/static/images/heroes/frosty.png" ),
        Hero( "Gravekeeper", "/static/images/heroes/taint.png" ),
        Hero( "Myrmidon", "/static/images/heroes/hydromancer.png" ),
        Hero( "Parasite", "/static/images/heroes/parasite.png" ),
        Hero( "Plague Rider", "/static/images/heroes/diseasedrider.png" ),
        Hero( "Revenant", "/static/images/heroes/revenant.png" ),
        Hero( "Soul Reaper", "/static/images/heroes/helldemon.png" ),
        Hero( "Succubus", "/static/images/heroes/succubis.png" ),
        Hero( "Wretched Hag", "/static/images/heroes/babayaga.png" ),
        Hero( "Artesia", "/static/images/heroes/artesia.png" ),
        Hero( "Circe", "/static/images/heroes/circe.png" ),
        Hero( "Fayde", "/static/images/heroes/fade.png" ),
        Hero( "Geomancer", "/static/images/heroes/geomancer.png" ),
        Hero( "Goldenveil", "/static/images/heroes/goldenveil.png" ),
        Hero( "Hellbringer", "/static/images/heroes/hellbringer.png" ),
        Hero( "Parallax", "/static/images/heroes/parallax.png" ),
        Hero( "Prophet", "/static/images/heroes/prophet.png" ),
        Hero( "Puppet Master", "/static/images/heroes/puppetmaster.png" ),
        Hero( "Riftwalker", "/static/images/heroes/riftmage.png" ),
        Hero( "Voodoo Jester", "/static/images/heroes/voodoo.png" ),
        Hero( "Torturer", "/static/images/heroes/xalynx.png" ),
    ],
    "str": [
        Hero( "Armadon", "/static/images/heroes/armadon.png" ),
        Hero( "Hammerstorm", "/static/images/heroes/hammerstorm.png" ),
        Hero( "Legionnaire", "/static/images/heroes/legionnaire.png" ),
        Hero( "Magebane", "/static/images/heroes/javaras.png" ),
        Hero( "Pandamonium", "/static/images/heroes/panda.png" ),
        Hero( "Predator", "/static/images/heroes/predator.png" ),
        Hero( "Prisoner 945", "/static/images/heroes/prisoner.png" ),
        Hero( "Rally", "/static/images/heroes/rally.png" ),
        Hero( "Behemoth", "/static/images/heroes/behemoth.png" ),
        Hero( "Berzerker", "/static/images/heroes/berzerker.png" ),
        Hero( "Drunken Master", "/static/images/heroes/drunkenmaster.png" ),
        Hero( "Flux", "/static/images/heroes/flux.png" ),
        Hero( "The Gladiator", "/static/images/heroes/gladiator.png" ),
        Hero( "Ichor", "/static/images/heroes/ichor.png" ),
        Hero( "Jeraziah", "/static/images/heroes/jereziah.png" ),
        Hero( "Xemplar", "/static/images/heroes/mimix.png" ),
        Hero( "Bramble", "/static/images/heroes/plant.png" ),
        Hero( "Rampage", "/static/images/heroes/rampage.png" ),
        Hero( "Pebbles", "/static/images/heroes/rocky.png" ),
        Hero( "Salomon", "/static/images/heroes/salomon.png" ),
        Hero( "Shellshock", "/static/images/heroes/shellshock.png" ),
        Hero( "Solstice", "/static/images/heroes/solstice.png" ),
        Hero( "Keeper of the Forest", "/static/images/heroes/treant.png" ),
        Hero( "Tundra", "/static/images/heroes/tundra.png" ),
        Hero( "Balphagore", "/static/images/heroes/bephelgor.png" ),
        Hero( "Magmus", "/static/images/heroes/magmar.png" ),
        Hero( "Maliken", "/static/images/heroes/maliken.png" ),
        Hero( "Ravenor", "/static/images/heroes/ravenor.png" ),
        Hero( "Amun-Ra", "/static/images/heroes/ra.png" ),
        Hero( "Accursed", "/static/images/heroes/accursed.png" ),
        Hero( "Adrenaline", "/static/images/heroes/adrenaline.png" ),
        Hero( "Apex", "/static/images/heroes/apex.png" ),
        Hero( "Cthulhuphant", "/static/images/heroes/cthulhuphant.png" ),
        Hero( "Deadlift", "/static/images/heroes/deadlift.png" ),
        Hero( "Deadwood", "/static/images/heroes/deadwood.png" ),
        Hero( "Devourer", "/static/images/heroes/devourer.png" ),
        Hero( "Lord Salforis", "/static/images/heroes/dreadknight.png" ),
        Hero( "Electrician", "/static/images/heroes/electrician.png" ),
        Hero( "Draconis", "/static/images/heroes/flamedragon.png" ),
        Hero( "Gauntlet", "/static/images/heroes/gauntlet.png" ),
        Hero( "Kane", "/static/images/heroes/kane.png" ),
        Hero( "King Klout", "/static/images/heroes/king_klout.png" ),
        Hero( "Kraken", "/static/images/heroes/kraken.png" ),
        Hero( "Lodestone", "/static/images/heroes/lodestone.png" ),
        Hero( "Moraxus", "/static/images/heroes/moraxus.png" ),
        Hero( "Pharaoh", "/static/images/heroes/mumra.png" ),
        Hero( "Pestilence", "/static/images/heroes/pestilence.png" ),
        Hero( "War Beast", "/static/images/heroes/wolfman.png" ),
    ],
}

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
    for stat in heroes:
        for index, hero in enumerate( random.sample( all_heroes[ stat ], 8 ) ):
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
    socketio.run( app, host = "localhost", port = 80, allow_unsafe_werkzeug=True, debug = True )
