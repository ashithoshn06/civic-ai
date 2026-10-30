import os
import firebase_admin
from firebase_admin import credentials, firestore, auth, storage
from .config import PROJECT_ID,SERVICE_ACCOUNT,STORAGE_BUCKET
_db=None
def initialize():
    global _db
    if _db is not None:return _db
    if not firebase_admin._apps:
        if os.path.exists(SERVICE_ACCOUNT):
            cred=credentials.Certificate(SERVICE_ACCOUNT)
            firebase_admin.initialize_app(cred,{"projectId":PROJECT_ID, **({"storageBucket": STORAGE_BUCKET} if STORAGE_BUCKET else {})})
        else:
            firebase_admin.initialize_app(options={"projectId":PROJECT_ID, **({"storageBucket": STORAGE_BUCKET} if STORAGE_BUCKET else {})})
    _db=firestore.client()
    return _db
def db():
    return initialize()
def verify_token(token:str):
    initialize()
    return auth.verify_id_token(token,check_revoked=True)
def user_doc(uid):
    return db().collection("users").document(uid).get()
def role_for(uid):
    snap=user_doc(uid)
    return (snap.to_dict() or {}).get("role","citizen") if snap.exists else "citizen"
