import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
FIREBASE_SERVICE_ACCOUNT_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
FIREBASE_KEY_FILE_PATH = os.getenv("FIREBASE_KEY_FILE_PATH", "")
CRON_SECRET = os.getenv("CRON_SECRET", "default_secret")
PORT = int(os.getenv("PORT", "8000"))

# Validate essential configs (warn if empty in production, but we keep it lax for setup)
if not LINE_CHANNEL_ACCESS_TOKEN:
    print("WARNING: LINE_CHANNEL_ACCESS_TOKEN is not configured!")
if not LINE_CHANNEL_SECRET:
    print("WARNING: LINE_CHANNEL_SECRET is not configured!")
