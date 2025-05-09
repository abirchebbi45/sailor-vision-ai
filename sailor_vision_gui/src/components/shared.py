# src/components/shared.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QSizePolicy, QSlider,
                            QToolButton, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QEvent, QUrl
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QColor, QPen
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget  # Import QVideoWidget
import os

from utils import format_relative_time
import logging

logger = logging.getLogger(__name__)

class HeaderWidget(QWidget):
    search_text_changed = pyqtSignal(str)
    action_button_clicked = pyqtSignal()

    def __init__(
        self,
        title: str = "",
        action_button_text: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.title = title
        self.action_button_text = action_button_text
        self.init_ui()

    def init_ui(self):
        self.setObjectName("headerWidget")
        self.setFixedHeight(100)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)

        # — Titre —
        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("pageTitleLabel")
        self.title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        layout.addWidget(self.title_label)

        layout.addStretch()

        # — Search box —
        self.search_box = QLineEdit()
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("Search...")
        self.search_box.setFixedHeight(30)
        self.search_box.textChanged.connect(self.on_search_text_changed)
        layout.addWidget(self.search_box)

        # — Bouton d’action (optionnel) —
        if self.action_button_text:
            btn = QPushButton(self.action_button_text)
            btn.setObjectName("actionButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.clicked.connect(self.on_action_button_clicked)
            layout.addWidget(btn)

        self.setLayout(layout)
    
    def set_title(self, title):
        self.title = title
        self.title_label.setText(title)
    
    def set_action_button(self, text="", visible=True):
        if hasattr(self, 'action_button'):
            self.action_button.setText(text)
            self.action_button.setVisible(visible)
        elif text and visible:
            self.action_button = QPushButton(text)
            self.action_button.setObjectName("actionButton")
            self.action_button.setCursor(Qt.PointingHandCursor)
            self.action_button.clicked.connect(self.on_action_button_clicked)
            self.layout().addWidget(self.action_button)
    
    def on_search_text_changed(self, text):
        self.search_text_changed.emit(text)
    
    def on_action_button_clicked(self):
        self.action_button_clicked.emit()

    def set_search_box_visibility(self, visible=True):
        """Set search box visibility"""
        if hasattr(self, 'search_box'):
            self.search_box.setVisible(visible)

    def set_search_placeholder(self, text):
        """Set search box placeholder text"""
        if hasattr(self, 'search_box'):
            self.search_box.setPlaceholderText(text)

class SidebarNavButton(QWidget):
    clicked = pyqtSignal()
    
    def __init__(self, icon_name, text, parent=None):
        super().__init__(parent)
        self.setObjectName("NavButton") 
        self.active = False
        self.init_ui(icon_name, text)
        
    def init_ui(self, icon_name, text):
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)  # Adjust margins for compact size
        layout.setSpacing(8)  # Add spacing between icon and text
        
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)  # Reduce the icon size
        self.icon_label.setScaledContents(True)  # Allow the icon to scale properly
        icon = QIcon(icon_name)  # Use the provided icon name directly
        if not icon.isNull():
            self.icon_label.setPixmap(icon.pixmap(24, 24))  # Set the icon size explicitly
        
        self.text_label = QLabel(text)
        self.text_label.setObjectName("navButtonText")
        self.text_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)  # Align text properly
        self.text_label.setStyleSheet("font-size: 12px;")  # Minimize text size
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addStretch()
        
        self.setLayout(layout)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("active", "false")  # Ensure the default state is inactive
        self.update_stylesheet()
    
    def set_active(self, active):
        self.active = active
        self.setProperty("active", "true" if active else "false")
        self.update_stylesheet()
    
    def update_stylesheet(self):
        """Update the stylesheet dynamically based on the active state."""
        if self.active:
            self.setStyleSheet("""
                QWidget#NavButton {
                    background-color: #E3F2FD;
                }
                QWidget#NavButton QLabel {
                    color: #1E88E5;
                    font-weight: bold;  /* Make text bold when active */
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget#NavButton {
                    background-color: transparent;
                }
                QWidget#NavButton:hover {
                    background-color: #f5f5f5;
                }
                QWidget#NavButton QLabel {
                    color: #333333;
                    font-weight: normal;  /* Normal text weight when inactive */
                }
            """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class Sidebar(QWidget):
    dashboard_clicked = pyqtSignal()
    live_feed_clicked = pyqtSignal()
    playback_clicked = pyqtSignal()
    alerts_clicked = pyqtSignal()
    user_management_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    profile_clicked = pyqtSignal()
    view_profile_clicked = pyqtSignal()  # Signal for "View Profile" action
    logout_clicked = pyqtSignal()       # Signal for "Logout" action
    
    def __init__(self, user_data=None):
        super().__init__()
        self.user_data = user_data
        self.active_button = None
        self.init_ui()
    
    def init_ui(self):
        self.setObjectName("Sidebar")
        self.setMinimumWidth(200)
        self.setMaximumWidth(200)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Logo container with proper padding
        logo_container = QWidget()
        logo_container.setObjectName("logoContainer")
        logo_container.setFixedHeight(60)  # Reduced height
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(15, 5, 15, 5)  # Added horizontal padding
        
        logo_label = QLabel()
        logo_label.setFixedSize(140, 50)
        logo_label.setScaledContents(True)
        logo_icon = QIcon("/home/abirc240/Desktop/sailor-vision-ai/sailor_vision_gui/src/assets/Sailor vision logo.png")
        logo_pixmap = logo_icon.pixmap(QSize(140, 50))
        logo_label.setPixmap(logo_pixmap)
        logo_layout.addWidget(logo_label, 0, Qt.AlignCenter)
        
        layout.addWidget(logo_container)
        
        # Navigation items with proper icons and reduced size
        nav_widget = QWidget()
        nav_widget.setObjectName("navigationList")
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 15, 0, 0)  # Added top padding
        nav_layout.setSpacing(2)  # Reduced spacing
        
        # Create navigation buttons with icons
        icon_size = QSize(50,50)
        self.dashboard_btn = self.create_nav_button("dashboard", "Dashboard", "/home/abirc240/Desktop/sailor-vision-ai/sailor_vision_gui/src/assets/dashboard.png", icon_size)
        self.dashboard_btn.clicked.connect(self.on_dashboard_clicked)
        
        self.live_feed_btn = self.create_nav_button("camera", "Live Feed", "/home/abirc240/Desktop/sailor-vision-ai/sailor_vision_gui/src/assets/live.png", icon_size)
        self.live_feed_btn.clicked.connect(self.on_live_feed_clicked)
        
        self.playback_btn = self.create_nav_button("play", "Playback", "/home/abirc240/Desktop/sailor-vision-ai/sailor_vision_gui/src/assets/playback.png", icon_size) 
        self.playback_btn.clicked.connect(self.on_playback_clicked)
        
        self.alerts_btn = self.create_nav_button("bell", "Alerts", "/home/abirc240/Desktop/sailor-vision-ai/sailor_vision_gui/src/assets/bell.png", icon_size)
        self.alerts_btn.clicked.connect(self.on_alerts_clicked)
        
        self.user_mgmt_btn = self.create_nav_button("users", "User Management", "/home/abirc240/Desktop/sailor-vision-ai/sailor_vision_gui/src/assets/users.png", icon_size)
        self.user_mgmt_btn.clicked.connect(self.on_user_management_clicked)
        
        self.settings_btn = self.create_nav_button("settings", "Settings", "/home/abirc240/Desktop/sailor-vision-ai/sailor_vision_gui/src/assets/settings.png", icon_size)
        self.settings_btn.clicked.connect(self.on_settings_clicked)
        
        # Add buttons to navigation layout
        nav_layout.addWidget(self.dashboard_btn)
        nav_layout.addWidget(self.live_feed_btn)
        nav_layout.addWidget(self.playback_btn)
        nav_layout.addWidget(self.alerts_btn)
        nav_layout.addWidget(self.user_mgmt_btn)
        nav_layout.addWidget(self.settings_btn)
        nav_layout.addStretch()
        
        layout.addWidget(nav_widget)
        layout.addStretch()
        
        # User profile at bottom
        if self.user_data:
            profile_container = QWidget()
            profile_container.setObjectName("userProfileContainer")
            profile_container.setFixedHeight(70)
            profile_layout = QHBoxLayout(profile_container)
            profile_layout.setContentsMargins(15, 10, 15, 10)

            self.avatar_label = QLabel()  # Store avatar_label as an instance variable
            self.avatar_label.setObjectName("userAvatar")
            self.avatar_label.setFixedSize(36, 36)
            default_avatar = QIcon("src/assets/icons/user.png").pixmap(36, 36)
            if not default_avatar.isNull():
                self.avatar_label.setPixmap(default_avatar)
            else:
                self.avatar_label.setPixmap(QIcon.fromTheme("user-info").pixmap(36, 36))
            self.avatar_label.setCursor(Qt.PointingHandCursor)
            self.avatar_label.mousePressEvent = self.toggle_profile_menu  # Attach menu toggle

            user_info = QWidget()
            user_info_layout = QVBoxLayout(user_info)
            user_info_layout.setContentsMargins(10, 0, 0, 0)
            user_info_layout.setSpacing(0)

            user_name = QLabel(self.user_data.get("first_name", "User") + " " + self.user_data.get("last_name", ""))
            user_name.setObjectName("userName")
            user_info_layout.addWidget(user_name)

            profile_layout.addWidget(self.avatar_label)
            profile_layout.addWidget(user_info)
            profile_layout.addStretch()

            layout.addWidget(profile_container)

            # Profile menu (hidden by default)
            self.profile_menu = QFrame(self)
            self.profile_menu.setObjectName("profileMenu")
            self.profile_menu.setFrameShape(QFrame.StyledPanel)
            self.profile_menu.setVisible(False)

            menu_layout = QVBoxLayout(self.profile_menu)
            menu_layout.setContentsMargins(0, 0, 0, 0)

            view_profile_button = QPushButton("View Profile")
            view_profile_button.setObjectName("viewProfileButton")
            view_profile_button.clicked.connect(self.view_profile_clicked.emit)
            menu_layout.addWidget(view_profile_button)

            logout_button = QPushButton("Logout")
            logout_button.setObjectName("logoutButton")
            logout_button.clicked.connect(self.logout_clicked.emit)
            menu_layout.addWidget(logout_button)

            layout.addWidget(self.profile_menu)
        
        self.setLayout(layout)
        self.set_active_button(self.dashboard_btn)

    def create_nav_button(self, icon_name, text, icon_path, icon_size):
        button = SidebarNavButton(icon_name, text)
        
        # Try custom icon first
        custom_icon = QIcon(icon_path)
        if not custom_icon.isNull():
            button.icon_label.setPixmap(custom_icon.pixmap(icon_size))
        
        # Make button smaller
        button.setFixedHeight(40) ## changed
        button.layout().setContentsMargins(15, 3, 15, 3)
        
        return button
    
    def set_active_button(self, button):
        """Set the active button and deactivate the previous one."""
        if self.active_button:
            self.active_button.set_active(False)  # Deactivate the previous button
        button.set_active(True)  # Activate the new button
        self.active_button = button
    
    def on_dashboard_clicked(self):
        self.set_active_button(self.dashboard_btn)  # Update active button
        self.dashboard_clicked.emit()
    
    def on_live_feed_clicked(self):
        self.set_active_button(self.live_feed_btn)  # Update active button
        self.live_feed_clicked.emit()
    
    def on_playback_clicked(self):
        self.set_active_button(self.playback_btn)  # Update active button
        self.playback_clicked.emit()
    
    def on_alerts_clicked(self):
        self.set_active_button(self.alerts_btn)  # Update active button
        self.alerts_clicked.emit()
    
    def on_user_management_clicked(self):
        self.set_active_button(self.user_mgmt_btn)  # Update active button
        self.user_management_clicked.emit()
    
    def on_settings_clicked(self):
        self.set_active_button(self.settings_btn)  # Update active button
        self.settings_clicked.emit()
    
    def on_profile_clicked(self):
        self.profile_clicked.emit()

    def toggle_profile_menu(self, event):
        """Toggle the visibility of the profile menu and position it above the avatar."""
        if self.profile_menu.isVisible():
            self.profile_menu.setVisible(False)
        else:
            # Get the global position of the avatar
            avatar_geometry = self.avatar_label.geometry()
            global_position = self.avatar_label.mapToGlobal(avatar_geometry.topLeft())
            
            # Adjust the position to display the menu above the avatar
            menu_x = global_position.x()
            menu_y = global_position.y() - self.profile_menu.height()  # Position above the avatar
            
            # Ensure the menu is fully visible on the screen
            screen_geometry = self.screen().geometry()
            if menu_y < screen_geometry.top():
                menu_y = screen_geometry.top() + 10  # Add some padding if it goes off-screen
            
            self.profile_menu.move(menu_x, menu_y)
            self.profile_menu.setVisible(True)

class CameraWidget(QFrame):
    def __init__(self, camera):
        super().__init__()
        self.camera = camera
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Set up frame
        self.setObjectName("cameraWidget")
        self.setFixedHeight(320)
        self.setFrameShape(QFrame.StyledPanel)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Camera feed (placeholder)
        feed_container = QWidget()
        feed_container.setObjectName("cameraFeed")
        feed_container.setFixedHeight(200)
        
        # Example image with detection boxes (would be dynamic in real app)
        # Here we just show a placeholder
        placeholder = QLabel("Camera Feed")
        placeholder.setAlignment(Qt.AlignCenter)
        
        feed_layout = QVBoxLayout(feed_container)
        feed_layout.addWidget(placeholder)
        
        layout.addWidget(feed_container)
        
        # Camera title
        title = QLabel(self.camera.location or f"Camera {self.camera.name}")
        title.setObjectName("cameraTitle")
        layout.addWidget(title)
        
        # Camera details
        details = QLabel(f"Camera {self.camera.name}: {self.camera.location}")
        layout.addWidget(details)
        
        # Status
        status = QLabel(f"Status: {'Active' if self.camera.is_active else 'Inactive'}")
        layout.addWidget(status)

class LiveFeedWidget(QFrame):
    expand_clicked = pyqtSignal(int)  # Signal for expand button click with camera id
    
    def __init__(self, camera):
        super().__init__()
        self.camera = camera
        self.detections = []
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Set up frame
        self.setObjectName("liveFeedWidget")
        self.setFixedHeight(300)
        self.setFrameShape(QFrame.StyledPanel)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Feed header
        header_layout = QHBoxLayout()
        
        # Connection status
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(15, 15)
        self.status_indicator.setObjectName("statusIndicator")
        
        status_text = QLabel("Connected")
        
        header_layout.addWidget(self.status_indicator)
        header_layout.addWidget(status_text)
        header_layout.addStretch()
        
        # Expand button
        expand_btn = QPushButton("Expand")
        expand_btn.clicked.connect(lambda: self.expand_clicked.emit(self.camera.id))
        header_layout.addWidget(expand_btn)
        
        layout.addLayout(header_layout)
        
        # Camera feed
        self.feed_label = QLabel()
        self.feed_label.setObjectName("cameraFeed")
        self.feed_label.setAlignment(Qt.AlignCenter)
        self.feed_label.setMinimumHeight(200)
        self.feed_label.setText("Loading feed...")
        
        layout.addWidget(self.feed_label)
    
    def update_frame(self, pixmap):
        """Update the feed with a new frame"""
        self.feed_label.setPixmap(pixmap.scaled(
            self.feed_label.width(), 
            self.feed_label.height(),
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        ))

class UserCard(QFrame):
    edit_clicked = pyqtSignal(int)  # Signal for edit button click with user id
    delete_clicked = pyqtSignal(int)  # Signal for delete button click with user id
    
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Set up frame
        self.setObjectName("userCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(150)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # User name and role
        name_role = QLabel(f"{self.user.first_name or ''} {self.user.last_name or ''} - {self.user.role.value if hasattr(self.user.role, 'value') else str(self.user.role)}")
        name_role.setObjectName("userName")
        layout.addWidget(name_role)
        
        # Job title
        job_title = QLabel(self.user.job_title or "")
        job_title.setObjectName("userJobTitle")
        layout.addWidget(job_title)
        
        # Email
        email = QLabel(self.user.email)
        layout.addWidget(email)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        edit_btn = QPushButton("Edit")
        edit_btn.setObjectName("outlineButton")
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.user.id))
        
        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("outlineButton")
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.user.id))
        
        buttons_layout.addWidget(edit_btn)
        buttons_layout.addWidget(delete_btn)
        
        layout.addLayout(buttons_layout)

class VideoPlayerWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.source = None
        self.is_playing = False
        self.current_time = 0
        self.total_time = 100  # Default duration in seconds
        
        # Initialize QMediaPlayer before calling init_ui
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.media_player.mediaStatusChanged.connect(self.check_for_errors)  # Connect media status signal
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Set up frame
        self.setObjectName("videoPlayer")
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(300)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Video display
        self.video_display = QVideoWidget()  # Use QVideoWidget for video playback
        self.video_display.setMinimumHeight(200)
        
        layout.addWidget(self.video_display)
        
        # Controls bar
        controls_layout = QHBoxLayout()
        
        # Play/pause button
        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon.fromTheme("media-playback-start"))
        self.play_button.clicked.connect(self.toggle_playback)
        controls_layout.addWidget(self.play_button)
        
        # Next frame button
        next_frame_button = QPushButton()
        next_frame_button.setIcon(QIcon.fromTheme("media-skip-forward"))
        controls_layout.addWidget(next_frame_button)
        
        # Previous frame button
        prev_frame_button = QPushButton()
        prev_frame_button.setIcon(QIcon.fromTheme("media-skip-backward"))
        controls_layout.addWidget(prev_frame_button)
        
        # Time indicator
        self.time_label = QLabel("1:11 / 2:55")
        controls_layout.addWidget(self.time_label)
        
        # Seek slider
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 100)
        self.seek_slider.setValue(0)
        self.seek_slider.sliderMoved.connect(self.seek)
        controls_layout.addWidget(self.seek_slider)
        
        # Fullscreen button
        fullscreen_button = QPushButton()
        fullscreen_button.setIcon(QIcon.fromTheme("view-fullscreen"))
        controls_layout.addWidget(fullscreen_button)
        
        # Settings button
        settings_button = QPushButton()
        settings_button.setIcon(QIcon.fromTheme("preferences-system"))
        controls_layout.addWidget(settings_button)
        
        layout.addLayout(controls_layout)
        
        # Attach media player to video display
        self.media_player.setVideoOutput(self.video_display)  # Attach QVideoWidget to QMediaPlayer
    
    def check_for_errors(self, status):
        """Check for errors in the media player"""
        if self.media_player.error() != QMediaPlayer.NoError:
            error_message = self.media_player.errorString()
            print(f"MediaPlayer Error: {error_message}")
            logger.error(f"MediaPlayer Error: {error_message}")
        
    def set_source(self, file_path):
        """Set the video source"""
        if not os.path.exists(file_path):
            print(f"Video file not found: {file_path}")
            logger.error(f"Video file not found: {file_path}")
            return
        self.source = file_path
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
        print(f"Video source set: {file_path}")
        logger.info(f"Video source set: {file_path}")
        
    def play(self):
        """Start video playback"""
        if self.source:
            self.media_player.play()
            self.is_playing = True
            print("Video playback started")
        else:
            print("No video source set")
        
    def pause(self):
        """Pause video playback"""
        if self.is_playing:
            self.media_player.pause()
            self.is_playing = False
            print("Video playback paused")
    
    def toggle_playback(self):
        """Toggle between play and pause"""
        if self.is_playing:
            self.pause()
        else:
            self.play()
    
    def seek(self, position):
        """Seek to position"""
        self.current_time = (position / 100) * self.total_time
        # In a real app, you would seek the video to the specified position

class RecordingItem(QFrame):
    """Widget représentant un élément d'enregistrement dans la liste"""
    def __init__(self, recording, playback_screen):
        super().__init__()
        self.recording = recording
        self.playback_screen = playback_screen
        self.setObjectName("recordingItem")  # Assign an object name for styling
        self.setMinimumHeight(80)
        self.setMaximumHeight(80)
        self.init_ui()