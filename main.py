from flask import Flask
from flask_socketio import SocketIO

from threading import Timer
import atexit

app = Flask( __name__ )
socketio = SocketIO( app )

state = { "value": 0 }
updateTimer = None

def update():
    state[ "value" ] += 1

    startUpdates()

def startUpdates():
    global updateTimer
    updateTimer = Timer( 1, update )
    updateTimer.start()

def cancelUpdates():
    updateTimer.cancel()

@app.route( "/" )
def home():
    return f"Hello world! { state[ "value" ] }"

if __name__ == "__main__":
    startUpdates()
    atexit.register( cancelUpdates )

    socketio.run( app, host = "localhost", port = 80, debug = True )
