from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,EmailStr
from sqlalchemy.orm import Session
from ...db import get_db
from ...models import User,AuditLog
from ...core.security import verify_password,create_token
router=APIRouter()
class Login(BaseModel): email:EmailStr; password:str
@router.post("/login")
def login(body:Login,db:Session=Depends(get_db)):
    u=db.query(User).filter_by(email=body.email).first()
    if not u or not verify_password(body.password,u.password_hash): raise HTTPException(401,"Invalid credentials")
    db.add(AuditLog(user_email=u.email,action="login")); db.commit()
    return {"access_token":create_token(u.email),"user":{"email":u.email,"role":u.role}}
