from threading import Timer
from dotenv import load_dotenv
from os import getenv
from os import popen

import hero_sets
import players
import teams
import heroes
import messages

def getenv_bool( key, default ):
    value = getenv( key )
    if not value: return default
    value = value.lower()
    if value in ( "true", "yes" ): return True
    if value in ( "false", "no" ): return False
    raise ValueError()

load_dotenv()

hero_set = getenv( "HERO_SET" ) or "reborn"
hero_set = getattr( hero_sets, hero_set )
pool_countdown_duration = int( getenv( "POOL_COUNTDOWN_DURATION" ) or 5 )
banning_countdown_duration = int( getenv( "BANNING_COUNTDOWN_DURATION" ) or 10 )
banning_duration = int( getenv( "BANNING_DURATION" ) or 30 )
picking_countdown_duration = int( getenv( "PICKING_COUNTDOWN_DURATION" ) or 10 )
picking_duration = int( getenv( "PICKING_DURATION" ) or 30 )

team_size = 3
pool_size = 8

ban_count = 4
initial_pick_count = 1
later_pick_count = 2

fate_formatted = "<span style=\"color:orange\">Fate</span>"

revision = open( "revision.txt" ).read().strip()
sha = popen( "git rev-parse --short HEAD" ).read().strip()

## STATE ##
state = "lobby"
timer = None
first_ban = None
active_team = None
remaining_picks = 0

def initialize_state():
    global first_ban
    first_ban = teams.legion

def serialize_state():
    return {
        "state": state,
        "first_ban": first_ban.name,
        "stats": { stat.name: stat.is_enabled for stat in heroes.stats },
        "active_team": active_team.name if active_team else None,
        "remaining_picks": remaining_picks,
    }

def set_state( new_state, seconds, callback ):
    global state
    state = new_state
    messages.emit_update_state()
    set_timer( seconds, callback )

def set_timer( seconds, callback ):
    global timer
    if timer: timer.cancel()

    if seconds == 0:
        if callback: callback()
    else:
        timer = Timer( seconds, callback )
        timer.start()
        messages.emit_set_timer( seconds )

def set_first_ban( player, team ):
    if state != "lobby":
        return

    global first_ban
    if first_ban == team:
        return

    first_ban = team
    messages.emit_update_state()
    messages.emit_message( f"{ player.get_formatted_name() } has set { team.get_formatted_name() } to ban first." )

def toggle_stat( player, stat ):
    if state != "lobby":
        return

    stat.is_enabled = not stat.is_enabled
    messages.emit_update_state()
    action = "enabled" if stat.is_enabled else "disabled"
    messages.emit_message( f"{ player.get_formatted_name() } has { action } { stat.get_formatted_name() } heroes." )

def click_slot( player, team, index ):
    assert team is not teams.observer
    if state != "lobby":
        return

    slot_player = team.get( index )
    if slot_player == player:
        player.set_team( teams.observer )
        return

    if slot_player:
        return

    if player.team == team:
        team.set_player_index( player, index )
    else:
        player.set_team( team, index )

def start_draft( player ):
    if state != "lobby":
        return

    if not teams.can_draft():
        messages.emit_message( f"<span style=\"color: red\">Cannot start with empty teams</span>", to = player.session_id )
        return

    messages.emit_message( f"{ player.get_formatted_name() } has started the draft!" )

    set_state( "pool_countdown", pool_countdown_duration, pool_countdown_callback )
    draft_countdown( pool_countdown_duration )

def draft_countdown( seconds ):
    if state != "pool_countdown": return
    if seconds == 0: return
    messages.emit_message( f"Draft starting in { seconds } seconds.." )
    Timer( 1, draft_countdown, [ seconds - 1 ] ).start()

def cancel_draft( player ):
    if state == "lobby" or state == "results":
        return
    reset_draft()
    messages.emit_message( f"{ player.get_formatted_name() } has cancelled the draft!" )

def end_draft( player ):
    if state != "results":
        return
    reset_draft()
    messages.emit_message( f"{ player.get_formatted_name() } has ended the draft!" )

def reset_draft( clear_players = False ):
    global active_team
    active_team = None
    global remaining_picks
    remaining_picks = 0
    heroes.reset()
    if clear_players:
        players.Players.clear()
        teams.clear()
    else:
        players.Players.reset()
    set_state( "lobby", 0, None )

def pool_countdown_callback():
    heroes.generate_pool()
    set_state( "banning_countdown", banning_countdown_duration, banning_countdown_callback )

def dibs_hero( player, hero ):
    if state in ( "lobby", "pool_countdown", "results" ):
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
    set_state( "banning", banning_duration, banning_timer_callback )

def veto_hero( player, hero ):
    if state not in ( "banning_countdown", "banning" ):
        return

    if player.is_observer():
        return

    if hero.is_banned:
        return
    if hero.is_picked:
        return

    player.toggle_veto( hero )

def ban_hero( player, hero, is_veto = False ):
    if state != "banning":
        return

    global active_team
    if player and player.team != active_team:
        return

    if hero.is_banned:
        return

    hero.set_banned()
    if player:
        messages.emit_message( f"{ player.get_formatted_name() } has banned { hero.name }." )
    elif is_veto:
        messages.emit_message( f"{ hero.name } was banned based on veto votes." )
    else:
        messages.emit_message( f"{ fate_formatted } has banned { hero.name }." )

    players.Players.check_dibs_veto( hero )

    timer.cancel()

    if heroes.calc_ban_count() == ban_count:
        players.Players.clear_veto()
        active_team = None
        set_state( "picking_countdown", picking_countdown_duration, picking_countdown_callback )
    else:
        active_team = active_team.get_other()
        set_state( "banning", banning_duration, banning_timer_callback )

def banning_timer_callback():
    hero, is_veto = active_team.get_random_ban()
    ban_hero( None, hero, is_veto )

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
        set_state( "results", 0, None )
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
    messages.emit_hero_picked( hero.stat, hero.stat.index( hero ) )
    messages.emit_message(
        f"{ player.get_formatted_name() } has picked { hero.name }."
        if not is_fate else
        f"{ fate_formatted } has picked { hero.name } for { player.get_formatted_name() }."
    )

    players.Players.check_dibs_veto( hero )

    global remaining_picks
    remaining_picks -= 1
    if remaining_picks > 0:
        return

    timer.cancel()

    start_picking( active_team.get_other(), later_pick_count )

def picking_timer_callback():
    for _ in range( remaining_picks ):
        picking_players = active_team.picking_players()
        assert( picking_players )
        player = next( ( player for player in picking_players if player.dibs ), picking_players[ 0 ] )
        hero = player.dibs if player.dibs else active_team.get_random_pick()
        pick_hero( player, hero, is_fate = not player.dibs )
