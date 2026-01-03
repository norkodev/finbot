"""Database setup and configuration."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
import os
import yaml


# Base class for all models
Base = declarative_base()


def _load_config():
    """Load configuration from settings.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'settings.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        # Return default config
        return {
            'database': {
                'path': './data/database/finanzas.db'
            }
        }


def get_database_url():
    """Get database URL from configuration."""
    config = _load_config()
    db_path = config.get('database', {}).get('path', './data/database/finanzas.db')
    
    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    return f"sqlite:///{db_path}"


def create_db_engine(echo=False):
    """
    Create database engine.
    
    Args:
        echo: Whether to echo SQL statements (for debugging)
        
    Returns:
        SQLAlchemy engine
    """
    url = get_database_url()
    return create_engine(
        url,
        echo=echo,
        connect_args={"check_same_thread": False},  # Needed for SQLite
    )


def get_session_maker(engine=None):
    """
    Get session maker for database operations.
    
    Args:
        engine: SQLAlchemy engine (creates new one if not provided)
        
    Returns:
        Session class
    """
    if engine is None:
        engine = create_db_engine()
    
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db(engine=None):
    """
    Initialize database by creating all tables.
    
    Args:
        engine: SQLAlchemy engine (creates new one if not provided)
    """
    if engine is None:
        engine = create_db_engine()
    
    # Import all models to ensure they're registered
    from . import statement, transaction, installment, merchant, processing_log
    
    # Create all tables
    Base.metadata.create_all(bind=engine)


def get_session(engine=None):
    """
    Get a database session.
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        Database session
    """
    SessionLocal = get_session_maker(engine)
    return SessionLocal()
