from flask import Flask, jsonify, render_template, request
import requests
import os
from dotenv import load_dotenv

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

if __name__ == '__main__':
    app.run(debug=True, port=8000, host='0.0.0.0')