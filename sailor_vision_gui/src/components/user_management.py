from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QGridLayout, QFrame, QScrollArea,
                            QDialog, QLineEdit, QComboBox, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon

from src.services.user_service import UserService
from src.components.shared import HeaderWidget, UserCard
from models import User, UserRole

class UserDialog(QDialog):
    def __init__(self, user=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.user_service = UserService()
        
        # Set window properties
        self.setWindowTitle("Add User" if not user else "Edit User")
        self.setFixedSize(500, 500)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        
        self.init_ui()
        
        # If editing user, populate fields
        if self.user:
            self.populate_fields()
    
    def init_ui(self):
        """Initialize dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Add User" if not self.user else "Edit User")
        title.setObjectName("dialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Form layout
        form_layout = QVBoxLayout()
        
        # Username field
        username_layout = QHBoxLayout()
        username_label = QLabel("Username:")
        username_label.setFixedWidth(100)
        self.username_input = QLineEdit()
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        form_layout.addLayout(username_layout)
        
        # Email field
        email_layout = QHBoxLayout()
        email_label = QLabel("Email:")
        email_label.setFixedWidth(100)
        self.email_input = QLineEdit()
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        form_layout.addLayout(email_layout)
        
        # First name field
        firstname_layout = QHBoxLayout()
        firstname_label = QLabel("First Name:")
        firstname_label.setFixedWidth(100)
        self.firstname_input = QLineEdit()
        firstname_layout.addWidget(firstname_label)
        firstname_layout.addWidget(self.firstname_input)
        form_layout.addLayout(firstname_layout)
        
        # Last name field
        lastname_layout = QHBoxLayout()
        lastname_label = QLabel("Last Name:")
        lastname_label.setFixedWidth(100)
        self.lastname_input = QLineEdit()
        lastname_layout.addWidget(lastname_label)
        lastname_layout.addWidget(self.lastname_input)
        form_layout.addLayout(lastname_layout)
        
        # Job title field
        job_layout = QHBoxLayout()
        job_label = QLabel("Job Title:")
        job_label.setFixedWidth(100)
        self.job_input = QLineEdit()
        job_layout.addWidget(job_label)
        job_layout.addWidget(self.job_input)
        form_layout.addLayout(job_layout)
        
        # Role selection
        role_layout = QHBoxLayout()
        role_label = QLabel("Role:")
        role_label.setFixedWidth(100)
        self.role_combo = QComboBox()
        
        # Add roles to combo box
        for role in UserRole:
            self.role_combo.addItem(role.value, role)
        
        role_layout.addWidget(role_label)
        role_layout.addWidget(self.role_combo)
        form_layout.addLayout(role_layout)
        
        # Password field (only for new users)
        if not self.user:
            password_layout = QHBoxLayout()
            password_label = QLabel("Password:")
            password_label.setFixedWidth(100)
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.Password)
            password_layout.addWidget(password_label)
            password_layout.addWidget(self.password_input)
            form_layout.addLayout(password_layout)
            
            # Confirm password field
            confirm_layout = QHBoxLayout()
            confirm_label = QLabel("Confirm:")
            confirm_label.setFixedWidth(100)
            self.confirm_input = QLineEdit()
            self.confirm_input.setEchoMode(QLineEdit.Password)
            confirm_layout.addWidget(confirm_label)
            confirm_layout.addWidget(self.confirm_input)
            form_layout.addLayout(confirm_layout)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self.save_user)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
    
    def populate_fields(self):
        """Populate the input fields with the user's existing data."""
        if not self.user:
            return
        
        self.username_input.setText(self.user.username)
        self.email_input.setText(self.user.email)
        self.firstname_input.setText(self.user.first_name or "")
        self.lastname_input.setText(self.user.last_name or "")
        self.job_input.setText(self.user.job_title or "")
        
        # Set role
        if self.user.role:
            index = self.role_combo.findText(self.user.role.value if hasattr(self.user.role, "value") else str(self.user.role))
            if index >= 0:
                self.role_combo.setCurrentIndex(index)
    
    def save_user(self):
        """Save the user data to the database."""
        # Validate input
        if not self.validate_input():
            return
        
        # Build user data
        user_data = {
            "username": self.username_input.text().strip(),
            "email": self.email_input.text().strip(),
            "first_name": self.firstname_input.text().strip(),
            "last_name": self.lastname_input.text().strip(),
            "job_title": self.job_input.text().strip(),
            "role": self.role_combo.currentData()
        }
        
        # Add password if creating new user
        if not self.user:
            user_data["password"] = self.password_input.text()
        
        try:
            if self.user:
                # Update existing user
                success = self.user_service.update_user(self.user.id, user_data)
            else:
                # Create new user
                success = self.user_service.create_user(user_data)
            
            if success:
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save user. Please try again.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
    
    def validate_input(self):
        """Validate the user input fields before saving."""
        # Check required fields
        if not self.username_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Username is required.")
            return False
        
        if not self.email_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Email is required.")
            return False
        
        # Check password if creating new user
        if not self.user:
            if not self.password_input.text():
                QMessageBox.warning(self, "Validation Error", "Password is required.")
                return False
            
            if self.password_input.text() != self.confirm_input.text():
                QMessageBox.warning(self, "Validation Error", "Passwords do not match.")
                return False
            
            if len(self.password_input.text()) < 8:
                QMessageBox.warning(self, "Validation Error", "Password must be at least 8 characters.")
                return False
        
        return True

class UserManagementScreen(QWidget):
    def __init__(self, user_data=None):
        super().__init__()
        self.user_data = user_data
        self.user_service = UserService()
        
        self.init_ui()
        
        # Load initial data
        self.load_users()
    
    def init_ui(self):
        """Initialize the main user management screen UI components."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create scroll area for users grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        # Container for users grid
        self.users_container = QWidget()
        self.users_layout = QGridLayout(self.users_container)
        self.users_layout.setContentsMargins(20, 0, 20, 20)
        self.users_layout.setSpacing(20)
        
        scroll_area.setWidget(self.users_container)
        layout.addWidget(scroll_area)
    
    def load_users(self):
        """Load all users from the service and display them in the grid."""
        # Clear existing user cards
        self.clear_layout(self.users_layout)
        
        # Get all users from service
        users = self.user_service.get_all_users()
        
        # Add user cards to grid
        for i, user in enumerate(users):
            row = i // 3
            col = i % 3
            
            user_card = UserCard(user)
            user_card.edit_clicked.connect(self.show_edit_user_dialog)
            user_card.delete_clicked.connect(self.confirm_delete_user)
            
            self.users_layout.addWidget(user_card, row, col)
    
    def show_add_user_dialog(self):
        """Open a dialog to add a new user."""
        dialog = UserDialog(parent=self)
        
        if dialog.exec_() == QDialog.Accepted:
            # Reload users
            self.load_users()
    
    def show_edit_user_dialog(self, user_id):
        """Open a dialog to edit an existing user's details."""
        user = self.user_service.get_user(user_id)
        if user:
            dialog = UserDialog(user, parent=self)
            
            if dialog.exec_() == QDialog.Accepted:
                # Reload users
                self.load_users()
    
    def confirm_delete_user(self, user_id):
        """Prompt the user for confirmation before deleting a user."""
        user = self.user_service.get_user(user_id)
        if not user:
            return
        
        reply = QMessageBox.question(
            self, 
            "Confirm Delete",
            f"Are you sure you want to delete user {user.username}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.user_service.delete_user(user_id)
            if success:
                # Reload users
                self.load_users()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete user.")
    
    def on_add_user_clicked(self):
        """Handle the action when the 'Add User' button is clicked."""
        self.show_add_user_dialog()

    def filter_users(self, search_text):
        """Filter the displayed users based on the search text."""
        if not search_text:
            # If the search text is empty, show all users.
            for i in range(self.users_layout.count()):
                widget = self.users_layout.itemAt(i).widget()
                if widget:
                    widget.setVisible(True)
            return
        
        # Filter users based on the search text.
        search_text = search_text.lower()
        for i in range(self.users_layout.count()):
            widget = self.users_layout.itemAt(i).widget()
            if widget and isinstance(widget, UserCard):
                user = widget.user
                # Check if the search text matches any user attributes.
                if (search_text in user.username.lower() or
                    search_text in (user.email or "").lower() or
                    search_text in (user.first_name or "").lower() or
                    search_text in (user.last_name or "").lower() or
                    search_text in (user.job_title or "").lower()):
                    widget.setVisible(True)
                else:
                    widget.setVisible(False)
        
    def clear_layout(self, layout):
        """Remove all widgets from the given layout."""
        if layout is None:
            return
        
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            
            if widget is not None:
                widget.deleteLater()
            else:
                self.clear_layout(item.layout())