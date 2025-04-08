import requests

url = "https://api.ultravox.ai/api/webhooks"

payload = {
    "events": ["call.ended"],
    "url": "https://d425-13-203-58-245.ngrok-free.app/get-latest-transcript"
}
headers = {
    "X-API-Key": "qZyBHTvL.K7lN1fFqDq2IfVwJdC4XJHcxbsTY9n7A",
    "Content-Type": "application/json"
}

response = requests.request("POST", url, json=payload, headers=headers)

print(response.text)