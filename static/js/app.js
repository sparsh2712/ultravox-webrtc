// Import Ultravox client as an ES module
import { UltravoxSession, UltravoxSessionStatus } from 'https://cdn.jsdelivr.net/npm/ultravox-client/+esm';

document.addEventListener('DOMContentLoaded', () => {
    const startCallBtn = document.getElementById('start-call');
    const endCallBtn = document.getElementById('end-call');
    const statusMessage = document.getElementById('status-message');
    const chatMessages = document.getElementById('chat-messages');
    
    let ultravoxSession = null;
    let lastTranscript = null;

    function updateStatus(message) {
        statusMessage.textContent = message;
    }

    function addMessage(text, speaker) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message-container');
        messageDiv.classList.add(speaker);
        
        const messageText = document.createElement('p');
        messageText.textContent = text;
        
        messageDiv.appendChild(messageText);
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function clearWaitingMessage() {
        const waitingMessages = document.querySelectorAll('.message-container.waiting');
        waitingMessages.forEach(msg => msg.remove());
    }

    startCallBtn.addEventListener('click', async () => {
        updateStatus('Connecting to agent...');
        startCallBtn.disabled = true;
        
        try {
            // Get join URL from backend
            const response = await fetch('/api/get-join-url');
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            const joinUrl = data.joinUrl;
            
            // Initialize Ultravox session
            ultravoxSession = new UltravoxSession();
            
            // Set up event handlers
            ultravoxSession.addEventListener('status', () => {
                const status = ultravoxSession.status;
                
                if (status === UltravoxSessionStatus.CONNECTING) {
                    updateStatus('Connecting...');
                } else if (status === UltravoxSessionStatus.CONNECTED) {
                    updateStatus('Connected');
                    clearWaitingMessage();
                } else if (status === UltravoxSessionStatus.LISTENING) {
                    updateStatus('Agent is listening...');
                } else if (status === UltravoxSessionStatus.SPEAKING) {
                    updateStatus('Agent is speaking...');
                } else if (status === UltravoxSessionStatus.DISCONNECTED) {
                    updateStatus('Disconnected');
                    endCall();
                }
            });
            
            ultravoxSession.addEventListener('transcripts', () => {
                const transcripts = ultravoxSession.transcripts;
                if (transcripts.length === 0) return;
                
                const transcript = transcripts[transcripts.length - 1];
                
                if (lastTranscript && lastTranscript.speaker !== transcript.speaker) {
                    if (lastTranscript.text.trim()) {
                        addMessage(lastTranscript.text, lastTranscript.speaker);
                    }
                    lastTranscript = null;
                }
                
                lastTranscript = transcript;
                
                if (transcript.isFinal) {
                    addMessage(transcript.text, transcript.speaker);
                    lastTranscript = null;
                }
            });
            
            // Join the call
            ultravoxSession.joinCall(joinUrl);
            
            // Update UI
            endCallBtn.disabled = false;
            updateStatus('Call started');
            
        } catch (error) {
            console.error('Failed to start call:', error);
            updateStatus('Failed to start call: ' + error.message);
            startCallBtn.disabled = false;
        }
    });
    
    endCallBtn.addEventListener('click', endCall);
    
    async function endCall() {
        if (ultravoxSession) {
            try {
                await ultravoxSession.leaveCall();
            } catch (error) {
                console.error('Error leaving call:', error);
            }
            
            ultravoxSession = null;
        }
        
        // Update UI
        startCallBtn.disabled = false;
        endCallBtn.disabled = true;
        updateStatus('Call ended');
        
        // Add waiting message
        clearWaitingMessage();
        const waitingDiv = document.createElement('div');
        waitingDiv.classList.add('message-container', 'waiting');
        waitingDiv.innerHTML = '<p>Click the button to start a new conversation...</p>';
        chatMessages.appendChild(waitingDiv);
    }
});