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
        self.is_picked = False

    def set_banned( self ):
        self.is_banned = True
        self.emit_update_hero()

    def set_picked( self ):
        assert not self.is_banned
        self.is_picked = True
        self.emit_update_hero()

    def is_available( self ):
        return not self.is_banned and not self.is_picked

    def calc_veto_count( self, team ):
        return sum( 1 for player in team if self in player.veto )

    def emit_update_hero( self ):
        stat = self.stat
        index = stat.index( self )
        messages.emit_update_hero( stat, index )

    def serialize( self ):
        return {
            "name": self.name,
            "path": f"{ logic.hero_set[ "path" ] }/{ self.key }",
            "is_banned": self.is_banned,
            "is_picked": self.is_picked,
            "legion_vetos": [ player.name for player in teams.Teams.legion.players if player and self in player.veto ],
            "hellbourne_vetos": [ player.name for player in teams.Teams.hellbourne.players if player and self in player.veto ],
        }

class Stat:
    def __init__( self, name, full_name, color ):
        self.name = name
        self.full_name = full_name
        self.color = color
        self.is_enabled = True
        self.pool = [ None for _ in range( logic.pool_size ) ]

    def reset( self ):
        self.pool = [ None for _ in range( logic.pool_size ) ]
        for index, _ in enumerate( self.pool ):
            messages.emit_update_hero( self, index )

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
            messages.emit_update_hero( self, index )

    def serialize( self ):
        return [ hero.serialize() if hero else None for hero in self.pool ]

    def get_formatted_name( self ):
        return f"<span style=\"color: { self.color }\">{ self.full_name.capitalize() }</span>"

class Heroes:
    agi = Stat( "agi", "agility", "green" )
    int = Stat( "int", "intelligence", "blue" )
    str = Stat( "str", "strength", "red" )
    stats = [ agi, int, str ]
    stats_dict = { stat.name: stat for stat in stats }

    def reset():
        for stat in Heroes.stats:
            stat.reset()

    def generate_pool():
        for stat in Heroes.stats:
            stat.generate_pool()

    def get( stat, index = None ):
        if index is None: return Heroes.stats_dict[ stat ]
        return Heroes.get( stat ).get( index )

    def calc_ban_count():
        return sum( stat.calc_ban_count() for stat in Heroes.stats )

    def emit_update_heroes( **kwargs ):
        for stat in Heroes.stats:
            stat.emit_update_heroes( **kwargs )

    def serialize():
        return { stat.name: stat.serialize() for stat in Heroes.stats }
