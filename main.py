from flask import Flask
from flask_socketio import SocketIO

from threading import Thread
from time import sleep

app = Flask( __name__ )
socketio = SocketIO( app )

state = { "value": 0 }

def logic():
    print( "starting logic thread" )
    while True:
        sleep( 1 )
        update()

def update():
    state[ "value" ] += 1

@app.route( "/" )
def home():
    return f"Hello world! { state[ "value" ] }"

if __name__ == "__main__":
    Thread( target = logic, daemon = True ).start()

    socketio.run( app, host = "localhost", port = 80 )
