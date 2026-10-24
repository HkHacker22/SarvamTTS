import os
from sarvamai import SarvamAI

api_key = os.environ.get("SARVAM_API_KEY") or open(".env").read().split("SARVAM_API_KEY=")[1].strip()
if not api_key or api_key.strip() == "":
    raise SystemExit("SARVAM_API_KEY is missing. Add your key to .env")

client = SarvamAI(api_subscription_key=api_key)

response = client.chat.completions(
    messages=[{"role": "user", "content": "Hello, just say hi back."}],
    model="sarvam-105b-conversations",
)

# Try to extract reply
try:
    print(response.choices[0].message.content)
except Exception:
    print(response)
