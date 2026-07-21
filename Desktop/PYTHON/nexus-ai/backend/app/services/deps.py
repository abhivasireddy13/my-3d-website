from fastapi import Depends, HTTPException, Header
from app.core.security import decode_token

def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1]
    data = decode_token(token)
    if not data or data.get("type") != "access":
        raise HTTPException(401, "Invalid or expired token")
    return {"user_id": data["sub"], "role": data["role"]}

def require_role(*roles):
    def checker(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return checker
