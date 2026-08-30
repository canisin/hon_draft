from flask import render_template, send_from_directory, session, request

from app import app
import players
import utils
import draft

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
