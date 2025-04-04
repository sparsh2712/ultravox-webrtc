from flask import Flask, jsonify, render_template, request
import requests
import os
from dotenv import load_dotenv

app = Flask(__name__, static_folder='static', template_folder='templates')
load_dotenv()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get-join-url', methods=['GET'])
def get_join_url():
    api_key = os.getenv("ULTRAVOX_API_KEY")
    url = "https://api.ultravox.ai/api/calls"

    try:
        with open("prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()
        
        payload = {
            "systemPrompt": system_prompt,
            "temperature": 0.1,
            "model": "fixie-ai/ultravox",
            "voice": "Chinmay-English-Indian",
            "medium": {"webRtc": {}}
        }

        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

        response = requests.request("POST", url, json=payload, headers=headers)
        data = response.json()
        return jsonify({"joinUrl": data["joinUrl"]})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080)