from sys import stderr
from os import getenv
import threading
from time import time
import enum
from enum import Enum

def log( message ):
    print( message, file = stderr )

def getenv_bool( key, default ):
    value = getenv( key )
    if not value: return default
    value = value.lower()
    if value in ( "true", "yes" ): return True
    if value in ( "false", "no" ): return False
    raise ValueError()

class Timer:
    class State( Enum ):
        stopped = enum.auto()
        running = enum.auto()
        paused = enum.auto()

    def __init__( self, function ):
        self.function = function
        self.lock = threading.Lock()
        self.timer = None
        self.last_start = 0
        self.remaining_interval = 0
        self.state = Timer.State.stopped

    def _set_timer( self, seconds ):
        timer = None
        def function():
            with self.lock:
                if timer != self.timer: return  # timer has changed, this capture is invalid
                self.timer = None
                self.state = Timer.State.stopped
            self.function()
        self.timer = threading.Timer( seconds, function )
        timer = self.timer
        self.timer.start()
        self.last_start = time()
        self.state = Timer.State.running

    def _clear_timer( self ):
        assert self.state == Timer.State.running
        self.timer.cancel()
        self.timer = None

    def _calc_remaining_interval( self ):
        assert self.state == Timer.State.running
        elapsed = time() - self.last_start
        return max( 0, self.timer.interval - elapsed )

    def start( self, seconds ):
        with self.lock:
            assert self.state == Timer.State.stopped
            self._set_timer( seconds )

    def cancel( self ):
        with self.lock:
            if self.state == Timer.State.stopped: return    # nothing to cancel
            if self.state == Timer.State.running: self._clear_timer()
            self.state = Timer.State.stopped

    def get_remaining_interval( self ):
        with self.lock:
            if self.state == Timer.State.stopped: return 0
            if self.state == Timer.State.paused: return self.remaining_interval
            if self.state == Timer.State.running: return self._calc_remaining_interval()

    def try_pause( self ):
        with self.lock:
            if self.state == Timer.State.stopped: return False      # nothing to pause
            if self.state == Timer.State.paused: return False       # already paused
            remaining_interval = self._calc_remaining_interval()
            self._clear_timer()
            self.remaining_interval = remaining_interval
            self.state = Timer.State.paused
            return True

    def try_resume( self ):
        with self.lock:
            if self.state == Timer.State.stopped: return False      # nothing to resume
            if self.state == Timer.State.running: return False      # already running
            self._set_timer( self.remaining_interval )
            return True

    def try_extend( self, seconds ):
        with self.lock:
            if self.state == Timer.State.stopped: return False      # nothing to extend
            if self.state == Timer.State.running:
                remaining_interval = self._calc_remaining_interval()
                self._clear_timer()
                self._set_timer( remaining_interval + seconds )
            if self.state == Timer.State.paused:
                self.remaining_interval += seconds
            return True

    def serialize( self ):
        with self.lock:
            if self.state == Timer.State.stopped: return { "state": "stopped", "seconds": 0 }
            if self.state == Timer.State.running: return { "state": "running", "seconds": self._calc_remaining_interval() }
            if self.state == Timer.State.paused:  return { "state": "paused",  "seconds": self.remaining_interval }
