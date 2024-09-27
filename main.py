from flask import Flask
from flask_socketio import SocketIO

app = Flask( __name__ )
socketio = SocketIO( app )

@app.route( "/" )
def home():
    return "Hello world!"

if __name__ == "__main__":
    socketio.run( app, host = "localhost", port = 80, debug = True )
