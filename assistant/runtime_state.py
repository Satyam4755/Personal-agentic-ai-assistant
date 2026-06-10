import threading

LISTENING = "LISTENING"
SCANNING = "SCANNING"
IDLE = "IDLE"
PROCESSING = "PROCESSING"
SPEAKING = "SPEAKING"

CURRENT_STATE = LISTENING
ASSISTANT_STATE = IDLE
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


def get_assistant_state():
    with _state_lock:
        return ASSISTANT_STATE


def set_assistant_state(state):
    global ASSISTANT_STATE
    with _state_lock:
        ASSISTANT_STATE = state
