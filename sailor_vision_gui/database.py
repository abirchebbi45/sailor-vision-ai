import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from config import get_db_url

# Set up logging
logger = logging.getLogger(__name__)

# Create base class for declarative models
Base = declarative_base()

# Create database engine
engine = None
Session = None

def init_db():
    """Initialize database engine and session factory"""
    global engine, Session
    
    try:
        # Create engine
        db_url = get_db_url()
        engine = create_engine(db_url)
        
        # Create session factory
        session_factory = sessionmaker(bind=engine)
        Session = scoped_session(session_factory)
        
        # Create tables
        Base.metadata.create_all(engine)
        
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

def get_session():
    try:
        session = Session()
        if session is None:
            raise ValueError("Session is None")
        return session
    except Exception as e:
        logger.error(f"Error creating new session: {e}")
        return None

def close_session(session):
    """Close database session"""
    if session:
        session.close()

# Ensure the session factory is initialized correctly
def create_new_session():
    global Session
    if Session is None:
        raise RuntimeError("Session factory is not initialized. Call init_db() first.")
    return Session()