from fastapi import Header,HTTPException
from .firebase import verify_token,role_for
def current_user(authorization:str|None=Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401,"Sign in is required.")
    try:return verify_token(authorization.split(" ",1)[1])
    except Exception:raise HTTPException(401,"Invalid or expired authentication token.")
def require_roles(*roles):
    def dependency(user= None):
        # Use current_user dependency directly in route, then call this helper.
        def check(uid):
            role=role_for(uid)
            if role not in roles:raise HTTPException(403,"You do not have permission for this action.")
            return role
        return dependency
    return dependency
def ensure_role(uid,allowed):
    role=role_for(uid)
    if role not in allowed:raise HTTPException(403,"Insufficient permissions.")
    return role
