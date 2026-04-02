import threading

LISTENING = "LISTENING"
SCANNING = "SCANNING"

CURRENT_STATE = LISTENING
RUNNING = True
_state_lock = threading.Lock()


def get_current_state():
    with _state_lock:
        return CURRENT_STATE


def set_current_state(state):
    global CURRENT_STATE
    with _state_lock:
        CURRENT_STATE = state


def is_running():
    with _state_lock:
        return RUNNING


def set_running(running):
    global RUNNING
    with _state_lock:
        RUNNING = running
