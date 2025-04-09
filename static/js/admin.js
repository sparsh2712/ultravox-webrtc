// admin.js - Handle admin authentication and feedback recording

document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const adminModeBtn = document.getElementById('admin-mode-btn');
    const adminModal = document.getElementById('admin-modal');
    const feedbackModal = document.getElementById('feedback-modal');
    const adminLoginBtn = document.getElementById('admin-login-btn');
    const adminPasswordInput = document.getElementById('admin-password');
    const adminErrorMsg = document.getElementById('admin-error');
    const closeModalBtns = document.querySelectorAll('.close-modal');
    const feedbackBtn = document.getElementById('feedback-btn');
    
    // Feedback recording elements
    const startRecordingBtn = document.getElementById('start-recording');
    const stopRecordingBtn = document.getElementById('stop-recording');
    const uploadFeedbackBtn = document.getElementById('upload-feedback');
    const recordingStatus = document.getElementById('recording-status');
    const recordingTime = document.getElementById('recording-time');
    const audioPreview = document.getElementById('audio-preview');
    
    // Audio recording variables
    let mediaRecorder = null;
    let audioChunks = [];
    let recordingStartTime = 0;
    let recordingTimer = null;
    let audioBlob = null;
    let isAdminMode = false;
    
    // Show admin login modal
    adminModeBtn.addEventListener('click', () => {
        if (isAdminMode) {
            // If already in admin mode, exit admin mode
            exitAdminMode();
        } else {
            // Show admin login modal
            adminModal.style.display = 'block';
            adminPasswordInput.focus();
            adminPasswordInput.value = '';
            adminErrorMsg.textContent = '';
        }
    });
    
    // Show feedback modal when feedback button is clicked
    feedbackBtn.addEventListener('click', () => {
        // Reset feedback modal state
        stopRecordingBtn.disabled = true;
        startRecordingBtn.disabled = false;
        uploadFeedbackBtn.disabled = true;
        recordingStatus.textContent = 'Ready to record';
        recordingTime.textContent = '00:00';
        audioPreview.innerHTML = '';
        
        // Show feedback modal
        feedbackModal.style.display = 'block';
    });
    
    // Close modals when clicking on X
    closeModalBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            modal.style.display = 'none';
            
            // If closing feedback modal, stop any ongoing recording
            if (modal === feedbackModal && mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
                clearInterval(recordingTimer);
            }
        });
    });
    
    // Close modals when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === adminModal) {
            adminModal.style.display = 'none';
        } else if (e.target === feedbackModal) {
            feedbackModal.style.display = 'none';
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
                clearInterval(recordingTimer);
            }
        }
    });
    
    // Handle admin login
    adminLoginBtn.addEventListener('click', verifyAdmin);
    adminPasswordInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            verifyAdmin();
        }
    });
    
    // Verify admin password
    async function verifyAdmin() {
        const password = adminPasswordInput.value.trim();
        
        if (!password) {
            adminErrorMsg.textContent = 'Please enter a password';
            return;
        }
        
        try {
            const response = await fetch('/api/verify-admin', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ password })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Password correct - enable admin mode
                enableAdminMode();
                adminModal.style.display = 'none';
            } else {
                // Password incorrect
                adminErrorMsg.textContent = data.error || 'Invalid password';
            }
        } catch (error) {
            console.error('Error verifying admin:', error);
            adminErrorMsg.textContent = 'Verification failed. Please try again.';
        }
    }
    
    // Enable admin mode
    function enableAdminMode() {
        isAdminMode = true;
        adminModeBtn.classList.add('admin-mode-active');
        adminModeBtn.textContent = 'Exit Admin Mode';
        
        // Show feedback button
        feedbackBtn.style.display = 'inline-block';
    }
    
    // Exit admin mode
    function exitAdminMode() {
        isAdminMode = false;
        adminModeBtn.classList.remove('admin-mode-active');
        adminModeBtn.textContent = 'Admin Mode';
        
        // Hide feedback button
        feedbackBtn.style.display = 'none';
    }
    
    // Audio recording functionality
    startRecordingBtn.addEventListener('click', startRecording);
    stopRecordingBtn.addEventListener('click', stopRecording);
    uploadFeedbackBtn.addEventListener('click', uploadFeedback);
    
    // Start audio recording
    async function startRecording() {
        try {
            audioChunks = [];
            
            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Create media recorder
            mediaRecorder = new MediaRecorder(stream);
            
            // Handle data available event
            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    audioChunks.push(e.data);
                }
            };
            
            // Handle recording stop
            mediaRecorder.onstop = () => {
                // Enable/disable buttons
                startRecordingBtn.disabled = false;
                stopRecordingBtn.disabled = true;
                uploadFeedbackBtn.disabled = false;
                
                // Create audio blob
                audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                
                // Create audio element for preview
                const audioURL = URL.createObjectURL(audioBlob);
                const audioElement = document.createElement('audio');
                audioElement.src = audioURL;
                audioElement.controls = true;
                audioElement.style.width = '100%';
                
                // Clear previous preview and add new one
                audioPreview.innerHTML = '';
                audioPreview.appendChild(audioElement);
                
                // Update status
                recordingStatus.textContent = 'Recording finished. Ready to upload.';
                
                // Stop all tracks to release microphone
                stream.getTracks().forEach(track => track.stop());
                
                // Clear timer
                clearInterval(recordingTimer);
            };
            
            // Start recording
            mediaRecorder.start();
            
            // Update UI
            startRecordingBtn.disabled = true;
            stopRecordingBtn.disabled = false;
            recordingStatus.textContent = 'Recording in progress...';
            
            // Start timer
            recordingStartTime = Date.now();
            updateRecordingTime();
            recordingTimer = setInterval(updateRecordingTime, 1000);
            
        } catch (error) {
            console.error('Error starting recording:', error);
            recordingStatus.textContent = 'Failed to access microphone. Please check permissions.';
        }
    }
    
    // Stop recording
    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
        }
    }
    
    // Update recording time display
    function updateRecordingTime() {
        const elapsedTime = Math.floor((Date.now() - recordingStartTime) / 1000);
        const minutes = Math.floor(elapsedTime / 60).toString().padStart(2, '0');
        const seconds = (elapsedTime % 60).toString().padStart(2, '0');
        recordingTime.textContent = `${minutes}:${seconds}`;
    }
    
    // Upload feedback recording
    async function uploadFeedback() {
        if (!audioBlob) {
            recordingStatus.textContent = 'No recording to upload.';
            return;
        }
        
        try {
            // Get current call ID if available
            let callId = 'unknown';
            if (window.ultravoxSession) {
                callId = window.ultravoxSession.callId || 'unknown';
            }
            
            // Create form data with audio file
            const formData = new FormData();
            formData.append('audio', audioBlob, 'feedback.webm');
            formData.append('callId', callId);
            
            // Update status
            recordingStatus.textContent = 'Uploading feedback...';
            uploadFeedbackBtn.disabled = true;
            
            // Send to server
            const response = await fetch('/api/upload-feedback', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                recordingStatus.textContent = 'Feedback uploaded successfully!';
                
                // Clear audio preview and reset
                audioPreview.innerHTML = '';
                audioBlob = null;
                
                // Close modal after short delay
                setTimeout(() => {
                    feedbackModal.style.display = 'none';
                }, 1500);
            } else {
                throw new Error(result.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Error uploading feedback:', error);
            recordingStatus.textContent = 'Failed to upload: ' + error.message;
            uploadFeedbackBtn.disabled = false;
        }
    }
});