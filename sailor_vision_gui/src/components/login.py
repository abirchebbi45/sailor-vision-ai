# src/components/login.py
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QFrame, QMessageBox, QInputDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QIcon

from src.services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)

class LoginScreen(QWidget):
    login_successful = pyqtSignal(dict)  # Émet un dictionnaire
    
    def __init__(self):
        super().__init__()
        self.auth_service = AuthService()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignCenter)
        
        login_container = QFrame()
        login_container.setObjectName("loginContainer")
        login_container.setFixedWidth(400)
        login_container.setFixedHeight(500)
        
        login_layout = QVBoxLayout(login_container)
        login_layout.setAlignment(Qt.AlignCenter)
        login_layout.setSpacing(20)
        login_layout.setContentsMargins(30, 30, 30, 30)
        
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_icon = QIcon("/home/abirc240/Desktop/sailor-vision-ai/sailor_vision_gui/src/assets/Sailor vision logo.png")  # Chemin relatif
        logo_pixmap = logo_icon.pixmap(QSize(120, 120))
        logo_label.setPixmap(logo_pixmap)
        login_layout.addWidget(logo_label)
        
        title_label = QLabel("Access Account")
        title_label.setObjectName("loginTitle")
        title_label.setAlignment(Qt.AlignCenter)
        login_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Your gateway to innovative solutions")
        subtitle_label.setObjectName("loginSubtitle")
        subtitle_label.setAlignment(Qt.AlignCenter)
        login_layout.addWidget(subtitle_label)
        
        login_layout.addSpacing(20)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Your email address")
        self.email_input.setObjectName("loginInput")
        login_layout.addWidget(self.email_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setObjectName("loginInput")
        login_layout.addWidget(self.password_input)
        
        forgot_password = QLabel("<a href='#' style='color: #1E88E5; text-decoration: none;'>Forget your password?</a>")
        forgot_password.setObjectName("forgotPassword")
        forgot_password.setAlignment(Qt.AlignRight)
        forgot_password.setOpenExternalLinks(False)
        forgot_password.linkActivated.connect(self.forgot_password)
        login_layout.addWidget(forgot_password)
        
        login_button = QPushButton("Log In")
        login_button.setObjectName("primaryButton")
        login_button.setFixedHeight(40)
        login_button.clicked.connect(self.login)
        login_layout.addWidget(login_button)
        
        main_layout.addWidget(login_container, alignment=Qt.AlignCenter)
        self.setLayout(main_layout)
        self.email_input.setFocus()
        
    def login(self):
        """Handle login attempt"""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        if not email or not password:
            QMessageBox.warning(self, "Login Error", "Please enter both email and password.")
            return
        
        user_data = self.auth_service.authenticate(email, password)  # Renomme la variable pour plus de clarté
        if user_data:
            self.login_successful.emit(user_data)
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid email or password. Please try again.")
    
    def forgot_password(self):
        """Handle forgot password click"""
        try:
            # Utiliser l'email de l'utilisateur connecté
            email = self.email_input.text().strip()
            if not email:
                logger.warning("Forgot Password: No email provided.")
                QMessageBox.warning(self, "Input Error", "Please enter your email address in the login field.")
                return
            
            logger.info(f"Forgot Password: Attempting to send reset token to {email}.")
            reset_token = self.auth_service.reset_password_request(email)
            if reset_token:
                QMessageBox.information(self, "Password Reset", 
                                         f"A password reset token has been sent to {email}. "
                                         "Please check your inbox and use the token to reset your password.")
                logger.info(f"Forgot Password: Reset token sent successfully to {email}.")

                # Afficher directement la boîte de dialogue pour vérifier le jeton
                self.reset_password()
            else:
                logger.error(f"Forgot Password: Failed to send reset token to {email}.")
                QMessageBox.warning(self, "Error", 
                                    "An error occurred while sending the reset token. Please try again.")
        except Exception as e:
            logger.error(f"Forgot Password: Unexpected error occurred: {str(e)}")

    def reset_password(self):
        """Handle password reset using token"""
        try:
            # Request the token
            token, ok = QInputDialog.getText(self, "Reset Password", "Enter your reset token:")
            if not ok:  # User clicked cancel
                logger.info("Reset Password: User canceled the token input dialog.")
                return  # Exit without showing any message

            if not token.strip():  # Token is empty
                logger.warning("Reset Password: Invalid or empty token provided.")
                QMessageBox.warning(self, "Input Error", "Please provide a valid reset token.")
                return

            # Request the new password
            new_password, ok = QInputDialog.getText(self, "Reset Password", "Enter your new password:", QLineEdit.Password)
            if not ok or not new_password.strip():
                logger.warning("Reset Password: Invalid or empty new password provided.")
                QMessageBox.warning(self, "Input Error", "Please provide a valid new password.")
                return

            logger.info("Reset Password: Attempting to reset password.")
            success = self.auth_service.reset_password(token.strip(), new_password.strip())
            if success:
                QMessageBox.information(self, "Password Reset", "Your password has been successfully reset.")
                logger.info("Reset Password: Password reset successfully.")
            else:
                logger.error("Reset Password: Failed to reset password. Invalid token or other error.")
                QMessageBox.warning(self, "Error", "Invalid token or an error occurred. Please try again.")
        except Exception as e:
            logger.error(f"Reset Password: Unexpected error occurred: {str(e)}")

class TokenVerificationDialog:
    def __init__(self):
        # Initialize the dialog components
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_process)

    def cancel_process(self):
        """Handle the cancel action to cleanly cancel the process."""
        logger.info("Token verification process canceled by the user.")
        # Add logic to reset any state or cleanup if necessary
        self.close()  # Close the dialog
        # Optionally, navigate back to the login screen or reset the application state
        self.parent().reset_to_initial_state()  # Example method to reset state