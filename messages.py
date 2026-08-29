import draft
import teams
import players
import heroes

from flask_socketio import join_room, leave_room
from os import popen

socketio = None
def initialize( socketio ):
    globals()[ "socketio" ] = socketio

def emit_update_state( **kwargs ):
    socketio.emit( "update-state", draft.serialize_state(), **kwargs )

def emit_update_client_id( player, **kwargs ):
    kwargs[ "to" ] = player.session_id
    socketio.emit( "update-client-id", player.id, **kwargs )

def emit_update_client_team( player, **kwargs ):
    kwargs[ "to" ] = player.session_id
    socketio.emit( "update-client-team", player.team.name, **kwargs )

def emit_update_hero( hero, **kwargs ):
    socketio.emit( "update-hero", hero.serialize(), **kwargs )

def emit_update_heroes( **kwargs ):
    socketio.emit( "update-heroes", heroes.serialize(), **kwargs )

def emit_hero_picked( hero, **kwargs ):
    socketio.emit( "hero-picked", hero.name, **kwargs )

def emit_update_player( player, **kwargs ):
    socketio.emit( "update-player", player.serialize(), **kwargs )

def emit_update_players( **kwargs ):
    socketio.emit( "update-players", players.serialize(), **kwargs )

def emit_update_teams( **kwargs ):
    socketio.emit( "update-teams", teams.serialize(), **kwargs )

class _MessageHelper:
    def __init__( self, key, **kwargs ):
        self.key = key
        self.params = kwargs

    def emit( self, team = None, **kwargs ):
        if team: kwargs[ "to" ] = team.name
        socketio.emit( "message", { "key": self.key, "params": self.params }, **kwargs )

def message( key, **kwargs ):
    return _MessageHelper( key, **kwargs )

revision = open( "revision.txt" ).read().strip()
sha = popen( "git rev-parse --short HEAD" ).read().strip()
def emit_welcome( **kwargs ):
    message( "welcome", revision = revision, sha = sha ).emit( **kwargs )
    message( "name_help" ).emit( **kwargs )

def update_rooms( team ):
    if team is teams.observers:
        join_room( teams.legion.name )
        join_room( teams.hellbourne.name )
        join_room( teams.observers.name )
    else:
        join_room( team.name )
        leave_room( team.get_other().name )
        leave_room( teams.observers.name )
