import requests
import time

API_KEY = "8a53b4565b6646fdb9b2a533e302a48c"

url = "https://gateway.pixazo.ai/ltx-2-3-quality-text-to-video/v1/ltx-2-3-quality-text-to-video-request"

headers = {
    "Content-Type": "application/json",
    "Ocp-Apim-Subscription-Key": API_KEY
}

payload = {
    "prompt": "A cinematic drone shot over a futuristic city at night",
    "num_frames": 121,
    "resolution": "landscape_16_9",
    "frames_per_second": 24,
    "video_quality": "high"
}

response = requests.post(url, json=payload, headers=headers)

print("STATUS:", response.status_code)
print("RAW:", response.text)

try:
    data = response.json()
except Exception as e:
    print("No JSON response")
    exit()

if "request_id" not in data:
    print("❌ Error API:", data)
    exit()

print("Request ID:", data["request_id"])
polling_url = data["polling_url"]

while True:
    status_res = requests.get(polling_url, headers=headers).json()
    print("STATUS:", status_res["status"])

    if status_res["status"] == "COMPLETED":
        print("VIDEO:", status_res["output"]["media_url"][0])
        break

    if status_res["status"] in ["FAILED", "ERROR"]:
        print("ERROR:", status_res)
        break

    time.sleep(5)