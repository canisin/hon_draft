import heroes
import draft
import messages

import random

class Team:
    def __init__( self, name, color ):
        self.name = name
        self.color = color
        self.players = [ None for _ in range( draft.team_size ) ]

    def get( self, index ):
        return self.players[ index ]

    def index( self, player ):
        return self.players.index( player )

    def is_empty( self ):
        return all( player is None for player in self.players )

    def clear( self ):
        self.players = [ None for _ in range( draft.team_size ) ]

    def add_player( self, player, index ):
        assert player not in self.players
        assert self.players[ index ] is None
        self.players[ index ] = player
        messages.emit_update_slot( self, index )

    def remove_player( self, player ):
        assert player in self.players
        index = self.players.index( player )
        self.players[ index ] = None
        messages.emit_update_slot( self, index )

    def set_player_index( self, player, index ):
        assert player in self.players
        self.remove_player( player )
        self.add_player( player, index )

    def picking_players( self ):
        return [ player for player in self.players if player and not player.hero ]

    def get_random_ban( self ):
        veto_counts = {}
        for player in self.players:
            if player is None: continue
            for hero in player.veto:
                veto_counts.setdefault( hero, 0 )
                veto_counts[ hero ] += 1
        if veto_counts:
            max_count = max( veto_counts.values() )
            max_count_heroes = [ hero for hero, count in veto_counts.items() if count == max_count ]
            hero = random.choice( max_count_heroes )
            return hero, True
        else:
            stat = random.choice( [ stat for stat in heroes.stats if stat.is_enabled ] )
            hero = stat.get_random()
            return hero, False

    def missing_stats( self ):
        counts = { stat: 0 for stat in heroes.stats if stat.is_enabled }
        for player in self.players:
            if not player or not player.hero: continue
            counts[ player.hero.stat ] += 1
        min_count = min( counts.values() )
        for count in counts.values(): count -= min_count
        return [ stat for stat, count in counts.items() if count == 0 ]

    def get_random_pick( self ):
        stat = random.choice( self.missing_stats() )
        return stat.get_random()

    def get_other( self ):
        if self == legion: return hellbourne
        if self == hellbourne: return legion

    def emit_update_slots( self, **kwargs ):
        for index in range( draft.team_size ):
            messages.emit_update_slot( self, index, **kwargs )

    def serialize( self ):
        return [ player.serialize_slot() if player else None for player in self.players ]

    def get_formatted_name( self ):
        return f"<span style=\"color: { self.color }\">The { self.name.capitalize() }</span>"

class Observers:
    def __init__( self, name, color ):
        self.name = name
        self.color = color
        self.players = []

    def clear( self ):
        self.players = []

    def add_player( self, player, index = None ):
        assert index is None
        assert player not in self.players
        self.players.append( player )

    def remove_player( self, player ):
        assert player in self.players
        self.players.remove( player )

legion = Team( "legion", "green" )
hellbourne = Team( "hellbourne", "red" )
teams = [ legion, hellbourne ]
observer = Observers( "observers", "blue" )

def clear():
    legion.clear()
    hellbourne.clear()
    observer.clear()

def get( team ):
    if team == "legion": return legion
    if team == "hellbourne": return hellbourne

def can_draft():
    return not any( team.is_empty() for team in teams )

def emit_update_slots( **kwargs ):
    for team in teams:
        team.emit_update_slots( **kwargs )

def serialize():
    return { team.name: team.serialize() for team in teams }
