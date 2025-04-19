# src/components/shared.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QSizePolicy, QSlider,
                            QToolButton, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QEvent
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QColor, QPen

from utils import format_relative_time

class HeaderWidget(QWidget):
    search_text_changed = pyqtSignal(str)
    action_button_clicked = pyqtSignal()
    
    def __init__(self, title="", action_button_text="", parent=None):
        super().__init__(parent)
        self.title = title
        self.action_button_text = action_button_text
        self.init_ui()
    
    def init_ui(self):
        self.setObjectName("headerWidget")
        self.setMinimumHeight(20)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        
        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("pageTitleLabel")
        layout.addWidget(self.title_label)
        layout.addStretch()
        
        self.search_box = QLineEdit()
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("Search...")
        self.search_box.textChanged.connect(self.on_search_text_changed)
        layout.addWidget(self.search_box)
        
        if self.action_button_text:
            self.action_button = QPushButton(self.action_button_text)
            self.action_button.setObjectName("actionButton")
            self.action_button.setCursor(Qt.PointingHandCursor)
            self.action_button.clicked.connect(self.on_action_button_clicked)
            layout.addWidget(self.action_button)
        
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
        self.active = False
        self.init_ui(icon_name, text)
    
    def init_ui(self, icon_name, text):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        icon = QIcon.fromTheme(icon_name, QIcon())
        if not icon.isNull():
            self.icon_label.setPixmap(icon.pixmap(24, 24))
        
        self.text_label = QLabel(text)
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addStretch()
        
        self.setLayout(layout)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("NavButton")
    
    def set_active(self, active):
        self.active = active
        if active:
            self.setProperty("active", "true")
        else:
            self.setProperty("active", "false")
        self.style().unpolish(self)
        self.style().polish(self)
    
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
        logo_icon = QIcon("src/assets/Sailor vision logo_.png")
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
        icon_size = QSize(20, 20)
        
        self.dashboard_btn = self.create_nav_button("dashboard", "Dashboard", "src/assets/icons/dashboard.png", icon_size)
        self.dashboard_btn.clicked.connect(self.on_dashboard_clicked)
        
        self.live_feed_btn = self.create_nav_button("camera", "Live Feed", "src/assets/icons/camera.png", icon_size)
        self.live_feed_btn.clicked.connect(self.on_live_feed_clicked)
        
        self.playback_btn = self.create_nav_button("play", "Playback", "src/assets/icons/playback.png", icon_size) 
        self.playback_btn.clicked.connect(self.on_playback_clicked)
        
        self.alerts_btn = self.create_nav_button("bell", "Alerts", "src/assets/icons/bell.png", icon_size)
        self.alerts_btn.clicked.connect(self.on_alerts_clicked)
        
        self.user_mgmt_btn = self.create_nav_button("users", "User Management", "src/assets/icons/users.png", icon_size)
        self.user_mgmt_btn.clicked.connect(self.on_user_management_clicked)
        
        self.settings_btn = self.create_nav_button("settings", "Settings", "src/assets/icons/settings.png", icon_size)
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
            profile_container.setFixedHeight(70)  # Fixed height
            profile_layout = QHBoxLayout(profile_container)
            profile_layout.setContentsMargins(15, 10, 15, 10)
            
            avatar_label = QLabel()
            avatar_label.setObjectName("userAvatar")
            avatar_label.setFixedSize(36, 36)
            default_avatar = QIcon("src/assets/icons/user.png").pixmap(36, 36)
            if not default_avatar.isNull():
                avatar_label.setPixmap(default_avatar)
            else:
                # Fallback to system icon if custom icon not found
                avatar_label.setPixmap(QIcon.fromTheme("user-info").pixmap(36, 36))
            
            user_info = QWidget()
            user_info_layout = QVBoxLayout(user_info)
            user_info_layout.setContentsMargins(10, 0, 0, 0)
            user_info_layout.setSpacing(0)
            
            user_name = QLabel(self.user_data.get("first_name", "User") + " " + self.user_data.get("last_name", ""))
            user_name.setObjectName("userName")
            user_info_layout.addWidget(user_name)
            
            view_profile = QPushButton("View profile")
            view_profile.setObjectName("viewProfileLink")
            view_profile.setFlat(True)
            view_profile.setCursor(Qt.PointingHandCursor)
            view_profile.clicked.connect(self.on_profile_clicked)
            user_info_layout.addWidget(view_profile)
            
            profile_layout.addWidget(avatar_label)
            profile_layout.addWidget(user_info)
            profile_layout.addStretch()
            
            layout.addWidget(profile_container)
        
        self.setLayout(layout)
        self.set_active_button(self.dashboard_btn)

    def create_nav_button(self, icon_name, text, icon_path, icon_size):
        button = SidebarNavButton(icon_name, text)
        
        # Try custom icon first
        custom_icon = QIcon(icon_path)
        if not custom_icon.isNull():
            button.icon_label.setPixmap(custom_icon.pixmap(icon_size))
        
        # Make button smaller
        button.setFixedHeight(40)
        button.layout().setContentsMargins(15, 3, 15, 3)
        
        return button
    
    def set_active_button(self, button):
        if self.active_button:
            self.active_button.set_active(False)
        button.set_active(True)
        self.active_button = button
    
    def on_dashboard_clicked(self):
        self.set_active_button(self.dashboard_btn)
        self.dashboard_clicked.emit()
    
    def on_live_feed_clicked(self):
        self.set_active_button(self.live_feed_btn)
        self.live_feed_clicked.emit()
    
    def on_playback_clicked(self):
        self.set_active_button(self.playback_btn)
        self.playback_clicked.emit()
    
    def on_alerts_clicked(self):
        self.set_active_button(self.alerts_btn)
        self.alerts_clicked.emit()
    
    def on_user_management_clicked(self):
        self.set_active_button(self.user_mgmt_btn)
        self.user_management_clicked.emit()
    
    def on_settings_clicked(self):
        self.set_active_button(self.settings_btn)
        self.settings_clicked.emit()
    
    def on_profile_clicked(self):
        self.profile_clicked.emit()

""" class Sidebar(QWidget):
    def __init__(self, username, first_name=None, last_name=None):
        super().__init__()
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.init_ui()
        
    def init_ui(self):
        #Initialize the UI components
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.dashboard_button = self.create_menu_button("Dashboard", "dashboard", True)
        self.live_feed_button = self.create_menu_button("Live Feed", "camera")
        self.playback_button = self.create_menu_button("Playback", "play")
        self.alerts_button = self.create_menu_button("Alerts", "bell")
        self.user_management_button = self.create_menu_button("User Management", "users")
        self.settings_button = self.create_menu_button("Settings", "settings")
        
        layout.addWidget(self.dashboard_button)
        layout.addWidget(self.live_feed_button)
        layout.addWidget(self.playback_button)
        layout.addWidget(self.alerts_button)
        layout.addWidget(self.user_management_button)
        layout.addWidget(self.settings_button)
        
        layout.addStretch()
        
        user_info = QWidget()
        user_layout = QHBoxLayout(user_info)
        
        user_avatar = QLabel()
        user_avatar.setFixedSize(30, 30)
        user_avatar.setScaledContents(True)
        user_avatar.setObjectName("userAvatar")
        
        default_avatar = QPixmap("assets/default_profile.svg")
        user_avatar.setPixmap(default_avatar)
        
        display_name = f"{self.first_name or ''} {self.last_name or ''}".strip() or self.username
        user_name = QLabel(display_name)
        user_name.setObjectName("userName")
        
        user_settings = QToolButton()
        user_settings.setIcon(QIcon.fromTheme("settings"))
        user_settings.setAutoRaise(True)
        
        user_layout.addWidget(user_avatar)
        user_layout.addWidget(user_name)
        user_layout.addStretch()
        user_layout.addWidget(user_settings)
        
        view_profile = QPushButton("View profile")
        view_profile.setObjectName("linkButton")
        view_profile.setFlat(True)
        
        user_container = QVBoxLayout()
        user_container.addWidget(user_info)
        user_container.addWidget(view_profile)
        
        layout.addLayout(user_container)
        
        self.setFixedWidth(200)
        self.setObjectName("sidebar")

    def create_menu_button(self, text, icon_name, is_active=False):
        #Crée un bouton de menu pour la sidebar
        button = QPushButton(text)
        button.setIcon(QIcon.fromTheme(icon_name))
        button.setIconSize(QSize(20, 20))
        button.setCheckable(True)
        button.setChecked(is_active)
        button.setObjectName("sidebarButton")
        button.setStyleSheet(
            QPushButton {
                padding: 10px;
                text-align: left;
                border-radius: 5px;
            }
            QPushButton[active="true"] {
                background-color: #E3F2FD;
                color: #1E88E5;
            }
)
        return button """

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
        feed_container.setStyleSheet("#cameraFeed { background-color: #313131; }")
        
        # Example image with detection boxes (would be dynamic in real app)
        # Here we just show a placeholder
        placeholder = QLabel("Camera Feed")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: white;")
        
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
        self.status_indicator.setStyleSheet("#statusIndicator { background-color: #4CAF50; border-radius: 7px; }")
        
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
        self.feed_label.setStyleSheet("#cameraFeed { background-color: #313131; }")
        self.feed_label.setText("Loading feed...")
        
        layout.addWidget(self.feed_label)
        
        """ # Camera label
        camera_label = QLabel(self.camera.name.upper())
        camera_label.setAlignment(Qt.AlignCenter)
        camera_label.setObjectName("cameraLabel")
        
        layout.addWidget(camera_label) """
    
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
        self.video_display = QLabel()
        self.video_display.setAlignment(Qt.AlignCenter)
        self.video_display.setMinimumHeight(200)
        self.video_display.setStyleSheet("background-color: #313131;")
        
        # Default "no video" message
        self.video_display.setText("No video selected")
        
        # Play button overlay
        play_overlay = QPushButton()
        play_overlay.setIcon(QIcon.fromTheme("media-playback-start"))
        play_overlay.setIconSize(QSize(50, 50))
        play_overlay.setStyleSheet("background: transparent; border: none;")
        play_overlay.clicked.connect(self.toggle_playback)
        
        # Position play button over video display
        play_layout = QVBoxLayout()
        play_layout.addWidget(play_overlay, 0, Qt.AlignCenter)
        self.video_display.setLayout(play_layout)
        
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
    
    def set_source(self, source):
        """Set video source"""
        self.source = source
        self.current_time = 0
        self.seek_slider.setValue(0)
        
        # In a real app, you would load the video source
        # Here we just show a placeholder
        self.video_display.setText("")
        self.video_display.setStyleSheet("background-color: #313131; background-image: url(assets/video_placeholder.svg); background-repeat: no-repeat; background-position: center;")
        
        # Start playing
        self.play()
    
    def play(self):
        """Play video"""
        if not self.source:
            return
        
        self.is_playing = True
        self.play_button.setIcon(QIcon.fromTheme("media-playback-pause"))
        
        # In a real app, you would start the video playback
    
    def pause(self):
        """Pause video"""
        self.is_playing = False
        self.play_button.setIcon(QIcon.fromTheme("media-playback-start"))
        
        # In a real app, you would pause the video playback
    
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