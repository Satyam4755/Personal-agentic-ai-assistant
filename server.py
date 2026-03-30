import queue
import json
from flask import Flask, send_from_directory, request, Response
import logging

app = Flask(__name__, template_folder='ui/templates', static_folder='ui/static')
# Suppress werkzeug logging to avoid cluttering our terminal logs stream
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

clients = []

# Expose backend instances here
command_handler = None

def emit_event(event_type, **kwargs):
    kwargs['type'] = event_type
    data = json.dumps(kwargs)
    for q in list(clients):
        try:
            q.put_nowait(data)
        except queue.Full:
            pass

@app.route('/')
def index():
    return send_from_directory('ui/templates', 'index.html')

@app.route('/stream')
def stream():
    def event_stream(q):
        try:
            while True:
                data = q.get()
                yield f"data: {data}\n\n"
        except GeneratorExit:
            if q in clients:
                clients.remove(q)

    # Max size ensures disconnected clients don't bloat memory
    q = queue.Queue(maxsize=100)
    clients.append(q)
    return Response(event_stream(q), mimetype="text/event-stream")

@app.route('/command', methods=['POST'])
def handle_command():
    data = request.json
    command = data.get('command')

    if not command:
        return {"response": "No command received"}

    if not command_handler:
        return {"response": "Backend not ready"}

    response, should_exit = command_handler.handle_command(command)

    if hasattr(command_handler, "voice_engine") and command_handler.voice_engine:
        try:
            command_handler.voice_engine._suppress_ui_chat = True
            command_handler.voice_engine.speak(response)
            command_handler.voice_engine._suppress_ui_chat = False
        except:
            pass
            
    if should_exit:
        def shutdown():
            import time
            import os
            time.sleep(2)
            os._exit(0)
        import threading
        threading.Thread(target=shutdown, daemon=True).start()

    return {"response": response, "should_exit": should_exit}

@app.route('/toggle_voice', methods=['POST'])
def toggle_voice_api():
    data = request.json
    state = data.get('state', True)
    from assistant.voice_engine import toggle_voice
    toggle_voice(state)
    return {"status": "success", "voice_enabled": state}

@app.route('/stop', methods=['POST'])
def stop():
    if command_handler and hasattr(command_handler, "voice_engine"):
        command_handler.voice_engine.stop_speaking()
    return {"status": "stopped"}
