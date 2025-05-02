""" import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QFrame, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QIcon

from src.services.auth_service import AuthService
from models import User

class LoginScreen(QWidget):
    login_successful = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.auth_service = AuthService()
        self.init_ui()
        
    def init_ui(self):
        #Initialize the UI components
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignCenter)
        
        # Login container
        login_container = QFrame()
        login_container.setObjectName("loginContainer")
        login_container.setFixedWidth(400)
        login_container.setFixedHeight(500)
        
        login_layout = QVBoxLayout(login_container)
        login_layout.setAlignment(Qt.AlignCenter)
        login_layout.setSpacing(20)
        login_layout.setContentsMargins(30, 30, 30, 30)
        
        # Logo
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_icon = QIcon("assets/Sailor vision logo.png")
        logo_pixmap = logo_icon.pixmap(QSize(120, 120))
        logo_label.setPixmap(logo_pixmap)
        login_layout.addWidget(logo_label)
        
        # Title
        title_label = QLabel("Access Account")
        title_label.setObjectName("loginTitle")
        title_label.setAlignment(Qt.AlignCenter)
        login_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Your gateway to innovative solutions")
        subtitle_label.setObjectName("loginSubtitle")
        subtitle_label.setAlignment(Qt.AlignCenter)
        login_layout.addWidget(subtitle_label)
        
        # Spacer
        login_layout.addSpacing(20)
        
        # Email field
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Your email address")
        self.email_input.setObjectName("loginInput")
        login_layout.addWidget(self.email_input)
        
        # Password field
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setObjectName("loginInput")
        login_layout.addWidget(self.password_input)
        
        # Forgot password link
        forgot_password = QLabel("<a href='#' style='color: #1E88E5; text-decoration: none;'>Forget your password?</a>")
        forgot_password.setObjectName("forgotPassword")
        forgot_password.setAlignment(Qt.AlignRight)
        forgot_password.setOpenExternalLinks(False)
        forgot_password.linkActivated.connect(self.forgot_password)
        login_layout.addWidget(forgot_password)
        
        # Login button
        login_button = QPushButton("Log In")
        login_button.setObjectName("primaryButton")
        login_button.setFixedHeight(40)
        login_button.clicked.connect(self.login)
        login_layout.addWidget(login_button)
        
        # Add login container to main layout
        main_layout.addWidget(login_container, alignment=Qt.AlignCenter)
        
        # Add attribution - remove this in production
        attribution = QLabel("Made with Visily")
        attribution.setObjectName("attribution")
        attribution.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(attribution)
        
        self.setLayout(main_layout)
        
        # Set some initial focus
        self.email_input.setFocus()
        
    def login(self):
        #Handle login attempt
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        if not email or not password:
            QMessageBox.warning(self, "Login Error", "Please enter both email and password.")
            return
        
        # Try to authenticate
        user = self.auth_service.authenticate(email, password)
        
        if user:
            self.login_successful.emit(user_data)
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid email or password. Please try again.")
    
    def forgot_password(self):
        #Handle forgot password click
        email = self.email_input.text().strip()
        if not email:
            QMessageBox.information(self, "Password Reset", 
                                   "Please enter your email address and click 'Forget your password?' again.")
            return
        
        # In a real app, this would send a password reset email
        QMessageBox.information(self, "Password Reset", 
                               f"Password reset instructions have been sent to {email} if this account exists.")
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QFrame, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QIcon

from src.services.auth_service import AuthService
from models import User

class LoginScreen(QWidget):
    login_successful = pyqtSignal(User)
    
    def __init__(self):
        super().__init__()
        self.auth_service = AuthService()
        self.init_ui()
        
    def init_ui(self):
        #Initialize the UI components
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignCenter)
        
        # Login container
        login_container = QFrame()
        login_container.setObjectName("loginContainer")
        login_container.setFixedWidth(400)
        login_container.setFixedHeight(500)
        
        login_layout = QVBoxLayout(login_container)
        login_layout.setAlignment(Qt.AlignCenter)
        login_layout.setSpacing(20)
        login_layout.setContentsMargins(30, 30, 30, 30)
        
        # Logo
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_icon = QIcon("/home/abirc240/Desktop/sailor-vision-ai/sailor_vision_gui/src/assets/Sailor vision logo.png")
        logo_pixmap = logo_icon.pixmap(QSize(120, 120))
        logo_label.setPixmap(logo_pixmap)
        login_layout.addWidget(logo_label)
        
        # Title
        title_label = QLabel("Access Account")
        title_label.setObjectName("loginTitle")
        title_label.setAlignment(Qt.AlignCenter)
        login_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Your gateway to innovative solutions")
        subtitle_label.setObjectName("loginSubtitle")
        subtitle_label.setAlignment(Qt.AlignCenter)
        login_layout.addWidget(subtitle_label)
        
        # Spacer
        login_layout.addSpacing(20)
        
        # Email field
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Your email address")
        self.email_input.setObjectName("loginInput")
        login_layout.addWidget(self.email_input)
        
        # Password field
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setObjectName("loginInput")
        login_layout.addWidget(self.password_input)
        
        # Forgot password link
        forgot_password = QLabel("<a href='#' style='color: #1E88E5; text-decoration: none;'>Forget your password?</a>")
        forgot_password.setObjectName("forgotPassword")
        forgot_password.setAlignment(Qt.AlignRight)
        forgot_password.setOpenExternalLinks(False)
        forgot_password.linkActivated.connect(self.forgot_password)
        login_layout.addWidget(forgot_password)
        
        # Login button
        login_button = QPushButton("Log In")
        login_button.setObjectName("primaryButton")
        login_button.setFixedHeight(40)
        login_button.clicked.connect(self.login)
        login_layout.addWidget(login_button)
        
        # Add login container to main layout
        main_layout.addWidget(login_container, alignment=Qt.AlignCenter)
        
        # Add attribution - remove this in production
        attribution = QLabel("Made with Visily")
        attribution.setObjectName("attribution")
        attribution.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(attribution)
        
        self.setLayout(main_layout)
        
        # Set some initial focus
        self.email_input.setFocus()
        
    def login(self):
        #Handle login attempt
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        if not email or not password:
            QMessageBox.warning(self, "Login Error", "Please enter both email and password.")
            return
        
        # Try to authenticate
        user = self.auth_service.authenticate(email, password)
        
        if user:
            self.login_successful.emit(user)
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid email or password. Please try again.")
    
    def forgot_password(self):
        #Handle forgot password click
        email = self.email_input.text().strip()
        if not email:
            QMessageBox.information(self, "Password Reset", 
                                   "Please enter your email address and click 'Forget your password?' again.")
            return
        
        # In a real app, this would send a password reset email
        QMessageBox.information(self, "Password Reset", 
                               f"Password reset instructions have been sent to {email} if this account exists.")
 """

# src/components/login.py
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QFrame, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QIcon

from src.services.auth_service import AuthService

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
        email = self.email_input.text().strip()
        if not email:
            QMessageBox.information(self, "Password Reset", 
                                   "Please enter your email address and click 'Forget your password?' again.")
            return
        QMessageBox.information(self, "Password Reset", 
                               f"Password reset instructions have been sent to {email} if this account exists.")