import requests
import os 
from dotenv import load_dotenv
load_dotenv()

ngrok_url = os.getenv("NGROK_URL")
api_key = os.getenv("ULTRAVOX_API_KEY")
base_url = "https://api.ultravox.ai/api/webhooks"

headers = {
    "X-API-Key": api_key
}
#Enlist all existing webhooks
response = requests.request("GET", base_url, headers=headers)
data = response.json()
print(data)
webhook_list = data['results']

#Delete all existing webhooks
for webhook in webhook_list:
    webhook_id = webhook['webhookId']
    delete_url = f"{base_url}/{webhook_id}"
    response = requests.request("DELETE", delete_url, headers=headers)

#Add new webhook
headers["Content-Type"] = "application/json"
payload_1 = {
    "events": ["call.started"],
    "url": f"{ngrok_url}/api/webhooks/call-started"
}
response = requests.request("POST", base_url, json=payload_1, headers=headers)

payload_2 = {
    "events": ["call.ended"],
    "url": f"{ngrok_url}/api/webhooks/call-ended"
}
response = requests.request("POST", base_url, json=payload_2, headers=headers)