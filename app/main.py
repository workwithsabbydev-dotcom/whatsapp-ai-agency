from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logging import logger
from app.services.sheets import sheets_service
from app.api.routes.webhook import router as webhook_router
from app.db.database import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan handler replacing deprecated on_event."""
    logger.info("Starting up WhatsApp AI Platform...")
    sheets_service.start_background_refresh()
    yield
    logger.info("Shutting down WhatsApp AI Platform...")
    await engine.dispose()

app = FastAPI(
    title="WhatsApp AI Agency Platform",
    description="Multi-tenant WhatsApp automation backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
)

# Register Routers
app.include_router(webhook_router)

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Basic health check endpoint to verify the service is running.
    """
    return {"status": "ok", "environment": settings.ENVIRONMENT}

# Global exception handler for unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
