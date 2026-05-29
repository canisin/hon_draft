import main
import logic

def emit_update_state( **kwargs ):
    main.socketio.emit( "update-state", logic.serialize_state(), **kwargs )

def emit_update_client_id( player, **kwargs ):
    kwargs[ "to" ] = player.session_id
    main.socketio.emit( "update-client-id", player.id, **kwargs )

def emit_update_client_team( player, **kwargs ):
    kwargs[ "to" ] = player.session_id
    main.socketio.emit( "update-client-team", player.team.name, **kwargs )

def emit_set_timer( seconds, **kwargs ):
    main.socketio.emit( "set-timer", seconds, **kwargs )

def emit_update_hero( stat, index, **kwargs ):
    hero = stat.get( index )
    main.socketio.emit( "update-hero", ( stat.name, index, hero.serialize() if hero else None ), **kwargs )

def emit_update_slot( team, index, **kwargs ):
    player = team.get( index )
    main.socketio.emit( "update-slot", ( team.name, index, player.serialize_slot() if player else None ), **kwargs )

def emit_hero_picked( stat, index, **kwargs ):
    main.socketio.emit( "hero-picked", ( stat.name, index ), **kwargs )

def emit_update_player( player, **kwargs ):
    main.socketio.emit( "update-player", player.serialize_player(), **kwargs )

def emit_add_player( player, **kwargs ):
    main.socketio.emit( "add-player", player.serialize_player(), **kwargs )

def emit_remove_player( player, **kwargs ):
    main.socketio.emit( "remove-player", player.id, **kwargs )

def emit_message( message, team = None, **kwargs ):
    if team: kwargs[ "to" ] = team.name
    main.socketio.emit( "message", message, **kwargs )

def emit_welcome( **kwargs ):
    emit_message( f"Welcome to HoNDraft! [.{logic.revision}-{logic.sha}]", **kwargs )
    emit_message( "Type <b>/name new_name</b> in chat to change your name.", **kwargs )
