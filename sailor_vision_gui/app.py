import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFontDatabase, QFont

from src.components.login import LoginScreen
from components.dashboard import DashboardScreen
from components.live_feed import LiveFeedScreen
from components.playback import PlaybackScreen
from components.alerts import AlertsScreen
from components.user_management import UserManagementScreen
from components.settings import SettingsScreen
from components.shared import Sidebar

from database import init_db
from models import User, Camera, Alert, Recording
from config import load_config

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize database
        init_db()
        
        # Load configuration
        self.config = load_config()
        
        # Set up the main window
        self.setWindowTitle("SailorVision - Maritime Surveillance")
        self.setMinimumSize(1200, 800)
        
        # Create stacked widget for different screens
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create the login screen first
        self.login_screen = LoginScreen()
        self.login_screen.login_successful.connect(self.show_main_interface)
        
        # Create the content widget (will be populated after login)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # Create stacked widget for main content
        self.stacked_widget = QStackedWidget()
        
        # Initially just show the login screen
        self.main_layout.addWidget(self.login_screen)
        
    def show_main_interface(self, user):
        """Show the main interface after successful login"""
        # Remove login screen
        self.login_screen.setParent(None)
        
        # Setup sidebar and content area
        self.setup_main_interface(user)
        
        # Add content widget to main layout
        self.main_layout.addWidget(self.content_widget)
        
    def setup_main_interface(self, user):
        """Set up the main interface with sidebar and content area"""
        # Create horizontal layout for sidebar and content
        self.horizontal_layout = QVBoxLayout()
        self.horizontal_layout.setContentsMargins(0, 0, 0, 0)
        self.horizontal_layout.setSpacing(0)
        
        # Create sidebar
        self.sidebar = Sidebar(user)
        
        # Create screens
        self.dashboard_screen = DashboardScreen()
        self.live_feed_screen = LiveFeedScreen()
        self.playback_screen = PlaybackScreen()
        self.alerts_screen = AlertsScreen()
        self.user_management_screen = UserManagementScreen()
        self.settings_screen = SettingsScreen(user)
        
        # Add screens to stacked widget
        self.stacked_widget.addWidget(self.dashboard_screen)
        self.stacked_widget.addWidget(self.live_feed_screen)
        self.stacked_widget.addWidget(self.playback_screen)
        self.stacked_widget.addWidget(self.alerts_screen)
        self.stacked_widget.addWidget(self.user_management_screen)
        self.stacked_widget.addWidget(self.settings_screen)
        
        # Connect sidebar buttons to change screen
        self.sidebar.dashboard_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.dashboard_screen))
        self.sidebar.live_feed_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.live_feed_screen))
        self.sidebar.playback_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.playback_screen))
        self.sidebar.alerts_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.alerts_screen))
        self.sidebar.user_management_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.user_management_screen))
        self.sidebar.settings_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.settings_screen))
        
        # Add sidebar and stacked widget to content layout
        self.content_layout.addWidget(self.sidebar, 0, Qt.AlignLeft)
        self.content_layout.addWidget(self.stacked_widget)

def setup_fonts():
    """Set up application fonts"""
    font_db = QFontDatabase()
    font_db.addApplicationFont(":/fonts/Inter-Regular.ttf")
    font_db.addApplicationFont(":/fonts/Inter-Bold.ttf")
    font_db.addApplicationFont(":/fonts/Inter-Medium.ttf")
    
    # Set application font
    app_font = QFont("Inter")
    QApplication.setFont(app_font)

def main():
    # Create application
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set stylesheet
    with open("assets/style.qss", "r") as f:
        app.setStyleSheet(f.read())
    
    # Setup fonts
    setup_fonts()
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
