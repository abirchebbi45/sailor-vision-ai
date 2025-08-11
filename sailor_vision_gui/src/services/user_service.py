import logging
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from database import get_session, close_session
from models import User, UserRole
from utils import hash_password

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, db_session):
        """Initialize the UserService with a database session"""
        self.db_session = db_session

    def get_all_users(self):
        """Get all users"""
        try:
            users = self.db_session.query(User).all()
            return users
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving users: {str(e)}")
            return []

    def get_user(self, user_id):
        """Get a user by ID"""
        try:
            user = self.db_session.query(User).filter(User.id == user_id).first()
            return user
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving user {user_id}: {str(e)}")
            return None

    def get_user_by_email(self, email):
        """Get a user by email"""
        try:
            user = self.db_session.query(User).filter(User.email == email).first()
            return user
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving user by email {email}: {str(e)}")
            return None

    def get_user_by_username(self, username):
        """Get a user by username"""
        try:
            user = self.db_session.query(User).filter(User.username == username).first()
            return user
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving user by username {username}: {str(e)}")
            return None

    def create_user(self, user_data):
        """Create a new user"""
        # Check if user already exists
        existing_user = self.get_user_by_email(user_data.get('email')) or self.get_user_by_username(user_data.get('username'))
        if existing_user:
            logger.warning(f"User with email {user_data.get('email')} or username {user_data.get('username')} already exists")
            return False  # Indicate failure due to duplicate email/username

        try:
            # Hash password
            password_hash = hash_password(user_data.get('password', ''))

            # Create user
            user = User(
                username=user_data.get('username'),
                email=user_data.get('email'),
                password_hash=password_hash,
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                role=user_data.get('role', UserRole.OPERATOR),
                job_title=user_data.get('job_title'),
                profile_picture=user_data.get('profile_picture'),
                is_active=True,
                created_at=datetime.now()
            )

            self.db_session.add(user)
            self.db_session.commit()

            logger.info(f"User {user.username} created successfully")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error creating user: {str(e)}")
            self.db_session.rollback()
            return False

    def update_user(self, user_id, user_data):
        """Update user information"""
        try:
            user = self.db_session.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found for update")
                return False

            # Update fields if provided
            if 'username' in user_data:
                user.username = user_data['username']
            if 'email' in user_data:
                user.email = user_data['email']
            if 'first_name' in user_data:
                user.first_name = user_data['first_name']
            if 'last_name' in user_data:
                user.last_name = user_data['last_name']
            if 'role' in user_data:
                user.role = user_data['role']
            if 'job_title' in user_data:
                user.job_title = user_data['job_title']
            if 'profile_picture' in user_data:
                user.profile_picture = user_data['profile_picture']
            if 'is_active' in user_data:
                user.is_active = user_data['is_active']
            if 'password' in user_data and user_data['password']:
                user.password_hash = hash_password(user_data['password'])

            self.db_session.commit()
            logger.info(f"User {user.username} updated successfully")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            self.db_session.rollback()
            return False

    def delete_user(self, user_id):
        """Delete a user"""
        try:
            user = self.db_session.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found for deletion")
                return False

            self.db_session.delete(user)
            self.db_session.commit()
            logger.info(f"User {user_id} deleted successfully")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            self.db_session.rollback()
            return False

    def update_last_login(self, user_id):
        """Update user's last login timestamp"""
        try:
            user = self.db_session.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found for last login update")
                return False

            user.last_login = datetime.now()
            self.db_session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating last login for user {user_id}: {str(e)}")
            self.db_session.rollback()
            return False

    def change_password(self, user_id, current_password, new_password):
        """Change user's password"""
        # First, get the user
        user = self.get_user(user_id)
        if not user:
            logger.warning(f"User {user_id} not found for password change")
            return False

        # Verify current password
        from utils import verify_password
        if not verify_password(user.password_hash, current_password):
            logger.warning(f"Invalid current password for user {user_id}")
            return False

        # Update to new password
        try:
            user = self.db_session.query(User).filter(User.id == user_id).first()
            user.password_hash = hash_password(new_password)
            self.db_session.commit()
            logger.info(f"Password changed for user {user_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error changing password for user {user_id}: {str(e)}")
            self.db_session.rollback()
            return False

    def get_users_by_role(self, role):
        """Get users by role"""
        try:
            users = self.db_session.query(User).filter(User.role == role).all()
            return users
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving users by role {role}: {str(e)}")
            return []