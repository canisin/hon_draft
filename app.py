from flask import Flask
from flask_socketio import SocketIO

app = Flask( __name__ )
app.secret_key = "honzor"
socketio = SocketIO( app )
