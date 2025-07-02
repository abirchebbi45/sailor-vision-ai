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
    """Get a new session."""
    global engine, Session  # Déplacé au début de la fonction
    
    try:
        session = Session()
        return session
    except Exception as e:
        logger.error(f"Error creating DB session: {e}")
        # Essayer de recréer l'engine et le sessionmaker
        import sqlalchemy
        try:
            db_url = get_db_url()  # Utiliser get_db_url() au lieu de DB_URL
            engine = sqlalchemy.create_engine(db_url)
            Session = sqlalchemy.orm.sessionmaker(bind=engine)
            return Session()
        except Exception as e2:
            logger.error(f"Could not recover database connection: {e2}")
            raise

def close_session(session):
    """Close a session safely."""
    if session:
        try:
            session.close()
        except Exception as e:
            logger.error(f"Error closing DB session: {e}")
