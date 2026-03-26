import queue
import json
from flask import Flask, send_from_directory, request, Response
import logging

app = Flask(__name__, template_folder='ui/templates', static_folder='ui/static')
# Suppress werkzeug logging to avoid cluttering our terminal logs stream
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

clients = []
command_queue = queue.Queue()

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
def command():
    content = request.json.get('command')
    if content:
        command_queue.put(content)
    return {"status": "ok"}
