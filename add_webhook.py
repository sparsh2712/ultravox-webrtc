import requests
import os 
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ULTRAVOX_API_KEY")
url = "https://api.ultravox.ai/api/webhooks"
payload = {
    "events": ["call.started"],
    "url": "https://d425-13-203-58-245.ngrok-free.app/api/webhooks/call-started"
}
headers = {
    "X-API-Key": api_key,
    "Content-Type": "application/json"
}
response = requests.request("POST", url, json=payload, headers=headers)
print(response.text)