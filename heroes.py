import teams
import logic
import messages

import random

class Hero:
    def __init__( self, name, key, stat ):
        self.name = name
        self.key = key
        self.stat = stat
        self.is_banned = False
        self.picked_by = None

    def set_banned( self ):
        self.is_banned = True
        self.emit_update_hero()

    def set_picked( self, player ):
        assert not self.is_banned
        self.picked_by = player
        self.emit_update_hero()

    def is_available( self ):
        return not self.is_banned and not self.picked_by

    def calc_veto_count( self, team ):
        return sum( 1 for player in team if self in player.veto )

    def emit_update_hero( self, **kwargs ):
        stat = self.stat
        index = stat.index( self )
        messages.emit_update_hero( stat, index, **kwargs )

    def serialize( self ):
        return {
            "name": self.name,
            "path": f"{ logic.hero_set[ "path" ] }/{ self.key }",
            "is_banned": self.is_banned,
            "picked_by": self.picked_by.name if self.picked_by else None,
            "legion_vetos": [ player.name for player in teams.legion.players if player and self in player.veto ],
            "hellbourne_vetos": [ player.name for player in teams.hellbourne.players if player and self in player.veto ],
            "legion_dibs": [ player.name for player in teams.legion.players if player and self is player.dibs ],
            "hellbourne_dibs": [ player.name for player in teams.hellbourne.players if player and self is player.dibs ],
        }

class Stat:
    def __init__( self, name, color ):
        self.name = name
        self.color = color
        self.is_enabled = True
        self.pool = [ None for _ in range( logic.pool_size ) ]

    def reset( self ):
        self.pool = [ None for _ in range( logic.pool_size ) ]
        self.emit_update_heroes()

    def generate_pool( self ):
        if not self.is_enabled: return
        heroes = logic.hero_set[ self.name ]
        heroes = random.sample( heroes, logic.pool_size )
        self.pool = [ Hero( name, key, self ) for name, key in heroes ]
        self.emit_update_heroes()

    def get( self, index ):
        return self.pool[ index ]

    def index( self, hero ):
        return self.pool.index( hero )

    def calc_ban_count( self ):
        if not self.is_enabled: return 0
        return sum( 1 for hero in self.pool if hero.is_banned )

    def get_random( self ):
        return random.choice( [ hero for hero in self.pool if hero.is_available() ] )

    def emit_update_heroes( self, **kwargs ):
        for index in range( logic.pool_size ):
            messages.emit_update_hero( self, index, **kwargs )

    def serialize( self ):
        return [ hero.serialize() if hero else None for hero in self.pool ]

    def get_formatted_name( self ):
        return f"<span style=\"color: { self.color }\">{ self.full_name.capitalize() }</span>"

agi = Stat( "agi", "green" )
int = Stat( "int", "blue" )
str = Stat( "str", "red" )
stats = [ agi, int, str ]
stats_dict = { stat.name: stat for stat in stats }

def reset():
    for stat in stats:
        stat.reset()

def generate_pool():
    for stat in stats:
        stat.generate_pool()

def get( stat, index = None ):
    if index is None: return stats_dict[ stat ]
    return get( stat ).get( index )

def calc_ban_count():
    return sum( stat.calc_ban_count() for stat in stats )

def emit_update_heroes( **kwargs ):
    for stat in stats:
        stat.emit_update_heroes( **kwargs )

def serialize():
    return { stat.name: stat.serialize() for stat in stats }
