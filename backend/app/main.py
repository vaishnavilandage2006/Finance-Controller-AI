from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import Base,engine
from .models import *
from .api.routes.auth import router as auth_router
from .api.routes.core import router as core_router
from .core.config import settings
app=FastAPI(title="AI Finance Controller",docs_url="/docs")
Base.metadata.create_all(engine)
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(",")],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(auth_router,prefix="/api/auth",tags=["auth"])
app.include_router(core_router,prefix="/api",tags=["finance"])
