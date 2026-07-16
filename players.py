import teams
import heroes
import draft
import messages

from uuid import uuid4

class Player:
    def __init__( self, name, id ):
        self.name = name
        self.id = id
        self.session_id = None
        self.hero = None
        self.dibs = None
        self.veto = []
        self.team = teams.observers
        self.is_disconnected = False

    def set_name( self, name ):
        old_name = self.get_formatted_name()
        self.name = name
        messages.emit_update_player( self )
        self.emit_update_slot()
        new_name = self.get_formatted_name()
        messages.emit_message( f"{ old_name } changed name to { new_name }." )

    def set_team( self, team, index = None ):
        self.team.remove_player( self )
        self.team = team
        self.update_client_team()
        messages.emit_update_player( self )
        team.add_player( self, index )
        if team is teams.observers:
            messages.emit_message( f"{ self.get_formatted_name() } is now an observer." )
        else:
            messages.emit_message( f"{ self.get_formatted_name() } has joined { team.get_formatted_name() }." )

    def is_observer( self ):
        return self.team is teams.observers

    def set_disconnected( self, is_disconnected ):
        self.is_disconnected = is_disconnected
        if is_disconnected:
            messages.emit_message( f"{ self.get_formatted_name() } has disconnected." )
        else:
            messages.emit_message( f"{ self.get_formatted_name() } has reconnected." )
        messages.emit_update_player( self )
        self.emit_update_slot()

    def set_hero( self, hero ):
        self.dibs = None
        self.hero = hero
        self.emit_update_slot()

    def toggle_dibs( self, hero ):
        assert not self.hero
        is_dibs = self.dibs != hero
        self.dibs = hero if is_dibs else None
        self.emit_update_slot()
        messages.emit_message(
            f"{ self.get_formatted_name() } has called dibs on { hero.name }."
            if is_dibs else
            f"{ self.get_formatted_name() } has retracted their dibs for { hero.name }.",
            team = self.team )

    def toggle_veto( self, hero ):
        is_veto = hero not in self.veto
        if is_veto:
            self.veto.append( hero )
        else:
            self.veto.remove( hero )
        hero.emit_update_hero()
        messages.emit_message(
            f"{ self.get_formatted_name() } wants { hero.name } to be banned."
            if is_veto else
            f"{ self.get_formatted_name() } no longer wants { hero.name } to be banned.",
            team = self.team )

    def check_dibs( self, hero ):
        if self.dibs is hero:
            self.dibs = None
            self.emit_update_slot()
        
    def check_veto( self, hero ):
        if hero in self.veto:
            self.veto.remove( hero )
            hero.emit_update_hero()

    def clear_veto( self ):
        veto = self.veto
        self.veto = []
        for hero in veto:
            hero.emit_update_hero()

    def reset( self ):
        self.hero = None
        self.dibs = None
        self.veto = []
        self.emit_update_slot()

    def emit_update_slot( self, **kwargs ):
        team = self.team
        if team is teams.observers: return
        index = team.index( self )
        messages.emit_update_slot( team, index, **kwargs )

    def update_client_team( self ):
        messages.emit_update_client_team( self )
        teams.emit_update_slots( to = self.session_id )
        messages.update_rooms( self.team )

    def serialize_slot( self ):
        return {
            "player_name": self.name,
            "player_id": self.id,
            "is_disconnected": self.is_disconnected,
            "hero": self.hero.serialize() if self.hero else self.dibs.serialize() if self.dibs else None,
            "is_dibs": True if self.dibs else False,
        }

    def serialize_player( self ):
        return {
            "name": self.name,
            "id": self.id,
            "is_disconnected": self.is_disconnected,
            "team": self.team.name,
        }

    def get_formatted_name( self ):
        return f"<span style=\"color: { self.team.color }\">{ self.name }</span>"

players = []

def reset():
    for player in players:
        if player.is_disconnected:
            remove( player )
    for player in players:
        player.reset()

def clear():
    global players
    players = []

def check_dibs_veto( hero ):
    for player in players:
        player.check_dibs( hero )
        player.check_veto( hero )

def clear_veto():
    for player in players:
        player.clear_veto()

def generate_id():
    return uuid4().hex

def get( id ):
    return next( ( player for player in players if player.id == id ), None )

def connect( id, name, session_id ):
    player = get( id )
    is_new_player = False
    if not player:
        player = Player( name, id )
        is_new_player = True
    player.session_id = session_id
    messages.emit_welcome( to = session_id )

    messages.emit_update_client_id( player )
    messages.emit_update_client_team( player )

    messages.emit_update_state( to = session_id )
    teams.emit_update_slots( to = session_id )
    heroes.emit_update_heroes( to = session_id )
    messages.emit_update_players( to = session_id )

    if is_new_player:
        add( player )
    elif player.is_disconnected:
        restore( player )

    messages.update_rooms( player.team )

def disconnect( id, session_id ):
    player = get( id )
    if not player: return
    if player.session_id != session_id:
        print( "Discarding disconnect event for invalid socket id" )
        return
    if draft.state == draft.State.lobby:
        remove( player )
    else:
        player.set_disconnected( True )

def add( player ):
    players.append( player )
    teams.observers.add_player( player )
    messages.emit_update_players()
    messages.emit_message( f"{ player.get_formatted_name() } joined." )

def restore( player ):
    player.set_disconnected( False )

def remove( player ):
    players.remove( player )
    player.team.remove_player( player )
    messages.emit_update_players()
    if player.is_disconnected:
        messages.emit_message( f"{ player.get_formatted_name() } has been removed." )
    else:
        messages.emit_message( f"{ player.get_formatted_name() } left." )

def serialize():
    return [ player.serialize_player() for player in players ]
