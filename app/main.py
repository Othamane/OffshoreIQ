"""
OffshoreIQ — FastAPI Application Entry Point
Moroccan Nearshore IT Talent Matching powered by GraphRAG + Multi-Agent System
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router
from app.core.config import settings
from app.core.logging import logger
from app.db.neo4j_db import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown events."""
    logger.info("🚀 OffshoreIQ starting up (env=%s)", settings.app_env)
    try:
        db.connect()
    except Exception as e:
        logger.error("❌ Neo4j connection failed: %s", e)
        logger.warning("App will start but Neo4j features will be unavailable.")
    yield
    db.close()
    logger.info("OffshoreIQ shut down.")


app = FastAPI(
    title="OffshoreIQ",
    description=(
        "GraphRAG-powered IT Talent Matching for Moroccan Nearshore Offshoring. "
        "Uses Neo4j multi-hop graph traversal + LangGraph multi-agent system."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Static files & templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# API routes
app.include_router(router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    """Serve the main UI."""
    return templates.TemplateResponse("index.html", {"request": request})
