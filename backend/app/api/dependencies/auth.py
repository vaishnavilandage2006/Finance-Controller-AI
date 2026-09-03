from fastapi import Depends,Header,HTTPException
from sqlalchemy.orm import Session
from ...db import get_db
from ...models import User
from ...core.security import decode_token
def current_user(authorization:str=Header(default=""),db:Session=Depends(get_db)):
    if not authorization.startswith("Bearer "): raise HTTPException(401,"Authentication required")
    data=decode_token(authorization[7:]); u=db.query(User).filter_by(email=data["sub"],active=True).first()
    if not u: raise HTTPException(401,"User not found")
    return u
def require_roles(*roles):
    def dep(user=Depends(current_user)):
        if user.role not in roles: raise HTTPException(403,"Insufficient permission")
        return user
    return dep
