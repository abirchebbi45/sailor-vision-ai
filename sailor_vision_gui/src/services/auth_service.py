import logging
from sqlalchemy.orm.exc import NoResultFound
from datetime import datetime

from database import get_session, close_session
from models import User
from utils import verify_password, generate_token

logger = logging.getLogger(__name__)

class AuthService:
    def authenticate(self, email, password):
        """Authenticate user by email and password"""
        session = get_session()
        try:
            # Find user by email
            user = session.query(User).filter(User.email == email).one()
            
            # Verify password
            if verify_password(password, user.password_hash):
                # Preload user data
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "role": user.role
                }
                user.last_login = datetime.now()
                session.commit()
                print(f"user_data: {user_data}")
                return user_data
            else:
                logger.warning(f"Invalid password for user: {email}")
                return None
        except NoResultFound:
            logger.warning(f"User not found: {email}")
            return None
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            session.rollback()
            return None
        finally:
            close_session(session)
    
    def get_token(self, user):
        """Generate authentication token for user"""
        if not user:
            return None
        
        try:
            return generate_token(user.id, user.username, user.role)
        except Exception as e:
            logger.error(f"Token generation error: {str(e)}")
            return None
    
    def reset_password_request(self, email):
        """Request password reset"""
        session = get_session()
        try:
            # Check if user exists
            user = session.query(User).filter(User.email == email).one()
            
            # In a real app, this would generate a reset token and send an email
            # For now, we just log it
            logger.info(f"Password reset requested for: {email}")
            
            return True
        except NoResultFound:
            logger.warning(f"Password reset requested for non-existent user: {email}")
            return False
        except Exception as e:
            logger.error(f"Password reset request error: {str(e)}")
            return False
        finally:
            close_session(session)
    
    def reset_password(self, token, new_password):
        """Reset password using reset token"""
        # In a real app, this would verify the token and update the password
        # For now, we just return False
        logger.warning("Password reset not implemented")
        return False
