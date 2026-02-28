"""
Database configuration, models, and dependencies for the Netflix MCP Server.

This module contains:
- SQLAlchemy engine and session setup
- ORM models (Movie, ViewSummary)
- Dependency providers (get_db_session)
"""

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from fastmcp.server.lifespan import lifespan

# Load database URL from .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. Check your .env file."
    )

# SQLAlchemy setup: create engine
engine = create_engine(DATABASE_URL)
# SQLAlchemy setup: session factory
SessionLocal = sessionmaker(bind=engine)
# SQLAlchemy setup: base class for ORM models
Base = declarative_base()


@contextmanager
def get_db_session():
    """Dependency: provides a SQLAlchemy session and ensures it is closed after use."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@lifespan
async def db_lifespan(server):
    """Manage database engine lifecycle.

    This lifespan ensures the SQLAlchemy engine is properly disposed when
    the server shuts down, closing all connection pool connections gracefully.

    We yield an empty dict {} because we don't need to share state via
    ctx.lifespan_context - the engine is already a module-level variable,
    and sessions are managed per-tool via Depends(get_db_session).
    """
    # Startup: server is starting
    print("Netflix MCP Server starting... Database engine ready.")

    try:
        # Yield empty context - no shared state needed
        # If you wanted to share data with tools, you'd yield:
        # {"cache": some_cache, "config": some_config}
        # and access it in tools via ctx.lifespan_context["cache"]
        yield {}
    finally:
        # Teardown: server is shutting down
        # This ALWAYS runs, even if the server is cancelled/interrupted
        print("Shutting down... Disposing database engine.")
        engine.dispose()
        print("Netflix MCP Server shutdown complete.")


class Movie(Base):
    """Movie model (matches actual DB schema)"""

    __tablename__ = "movie"
    id = Column(BigInteger, primary_key=True, index=True)
    title = Column(String)
    original_title = Column(String)
    release_date = Column(Date)
    runtime = Column(Integer)
    locale = Column(String)
    available_globally = Column(Boolean)
    created_date = Column(DateTime)
    modified_date = Column(DateTime)


class ViewSummary(Base):
    """ViewSummary model (matches actual DB schema)"""

    __tablename__ = "view_summary"
    id = Column(BigInteger, primary_key=True, index=True)
    movie_id = Column(BigInteger)
    season_id = Column(BigInteger)
    hours_viewed = Column(Integer)
    views = Column(Integer)
    view_rank = Column(Integer)
    cumulative_weeks_in_top10 = Column(Integer)
    start_date = Column(Date)
    end_date = Column(Date)
    duration = Column(String)
    created_date = Column(DateTime)
    modified_date = Column(DateTime)
