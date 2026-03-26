const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const orb = document.getElementById('assistant-orb');
const terminalOutput = document.getElementById('terminal-output');

// Utility to push new chat messages
function addMessage(role, text) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', role);
    msgDiv.textContent = text;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Utility to push logs to the terminal
function logTerminal(text) {
    const logLine = document.createElement('p');
    logLine.textContent = `> ${text}`;
    terminalOutput.appendChild(logLine);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

// Handle sending commands
async function sendCommand() {
    const text = chatInput.value.trim();
    if (!text) return;

    // Echo to UI
    addMessage('user', text);
    chatInput.value = '';

    try {
        await fetch('/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: text })
        });
    } catch (err) {
        logTerminal(`Error sending command: ${err.message}`);
    }
}

sendBtn.addEventListener('click', sendCommand);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendCommand();
    }
});

// Setup Server-Sent Events (SSE) stream
function setupEventStream() {
    const eventSource = new EventSource('/stream');

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        const { type } = data;

        if (type === 'log') {
            logTerminal(data.content);
        } else if (type === 'chat') {
            const role = data.role === 'user' ? 'user' : 'assistant';
            addMessage(role, data.content);
        } else if (type === 'state') {
            if (data.status === 'speaking') {
                orb.classList.remove('idle');
                orb.classList.add('speaking');
            } else {
                orb.classList.remove('speaking');
                orb.classList.add('idle');
            }
        }
    };

    eventSource.onerror = function() {
        logTerminal('Connection lost. Attempting to reconnect...');
        eventSource.close();
        setTimeout(setupEventStream, 3000);
    };

    logTerminal('Connected to Assistant Core API.');
}

// Initialize
setupEventStream();
