from os import getenv
import enum
from enum import Enum
import threading
import random

import hero_sets
import players
import teams
import heroes
import sockets
import utils

hero_set = getenv( "HERO_SET" ) or "reborn"
hero_set = getattr( hero_sets, hero_set )
pool_countdown_duration = int( getenv( "POOL_COUNTDOWN_DURATION" ) or 5 )
banning_countdown_duration = int( getenv( "BANNING_COUNTDOWN_DURATION" ) or 10 )
banning_duration = int( getenv( "BANNING_DURATION" ) or 30 )
picking_countdown_duration = int( getenv( "PICKING_COUNTDOWN_DURATION" ) or 10 )
picking_duration = int( getenv( "PICKING_DURATION" ) or 30 )
timer_extension = int( getenv( "TIMER_EXTENSION" ) or 10 )

team_size = 3
pool_size = 8

ban_count = int( getenv( "BAN_COUNT" ) or 4 )
veto_count = int( getenv( "VETO_COUNT" ) or 2 )
initial_pick_count = int( getenv( "INITIAL_PICK_COUNT" ) or 1 )
later_pick_count = int( getenv( "LATER_PICK_COUNT" ) or 2 )

## STATE ##
state = None
timer = None
first_ban = None
active_team = None
remaining_picks = 0

class State( Enum ):
    lobby = enum.auto()
    pool_countdown = enum.auto()
    banning_countdown = enum.auto()
    banning = enum.auto()
    picking_countdown = enum.auto()
    picking = enum.auto()
    results = enum.auto()

def initialize_state():
    global state
    state = State.lobby
    global first_ban
    first_ban = teams.legion

def serialize_state():
    return {
        "state": state.name,
        "first_ban": first_ban.name,
        "stats": { stat.name: stat.is_enabled for stat in heroes.stats },
        "active_team": active_team.name if active_team else None,
        "remaining_picks": remaining_picks,
        "timer": timer.serialize() if timer else None,
    }

def set_state( new_state, seconds, callback ):
    global state
    state = new_state
    set_timer( seconds, callback )
    sockets.emit_update_state()

def set_timer( seconds, callback ):
    global timer
    if timer: timer.cancel()

    if seconds == 0:
        if callback: callback()
    else:
        timer = utils.Timer( callback )
        timer.start( seconds )

def can_modify_timer():
    if not timer: return False
    return state in ( State.banning, State.picking )

def pause_timer( player ):
    if not can_modify_timer(): return
    if timer.try_pause():
        sockets.emit_update_state()
        sockets.message( "pause_timer", player = player.id ).emit()

def resume_timer( player ):
    if not can_modify_timer(): return
    if timer.try_resume():
        sockets.emit_update_state()
        sockets.message( "resume_timer", player = player.id ).emit()

def extend_timer( player ):
    if not can_modify_timer(): return
    if timer.try_extend( timer_extension ):
        sockets.emit_update_state()
        sockets.message( "extend_timer", player = player.id, seconds = timer_extension ).emit()

def set_first_ban( player, team ):
    if state != State.lobby:
        return

    global first_ban
    if first_ban == team:
        return

    first_ban = team
    sockets.emit_update_state()
    sockets.message( "set_first_ban", player = player.id, team = team.name ).emit()

def toggle_stat( player, stat ):
    if state != State.lobby:
        return

    stat.is_enabled = not stat.is_enabled
    sockets.emit_update_state()
    sockets.message( "enable_stat" if stat.is_enabled else "disable_stat", player = player.id, stat = stat.name ).emit()

def click_slot( player, team, index ):
    assert team is not teams.observers
    if state == State.lobby:
        move_to_slot( player, team, index )
    else:
        swap_with_slot( player, team, index )

def move_to_slot( player, team, index ):
    slot_player = team.get( index )
    if slot_player == player:
        player.set_team( teams.observers )
        return

    if slot_player:
        return

    if player.team == team:
        team.set_player_index( player, index )
    else:
        player.set_team( team, index )

def swap_with_slot( player, team, index ):
    if team != player.team:
        return

    other_player = team.get( index )
    if not other_player:
        return

    if player == other_player:
        return

    if player.swap_request == other_player:
        player.set_swap_request( None )
        return

    if other_player.swap_request == player:
        player.accept_swap_request( other_player )
        return

    if not player.hero and not other_player.hero:
        return

    player.set_swap_request( other_player )

def start_draft( player ):
    if state != State.lobby:
        return

    if not teams.can_draft():
        sockets.message( "cannot_start_empty_teams" ).emit( to = player.session_id )
        return

    sockets.message( "start_draft", player = player.id ).emit()

    set_state( State.pool_countdown, pool_countdown_duration, pool_countdown_callback )
    draft_countdown( pool_countdown_duration )

def draft_countdown( seconds ):
    if state != State.pool_countdown: return
    if seconds == 0: return
    sockets.message( "draft_countdown", seconds = seconds ).emit()
    threading.Timer( 1, draft_countdown, [ seconds - 1 ] ).start()

def cancel_draft( player ):
    if state in ( State.lobby, State.results ):
        return
    reset_draft()
    sockets.message( "cancel_draft", player = player.id ).emit()

def end_draft( player ):
    if state != State.results:
        return
    reset_draft()
    sockets.message( "end_draft", player = player.id ).emit()

def reset_draft( clear_players = False ):
    global active_team
    active_team = None
    global remaining_picks
    remaining_picks = 0
    heroes.reset()
    if clear_players:
        players.clear()
        teams.clear()
    else:
        players.reset()
    set_state( State.lobby, 0, None )

def pool_countdown_callback():
    heroes.generate_pool()
    set_state( State.banning_countdown, banning_countdown_duration, banning_countdown_callback )

def dibs_hero( player, hero ):
    if state in ( State.lobby, State.pool_countdown, State.results ):
        return

    if player.is_observer():
        return

    if player.hero:
        return

    if hero.is_banned:
        return
    if hero.is_picked:
        return

    player.toggle_dibs( hero )

def banning_countdown_callback():
    global active_team
    active_team = first_ban
    set_state( State.banning, banning_duration, banning_timer_callback )

def veto_hero( player, hero ):
    if state not in ( State.banning_countdown, State.banning ):
        return

    if player.is_observer():
        return

    if hero.is_banned:
        return
    if hero.is_picked:
        return

    player.toggle_veto( hero )

def ban_hero( player, hero, is_veto = False ):
    if state != State.banning:
        return

    global active_team
    if player and player.team != active_team:
        return

    if hero.is_banned:
        return

    hero.set_banned()
    players.check_dibs_veto( hero )

    sockets.emit_update_hero( hero )
    if player:
        sockets.message( "player_ban_hero", player = player.id, hero = hero.name ).emit()
    elif is_veto:
        sockets.message( "vote_ban_hero", hero = hero.name ).emit()
    else:
        sockets.message( "fate_ban_hero", hero = hero.name ).emit()

    timer.cancel()

    if heroes.calc_ban_count() == ban_count:
        players.clear_veto()
        active_team = None
        set_state( State.picking_countdown, picking_countdown_duration, picking_countdown_callback )
    else:
        active_team = active_team.get_other()
        set_state( State.banning, banning_duration, banning_timer_callback )

def banning_timer_callback():
    hero, is_veto = active_team.get_random_ban()
    ban_hero( None, hero, is_veto )

def start_picking( team, pick_count ):
    global active_team
    active_team = team

    global remaining_picks
    remaining_picks = min( pick_count, len( active_team.picking_players() ) )

    if remaining_picks == 0:
        active_team = None
        set_state( State.results, 0, None )
    else:
        set_state( State.picking, picking_duration, picking_timer_callback )

def picking_countdown_callback():
    start_picking( first_ban, initial_pick_count )

def pick_hero( player, hero, is_fate = False ):
    if state != State.picking:
        return

    if player.team != active_team:
        return
    if player.hero:
        return

    if not hero.is_available():
        return

    is_denied = any( player and player.dibs == hero for player in player.team.get_other().players )

    player.set_hero( hero )
    hero.set_picked()
    players.check_dibs_veto( hero )

    sockets.emit_update_hero( hero )
    sockets.emit_hero_picked( hero, is_denied )
    sockets.message( "player_pick_hero" if not is_fate else "fate_pick_hero", player = player.id, hero = hero.name ).emit()

    global remaining_picks
    remaining_picks -= 1
    if remaining_picks > 0:
        return

    timer.cancel()

    start_picking( active_team.get_other(), later_pick_count )

def picking_timer_callback():
    for _ in range( remaining_picks ):
        picking_players = active_team.picking_players()
        assert picking_players
        player = random.choice( [ player for player in picking_players if player.dibs ] or picking_players )
        hero = player.dibs if player.dibs else active_team.get_random_pick()
        pick_hero( player, hero, is_fate = not player.dibs )
