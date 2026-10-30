import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1]/".env")
import firebase_admin
from firebase_admin import credentials,auth,firestore
project=os.getenv("FIREBASE_PROJECT_ID","civic-complaints-ai")
key=os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH","service-account.json")
if not Path(key).exists():raise SystemExit("Service account file missing. Set FIREBASE_SERVICE_ACCOUNT_PATH.")
if not firebase_admin._apps:firebase_admin.initialize_app(credentials.Certificate(key),{"projectId":project})
db=firestore.client()
accounts=[
 ("CITIZEN","DEMO_CITIZEN_EMAIL","DEMO_CITIZEN_PASSWORD","citizen",None),
 ("ADMIN","DEMO_ADMIN_EMAIL","DEMO_ADMIN_PASSWORD","admin",None),
 ("OFFICER","DEMO_OFFICER_EMAIL","DEMO_OFFICER_PASSWORD","department_officer","Roads and Infrastructure")
]
for label,email_key,pw_key,role,dept in accounts:
 email=os.getenv(email_key);password=os.getenv(pw_key)
 if not email or not password:
  print(f"Skipping {label}: set {email_key} and {pw_key} in backend/.env");continue
 try:u=auth.get_user_by_email(email)
 except auth.UserNotFoundError:u=auth.create_user(email=email,password=password,email_verified=True)
 profile={"email":email,"role":role,"created_by":"local-demo-setup"}
 if dept:profile["department"]=dept
 db.collection("users").document(u.uid).set(profile,merge=True)
 print(f"Ready: {label} {email} uid={u.uid}")
print("Demo account setup complete. Change demo passwords before any shared deployment.")
