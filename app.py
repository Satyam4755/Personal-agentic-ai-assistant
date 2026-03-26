import webview
import threading
from main import main as start_backend

def start_assistant():
    # Starts both the assistant loop and the Flask API
    start_backend()

if __name__ == '__main__':
    # Run the entire backend in a background thread
    threading.Thread(target=start_assistant, daemon=True).start()
    
    # Run PyWebview on the main thread
    webview.create_window("Jarvis Assistant", "http://127.0.0.1:3425")
    webview.start()
