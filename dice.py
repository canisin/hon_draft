import re
import random

random.seed()

roll_pattern = r"(\d*d\d+|\d+)"
signed_roll_pattern = rf"([+-])\s*{ roll_pattern }"
expression_pattern = rf"\s*{roll_pattern}(\s*{ signed_roll_pattern })*\s*"

roll_regex = re.compile( roll_pattern )
signed_roll_regex = re.compile( signed_roll_pattern )
expression_regex = re.compile( expression_pattern )

class Roll:
    def __init__( self, count, faces ):
        self.count = count
        self.faces = faces

    def parse( match ):
        has_sign = len( match.groups() ) > 1
        sign = match.group( 1 ) if has_sign else None
        sign = 1 if not sign or sign == "+" else -1
        roll = match.group( 2 ) if has_sign else match.group( 1 )
        parts = roll.split( 'd' )
        count = ( int( parts[ 0 ] ) if parts[ 0 ] else 1 ) * sign
        faces = int( parts[ 1 ] ) if len( parts ) > 1 else 0
        return Roll( count, faces )

    def roll( self ):
        if self.is_constant(): return self.count
        return sum( random.randint( 1, self.faces ) for _ in range( self.count ) )

    def is_constant( self ):
        return self.faces == 0

    def to_string( self ):
        if self.is_constant():
            return f"{ self.count }"
        else:
            return f"{ self.count }d{ self.faces }" 

def is_dice_expression( expression ):
    return bool( expression_regex.fullmatch( expression ) )

class DiceExpression:
    def __init__( self, rolls ):
        self.rolls = rolls

    def parse( expression ):
        if not is_dice_expression( expression ): return None

        rolls = []

        match = roll_regex.search( expression )
        while match:
            rolls.append( Roll.parse( match ) )
            match = signed_roll_regex.search( expression, match.end() )

        faces = set( map( lambda roll: roll.faces, rolls ) )
        rolls = [ Roll( sum( roll.count for roll in rolls if roll.faces == face ), face ) for face in faces ]
        rolls.sort( key = lambda roll: roll.faces, reverse = True )

        return DiceExpression( rolls )

    def roll( self ):
        return sum( roll.roll() for roll in self.rolls )

    def roll_average( self, count = 100 ):
        return sum( self.roll() for _ in range( count ) ) / count

    def to_string( self ):
        string = ""
        is_first_term = True
        for roll in self.rolls:
            if is_first_term:
                string += "-" if roll.count < 0 else ""
            else:
                string += f" { "+" if roll.count > 0 else "-" } "
            if roll.is_constant():
                string += f"{ abs( roll.count ) }"
            else:
                string += f"{ abs( roll.count ) }d{ roll.faces }"
            is_first_term = False
        return string
