import os
import re

def _replace_code_block( match ):
    body = match.group( 1 )
    body = re.sub( r"(?<!\\)@(\w+)", r"params.\1", body )
    return f"${{{ body }}}"

def _process_loc( loc ):
    loc = re.sub( r"(?<!\\)\[\[(.*?)(?<!\\)\]\]", _replace_code_block, loc )
    loc = re.sub( r"(?<!\\)#@(\w+)", r"${ localize( params.\1, params ) }", loc )
    loc = re.sub( r"(?<!\\)#(\w+)", r"${ localize( '\1', params ) }", loc )
    loc = re.sub( r"(?<!\\)@(\w+)", r"${ params.\1 }", loc )
    loc = loc.replace( r"\[[", "[[" )
    loc = loc.replace( r"\]]", "]]" )
    loc = loc.replace( r"\@", "@" )
    loc = loc.replace( r"\#", "#" )
    return loc

def generate_localization_script():
    os.makedirs( "generated/script", exist_ok = True )
    with open( "generated/script/localization.js", "w" ) as generated:
        generated.write( "const localizations = {\n" )
        with open( "data/localization.txt" ) as source:
            for line in source:
                line = line.strip()
                if not line or line.startswith( "#" ):
                    continue
                key, _, loc = line.partition( ":" )
                generated.write( f"\"{ key.strip() }\": ( params ) => `{ _process_loc( loc.strip() ) }`,\n" )
        generated.write( "};\n" )
