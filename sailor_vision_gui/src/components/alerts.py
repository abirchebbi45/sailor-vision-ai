from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QScrollArea, QLineEdit,
                            QDateEdit, QComboBox, QDialog, QTextEdit, QFormLayout, QCheckBox)
from PyQt5.QtCore import Qt, QDate, QSize, pyqtSignal, QTimer, QDateTime
from PyQt5.QtGui import QPixmap, QIcon
import os
import json
import logging
import csv
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from sqlalchemy.orm import joinedload

from shared.alert_subscriber import ROSAlertBridge
from src.services.alert_service import AlertService
from src.components.dashboard import SectionFrame 
from models import AlertType, Alert
from database import get_session, close_session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertDetailsDialog(QDialog):
    def __init__(self, alert, parent=None):
        super().__init__(parent)
        self.alert = alert
        self.setWindowTitle("Alert Details")
        self.setFixedSize(600, 500)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setObjectName("AlertDetailsDialog")
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        content = QFrame()
        content_layout = QFormLayout(content)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(10, 10, 10, 10)

        if hasattr(self.alert, "image_data") and self.alert.image_data and os.path.exists(self.alert.image_data):
            pixmap = QPixmap(self.alert.image_data).scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label = QLabel()
            image_label.setPixmap(pixmap)
            content_layout.addRow("Snapshot:", image_label)

        content_layout.addRow("Type:", QLabel(self.alert.type.value if hasattr(self.alert.type, "value") else str(self.alert.type)))
        content_layout.addRow("Date:", QLabel(self.alert.timestamp.strftime("%d/%m/%Y") if hasattr(self.alert, "timestamp") else "N/A"))
        content_layout.addRow("Time:", QLabel(self.alert.timestamp.strftime("%H:%M:%S") if hasattr(self.alert, "timestamp") else "N/A"))
        location = "Unknown"
        try:
            if hasattr(self.alert, "camera") and self.alert.camera:
                loc = getattr(self.alert.camera, "location", None)
                if loc:
                    location = loc
        except Exception:
            location = "Unknown"
        content_layout.addRow("Location:", QLabel(location))
        status = "Acknowledged" if getattr(self.alert, "is_acknowledged", False) else "Pending"
        content_layout.addRow("Status:", QLabel(status))
        if hasattr(self.alert, "detection_class") and self.alert.detection_class:
            content_layout.addRow("Detection:", QLabel(self.alert.detection_class))
        if hasattr(self.alert, "message") and self.alert.message:
            content_layout.addRow("Message:", QLabel(self.alert.message))

        layout.addWidget(content)

        # Notes section
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Add comments or notes...")
        self.notes_edit.setText(self.alert.notes if hasattr(self.alert, "notes") and self.alert.notes else "")
        layout.addWidget(self.notes_edit)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch()

        btn_save_notes = QPushButton("Save Notes")
        btn_save_notes.setObjectName("secondaryButton")
        btn_save_notes.clicked.connect(self.save_notes)


        close_button = QPushButton("Close")
        close_button.setObjectName("primaryButton")
        close_button.clicked.connect(self.accept)

        footer.addWidget(btn_save_notes)
        footer.addWidget(close_button)

        layout.addLayout(footer)

    def save_notes(self):
        notes = self.notes_edit.toPlainText()
        alert_id = self.alert.id if hasattr(self.alert, 'id') else None
        if alert_id:
            service = AlertService()
            success = service.save_alert_notes(alert_id, notes)
            if success:
                updated = service.get_alert(alert_id)
                self.alert = updated
                self.notes_edit.setText(updated.notes or "")
                QMessageBox.information(self, "Success", "Notes saved and updated.")
            else:
                QMessageBox.warning(self, "Error", "Failed to save notes.")


class AlertItem(QFrame):
    """A styled alert item widget for displaying alert information."""
    acknowledge_clicked = pyqtSignal(int)
    archive_clicked = pyqtSignal(int)
    details_clicked = pyqtSignal(int)
    selection_changed = pyqtSignal(int, bool)
    
    def __init__(self, alert, show_actions=True, show_details=False):
        super().__init__()
        self.alert = alert
        self.show_actions = show_actions
        self.show_details = show_details
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI for the alert item."""
        self.setObjectName("alertItem")
        self.setFrameShape(QFrame.StyledPanel)
        self.setMaximumHeight(70)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Left part - alert info
        alert_info = QVBoxLayout()
        alert_info.setSpacing(3)
        
        # Alert type with formatting
        alert_type_text = self.alert.type
        if not isinstance(alert_type_text, str) and hasattr(alert_type_text, 'value'):
            alert_type_text = alert_type_text.value
            
        title = QLabel(alert_type_text)
        title.setObjectName("alertType")
        type_font = title.font()
        type_font.setBold(True)
        title.setFont(type_font)
        alert_info.addWidget(title)
        
        # Get location safely without triggering lazy load
        location = "Unknown"
        try:
            # Try to get the camera location if it's already loaded
            if hasattr(self.alert, "_sa_instance_state"):
                # Using getattr with default to avoid SQLAlchemy lazy loading
                camera = getattr(self.alert, "camera", None)
                if camera is not None:
                    location = getattr(camera, "location", "Unknown") or "Unknown"
        except Exception:
            # If any error occurs (like detached session), use the default
            location = "Unknown"
            
        # Alert description with location
        desc_label = QLabel(f"{self.alert.message} • {location}")
        desc_label.setObjectName("alertDescription")
        alert_info.addWidget(desc_label)
        
        # Timestamp
        try:
            current_time = QDateTime.currentDateTime()
            alert_time = QDateTime.fromString(self.alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "yyyy-MM-dd HH:mm:ss")
            minutes_ago = (current_time.toSecsSinceEpoch() - alert_time.toSecsSinceEpoch()) // 60
            time_text = f"{minutes_ago} mins ago" if minutes_ago > 0 else "Just now"
        except:
            # Fallback if there's an issue with timestamp calculation
            time_text = "Recent"
            
        timestamp = QLabel(time_text)
        timestamp.setObjectName("alertTimestamp")
        alert_info.addWidget(timestamp)
        
        layout.addLayout(alert_info)
        layout.addStretch()
        
        # Action buttons
        if self.show_actions:
            # Button for acknowledging alert
            acknowledge_btn = QPushButton("Acknowledge")
            acknowledge_btn.setObjectName("acknowledgeButton")
            acknowledge_btn.setCursor(Qt.PointingHandCursor)
            acknowledge_btn.setFixedWidth(100)
            acknowledge_btn.setStyleSheet("""
                #acknowledgeButton {
                    background-color: #2196F3;
                    color: white;
                    border-radius: 4px;
                    padding: 6px 12px;
                    border: none;
                }
                #acknowledgeButton:hover {
                    background-color: #1976D2;
                    color: white;
                }
            """)
            acknowledge_btn.clicked.connect(lambda: self.acknowledge_clicked.emit(self.alert.id))
            layout.addWidget(acknowledge_btn)
            
            # Checkbox for selection
            self.checkbox = QCheckBox()
            self.checkbox.stateChanged.connect(lambda state: self.selection_changed.emit(self.alert.id, state == Qt.Checked))
            layout.addWidget(self.checkbox)
            
        # Details button (optional)
        if self.show_details:
            details_btn = QPushButton("Details")
            details_btn.setObjectName("outlineButton")
            details_btn.setCursor(Qt.PointingHandCursor)
            details_btn.clicked.connect(lambda: self.details_clicked.emit(self.alert.id))
            layout.addWidget(details_btn)
    
    def set_selected(self, selected):
        """Set the checkbox state programmatically."""
        if hasattr(self, 'checkbox'):
            self.checkbox.setChecked(selected)


class AlertsScreen(QWidget):
    def __init__(self, user_data=None, ros_node=None):
        super().__init__()
        self.user_data = user_data
        self.alert_service = AlertService()
        
        # Initialize the ROS bridge for alerts
        self.alert_bridge = ROSAlertBridge(ros_node)
        self.alert_bridge.alert_received.connect(self.on_alert_received)
        # self.alert_bridge.start()
        logger.info("Alert bridge started and connected to signal")
        
        self.selected_alerts = set()  # Track selected real-time alerts
        
        self.init_ui()
        
        # Load initial data
        self.load_alerts()
        self.load_alert_history()
        self.apply_history_filters()
    
    def init_ui(self):
        """Initialize the user interface components for the Alerts screen."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Alert content
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
        
        # Real-time alerts section
        rt_alerts_section = SectionFrame()
        rt_alerts_layout = QVBoxLayout(rt_alerts_section)
        rt_alerts_layout.setContentsMargins(15, 15, 15, 15)
        
        rt_alerts_header_layout = QHBoxLayout()
        rt_alerts_header = QLabel("Real-Time Alerts")
        rt_alerts_header.setObjectName("SectionTitle")
        rt_alerts_header_layout.addWidget(rt_alerts_header)

        # "Select All" checkbox
        self.select_all_checkbox = QCheckBox("Select All")
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)
        rt_alerts_header_layout.addWidget(self.select_all_checkbox, alignment=Qt.AlignRight)

        rt_alerts_layout.addLayout(rt_alerts_header_layout)

        # Real-time alerts list container
        self.rt_alerts_list_container = QWidget()
        self.rt_alerts_list = QVBoxLayout(self.rt_alerts_list_container)
        self.rt_alerts_list.setSpacing(10)

        rt_alerts_layout.addWidget(self.rt_alerts_list_container)

        # Acknowledge Selected button
        self.ack_selected_button = QPushButton("Acknowledge Selected")
        self.ack_selected_button.setObjectName("secondaryButton")
        self.ack_selected_button.clicked.connect(self.acknowledge_selected_alerts)
        self.ack_selected_button.setEnabled(False)  # Initially disabled
        rt_alerts_layout.addWidget(self.ack_selected_button, alignment=Qt.AlignRight)

        content_layout.addWidget(rt_alerts_section)
        
        # Alert history section
        history_section = SectionFrame()
        history_layout = QVBoxLayout(history_section)
        history_layout.setContentsMargins(15, 15, 15, 15)
        
        history_header = QLabel("Alert History")
        history_header.setObjectName("SectionTitle")
        history_layout.addWidget(history_header)
        
        # Filter bar
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(0, 10, 0, 15)
        
        # Date filter
        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setDate(QDate.currentDate())
        self.date_filter.setObjectName("dateFilter")
        self.date_filter.setFixedWidth(180)
        self.date_filter.setDisplayFormat("dd/MM/yyyy")
        self.date_filter.dateChanged.connect(self.apply_history_filters)

        self.type_filter = QComboBox()
        self.type_filter.setObjectName("typeFilter")
        self.type_filter.addItem("Type")
        for alert_type in AlertType:
            self.type_filter.addItem(alert_type.value)
        self.type_filter.setFixedWidth(180)
        self.type_filter.currentIndexChanged.connect(self.apply_history_filters)

        filter_layout.addWidget(self.date_filter)
        filter_layout.addWidget(self.type_filter)
        
        # Spacer
        filter_layout.addStretch()
        
        # Export button
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.export_alert_history)
        export_btn.setObjectName("secondaryButton")
        filter_layout.addWidget(export_btn)
        
        # More options button
        more_btn = QPushButton()
        more_btn.setIcon(QIcon.fromTheme("view-more"))
        more_btn.setObjectName("iconButton")
        more_btn.setFixedSize(32, 32)
        filter_layout.addWidget(more_btn)
        
        history_layout.addLayout(filter_layout)
        
        # History list
        self.history_list = QVBoxLayout()
        self.history_list.setSpacing(10)
        history_layout.addLayout(self.history_list)
        
        # Pagination
        pagination = QHBoxLayout()
        pagination.setAlignment(Qt.AlignCenter)
        pagination.setContentsMargins(0, 15, 0, 0)
        
        prev_page = QPushButton("<")
        prev_page.setObjectName("paginationButton")
        prev_page.setFixedSize(32, 32)
        pagination.addWidget(prev_page)
        
        # Page buttons
        pagination.addWidget(self.create_page_button("1", True))
        pagination.addWidget(self.create_page_button("2"), True)
        pagination.addWidget(self.create_page_button("3"), True)
        pagination.addWidget(self.create_page_button("4"), True)
        
        # Ellipsis
        ellipsis = QLabel("...")
        ellipsis.setAlignment(Qt.AlignCenter)
        pagination.addWidget(ellipsis)
        
        pagination.addWidget(self.create_page_button("10"))
        pagination.addWidget(self.create_page_button("11"))
        
        next_page = QPushButton(">")
        next_page.setObjectName("paginationButton")
        next_page.setFixedSize(32, 32)
        pagination.addWidget(next_page)
        
        history_layout.addLayout(pagination)
        
        content_layout.addWidget(history_section)
        
        # Alert details section (initially hidden)
        self.details_section = QFrame()
        self.details_section.setObjectName("contentSection")
        self.details_section.setVisible(False)
        details_layout = QVBoxLayout(self.details_section)
        details_layout.setContentsMargins(15, 15, 15, 15)
        
        details_header = QLabel("Alert Details")
        details_header.setObjectName("sectionHeader")
        details_layout.addWidget(details_header)
        
        # Details content will be dynamically filled
        self.details_content = QVBoxLayout()
        details_layout.addLayout(self.details_content)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setObjectName("primaryButton")
        close_btn.clicked.connect(lambda: self.details_section.setVisible(False))
        details_layout.addWidget(close_btn, alignment=Qt.AlignRight)
        
        content_layout.addWidget(self.details_section)
        
        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidget(content_widget)
        
        layout.addWidget(scroll_area)
    
    def create_page_button(self, text, is_active=False):
        """Create a pagination button with optional active state."""
        btn = QPushButton(text)
        btn.setFixedSize(32, 32)
        
        if is_active:
            btn.setObjectName("activePageButton")
        else:
            btn.setObjectName("pageButton")
        
        return btn
    
    def load_alerts(self):
        """Load and display real-time alerts from the alert service."""
        self.clear_layout(self.rt_alerts_list)
        
        try:
            # Create a new session for this operation
            session = get_session()
            alerts = session.query(Alert).options(joinedload(Alert.camera)).filter(
                Alert.is_acknowledged == False,
                Alert.is_archived == False
            ).order_by(Alert.timestamp.desc()).all()
            
            if alerts:
                # Batch UI updates for better performance
                self.rt_alerts_list_container.setUpdatesEnabled(False)
                for alert in alerts:
                    # Changed show_details to False for real-time alerts
                    alert_widget = AlertItem(alert, show_actions=True, show_details=False)
                    alert_widget.acknowledge_clicked.connect(self.acknowledge_alert)
                    alert_widget.selection_changed.connect(self.update_selected_alerts)
                    self.rt_alerts_list.addWidget(alert_widget)
                self.rt_alerts_list_container.setUpdatesEnabled(True)
            else:
                no_alerts = QLabel("No active alerts")
                no_alerts.setObjectName("emptyStateMessage")
                no_alerts.setAlignment(Qt.AlignCenter)
                self.rt_alerts_list.addWidget(no_alerts)
                self.select_all_checkbox.setChecked(False)  # Reset "Select All" if no alerts
                self.ack_selected_button.setEnabled(False)
        except Exception as e:
            logger.error(f"Error loading alerts: {str(e)}")
            no_alerts = QLabel("Error loading alerts")
            no_alerts.setObjectName("errorStateMessage")
            no_alerts.setAlignment(Qt.AlignCenter)
            self.rt_alerts_list.addWidget(no_alerts)
        finally:
            # Always close the session
            close_session(session)
    
    def toggle_select_all(self, state):
        """Select or deselect all real-time alerts based on the 'Select All' checkbox."""
        self.selected_alerts.clear()
        for i in range(self.rt_alerts_list.count()):
            item = self.rt_alerts_list.itemAt(i).widget()
            if isinstance(item, AlertItem) and item.show_actions:  # Ensure only real-time alerts are affected
                item.set_selected(state == Qt.Checked)
                if state == Qt.Checked:
                    self.selected_alerts.add(item.alert.id)
        self.ack_selected_button.setEnabled(bool(self.selected_alerts))

    def update_selected_alerts(self, alert_id, selected):
        """Update the set of selected real-time alerts when an alert's checkbox is toggled."""
        if selected:
            self.selected_alerts.add(alert_id)
        else:
            self.selected_alerts.discard(alert_id)
        self.ack_selected_button.setEnabled(bool(self.selected_alerts))
        if not self.selected_alerts:
            self.select_all_checkbox.setChecked(False)

    def acknowledge_selected_alerts(self):
        """Acknowledge all selected real-time alerts."""
        if not self.selected_alerts:
            QMessageBox.warning(self, "No Alerts Selected", "Please select alerts to acknowledge.")
            return

        # Get user ID for acknowledgment
        user_id = self.user_data.get('id') if self.user_data else None
        
        # Use the batch acknowledgment to reduce processing time
        self.alert_service.batch_acknowledge_alerts(list(self.selected_alerts), user_id)

        # Clear selection after acknowledging
        self.selected_alerts.clear()
        self.select_all_checkbox.setChecked(False)
        self.ack_selected_button.setEnabled(False)

        # Reload alerts and alert history
        self.load_alerts()
        self.load_alert_history()

    def load_alert_history(self):
        """Load and display the alert history from the alert service."""
        # Clear existing history
        self.clear_layout(self.history_list)
        
        try:
            # Create a new session for this operation
            session = get_session()
            
            # Get alert history from the database with eager loading of camera relationship
            history = session.query(Alert).options(joinedload(Alert.camera))\
                .filter(Alert.is_acknowledged == True)\
                .order_by(Alert.timestamp.desc()).all()
            
            # Add alert widgets to the list
            for alert in history:
                alert_widget = AlertItem(alert, show_actions=False, show_details=True)
                alert_widget.details_clicked.connect(self.show_alert_details)
                
                self.history_list.addWidget(alert_widget)
            
            # If no history, display a message
            if not history:
                no_history = QLabel("No alert history available")
                no_history.setObjectName("emptyStateMessage")
                no_history.setAlignment(Qt.AlignCenter)
                self.history_list.addWidget(no_history)
        except Exception as e:
            logger.error(f"Error loading alert history: {str(e)}")
            no_history = QLabel("Error loading alert history")
            no_history.setObjectName("errorStateMessage")
            no_history.setAlignment(Qt.AlignCenter)
            self.history_list.addWidget(no_history)
        finally:
            # Always close the session
            close_session(session)
    
    def acknowledge_alert(self, alert_id):
        """Mark an alert as acknowledged and refresh the UI."""
        user_id = self.user_data.get('id') if self.user_data else None
        success = self.alert_service.acknowledge_alert(alert_id, user_id)
        if success:
            # Reload alerts
            self.load_alerts()
            self.load_alert_history()
    
    def archive_alert(self, alert_id):
        """Archive an alert and refresh the UI."""
        success = self.alert_service.archive_alert(alert_id)
        if success:
            # Reload alerts
            self.load_alerts()
            self.load_alert_history()
    
    def show_alert_details(self, alert_id):
        """Open a dialog to display detailed information about a specific alert."""
        try:
            alert = self.alert_service.get_alert(alert_id)
            if alert:
                dialog = AlertDetailsDialog(alert, self)
                dialog.exec_()
            else:
                QMessageBox.warning(self, "Warning", "No alert found with the specified ID.")
        except Exception as e:
            logger.error(f"Error retrieving alert data: {str(e)}")
            QMessageBox.critical(self, "Critical Error", "An error occurred while retrieving the alert data. Please try again later.")
        
    def on_alert_received(self, alert_data):
        """Handle incoming alert data from the ROS bridge."""
        try:
            # Transfer processing to the main thread
            QTimer.singleShot(0, lambda: self._handle_alert(alert_data))
        except Exception as e:
            logger.error(f"Error transferring thread: {e}")

    def _handle_alert(self, alert_data):
        """Process alert data in the main thread and update the UI."""
        try:
            logger.info(f"Processing data: {json.dumps(alert_data)[:200]}...")  # Safe logging
            
            # 1. Save to the database
            success = self.alert_service.process_yolo_detection(alert_data)
            
            if success:
                # 2. Update the UI
                logger.info("Updating the user interface...")
                self.load_alerts()
                self.load_alert_history()
                
                logger.info("UI successfully updated")
            else:
                logger.warning("Failed to process alert")
                
        except Exception as e:
            logger.error(f"Error processing alert: {e}")
            import traceback
            logger.error(traceback.format_exc())  # Full stack trace

    def clear_layout(self, layout):
        """Clear all widgets and layouts from a given layout."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                self.clear_layout(item.layout())
    
    def closeEvent(self, event):
        """Handle the window close event by stopping services and cleaning up."""
        logger.info("Closing AlertsScreen and stopping services")
        self.alert_bridge.stop()
        event.accept()
        # Close the alert service
        self.alert_service.close()
        # Close the database service
        self.alert_service.close_db()
    
    def export_alert_history(self):
        """Export the alert history to a CSV file."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")
        
        if file_path:
            alerts = self.alert_service.get_alert_history()
            try:
                with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(["ID", "Type", "Message", "Date", "Time", "Camera", "Class"])
                    for alert in alerts:
                        writer.writerow([
                            alert.id,
                            alert.type if isinstance(alert.type, str) else alert.type.value,
                            alert.message,
                            alert.timestamp.strftime("%d/%m/%Y"),
                            alert.timestamp.strftime("%H:%M:%S"),
                            alert.camera.location if alert.camera else "N/A",
                            alert.detection_class
                        ])
                QMessageBox.information(self, "Export Successful", f"History successfully exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Error during export:\n{str(e)}")
    
    def apply_history_filters(self):
        """Filter the alert history based on selected date and type, then refresh the list."""
        all_history = self.alert_service.get_alert_history()
        sel_date = self.date_filter.date().toPyDate()
        sel_type = self.type_filter.currentText()

        def keep(a):
            # Filter by date
            if a.timestamp.date() != sel_date:
                return False
            # Filter by type
            if sel_type != "Type":
                txt = a.type if isinstance(a.type, str) else a.type.value
                if txt != sel_type:
                    return False
            return True

        filtered = [a for a in all_history if keep(a)]

        # Repopulate the history list
        self.clear_layout(self.history_list)
        if filtered:
            for alert in filtered:
                w = AlertItem(alert, show_actions=False, show_details=True)
                w.details_clicked.connect(self.show_alert_details)
                self.history_list.addWidget(w)
        else:
            no = QLabel("No alert history available")
            no.setObjectName("emptyStateMessage")
            no.setAlignment(Qt.AlignCenter)
            self.history_list.addWidget(no)
    
    def filter_alerts(self, text: str):
        """Filter both real-time alerts and history by type or message."""
        pattern = text.lower().strip()

        # 1) Filter unacknowledged alerts
        raw = self.alert_service.get_unacknowledged_alerts()
        filtered_rt = [
            a for a in raw
            if pattern in (a.type if isinstance(a.type, str) else a.type.value).lower()
               or pattern in a.message.lower()
        ]
        # Repopulate the real-time alerts list
        self.clear_layout(self.rt_alerts_list)
        if filtered_rt:
            for a in filtered_rt:
                w = AlertItem(a, show_actions=True)
                w.acknowledge_clicked.connect(self.acknowledge_alert)
                self.rt_alerts_list.addWidget(w)
        else:
            lbl = QLabel("No matching real-time alerts")
            lbl.setObjectName("emptyStateMessage")
            lbl.setAlignment(Qt.AlignCenter)
            self.rt_alerts_list.addWidget(lbl)

        # 2) Filter history
        hist = self.alert_service.get_alert_history()
        filtered_hist = [
            a for a in hist
            if pattern in (a.type if isinstance(a.type, str) else a.type.value).lower()
               or pattern in a.message.lower()
        ]
        # Repopulate the history list
        self.clear_layout(self.history_list)
        if filtered_hist:
            for a in filtered_hist:
                w = AlertItem(a, show_actions=False, show_details=True)
                w.details_clicked.connect(self.show_alert_details)
                self.history_list.addWidget(w)
        else:
            lbl = QLabel("No matching history alerts")
            lbl.setObjectName("emptyStateMessage")
            lbl.setAlignment(Qt.AlignCenter)
            self.history_list.addWidget

    def refresh_alerts(self):
        """Public method to refresh all alerts - can be called from other screens"""
        logger.info("Refreshing alerts from external signal")
        self.load_alerts()
        self.load_alert_history()



