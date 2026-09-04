from uuid import uuid4

import teams
import draft
import sockets

class Player:
    def __init__( self, name, id ):
        self.name = name
        self.id = id
        self.session_id = None
        self.hero = None
        self.dibs = None
        self.veto = {}
        self.swap_request = None
        self.team = teams.observers
        self.is_disconnected = False

    def set_name( self, name ):
        old_name = self.name
        self.name = name
        sockets.emit_update_player( self )
        sockets.message( "name_change", player = self.id, old_name = old_name ).emit()

    def set_team( self, team, index = None ):
        self.team.remove_player( self )
        self.team = team
        self.update_client_team()
        sockets.emit_update_player( self )
        team.add_player( self, index )
        if team is teams.observers:
            sockets.message( "change_team_observer", player = self.id ).emit()
        else:
            sockets.message( "change_team", player = self.id, team = team.name ).emit()

    def is_observer( self ):
        return self.team is teams.observers

    def set_disconnected( self, is_disconnected ):
        self.is_disconnected = is_disconnected
        if is_disconnected:
            sockets.message( "player_disconnect", player = self.id ).emit()
        else:
            sockets.message( "player_reconnect", player = self.id ).emit()
        sockets.emit_update_player( self )

    def set_hero( self, hero ):
        self.dibs = None
        self.swap_request = None
        self.hero = hero
        sockets.emit_update_player( self )
        for other_player in self.team.players:
            if not other_player: continue
            if other_player == self: continue
            if other_player.swap_request == self:
                other_player.swap_request = None
                sockets.emit_update_player( other_player )

    def toggle_dibs( self, hero ):
        assert not self.hero
        is_dibs = self.dibs != hero
        self.dibs = hero if is_dibs else None
        sockets.emit_update_player( self )
        sockets.message( "set_dibs" if is_dibs else "remove_dibs", player = self.id, hero = hero.name ).emit( team = self.team )

    def toggle_veto( self, hero ):
        if draft.veto_count == 0: return

        count = self.veto.get( hero, 0 ) + 1
        if count <= draft.veto_count:
            self.veto[ hero ] = count
            sockets.message( "set_veto" if count == 1 else "set_veto_count", count = count, player = self.id, hero = hero.name ).emit( team = self.team )
        else:
            self.veto.pop( hero )
            sockets.message( "remove_veto", player = self.id, hero = hero.name ).emit( team = self.team )
        sockets.emit_update_hero( hero )
        sockets.emit_update_player( self )

    def set_swap_request( self, other ):
        self.swap_request = other
        sockets.emit_update_player( self )
        # TODO: message: self wants to/no longer wants to swap heroes with other

    def execute_swap_request( self ):
        assert self.swap_request
        other = self.swap_request
        self.swap_request = None
        hero = self.hero
        other_hero = other.hero
        self.set_hero( other_hero )
        other.set_hero( hero )
        # TODO: message: other accepted self's request to swap heroes

    def accept_swap_request( self, other ):
        assert other.swap_request == self
        other.swap_request = None
        hero = self.hero
        other_hero = other.hero
        self.set_hero( other_hero )
        other.set_hero( hero )
        # TODO: message: self accepted other's request to swap heroes

    def check_dibs( self, hero ):
        if self.dibs is hero:
            self.dibs = None
            sockets.emit_update_player( self )
        
    def check_veto( self, hero ):
        if hero in self.veto:
            del self.veto[ hero ]
            sockets.emit_update_player( self )

    def clear_veto( self ):
        veto = self.veto
        self.veto = {}
        for hero in veto:
            sockets.emit_update_hero( hero )
        sockets.emit_update_player( self )

    def reset( self ):
        self.hero = None
        self.dibs = None
        self.veto = {}
        self.swap_request = None
        sockets.emit_update_player( self )

    def update_client_team( self ):
        sockets.emit_update_client_team( self )
        sockets.update_rooms( self.team )

    def serialize( self ):
        return {
            "name": self.name,
            "id": self.id,
            "is_disconnected": self.is_disconnected,
            "team": self.team.name,
            "hero": self.hero.name if self.hero else None,
            "dibs": self.dibs.name if self.dibs else None,
            "veto": { hero.name: count for hero, count in self.veto.items() },
            "swap_request": self.swap_request.id if self.swap_request else None,
        }

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
    sockets.emit_welcome( to = session_id )

    sockets.emit_update_client_id( player )
    sockets.emit_update_client_team( player )

    sockets.emit_update_state( to = session_id )
    sockets.emit_update_heroes( to = session_id )
    sockets.emit_update_players( to = session_id )
    sockets.emit_update_teams( to = session_id )

    if is_new_player:
        add( player )
    elif player.is_disconnected:
        restore( player )

    sockets.update_rooms( player.team )

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
    sockets.emit_update_players()
    sockets.message( "player_joined", player = player.id ).emit()

def restore( player ):
    player.set_disconnected( False )

def remove( player ):
    players.remove( player )
    player.team.remove_player( player )
    sockets.emit_update_players()
    if player.is_disconnected:
        sockets.message( "player_removed", player = player.id ).emit()
    else:
        sockets.message( "player_left", player = player.id ).emit()

def serialize():
    return { player.id : player.serialize() for player in players }
