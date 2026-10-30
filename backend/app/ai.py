import re,math
from collections import Counter
from .config import GEMINI_API_KEY,GEMINI_MODEL,ALLOW_DEMO_FALLBACK
_client=None
def gemini_analyze(title,description,category):
    global _client
    if GEMINI_API_KEY:
        try:
            from google import genai
            if _client is None:_client=genai.Client(api_key=GEMINI_API_KEY)
            prompt=f'''Analyze this civic complaint. Return ONLY valid JSON with keys category, summary, urgency (1-5), safety_risk (1-5), public_impact (1-5), affected_population (1-5), reasoning, action_brief. Allowed categories: Road damage, Waterlogging, Garbage, Streetlights, Drainage, Water supply, Public safety, Other.
Title: {title}
Description: {description}
Citizen selected category: {category}
Do not invent facts. If uncertain, use conservative scores.'''
            response=_client.models.generate_content(model=GEMINI_MODEL,contents=prompt)
            import json
            raw=response.text.strip().replace("```json","").replace("```","").strip()
            data=json.loads(raw)
            return validate(data),"gemini"
        except Exception as e:
            if not ALLOW_DEMO_FALLBACK:raise
    return fallback(title,description,category),"rules_fallback"
def validate(d):
    allowed=["Road damage","Waterlogging","Garbage","Streetlights","Drainage","Water supply","Public safety","Other"]
    cat=d.get("category")
    if cat not in allowed:cat="Other"
    def score(k):return max(1,min(5,int(d.get(k,2))))
    return {"category":cat,"summary":str(d.get("summary",""))[:300],"urgency":score("urgency"),"safety_risk":score("safety_risk"),"public_impact":score("public_impact"),"affected_population":score("affected_population"),"reasoning":str(d.get("reasoning","AI-assisted assessment; human review required."))[:500],"action_brief":str(d.get("action_brief","Review report and verify location."))[:500]}
def fallback(title,desc,category):
    t=(title+" "+desc).lower()
    urgent=any(x in t for x in ["electric wire","open manhole","accident","injury","fire","collapse","danger","school","hospital"])
    water=any(x in t for x in ["flood","waterlogging","water logged","overflow"])
    safety=5 if urgent else 3 if water else 2
    urgency=5 if urgent else 4 if water else 3
    impact=4 if any(x in t for x in ["main road","bus stand","school","hospital","market"]) else 3
    pop=4 if impact>=4 else 2
    cat=category
    for key,val in [("pothole","Road damage"),("garbage","Garbage"),("streetlight","Streetlights"),("drain","Drainage"),("water supply","Water supply"),("waterlogging","Waterlogging"),("flood","Waterlogging"),("electric wire","Public safety")]:
        if key in t:cat=val;break
    summary=(desc.strip()[:180] or title)
    return {"category":cat,"summary":summary,"urgency":urgency,"safety_risk":safety,"public_impact":impact,"affected_population":pop,"reasoning":f"Rule-based fallback: urgency {urgency}/5, safety risk {safety}/5, public impact {impact}/5 and affected population {pop}/5 inferred from report wording. Human verification required.","action_brief":"Verify the location, assess immediate safety risk and route to the relevant department."}
def priority_score(a):
    score=round((a["urgency"]*.30+a["safety_risk"]*.35+a["public_impact"]*.20+a["affected_population"]*.15)/5*100)
    return score,("Critical" if score>=85 else "High" if score>=65 else "Medium" if score>=40 else "Low")
def duplicate_candidates(text,existing,lat,lon):
    # Optional semantic model; transparent token fallback if unavailable.
    try:
        from sentence_transformers import SentenceTransformer,util
        model=SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        candidates=[]
        texts=[text]+[x.get("title","")+" "+x.get("description","") for x in existing]
        emb=model.encode(texts,convert_to_tensor=True)
        sims=util.cos_sim(emb[0],emb[1:])[0]
        for i,s in enumerate(sims):
            x=existing[i]
            dist=haversine(lat,lon,x.get("latitude",0),x.get("longitude",0))
            if float(s)>=.68 and dist<=1.0:candidates.append({"id":x["id"],"similarity":round(float(s),3),"distance_km":round(dist,2)})
        return candidates,"sentence-transformers"
    except Exception:
        words=set(re.findall(r"[a-z]{3,}",text.lower()))
        out=[]
        for x in existing:
            other=set(re.findall(r"[a-z]{3,}",(x.get("title","")+" "+x.get("description","")).lower()))
            sim=len(words&other)/max(1,len(words|other))
            dist=haversine(lat,lon,x.get("latitude",0),x.get("longitude",0))
            if sim>=.30 and dist<=1.0:out.append({"id":x["id"],"similarity":round(sim,3),"distance_km":round(dist,2)})
        return out,"token-similarity-fallback"
def haversine(a,b,c,d):
    r=6371
    p1,p2=math.radians(a),math.radians(c)
    dp=math.radians(c-a);dl=math.radians(d-b)
    z=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(z))
