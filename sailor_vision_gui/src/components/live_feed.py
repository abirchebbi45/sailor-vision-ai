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

from src.services.camera_service import CameraService
from database import get_session

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
            "is_active": self.streaming_checkbox.isChecked()  # Link checkbox to is_active
        }

class CameraFeedWidget(QFrame):
    expand_clicked = pyqtSignal(int)  # Signal for expand button click with camera id

    def __init__(self, camera):
        super().__init__()
        self.camera = camera
        self.init_ui()

    def init_ui(self):
        self.setObjectName("liveFeedWidget")
        self.setFrameShape(QFrame.StyledPanel)

        # Main layout for the widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Camera feed container (to hold the feed and overlay)
        feed_container = QFrame(self)
        feed_container.setObjectName("feedContainer")
        feed_container.setStyleSheet("background-color: #1a1a1a; border-radius: 8px;")
        feed_container_layout = QVBoxLayout(feed_container)
        feed_container_layout.setContentsMargins(0, 0, 0, 0)
        feed_container_layout.setSpacing(0)

        # Camera feed label (occupies full space)
        self.feed_label = QLabel(feed_container)
        self.feed_label.setObjectName("cameraFeed")
        self.feed_label.setAlignment(Qt.AlignCenter)
        self.feed_label.setMinimumHeight(200)
        self.feed_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.feed_label.setStyleSheet("background-color: #1a1a1a; border-radius: 8px;")
        feed_container_layout.addWidget(self.feed_label)

        # Display "No available live feed" if no image is provided
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
                self.feed_label.setText("No available live feed")
                self.feed_label.setStyleSheet("color: white; font-size: 14px;")
        else:
            self.feed_label.setText("No available live feed")
            self.feed_label.setStyleSheet("color: white; font-size: 14px;")

        # Overlay container for status and expand button
        overlay_container = QWidget(feed_container)
        overlay_container.setObjectName("overlayContainer")
        overlay_container.setStyleSheet("background: transparent;")
        overlay_layout = QHBoxLayout(overlay_container)
        overlay_layout.setContentsMargins(10, 10, 10, 10)
        overlay_layout.setSpacing(10)

        # Status indicator with colored dot and text
        self.status_indicator = QLabel(overlay_container)
        self.status_indicator.setObjectName("statusIndicator")
        self.update_status_indicator()  # Dynamically set the status indicator
        overlay_layout.addWidget(self.status_indicator, 0, Qt.AlignLeft)

        # Expand button
        expand_btn = QPushButton("Expand", overlay_container)
        expand_btn.setObjectName("expandButton")
        expand_btn.setCursor(Qt.PointingHandCursor)
        expand_btn.setStyleSheet("""
            #expandButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 15px;
                padding: 6px 12px;
                font-size: 12px;
            }
            #expandButton:hover {
                background-color: #1976D2;
            }
        """)
        expand_btn.clicked.connect(lambda: self.expand_clicked.emit(self.camera.get("id", 0)))
        overlay_layout.addWidget(expand_btn, 0, Qt.AlignRight)

        # Add overlay container to the feed container
        feed_container_layout.addWidget(overlay_container)

        # Add feed container to the main layout
        layout.addWidget(feed_container)

        # Camera name label
        camera_name = QLabel(self.camera.get("name", "Camera").upper())
        camera_name.setObjectName("cameraName")
        camera_name.setAlignment(Qt.AlignCenter)
        camera_name.setStyleSheet("""
            font-weight: bold; 
            padding: 8px; 
            color: #333333; 
            background-color: #f5f5f5;
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
        """)
        layout.addWidget(camera_name)

        # Apply overall widget styling
        self.setStyleSheet("""
            #liveFeedWidget {
                background-color: white;
                border-radius: 8px;
                margin: 5px;
            }
            #feedContainer {
                position: relative;
            }
            #cameraFeed {
                background-color: #1a1a1a;
                border-radius: 8px;
            }
            #overlayContainer {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 40px;
            }
        """)

    def update_status_indicator(self):
        """
        Updates the status indicator based on the camera's is_active field.
        """
        is_active = self.camera.get("is_active", False)  # Use is_active from the database
        status_color = "#4CAF50" if is_active else "#FF5252"
        status_text = "Active" if is_active else "Inactive"
        self.status_indicator.setText(
            f'<span style="color: {status_color}; font-size: 14px;">●</span> '
            f'<span style="color: white; font-size: 12px;">{status_text}</span>'
        )

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
            self.feed_label.setText("")  # Clear any previous "No available live feed" text

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
    def __init__(self, user_data=None, ros_node=None):
        super().__init__()
        self.user_data = user_data
        self.db_session = get_session()  # Initialize database session
        self.camera_service = CameraService(self.db_session)  # CameraService instance
        # Fetch cameras from the database
        self.cameras = self.camera_service.get_all_cameras()
        # Store references to camera widgets for quick access
        self.camera_widgets = {}
        
        # Variable to store the reference to the expanded camera widget
        self.expanded_camera_widget = None
        
        self.init_ui()

        # Start ROS image bridge
        self.ros_bridge = ROSImageBridge(ros_node)
        # Use Qt.QueuedConnection to avoid threading issues
        self.ros_bridge.image_received.connect(self.update_cam_a_feed, Qt.QueuedConnection)
        #self.ros_bridge.start()
    
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
        content_layout.setSpacing(0)
        
        # Header with search and add camera button
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        header_layout.addStretch()
        
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

        # Fetch all cameras from the database
        self.cameras = self.camera_service.get_all_cameras()

        # Add camera feeds to grid
        for i, camera in enumerate(self.cameras):
            row = i // 2
            col = i % 2
            camera_feed = CameraFeedWidget({
                "id": camera.id,
                "name": camera.name,
                "location": camera.location,
                "is_active": camera.is_active,  # Pass is_active to the widget
                "image_path": camera.rtsp_url  # Assuming RTSP URL is used for the feed
            })
            # Connect the expand signal to our method
            camera_feed.expand_clicked.connect(self.expand_camera)
            self.cameras_grid.addWidget(camera_feed, row, col)

            # Store the reference
            self.camera_widgets[camera.id] = camera_feed

    def expand_camera(self, camera_id):
        """
        Displays the camera in full screen when the expand button is clicked.

        Args:
            camera_id: ID of the camera to expand.
        """
        try:
            # Find the camera object with the given ID
            camera_data = next((cam for cam in self.cameras if cam.id == camera_id), None)
            if not camera_data:
                print(f"Camera with ID {camera_id} not found")
                return

            # Get the corresponding CameraFeedWidget
            camera_widget = self.camera_widgets.get(camera_id)
            if not camera_widget:
                print(f"Camera widget for ID {camera_id} not found")
                return

            # Get the current pixmap from the camera widget if available
            pixmap = None
            if hasattr(camera_widget.feed_label, 'pixmap') and camera_widget.feed_label.pixmap():
                pixmap = camera_widget.feed_label.pixmap()

            # Create and display the expanded widget
            self.expanded_camera_widget = ExpandedCameraWidget({
                "id": camera_data.id,
                "name": camera_data.name,
                "location": camera_data.location,
                "connected": camera_data.is_active,
                "image_path": camera_data.rtsp_url
            }, pixmap)
            self.expanded_camera_widget.close_clicked.connect(self.close_expanded_camera)

            # Add the expanded widget on top of the existing content
            self.main_layout.addWidget(self.expanded_camera_widget)

            # Hide the main content
            self.content_widget.setVisible(False)

            # If the camera is "CAM A", connect the video feed updates
            if camera_data.name == "CAM A":
                self.ros_bridge.image_received.connect(self.update_expanded_cam_feed, Qt.QueuedConnection)

            print(f"Camera {camera_data.name} expanded")
        except Exception as e:
            print(f"Error expanding camera: {e}")
            import traceback
            traceback.print_exc()

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

            # Add new camera to the database
            try:
                self.camera_service.add_camera({
                    "name": camera_data["name"],
                    "ip_address": camera_data["ip"],
                    "location": camera_data["ip"],  # Using IP as location for simplicity
                    "rtsp_url": "",  # Placeholder for RTSP URL
                    "is_active": camera_data["is_active"]  # Save is_active status
                })
                self.load_cameras()  # Refresh the camera grid
                QMessageBox.information(self, "Success", "Camera added successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add camera: {e}")

    def update_cam_a_feed(self, cv_image):
        """
        Updates the feed for Camera A with the image received from ROS.

        Args:
            cv_image: OpenCV image received from the ROS topic.
        """
        try:
            # Find the camera with the name "CAM A"
            cam_a = next((camera for camera in self.cameras if camera.name == "Cam A"), None)
            if not cam_a:
                print("Camera A not found in the database")
                return

            # Get the corresponding CameraFeedWidget
            camera_widget = self.camera_widgets.get(cam_a.id)
            if not camera_widget:
                print("Camera A widget not found")
                return

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
            
            # Update the feed for Camera A
            camera_widget.update_feed(pixmap)
        except Exception as e:
            print(f"Error updating feed for Camera A: {e}")
            import traceback
            traceback.print_exc()

    def closeEvent(self, event):
        """
        Ensure the database session is closed when the widget is closed.
        """
        self.db_session.close()
        super().closeEvent(event)