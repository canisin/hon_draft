from sys import stderr
from os import getenv

def log( message ):
    print( message, file = stderr )

def getenv_bool( key, default ):
    value = getenv( key )
    if not value: return default
    value = value.lower()
    if value in ( "true", "yes" ): return True
    if value in ( "false", "no" ): return False
    raise ValueError()
