from flask import Flask, jsonify, render_template, request
import requests
import os
from dotenv import load_dotenv
import threading
from datetime import datetime, timezone, timedelta
import os
import time
import wave
import io
import subprocess

app = Flask(__name__, static_folder='static', template_folder='templates')
load_dotenv()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get-join-url', methods=['POST'])
def get_join_url():
    api_key = os.getenv("ULTRAVOX_API_KEY")
    if not api_key:
        return jsonify({"error": "Ultravox API key not found"}), 500
        
    url = "https://api.ultravox.ai/api/calls"
    
    try:
        # Read system prompt
        try:
            with open("prompt.txt", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "You are a helpful AI assistant."
            print("Warning: prompt.txt not found, using default prompt")
        
        # Get selected voice
        voice_id = request.json.get('voiceId')
        if not voice_id:
            voice_id = "Chinmay-English-Indian"  # Default fallback
        
        # Create base payload
        payload = {
            "systemPrompt": system_prompt,
            "temperature": 0.1,
            "model": "fixie-ai/ultravox",
            "voice": "a14762fb-8e3c-494d-8765-4ff886acc318",
            "medium": {"webRtc": {}}
        }
        
        # Print payload for debugging
        print("Ultravox API Payload:", payload)
        
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        
        # Make the API request
        response = requests.request("POST", url, json=payload, headers=headers)
        
        # Check response status - 201 is success (Created)
        if response.status_code not in [200, 201]:
            print(f"Ultravox API error: {response.status_code}, Response: {response.text}")
            return jsonify({"error": f"Ultravox API returned status code {response.status_code}"}), 500
            
        data = response.json()
        
        # Validate response contains joinUrl
        if "joinUrl" not in data:
            print(f"Unexpected Ultravox API response: {data}")
            return jsonify({"error": "Ultravox API response missing joinUrl"}), 500
            
        return jsonify({"joinUrl": data["joinUrl"]})
    
    except Exception as e:
        print(f"Error getting join URL: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/elevenlabs-voices', methods=['GET'])
def get_elevenlabs_voices():
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
    
    if not elevenlabs_api_key:
        return jsonify({"error": "ElevenLabs API key not found"}), 500
    
    url = "https://api.elevenlabs.io/v1/voices"
    
    headers = {
        "xi-api-key": elevenlabs_api_key
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return jsonify({"error": f"ElevenLabs API returned status code {response.status_code}"}), 500
        
        data = response.json()
        
        # Debug the response structure
        print("ElevenLabs API Response:", data)
        
        # Check if 'voices' is in the response
        if "voices" not in data:
            return jsonify({"error": "Unexpected API response format - 'voices' key not found"}), 500
        
        voices = []
        for voice in data["voices"]:
            # Ensure the required keys exist
            voice_id = voice.get("voice_id")
            name = voice.get("name")
            
            if voice_id and name:
                voices.append({"id": voice_id, "name": name})
        
        return jsonify({"voices": voices})
    except Exception as e:
        print("Error fetching ElevenLabs voices:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/api/ultravox-voices', methods=['GET'])
def get_ultravox_voices():
    api_key = os.getenv("ULTRAVOX_API_KEY")
    if not api_key:
        return jsonify({"error": "Ultravox API key not found"}), 500
    
    url = "https://api.ultravox.ai/api/voices"
    
    headers = {
        "X-API-Key": api_key
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code not in [200, 201]:
            print(f"Ultravox API error: {response.status_code}, Response: {response.text}")
            return jsonify({"error": f"Failed to get voices: {response.status_code}"}), 500
            
        data = response.json()
        data = data.get("results", [])
        # Print the response for debugging
        print("Ultravox voices response:", data)
        
        # Process the voices based on the response structure
        voices = []
        if isinstance(data, list):
            for voice in data:
                voice_id = voice.get("voiceId")
                name = voice.get("name", "Unnamed Voice")
                voices.append({"id": voice_id, "name": name})
        
        # Add default voices as fallback if needed
        if not voices:
            defaults = [
                {"id": "Chinmay-English-Indian", "name": "Chinmay (Indian)"},
                {"id": "Emma-English-US", "name": "Emma (US)"},
                {"id": "Ryan-English-US", "name": "Ryan (US)"},
                {"id": "Ana-English-US", "name": "Ana (US)"},
                {"id": "Thomas-English-UK", "name": "Thomas (UK)"}
            ]
            voices.extend(defaults)
        
        return jsonify({"voices": voices})
    except Exception as e:
        print(f"Error fetching Ultravox voices: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/verify-admin', methods=['POST'])
def verify_admin():
    # Get the admin password from .env file
    admin_password = os.getenv("ADMIN_PASSWORD")
    
    if not admin_password:
        return jsonify({"success": False, "error": "Admin password not configured on server"}), 400
    
    # Get the password from the request
    data = request.json
    password = data.get('password', '')
    
    if password == admin_password:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Invalid password"}), 401

@app.route('/api/upload-feedback', methods=['POST'])
def upload_feedback():
    try:
        # Check if audio file was uploaded
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        call_id = request.form.get('callId', 'unknown')
        
        # Create directories if they don't exist
        feedback_dir = "feedback"
        if not os.path.exists(feedback_dir):
            os.makedirs(feedback_dir)
        
        # Generate filename with timestamp and call ID
        ist_offset = timedelta(hours=5, minutes=30)
        ist_timezone = timezone(ist_offset)
        current_time_ist = datetime.now(timezone.utc).astimezone(ist_timezone)
        timestamp = current_time_ist.strftime("%Y-%m-%d-%H-%M")
        filename = f"{timestamp}_{call_id}"
        
        # Save original WebM file
        webm_path = os.path.join(feedback_dir, f"{filename}.webm")
        audio_file.save(webm_path)
        
        # Convert to MP3 using FFmpeg (if available)
        mp3_path = os.path.join(feedback_dir, f"{filename}.mp3")
        try:
            # Check if FFmpeg is available
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            
            # Convert WebM to MP3
            command = [
                "ffmpeg",
                "-i", webm_path,
                "-codec:a", "libmp3lame",
                "-qscale:a", "2",
                mp3_path
            ]
            
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            # Remove the original WebM file after successful conversion
            os.remove(webm_path)
            
            final_path = mp3_path
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            # FFmpeg not available or conversion failed, keep the WebM file
            print(f"FFmpeg conversion failed or not available: {str(e)}")
            final_path = webm_path
        
        return jsonify({
            "success": True,
            "message": f"Feedback saved as {os.path.basename(final_path)}"
        })
        
    except Exception as e:
        print(f"Error saving feedback: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/api/save-transcript', methods=['POST'])
def save_transcripts():
    data = request.json
    print(f"Webhook data: {data}")
    
    try:
        event_type = data.get('event')
        call_data = data.get('call', {})
        
        print(f"Event type: {event_type}")
        
        # Handle call.ended event
        if event_type == 'call.ended':
            call_id = call_data.get('callId')
            join_time = call_data.get('created')
            if call_id:
                print(f"Call ended event for call ID: {call_id}")
                # Process in background thread to avoid webhook timeout
                threading.Thread(target=process_transcript, args=(call_id,join_time)).start()
                return jsonify({"status": "transcript processing started"}), 200
            else:
                print("Warning: call.ended event received but no callId found")
                return jsonify({"status": "error", "message": "No callId in payload"}), 400
        else:
            # Just acknowledge receipt of other event types
            return jsonify({"status": "acknowledged", "event": event_type}), 200
    
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
def process_transcript(call_id,join_time):
    print(f"Starting transcript processing for call ID: {call_id}")
    
    # Allow a short delay for call to fully complete on Ultravox side
    time.sleep(3)
    
    api_key = os.getenv("ULTRAVOX_API_KEY")
    if not api_key:
        print("Error: Ultravox API key not found in environment variables")
        return
    
    try:
        # Step 1: Get the call stages
        print(f"Fetching stages for call: {call_id}")
        stage_url = f"https://api.ultravox.ai/api/calls/{call_id}/stages"
        headers = {"X-API-Key": api_key}
        
        stage_response = requests.get(stage_url, headers=headers)
        
        if stage_response.status_code != 200:
            print(f"Error: Failed to get stages. Status code: {stage_response.status_code}")
            print(f"Response: {stage_response.text}")
            return
        
        stage_data = stage_response.json()
        results = stage_data.get("results", [])
        
        if not results:
            print(f"No stages found for call ID: {call_id}")
            return
        
        # Get the first stage ID
        stage_id = results[0].get("callStageId")
        print(f"Using stage ID: {stage_id}")
        
        # Step 2: Get the conversation messages
        print(f"Fetching messages for stage: {stage_id}")
        messages_url = f"https://api.ultravox.ai/api/calls/{call_id}/stages/{stage_id}/messages"
        
        messages_response = requests.get(messages_url, headers=headers)
        
        if messages_response.status_code != 200:
            print(f"Error: Failed to get messages. Status code: {messages_response.status_code}")
            print(f"Response: {messages_response.text}")
            return
        
        messages_data = messages_response.json()
        messages = messages_data.get("results", [])
        print(f"Found {len(messages)} messages")
        
        # Step 3: Format the transcript
        transcript_content = ""
        for msg in messages:
            role = msg.get('role')
            text = msg.get('text', '')
            
            if not text:
                continue
            
            if role == 'MESSAGE_ROLE_USER':
                speaker = 'USER'
            elif role == 'MESSAGE_ROLE_AGENT':
                speaker = 'AGENT'
            else:
                continue
            
            transcript_content += f"{speaker}: \"{text}\"\n\n"
        
        # Step 4: Save to file with date-based directory structure
        ist_offset = timedelta(hours=5, minutes=30)
        ist_timezone = timezone(ist_offset)
        current_time_ist = datetime.now(timezone.utc).astimezone(ist_timezone)
        date_str = current_time_ist.strftime("%Y-%m-%d")
        time_str = current_time_ist.strftime("%H-%M-%S")
        
        # Create directories if they don't exist
        directory = f"transcripts/{date_str}"
        if not os.path.exists("transcripts"):
            os.makedirs("transcripts")
            print("Created base directory: transcripts")
        
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created date directory: {directory}")
        
        # Save file with timestamp and call ID in filename
        output_file = f"{directory}/{time_str}_{call_id}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(transcript_content)
        
        print(f"Transcript successfully saved to {output_file}")
        
    except Exception as e:
        import traceback
        print(f"Error processing transcript: {str(e)}")
        print(traceback.format_exc())

if __name__ == '__main__':
    app.run(debug=True, port=8000, host='0.0.0.0')