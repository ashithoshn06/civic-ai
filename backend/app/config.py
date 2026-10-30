import os
from dotenv import load_dotenv
load_dotenv()
PROJECT_ID=os.getenv("FIREBASE_PROJECT_ID","civic-complaints-ai")
STORAGE_BUCKET=os.getenv("FIREBASE_STORAGE_BUCKET","")
SERVICE_ACCOUNT=os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH","service-account.json")
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY","")
GEMINI_MODEL=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
FRONTEND_ORIGINS=[x.strip() for x in os.getenv("FRONTEND_ORIGINS","http://localhost:5173").split(",") if x.strip()]
ALLOW_DEMO_FALLBACK=os.getenv("ALLOW_DEMO_FALLBACK","true").lower()=="true"
MAX_UPLOAD_MB=int(os.getenv("MAX_UPLOAD_MB","5"))
