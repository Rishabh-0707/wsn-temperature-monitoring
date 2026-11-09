import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import initialize
from .routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

def create_app(db_path=None):
    @asynccontextmanager
    async def lifespan(app):
        initialize(app.state.db_path)
        yield
    app = FastAPI(title="WSN Temperature Monitoring", version="1.0.0", lifespan=lifespan)
    app.state.db_path = db_path
    origins = os.environ.get("WSN_CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",")
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
    app.include_router(router)
    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}
    frontend = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="dashboard")
    return app

app = create_app()
