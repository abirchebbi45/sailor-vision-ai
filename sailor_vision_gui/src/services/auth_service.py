import logging
import smtplib
import os
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound

# Load environment variables from the specified .env file
load_dotenv("/home/abirc240/Desktop/sailor-vision-ai/sailor_vision_gui/.env")

from database import get_session, close_session
from models import User
from utils import verify_password, generate_token, verify_token, hash_password
from src.services.user_session import UserSession

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
                    "role": user.role.value if user.role else "Operator",  # Convert enum to string, default to Operator
                    "role_enum": user.role,   # Store original enum
                    "profile_picture": user.profile_picture  # Ensure this field is included
                }
                
                # Configure UserSession
                user_session = UserSession.get_instance()
                user_session.set_user(user_data)
                
                # Si le rôle est None, définir une valeur par défaut
                if user.role is None:
                    from models import UserRole
                    user.role = UserRole.OPERATOR
                    session.commit()
                    logger.info(f"Updated null role to OPERATOR for user {user.username}")
                
                user.last_login = datetime.now()
                session.commit()
                logger.info(f"User authenticated successfully: {email} with role {user.role}")
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

    def send_email(self, to_email, subject, body):
        """Send an email using Mailtrap's SMTP service"""
        try:
            logger.info(f"Send Email: Preparing to send email to {to_email}.")
            
            smtp_server = os.getenv("SMTP_SERVER")
            smtp_port = int(os.getenv("SMTP_PORT"))
            smtp_user = os.getenv("SMTP_USER")
            smtp_password = os.getenv("SMTP_PASSWORD")
            sender_email = os.getenv("EMAIL_SENDER")
            
            if not all([smtp_server, smtp_port, smtp_user, smtp_password, sender_email]):
                logger.error("Send Email: Missing SMTP configuration in environment variables.")
                return False
            
            # Create the email message
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = sender_email
            msg["To"] = to_email
            
            # Send the email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(sender_email, [to_email], msg.as_string())
            
            logger.info(f"Send Email: Email successfully sent to {to_email}.")
            return True
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, smtplib.SMTPException) as e:
            logger.error(f"Send Email: Network error occurred while sending email to {to_email}: {str(e)}")
            raise ConnectionError("Connection interrupted, please check your network.")
        except Exception as e:
            logger.error(f"Send Email: Error sending email to {to_email}: {str(e)}")
            return False

    def reset_password_request(self, email):
        """Request password reset"""
        session = get_session()
        try:
            logger.info(f"Reset Password Request: Searching for user with email {email}.")
            user = session.query(User).filter(User.email == email).one_or_none()

            if not user:
                logger.warning(f"Reset Password Request: Email {email} not found in database.")
                return None

            reset_token = generate_token(user.id, user.username, user.role)
            logger.info(f"Reset Password Request: Generated reset token for {email}.")

            subject = "Password Reset Request"
            body = f"Your password reset token is: {reset_token}\n\nUse this token to reset your password."
            self.send_email(email, subject, body)

            logger.info(f"Reset Password Request: Reset token sent to {email}.")
            return reset_token
        except Exception as e:
            logger.error(f"Reset Password Request: Error occurred: {str(e)}")
            return None
        finally:
            close_session(session)

    def reset_password(self, token, new_password):
        """Reset password using reset token"""
        try:
            logger.info("Reset Password: Verifying reset token.")
            payload = verify_token(token)
            if not payload:
                logger.warning("Reset Password: Invalid or expired token.")
                return False

            session = get_session()
            logger.info(f"Reset Password: Searching for user with ID {payload['user_id']}.")
            user = session.query(User).filter(User.id == payload["user_id"]).one_or_none()
            if not user:
                logger.warning("Reset Password: User not found for the provided token.")
                return False

            user.password_hash = hash_password(new_password)
            session.commit()
            logger.info(f"Reset Password: Password reset successfully for user {user.email}.")
            return True
        except Exception as e:
            logger.error(f"Reset Password: Error occurred: {str(e)}")
            return False
        finally:
            close_session(session)
