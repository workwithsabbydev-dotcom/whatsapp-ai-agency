from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Neon PostgreSQL async engine
# pool_size and max_overflow are critical for production under load.
# Neon's free tier supports ~100 connections via PgBouncer;
# these settings ensure we never exhaust that limit even with multiple Render instances.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Never echo SQL in production logs — it leaks query data and kills performance
    future=True,
    pool_pre_ping=True,
    pool_size=5,          # Base pool of persistent connections
    max_overflow=10,      # Allow burst to 15 total connections
    pool_timeout=30,      # Wait up to 30s for a free connection before erroring
    pool_recycle=1800,    # Recycle connections every 30 min to avoid Neon idle disconnects
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base()
