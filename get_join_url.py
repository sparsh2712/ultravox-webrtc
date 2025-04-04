import requests 
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("ULTRAVOX_API_KEY")
url = "https://api.ultravox.ai/api/calls"

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
print(data["joinUrl"])