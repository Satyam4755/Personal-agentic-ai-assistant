const chatMessages = document.getElementById('chat-messages');
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

// Utility wrappers for exactly matching requested API
function addUserMessage(text) {
    addMessage('user', text);
}

function addAssistantMessage(text) {
    addMessage('assistant', text);
}

function sendCommand() {
    const inputEl = document.getElementById("commandInput");
    const command = inputEl.value.trim();

    if (!command) return;
    
    console.log("Sending command:", command);

    addUserMessage(command);

    fetch("/command", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ command })
    })
    .then(res => res.json())
    .then(data => {
        if (data.response) {
            addAssistantMessage(data.response);
        }
    })
    .catch(err => {
        console.error(err);
        addAssistantMessage("Error processing command");
    });

    inputEl.value = "";
}

document.getElementById("commandInput").addEventListener("keypress", function(e) {
    if (e.key === "Enter") {
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
