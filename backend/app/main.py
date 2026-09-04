from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .db import Base,engine,SessionLocal
from .models import *
from .api.routes.auth import router as auth_router
from .api.routes.core import router as core_router
from .core.config import settings
from .core.bootstrap import ensure_demo_admin
app=FastAPI(title="AI Finance Controller",docs_url="/docs")
Base.metadata.create_all(engine)
bootstrap_db = SessionLocal()
try:
	ensure_demo_admin(bootstrap_db)
finally:
	bootstrap_db.close()
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(",")],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(auth_router,prefix="/api/auth",tags=["auth"])
app.include_router(core_router,prefix="/api",tags=["finance"])

static_dir = Path(__file__).resolve().parents[1] / "static"
if static_dir.is_dir():
	app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

	@app.get("/{path:path}", include_in_schema=False)
	async def serve_frontend(path: str):
		if path.startswith("api/"):
			return FileResponse(static_dir / "index.html", status_code=404)
		requested = (static_dir / path).resolve()
		if static_dir.resolve() in requested.parents and requested.is_file():
			return FileResponse(requested)
		return FileResponse(static_dir / "index.html")
