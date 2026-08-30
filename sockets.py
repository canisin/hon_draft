from flask import session, request
from flask_socketio import join_room, leave_room
from os import popen

from app import socketio
import draft
import teams
import players
import heroes
import commands
import utils

## OUTGOING EVENTS ##
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

## INCOMING EVENTS ##
@socketio.on( "connect" )
def on_connect( auth ):
    id = session[ "id" ]
    name = session[ "name" ]
    session_id = request.sid
    utils.log( f"socket connect: id: { id }, name: '{ name }', session_id: { session_id }" )
    players.connect( id, name, session_id )

@socketio.on( "disconnect" )
def on_disconnect():
    id = session[ "id" ]
    session_id = request.sid
    utils.log( f"socket disconnect: id: { id }, session_id: { session_id }" )
    players.disconnect( id, session_id )

@socketio.on( "first-ban" )
def on_first_ban( team ):
    player = players.get( session[ "id" ] )
    team = teams.get( team )
    draft.set_first_ban( player, team )

@socketio.on( "toggle-stat" )
def on_toggle_stat( stat ):
    player = players.get( session[ "id" ] )
    stat = heroes.get( stat )
    draft.toggle_stat( player, stat )

@socketio.on( "start-draft" )
def on_start_draft():
    player = players.get( session[ "id" ] )
    draft.start_draft( player )

@socketio.on( "cancel-draft" )
def on_cancel_draft():
    player = players.get( session[ "id" ] )
    draft.cancel_draft( player )

@socketio.on( "end-draft" )
def on_end_draft():
    player = players.get( session[ "id" ] )
    draft.end_draft( player )

@socketio.on( "pause-timer" )
def on_pause_timer():
    player = players.get( session[ "id" ] )
    draft.pause_timer( player )

@socketio.on( "resume-timer" )
def on_resume_timer():
    player = players.get( session[ "id" ] )
    draft.resume_timer( player )

@socketio.on( "extend-timer" )
def on_extend_timer():
    player = players.get( session[ "id" ] )
    draft.extend_timer( player )

@socketio.on( "click-slot" )
def on_click_slot( team, index ):
    player = players.get( session[ "id" ] )
    team = teams.get( team )
    draft.click_slot( player, team, index )

@socketio.on( "dibs-hero" )
def on_dibs_hero( stat, index ):
    player = players.get( session[ "id" ] )
    hero = heroes.get( stat, index )
    draft.dibs_hero( player, hero )

@socketio.on( "veto-hero" )
def on_veto_hero( stat, index ):
    player = players.get( session[ "id" ] )
    hero = heroes.get( stat, index )
    draft.veto_hero( player, hero )

@socketio.on( "ban-hero" )
def on_ban_hero( stat, index ):
    player = players.get( session[ "id" ] )
    hero = heroes.get( stat, index )
    draft.ban_hero( player, hero )

@socketio.on( "pick-hero" )
def on_pick_hero( stat, index ):
    player = players.get( session[ "id" ] )
    hero = heroes.get( stat, index )
    draft.pick_hero( player, hero )

@socketio.on( "message" )
def on_message( text ):
    player = players.get( session[ "id" ] )
    if commands.try_dispatch( player, text ): return
    message( "message", player = player.id, text = text ).emit( team = player.team )
