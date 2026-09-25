"""FastAPI app entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from compas_api.config import get_settings
from compas_api.db import init_db
from compas_api.routers import library, analysis, health, auth

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("compas.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    log.info("Compás API v0.2 starting — db=%s storage=%s", settings.db_path, settings.storage_dir)
    init_db()
    yield
    log.info("Compás API shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Compás API",
        version="0.2.0",
        description="Open, free musical companion for salsa & bachata dancers. Local-first.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(library.router)
    app.include_router(analysis.router)
    return app


app = create_app()
