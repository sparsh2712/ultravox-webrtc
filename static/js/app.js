import { UltravoxSession, UltravoxSessionStatus } from 'https://cdn.jsdelivr.net/npm/ultravox-client/+esm';

document.addEventListener('DOMContentLoaded', () => {
    const startCallBtn = document.getElementById('start-call');
    const endCallBtn = document.getElementById('end-call');
    const statusMessage = document.getElementById('status-message');
    const chatMessages = document.getElementById('chat-messages');
    const toggleSettingsBtn = document.getElementById('toggle-settings');
    const settingsContent = document.getElementById('settings-content');
    const voiceSelect = document.getElementById('voice-select');
    const refreshVoicesBtn = document.getElementById('refresh-voices');
    
    let ultravoxSession = null;
    let lastTranscript = null;
    let settingsVisible = false;

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
        
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function clearWaitingMessage() {
        const waitingMessages = document.querySelectorAll('.message-container.waiting');
        waitingMessages.forEach(msg => msg.remove());
    }
    
    toggleSettingsBtn.addEventListener('click', () => {
        settingsVisible = !settingsVisible;
        settingsContent.style.display = settingsVisible ? 'block' : 'none';
        toggleSettingsBtn.textContent = settingsVisible ? 'Hide Options' : 'Show Options';
    });
    
    refreshVoicesBtn.addEventListener('click', fetchUltravoxVoices);
    
    async function fetchUltravoxVoices() {
        try {
            updateStatus('Loading Ultravox voices...');
            const response = await fetch('/api/ultravox-voices');
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            voiceSelect.innerHTML = '';
            
            if (!data.voices || data.voices.length === 0) {
                const option = document.createElement('option');
                option.value = "";
                option.textContent = "No voices available";
                voiceSelect.appendChild(option);
                throw new Error("No voices found");
            }
            
            data.voices.forEach(voice => {
                const option = document.createElement('option');
                option.value = voice.id;
                option.textContent = voice.name;
                voiceSelect.appendChild(option);
            });
            
            updateStatus('Ready to start');
        } catch (error) {
            console.error('Failed to fetch voices:', error);
            updateStatus('Failed to load voices: ' + error.message);
            
            if (voiceSelect.options.length === 0) {
                const option = document.createElement('option');
                option.value = "Ruhaan-Elevenlabs";
                option.textContent = "Default Voice";
                voiceSelect.appendChild(option);
            }
        }
    }

    startCallBtn.addEventListener('click', async () => {
        updateStatus('Connecting to agent...');
        startCallBtn.disabled = true;
        
        try {
            const selectedVoice = voiceSelect.value;
            
            const response = await fetch('/api/get-join-url', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    voiceId: selectedVoice
                })
            });
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            const joinUrl = data.joinUrl;
            
            ultravoxSession = new UltravoxSession();
            window.ultravoxSession = ultravoxSession; // Make it globally accessible for feedback recording
            
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
            
            ultravoxSession.joinCall(joinUrl);
            
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
            window.ultravoxSession = null;
        }
        
        startCallBtn.disabled = false;
        endCallBtn.disabled = true;
        updateStatus('Call ended');
        
        clearWaitingMessage();
        const waitingDiv = document.createElement('div');
        waitingDiv.classList.add('message-container', 'waiting');
        waitingDiv.innerHTML = '<p>Click the button to start a new conversation...</p>';
        chatMessages.appendChild(waitingDiv);
    }
    
    // Fetch voices when the page loads
    fetchUltravoxVoices();
});