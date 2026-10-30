import uuid,datetime,os
from fastapi import FastAPI,Depends,HTTPException,UploadFile,File,Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from firebase_admin import firestore,storage as fb_storage
from .config import FRONTEND_ORIGINS,MAX_UPLOAD_MB
from .firebase import db,initialize
from .security import current_user,ensure_role
from .ai import gemini_analyze,priority_score,duplicate_candidates,haversine

app=FastAPI(title="Civic AI API",version="1.0.0",description="From Complaints to Action")
app.add_middleware(CORSMiddleware,allow_origins=FRONTEND_ORIGINS,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
STATUSES=["Submitted","Under Review","Assigned","In Progress","Resolved","Rejected"]
DEPARTMENTS=["Roads and Infrastructure","Sanitation","Water Supply","Electricity","Public Safety","General Administration"]
@app.on_event("startup")
def startup():
    try:initialize()
    except Exception as e:print("Firebase initialization deferred:",e)
@app.get("/")
def home():return {"message":"Civic AI API","status":"running"}
@app.get("/health")
def health():return {"status":"healthy","project":"Civic AI"}
@app.get("/api/me")
def me(user=Depends(current_user)):
    snap=db().collection("users").document(user["uid"]).get()
    data=snap.to_dict() if snap.exists else {"role":"citizen"}
    return {"uid":user["uid"],"email":user.get("email"),**data}
def user_role(uid):
    snap=db().collection("users").document(uid).get()
    return (snap.to_dict() or {}).get("role","citizen") if snap.exists else "citizen"
def complaint_dict(doc):
    x=doc.to_dict() or {};x["id"]=doc.id
    return x
def uploads_to_storage(uid,complaint_id,images):
    urls=[]
    for image in images or []:
        if not image.filename:continue
        if image.content_type not in ["image/jpeg","image/png","image/webp"]:continue
        content=image.file.read()
        if len(content)>MAX_UPLOAD_MB*1024*1024:raise HTTPException(413,f"Image exceeds {MAX_UPLOAD_MB} MB.")
        try:
            bucket=fb_storage.bucket()
            blob=bucket.blob(f"complaints/{uid}/{complaint_id}/{uuid.uuid4().hex}_{os.path.basename(image.filename)}")
            blob.upload_from_string(content,content_type=image.content_type)
            # Store storage path, not public URL. Access should be mediated by Storage rules.
            urls.append(blob.name)
        except Exception as e:raise HTTPException(500,"Image storage failed. Check Firebase Storage configuration.")
    return urls
@app.post("/api/complaints")
def create_complaint(title:str=Form(...),description:str=Form(...),category:str=Form(...),address:str=Form(...),latitude:float=Form(...),longitude:float=Form(...),images:list[UploadFile]=File(default=[]),user=Depends(current_user)):
    if len(title)>100 or len(description)<10 or len(description)>2000:raise HTTPException(422,"Check title and description length.")
    if not (-90<=latitude<=90 and -180<=longitude<=180):raise HTTPException(422,"Invalid coordinates.")
    uid=user["uid"];cid=uuid.uuid4().hex[:12].upper();public_id="CAI-"+uuid.uuid4().hex[:8].upper()
    existing=[complaint_dict(d) for d in db().collection("complaints").limit(250).stream()]
    analysis,ai_mode=gemini_analyze(title,description,category)
    score,priority=priority_score(analysis)
    dup,dup_mode=duplicate_candidates(title+" "+description,existing,latitude,longitude)
    department={"Road damage":"Roads and Infrastructure","Waterlogging":"Roads and Infrastructure","Garbage":"Sanitation","Streetlights":"Electricity","Drainage":"Sanitation","Water supply":"Water Supply","Public safety":"Public Safety","Other":"General Administration"}.get(analysis["category"],"General Administration")
    image_paths=uploads_to_storage(uid,cid,images[:5])
    now=datetime.datetime.now(datetime.timezone.utc)
    data={"public_id":public_id,"title":title,"description":description,"public_summary":analysis["summary"],"category":analysis["category"],"citizen_category":category,"latitude":latitude,"longitude":longitude,"address":address,"priority":priority,"priority_score":score,"priority_reason":analysis["reasoning"],"ai_analysis":analysis,"ai_mode":ai_mode,"duplicate_candidates":dup,"duplicate_mode":dup_mode,"department":department,"assigned_to":None,"status":"Submitted","image_paths":image_paths,"created_by":uid,"created_at":now,"updated_at":now,"timeline":[{"status":"Submitted","note":"Complaint received.","at":now.isoformat()}],"is_synthetic":False}
    db().collection("complaints").document(cid).set(data)
    db().collection("users").document(uid).set({"email":user.get("email"),"role":"citizen"},merge=True)
    db().collection("notifications").add({"uid":uid,"complaint_id":cid,"message":f"Complaint {public_id} submitted.","created_at":now,"read":False})
    return {"id":cid,"public_id":public_id,"status":"Submitted","priority":priority,"priority_score":score,"ai_mode":ai_mode,"duplicate_candidates":dup}
@app.get("/api/complaints")
def list_complaints(user=Depends(current_user)):
    role=user_role(user["uid"]);q=db().collection("complaints")
    docs=list(q.limit(300).stream());items=[complaint_dict(d) for d in docs]
    if role=="citizen":items=[x for x in items if x.get("created_by")==user["uid"]]
    elif role=="department_officer":
        profile=db().collection("users").document(user["uid"]).get().to_dict() or {}
        items=[x for x in items if x.get("department")==profile.get("department") or x.get("assigned_to")==user["uid"]]
    items.sort(key=lambda x:str(x.get("created_at","")),reverse=True)
    return {"items":items}
@app.get("/api/track/{public_id}")
def public_track(public_id:str):
    docs=list(db().collection("complaints").where("public_id","==",public_id).limit(1).stream())
    if not docs:raise HTTPException(404,"Complaint not found.")
    x=complaint_dict(docs[0])
    return {"public_id":x.get("public_id"),"category":x.get("category"),"status":x.get("status"),"priority":x.get("priority"),"public_summary":x.get("public_summary"),"timeline":x.get("timeline",[])}
class StatusUpdate(BaseModel):
    status:str
    note:str=Field(default="",max_length=500)
@app.patch("/api/complaints/{cid}/status")
def update_status(cid:str,payload:StatusUpdate,user=Depends(current_user)):
    role=user_role(user["uid"])
    if role not in ["admin","department_officer"]:raise HTTPException(403,"Only administrators and officers can update status.")
    if payload.status not in STATUSES:raise HTTPException(422,"Invalid status.")
    ref=db().collection("complaints").document(cid);snap=ref.get()
    if not snap.exists:raise HTTPException(404,"Complaint not found.")
    data=snap.to_dict()
    if role=="department_officer":
        profile=db().collection("users").document(user["uid"]).get().to_dict() or {}
        if data.get("department")!=profile.get("department"):raise HTTPException(403,"Complaint belongs to another department.")
    now=datetime.datetime.now(datetime.timezone.utc)
    timeline=data.get("timeline",[])+[{"status":payload.status,"note":payload.note or f"Status changed to {payload.status}.","at":now.isoformat()}]
    ref.update({"status":payload.status,"timeline":timeline,"updated_at":now})
    db().collection("notifications").add({"uid":data.get("created_by"),"complaint_id":cid,"message":f"Your complaint {data.get('public_id')} is now {payload.status}.","created_at":now,"read":False})
    return {"success":True,"status":payload.status}
@app.post("/api/complaints/{cid}/assign")
def assign(cid:str,officer_uid:str=Form(...),department:str=Form(...),user=Depends(current_user)):
    ensure_role(user["uid"],["admin"])
    if department not in DEPARTMENTS:raise HTTPException(422,"Invalid department.")
    ref=db().collection("complaints").document(cid);snap=ref.get()
    if not snap.exists:raise HTTPException(404,"Complaint not found.")
    ref.update({"assigned_to":officer_uid,"department":department,"status":"Assigned","updated_at":datetime.datetime.now(datetime.timezone.utc)})
    return {"success":True}
@app.get("/api/analytics/summary")
def analytics(user=Depends(current_user)):
    role=user_role(user["uid"]);docs=[complaint_dict(d) for d in db().collection("complaints").limit(500).stream()]
    if role=="citizen":docs=[x for x in docs if x.get("created_by")==user["uid"]]
    total=len(docs);resolved=sum(x.get("status")=="Resolved" for x in docs)
    cats={}
    for x in docs:cats[x.get("category","Other")]=cats.get(x.get("category","Other"),0)+1
    return {"total":total,"resolved":resolved,"high_priority":sum(x.get("priority") in ["High","Critical"] for x in docs),"open":sum(x.get("status") not in ["Resolved","Rejected"] for x in docs),"by_category":[{"category":k,"count":v} for k,v in cats.items()]}
@app.get("/api/notifications")
def notifications(user=Depends(current_user)):
    docs=list(db().collection("notifications").where("uid","==",user["uid"]).limit(50).stream())
    return {"items":[complaint_dict(d) for d in docs]}
@app.post("/api/admin/seed")
def seed(user=Depends(current_user)):
    ensure_role(user["uid"],["admin"])
    from pathlib import Path
    import json
    path=Path(__file__).resolve().parents[2]/"dataset"/"complaints.json"
    if not path.exists():raise HTTPException(500,"Dataset file not found.")
    records=json.loads(path.read_text(encoding="utf-8"))
    batch=db().batch()
    for r in records:
        ref=db().collection("complaints").document("SYN-"+r["id"])
        r2={**r,"created_by":"synthetic-demo","is_synthetic":True,"created_at":datetime.datetime.now(datetime.timezone.utc),"updated_at":datetime.datetime.now(datetime.timezone.utc),"timeline":[{"status":r.get("status","Submitted"),"note":"Synthetic demo record.","at":datetime.datetime.now(datetime.timezone.utc).isoformat()}]}
        batch.set(ref,r2)
    batch.commit()
    return {"inserted":len(records),"synthetic":True}
