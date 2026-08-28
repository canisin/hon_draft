from flask import Flask, render_template, send_from_directory, session, request
from flask_socketio import SocketIO
import dotenv
from os import getenv, makedirs
import re

import utils
import players
import teams
import heroes
import messages
import draft
import commands

dotenv.load_dotenv()

def generate_message_templates():
    def replace_function_call( match ):
        body = match.group( 1 )
        body = re.sub( r"(?<!\\)@(\w+)", r"message.\1", body )
        return f"${{{ body }}}"

    def process_template( template ):
        template = re.sub( r"(?<!\\)\[\[(.*?)(?<!\\)\]\]", replace_function_call, template )
        template = re.sub( r"(?<!\\)#@(\w+)", r"${ formatMessage( { ...message, key: message.\1 } ) }", template )
        template = re.sub( r"(?<!\\)#(\w+)", r"${ formatMessage( { ...message, key: '\1' } ) }", template )
        template = re.sub( r"(?<!\\)@(\w+)", r"${ message.\1 }", template )
        template = template.replace( r"\[[", "[[" )
        template = template.replace( r"\]]", "]]" )
        template = template.replace( r"\@", "@" )
        template = template.replace( r"\#", "#" )
        return template

    makedirs( "generated/script", exist_ok = True )
    with open( "generated/script/messageTemplates.js", "w" ) as generated:
        generated.write( "const messageTemplates = {\n" )
        with open( "data/messages.txt" ) as messages:
            for line in messages:
                line = line.strip()
                if not line or line.startswith( "#" ):
                    continue
                key, _, template = line.partition( ":" )
                generated.write( f"\"{ key.strip() }\": ( message ) => `{ process_template( template.strip() ) }`,\n" )
        generated.write( "};\n" )

app = Flask( __name__ )
app.secret_key = "honzor"
socketio = SocketIO( app )

draft.initialize_state()
messages.initialize( socketio )
generate_message_templates()

## ROUTES ##
@app.route( "/" )
def home():
    if "name" not in session:
        session[ "name" ] = "Unnamed Player"
    if "id" not in session:
        session[ "id" ] = players.generate_id()
    return render_template( "home.html",
        team_size = draft.team_size,
        pool_size = draft.pool_size,
        timer_extension = draft.timer_extension,
    )

@app.route( "/name", methods = [ "POST" ] )
def name():
    id = session[ "id" ]
    name = request.form[ "name" ]
    utils.log( f"name request: id: { id }, name: '{ name }'" )
    player = players.get( id )
    player.set_name( name )
    session[ "name" ] = name
    return ""

@app.route( "/generated/<path:filename>" )
def generated( filename ):
    return send_from_directory( "generated", filename )

## INCOMING SOCKET EVENTS ##
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
def on_message( message ):
    player = players.get( session[ "id" ] )
    if commands.try_dispatch( player, message ): return
    messages.message( "message", player = player.id, text = message ).emit( team = player.team )

if __name__ == "__main__":
    host = getenv( "HOST" ) or "0.0.0.0"
    port = getenv( "PORT" ) or None
    debug = utils.getenv_bool( "DEBUG", False )
    extra_files = [ "data/messages.txt" ]
    socketio.run( app, allow_unsafe_werkzeug = True, host = host, port = port, debug = debug, extra_files = extra_files )
