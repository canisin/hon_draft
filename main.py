from os import getenv
import dotenv

dotenv.load_dotenv()

from app import app, socketio
import routes  # route registrations
import sockets # socket registrations
import utils
import draft
import localization

draft.initialize_state()
localization.generate_localization_script()

if __name__ == "__main__":
    host = getenv( "HOST" ) or "0.0.0.0"
    port = getenv( "PORT" ) or None
    debug = utils.getenv_bool( "DEBUG", False )
    extra_files = [ "data/localization.txt" ]
    socketio.run( app, allow_unsafe_werkzeug = True, host = host, port = port, debug = debug, extra_files = extra_files )
