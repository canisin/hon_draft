import logic
import teams

from flask_socketio import join_room, leave_room
from os import popen

socketio = None
def initialize( socketio ):
    globals()[ "socketio" ] = socketio

def emit_update_state( **kwargs ):
    socketio.emit( "update-state", logic.serialize_state(), **kwargs )

def emit_update_client_id( player, **kwargs ):
    kwargs[ "to" ] = player.session_id
    socketio.emit( "update-client-id", player.id, **kwargs )

def emit_update_client_team( player, **kwargs ):
    kwargs[ "to" ] = player.session_id
    socketio.emit( "update-client-team", player.team.name, **kwargs )

def emit_set_timer( seconds, **kwargs ):
    socketio.emit( "set-timer", seconds, **kwargs )

def emit_update_hero( stat, index, **kwargs ):
    hero = stat.get( index )
    socketio.emit( "update-hero", ( stat.name, index, hero.serialize() if hero else None ), **kwargs )

def emit_update_slot( team, index, **kwargs ):
    player = team.get( index )
    socketio.emit( "update-slot", ( team.name, index, player.serialize_slot() if player else None ), **kwargs )

def emit_hero_picked( stat, index, **kwargs ):
    socketio.emit( "hero-picked", ( stat.name, index ), **kwargs )

def emit_update_player( player, **kwargs ):
    socketio.emit( "update-player", player.serialize_player(), **kwargs )

def emit_add_player( player, **kwargs ):
    socketio.emit( "add-player", player.serialize_player(), **kwargs )

def emit_remove_player( player, **kwargs ):
    socketio.emit( "remove-player", player.id, **kwargs )

def emit_message( message, team = None, **kwargs ):
    if team: kwargs[ "to" ] = team.name
    socketio.emit( "message", message, **kwargs )

revision = open( "revision.txt" ).read().strip()
sha = popen( "git rev-parse --short HEAD" ).read().strip()
def emit_welcome( **kwargs ):
    emit_message( f"Welcome to HoNDraft! [.{revision}-{sha}]", **kwargs )
    emit_message( "Type <b>/name new_name</b> in chat to change your name.", **kwargs )

def update_rooms( team ):
    if team is teams.observer:
        join_room( teams.legion.name )
        join_room( teams.hellbourne.name )
        join_room( teams.observer.name )
    else:
        join_room( team.name )
        leave_room( team.get_other().name )
        leave_room( teams.observer.name )
