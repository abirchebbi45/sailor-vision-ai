from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                            QScrollArea, QFrame, QLabel, QPushButton, QDialog, 
                            QLineEdit, QFormLayout, QDialogButtonBox, QMessageBox, 
                            QCheckBox, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter, QImage

from src.components.shared import HeaderWidget, Sidebar
from shared.ros_image_listener import ROSImageBridge
from PyQt5.QtCore import Qt
import cv2

class AddCameraDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Add a New Camera")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        title_label = QLabel("Add a New Camera")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)
        
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(10)
        form_layout.setHorizontalSpacing(20)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Camera Name")
        form_layout.addRow("Camera Name:", self.name_input)
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Camera IP/ID")
        form_layout.addRow("Camera IP/ID:", self.ip_input)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        form_layout.addRow("Username:", self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password:", self.password_input)
        
        self.streaming_checkbox = QCheckBox("Enable Live Streaming")
        self.streaming_checkbox.setChecked(True)
        form_layout.addRow("", self.streaming_checkbox)
        
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addSpacing(20)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_camera_data(self):
        """
        Retrieves the camera data entered in the dialog.

        Returns:
            dict: A dictionary containing camera details.
        """
        return {
            "name": self.name_input.text(),
            "ip": self.ip_input.text(),
            "username": self.username_input.text(),
            "password": self.password_input.text(),
            "streaming": self.streaming_checkbox.isChecked()
        }

class CameraFeedWidget(QFrame):
    expand_clicked = pyqtSignal(int)  # Signal for expand button click with camera id
    
    def __init__(self, camera):
        super().__init__()
        self.camera = camera
        self.init_ui()
        
    def init_ui(self):
        self.setObjectName("liveFeedWidget")
        self.setMinimumHeight(300)
        self.setFrameShape(QFrame.StyledPanel)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Feed content
        feed_container = QWidget()
        feed_container.setObjectName("feedContainer")
        feed_layout = QVBoxLayout(feed_container)
        feed_layout.setContentsMargins(0, 0, 0, 0)
        
        # Status and expand button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 10, 10, 10)
        
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(5)
        
        # Status indicator
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)
        self.status_indicator.setObjectName("statusIndicator")
        status_color = "#4CAF50" if self.camera.get("connected", True) else "#FF5252"
        self.status_indicator.setStyleSheet(f"#statusIndicator {{ background-color: {status_color}; border-radius: 6px; }}")
        
        status_text = QLabel("Connected" if self.camera.get("connected", True) else "Disconnected")
        status_text.setObjectName("statusText")
        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(status_text)
        
        header_layout.addWidget(status_container, 0, Qt.AlignLeft)
        header_layout.addStretch()
        
        # Expand button
        expand_btn = QPushButton("Expand")
        expand_btn.setObjectName("expandButton")
        expand_btn.setCursor(Qt.PointingHandCursor)
        expand_btn.clicked.connect(lambda: self.expand_clicked.emit(self.camera.get("id", 0)))
        header_layout.addWidget(expand_btn, 0, Qt.AlignRight)
        
        feed_layout.addLayout(header_layout)
        
        # Camera feed (we'll simulate with an image)
        self.feed_label = QLabel()
        self.feed_label.setObjectName("cameraFeed")
        self.feed_label.setAlignment(Qt.AlignCenter)
        self.feed_label.setMinimumHeight(200)
        self.feed_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        if self.camera.get("image_path"):
            pixmap = QPixmap(self.camera.get("image_path"))
            if not pixmap.isNull():
                self.feed_label.setPixmap(pixmap.scaled(
                    self.feed_label.width(), 
                    self.feed_label.height(),
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                ))
            else:
                self.feed_label.setStyleSheet("background-color: #313131;")
                self.feed_label.setText("No feed available")
        else:
            self.feed_label.setStyleSheet("background-color: #313131;")
            self.feed_label.setText("Loading feed...")
        
        feed_layout.addWidget(self.feed_label)
        layout.addWidget(feed_container)
        
        # Camera label
        camera_name = QLabel(self.camera.get("name", "Camera").upper())
        camera_name.setObjectName("cameraName")
        camera_name.setAlignment(Qt.AlignCenter)
        camera_name.setStyleSheet("font-weight: bold; padding: 10px;")
        layout.addWidget(camera_name)
    
    def update_feed(self, pixmap):
        """
        Updates the displayed image in the camera feed.

        Args:
            pixmap: QPixmap to display.
        """
        if not pixmap.isNull():
            # Scale the image while maintaining proportions
            scaled_pixmap = pixmap.scaled(
                self.feed_label.width(),
                self.feed_label.height(),
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.feed_label.setPixmap(scaled_pixmap)
            
            # Update the status indicator to show the camera is connected
            self.status_indicator.setStyleSheet("#statusIndicator { background-color: #4CAF50; border-radius: 6px; }")

class ExpandedCameraWidget(QWidget):
    close_clicked = pyqtSignal()
    
    def __init__(self, camera_data=None, pixmap=None):
        super().__init__()
        self.camera_data = camera_data
        self.pixmap = pixmap
        self.init_ui()
    
    def init_ui(self):
        self.setObjectName("expandedCameraWidget")
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header with camera name and close button
        header_layout = QHBoxLayout()
        
        camera_title = QLabel(self.camera_data.get("name", "Camera").upper())
        camera_title.setObjectName("expandedCameraTitle")
        camera_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        close_btn = QPushButton("Cancel")
        close_btn.setObjectName("cancelExpandButton")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close_clicked.emit)
        
        header_layout.addWidget(camera_title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        
        layout.addLayout(header_layout)
        
        # Video feed container
        self.feed_container = QLabel()
        self.feed_container.setObjectName("expandedFeedContainer")
        self.feed_container.setAlignment(Qt.AlignCenter)
        self.feed_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Display the image if available
        if self.pixmap and not self.pixmap.isNull():
            self.update_feed(self.pixmap)
        else:
            self.feed_container.setText("No feed available")
            self.feed_container.setStyleSheet("background-color: #313131; color: white;")
        
        layout.addWidget(self.feed_container)
        
        # Style the widget
        self.setStyleSheet("""
            #expandedCameraWidget {
                background-color: #f5f5f5;
            }
            #expandedFeedContainer {
                background-color: #313131;
                border-radius: 8px;
                min-height: 500px;
            }
            #cancelExpandButton {
                background-color: #E53935;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            #cancelExpandButton:hover {
                background-color: #D32F2F;
            }
        """)
    
    def update_feed(self, pixmap):
        """
        Updates the displayed image in the expanded camera feed.
        """
        if not pixmap.isNull():
            # Scale the image to fill the available space while maintaining proportions
            scaled_pixmap = pixmap.scaled(
                self.feed_container.width(), 
                self.feed_container.height(),
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.feed_container.setPixmap(scaled_pixmap)
    
    def resizeEvent(self, event):
        """
        Resizes the image when the widget size changes.
        """
        super().resizeEvent(event)
        if hasattr(self, 'feed_container') and self.pixmap and not self.pixmap.isNull():
            self.update_feed(self.pixmap)


class LiveFeedScreen(QWidget):
    def __init__(self, user_data=None):
        super().__init__()
        self.user_data = user_data
        # Sample camera data with more realistic information
        self.cameras = [
            {"id": 1, "name": "Cam A", "location": "Port Area", "connected": True, 
             "image_path": "src/assets/camera_feeds/port_feed.jpg"},
            {"id": 2, "name": "Cam B", "location": "Main Dock", "connected": True,
             "image_path": "src/assets/camera_feeds/dock_feed.jpg"},
            {"id": 3, "name": "Cam C", "location": "Harbor Entrance", "connected": True,
             "image_path": "src/assets/camera_feeds/harbor_feed.jpg"},
            {"id": 4, "name": "Cam D", "location": "Cargo Area", "connected": False}
        ]
        # Store references to camera widgets for quick access
        self.camera_widgets = {}
        
        # Variable to store the reference to the expanded camera widget
        self.expanded_camera_widget = None
        
        self.init_ui()

        # Start ROS image bridge
        self.ros_bridge = ROSImageBridge()
        # Use Qt.QueuedConnection to avoid threading issues
        self.ros_bridge.image_received.connect(self.update_cam_a_feed, Qt.QueuedConnection)
        self.ros_bridge.start()
    
    def init_ui(self):
        # Create a main layout to allow widget overlay
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Main content widget to hold the camera grid
        self.content_widget = QWidget()
        self.content_widget.setObjectName("contentWidget")
        
        # Sub-layout for the main content
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
        
        # Header with search and add camera button
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        header_layout.addStretch()
        
        add_camera_btn = QPushButton("+ Add Camera")
        add_camera_btn.setObjectName("addCameraButton")
        add_camera_btn.setCursor(Qt.PointingHandCursor)
        add_camera_btn.clicked.connect(self.show_add_camera_dialog)
        header_layout.addWidget(add_camera_btn)
        
        content_layout.addWidget(header_container)
        
        # Camera Grid in a scroll area
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        self.cameras_grid = QGridLayout()
        self.cameras_grid.setSpacing(20)
        self.load_cameras()
        scroll_layout.addLayout(self.cameras_grid)
        scroll_layout.addStretch()
        
        scroll_area = QScrollArea()
        scroll_area.setObjectName("feedScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_content)
        scroll_area.setFrameShape(QFrame.NoFrame)
        content_layout.addWidget(scroll_area)
        
        # Add the content widget to the main layout
        self.main_layout.addWidget(self.content_widget)
        
        # Apply stylesheet
        self.setStyleSheet("""
            #contentWidget {
                background-color: #f5f5f5;
            }
            #liveFeedWidget {
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            #cameraFeed {
                background-color: #313131;
                color: white;
                border-radius: 4px;
            }
            #statusIndicator {
                min-width: 12px;
                min-height: 12px;
                border-radius: 6px;
            }
            #statusText {
                color: #555;
                font-size: 13px;
            }
            #expandButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            #expandButton:hover {
                background-color: #1976D2;
            }
            #addCameraButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            #addCameraButton:hover {
                background-color: #1976D2;
            }
            #searchBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
            }
            #cameraName {
                font-weight: bold;
                color: #333;
            }
        """)
    
    def load_cameras(self):
        """
        Loads the camera feeds into the grid layout.
        """
        # Clear existing items
        for i in reversed(range(self.cameras_grid.count())):
            item = self.cameras_grid.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        # Add camera feeds to grid
        for i, camera in enumerate(self.cameras):
            row = i // 2
            col = i % 2
            camera_feed = CameraFeedWidget(camera)
            # Connect the expand signal to our method
            camera_feed.expand_clicked.connect(self.expand_camera)
            self.cameras_grid.addWidget(camera_feed, row, col)
            
            # Store the reference
            self.camera_widgets[camera["id"]] = camera_feed
    
    def expand_camera(self, camera_id):
        """
        Displays the camera in full screen when the expand button is clicked.

        Args:
            camera_id: ID of the camera to expand.
        """
        # Find the camera and its corresponding widget
        camera_data = next((cam for cam in self.cameras if cam["id"] == camera_id), None)
        camera_widget = self.camera_widgets.get(camera_id)
        
        if not camera_data or not camera_widget:
            print(f"Camera with ID {camera_id} not found")
            return
        
        # Get the current pixmap from the camera widget if available
        pixmap = None
        if hasattr(camera_widget.feed_label, 'pixmap') and camera_widget.feed_label.pixmap():
            pixmap = camera_widget.feed_label.pixmap()
        
        # Create and display the expanded widget
        self.expanded_camera_widget = ExpandedCameraWidget(camera_data, pixmap)
        self.expanded_camera_widget.close_clicked.connect(self.close_expanded_camera)
        
        # Add the expanded widget on top of the existing content
        self.main_layout.addWidget(self.expanded_camera_widget)
        
        # Hide the main content
        self.content_widget.setVisible(False)
        
        # If the camera is "Cam A", connect the video feed updates
        if camera_data.get("name") == "Cam A":
            self.ros_bridge.image_received.connect(self.update_expanded_cam_feed, Qt.QueuedConnection)
        
        print(f"Camera {camera_data.get('name')} expanded")
    
    def close_expanded_camera(self):
        """
        Closes the expanded view and returns to the normal display.
        """
        if self.expanded_camera_widget:
            # Disconnect the update signal if necessary
            try:
                self.ros_bridge.image_received.disconnect(self.update_expanded_cam_feed)
            except:
                pass  # The signal might not have been connected
                
            # Remove the expanded widget
            self.expanded_camera_widget.deleteLater()
            self.expanded_camera_widget = None
            
            # Show the main content
            self.content_widget.setVisible(True)
            
            print("Expanded view closed")
    
    def update_expanded_cam_feed(self, cv_image):
        """
        Updates the expanded camera feed with the image received from ROS.

        Args:
            cv_image: OpenCV image received from the ROS topic.
        """
        if not self.expanded_camera_widget:
            return
            
        try:
            # Convert the OpenCV image to QPixmap
            height, width, channel = cv_image.shape
            bytes_per_line = 3 * width
            
            # Convert BGR (OpenCV) to RGB (Qt)
            rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            
            # Create a QImage from the image data
            q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # Convert QImage to QPixmap
            pixmap = QPixmap.fromImage(q_image)
            
            # Update the expanded feed
            self.expanded_camera_widget.update_feed(pixmap)
            
        except Exception as e:
            print(f"Error updating expanded feed: {e}")
            import traceback
            traceback.print_exc()
    
    def show_add_camera_dialog(self):
        """
        Displays the dialog to add a new camera.
        """
        dialog = AddCameraDialog(self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            camera_data = dialog.get_camera_data()
            if not camera_data["name"]:
                QMessageBox.warning(self, "Validation Error", "Camera name is required")
                return
            if not camera_data["ip"]:
                QMessageBox.warning(self, "Validation Error", "Camera IP/ID is required")
                return
            
            # Add new camera
            self.cameras.append({
                "id": len(self.cameras) + 1,
                "name": camera_data["name"],
                "location": camera_data["ip"],
                "connected": True
            })
            self.load_cameras()
            QMessageBox.information(self, "Success", "Camera added successfully")

    def update_cam_a_feed(self, cv_image):
        """
        Updates the feed for Camera A with the image received from ROS.

        Args:
            cv_image: OpenCV image received from the ROS topic.
        """
        try:
            # Convert the OpenCV image to QPixmap for display in PyQt
            height, width, channel = cv_image.shape
            bytes_per_line = 3 * width
            
            # Convert BGR (OpenCV) to RGB (Qt)
            rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            
            # Create a QImage from the image data
            q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # Convert QImage to QPixmap
            pixmap = QPixmap.fromImage(q_image)
            
            print("Image received and converted to QPixmap")
            
            # Update all cameras for testing
            for i in range(self.cameras_grid.count()):
                item = self.cameras_grid.itemAt(i)
                if item and item.widget():
                    camera_widget = item.widget()
                    camera_name = camera_widget.camera.get("name", "")
                    if camera_name == "Cam A":
                        print(f"Updating feed for {camera_name}")
                        camera_widget.update_feed(pixmap)
                        # Store for future reference
                        self.camera_widgets["Cam A"] = camera_widget
                        break
        except Exception as e:
            print(f"Error updating feed: {e}")
            import traceback
            traceback.print_exc()