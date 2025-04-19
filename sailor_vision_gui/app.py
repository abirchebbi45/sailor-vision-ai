import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFontDatabase, QFont
import logging

from src.components.login import LoginScreen
from src.components.dashboard import DashboardScreen
from src.components.live_feed import LiveFeedScreen
from src.components.shared import Sidebar, HeaderWidget

from database import init_db
from models import User, Camera, Alert, Recording
from config import load_config

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize database
        init_db()
        
        # Main window configuration
        self.setWindowTitle("Sailor Vision AI - Maritime Surveillance")
        self.setMinimumSize(960, 680)  # Further reduced size for better adaptability
        
        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Login screen
        self.login_screen = LoginScreen()
        self.login_screen.login_successful.connect(self.handle_login_success)
        self.main_layout.addWidget(self.login_screen)
        
        # State variables
        self.current_content = None
        self.stacked_widget = None
        self.sidebar = None

    def handle_login_success(self, user_data):
        """Handle successful login"""
        logger.debug("Login successful, loading main interface")
        
        # Clean up login screen
        self.login_screen.setParent(None)
        self.main_layout.removeWidget(self.login_screen)
        
        # Create new interface
        self.initialize_main_interface(user_data)

    def initialize_main_interface(self, user_data):
        """Initialize main interface after login"""
        # Clean up previous content
        if self.current_content:
            self.current_content.deleteLater()
        
        # Create main container
        self.current_content = QWidget()
        self.main_layout.addWidget(self.current_content)
        
        # Main layout
        main_layout = QHBoxLayout(self.current_content)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = Sidebar(user_data=user_data)
        main_layout.addWidget(self.sidebar)

        # Container for header and content
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Header
        self.header = HeaderWidget("Dashboard")
        content_layout.addWidget(self.header)

        # Stacked Widget for screens
        self.stacked_widget = QStackedWidget()
        self.initialize_screens(user_data)
        
        # Sidebar connections
        self.sidebar.dashboard_clicked.connect(
            lambda: self.switch_view("Dashboard", self.dashboard_screen)
        )
        self.sidebar.live_feed_clicked.connect(
            lambda: self.switch_view("Live Feed", self.live_feed_screen)
        )
        self.sidebar.playback_clicked.connect(
            lambda: self.switch_view("Playback", None)  # To be implemented
        )
        self.sidebar.alerts_clicked.connect(
            lambda: self.switch_view("Alerts", None)  # To be implemented
        )
        self.sidebar.user_management_clicked.connect(
            lambda: self.switch_view("User Management", None)  # To be implemented
        )
        self.sidebar.settings_clicked.connect(
            lambda: self.switch_view("Settings", None)  # To be implemented
        )

        content_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(content_widget, 1)  # Give content area stretch factor of 1

        # Initial view
        self.switch_view("Dashboard", self.dashboard_screen)

    def initialize_screens(self, user_data):
        """Initialize different screens"""
        self.dashboard_screen = DashboardScreen(user_data=user_data)
        self.live_feed_screen = LiveFeedScreen(user_data=user_data)
        
        self.stacked_widget.addWidget(self.dashboard_screen)
        self.stacked_widget.addWidget(self.live_feed_screen)

    def switch_view(self, title, widget):
        """Change active view"""
        if widget:
            self.header.set_title(title)
            self.stacked_widget.setCurrentWidget(widget)
            
            # Configure search based on view
            if title == "Dashboard":
                self.header.set_search_box_visibility(True)
                self.header.set_search_placeholder("Search cameras, alerts...")
            elif title == "Live Feed":
                self.header.set_search_box_visibility(True)
                self.header.set_search_placeholder("Search cameras...")
            else:
                # Other views may have different search needs
                self.header.set_search_box_visibility(True)
                self.header.set_search_placeholder(f"Search {title.lower()}...")
        else:
            logger.warning(f"Screen '{title}' not implemented")

    def clear_layout(self, layout):
        """Recursively clear a layout"""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                self.clear_layout(item.layout())

def setup_fonts():
    """Configure application fonts"""
    font_db = QFontDatabase()
    try:
        font_db.addApplicationFont("assets/fonts/Inter-Regular.ttf")
        font_db.addApplicationFont("assets/fonts/Inter-Bold.ttf")
        font_db.addApplicationFont("assets/fonts/Inter-Medium.ttf")
        app_font = QFont("Inter")
        app_font.setPixelSize(14)  # Base font size
    except Exception as e:
        logger.warning(f"Error loading fonts: {str(e)}")
        app_font = QFont("Arial")
        app_font.setPixelSize(14)
    
    QApplication.setFont(app_font)

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Create font and asset directories if they don't exist
    os.makedirs("assets/fonts", exist_ok=True)
    
    # Setup style
    style_path = os.path.join(os.path.dirname(__file__), "src", "assets", "style.qss")
    try:
        with open(style_path, "r") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        logger.warning(f"Error loading style: {str(e)}")
        # Try to create a default style file
        os.makedirs(os.path.dirname(style_path), exist_ok=True)
        with open(style_path, "w") as f:
            f.write("""
            /* Default styling */
            QMainWindow {
                background-color: #f5f5f5;
            }
            """)
        logger.info(f"Created default style file at {style_path}")
    
    setup_fonts()
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()