# Fichier: src/components/alerts.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QScrollArea, QLineEdit,
                            QDateEdit, QComboBox, QDialog, QTextEdit, QFormLayout)
from PyQt5.QtCore import Qt, QDate, QSize, pyqtSignal, QTimer, QDateTime
from PyQt5.QtGui import QPixmap, QIcon
import os
import json
import logging
import csv
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from shared.alert_subscriber import ROSAlertBridge
from src.services.alert_service import AlertService
from src.components.dashboard import SectionFrame 
from models import AlertType, Alert

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
        location = self.alert.camera.location if hasattr(self.alert, "camera") and self.alert.camera else "Unknown"
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
        btn_save_notes.clicked.connect(self.save_notes)  # ✅ Connecter ici

        btn_email = QPushButton("Send by Email")
        btn_email.setObjectName("secondaryButton")

        close_button = QPushButton("Close")
        close_button.setObjectName("primaryButton")
        close_button.clicked.connect(self.accept)

        footer.addWidget(btn_save_notes)
        footer.addWidget(btn_email)
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
        
        self.init_ui()
        
        # Load initial data
        self.load_alerts()
        self.load_alert_history()
        self.apply_history_filters()
    
    def init_ui(self):
        """Initialize the UI components"""
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
        #rt_alerts_section.setObjectName("contentSection")
        rt_alerts_layout = QVBoxLayout(rt_alerts_section)
        rt_alerts_layout.setContentsMargins(15, 15, 15, 15)
        
        rt_alerts_header = QLabel("Real-Time Alerts")
        rt_alerts_header.setObjectName("SectionTitle")
        rt_alerts_layout.addWidget(rt_alerts_header)
        
        # Real-time alerts list
        self.rt_alerts_list = QVBoxLayout()
        self.rt_alerts_list.setSpacing(10)
        rt_alerts_layout.addLayout(self.rt_alerts_list)
        
        content_layout.addWidget(rt_alerts_section)
        
        # Alert history section
        history_section = SectionFrame()
        #history_section.setObjectName("contentSection")
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
        # Dès qu’on change la date, on réapplique les filtres :
        self.date_filter.dateChanged.connect(self.apply_history_filters)

        self.type_filter = QComboBox()
        self.type_filter.setObjectName("typeFilter")
        self.type_filter.addItem("Type")
        for alert_type in AlertType:
            self.type_filter.addItem(alert_type.value)
        self.type_filter.setFixedWidth(180)
        # Dès qu’on change la sélection, on réapplique :
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
        pagination.addWidget(self.create_page_button("2"))
        pagination.addWidget(self.create_page_button("3"))
        pagination.addWidget(self.create_page_button("4"))
        
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
        """Create a pagination button"""
        btn = QPushButton(text)
        btn.setFixedSize(32, 32)
        
        if is_active:
            btn.setObjectName("activePageButton")
        else:
            btn.setObjectName("pageButton")
        
        return btn
    
    def load_alerts(self):
        """Load and display real-time alerts"""
        # Clear existing alerts
        self.clear_layout(self.rt_alerts_list)
        
        # Get real-time alerts from the service
        alerts = self.alert_service.get_unacknowledged_alerts()
        
        # Add alert widgets to the list
        for alert in alerts:
            alert_widget = AlertItem(alert, show_actions=True, show_details=True)
            alert_widget.acknowledge_clicked.connect(self.acknowledge_alert)
            alert_widget.archive_clicked.connect(self.archive_alert)
            
            self.rt_alerts_list.addWidget(alert_widget)
        
        # If no alerts, display a message
        if not alerts:
            no_alerts = QLabel("No active alerts")
            no_alerts.setObjectName("emptyStateMessage")
            no_alerts.setAlignment(Qt.AlignCenter)
            self.rt_alerts_list.addWidget(no_alerts)
    
    def load_alert_history(self):
        """Load and display the alert history"""
        # Clear existing history
        self.clear_layout(self.history_list)
        
        # Get alert history from the service
        history = self.alert_service.get_alert_history()
        
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
    
    def acknowledge_alert(self, alert_id):
        """Acknowledge an alert"""
        user_id = self.user_data.get('id') if self.user_data else None
        success = self.alert_service.acknowledge_alert(alert_id, user_id)
        if success:
            # Reload alerts
            self.load_alerts()
            self.load_alert_history()
    
    def archive_alert(self, alert_id):
        """Archive an alert"""
        success = self.alert_service.archive_alert(alert_id)
        if success:
            # Reload alerts
            self.load_alerts()
            self.load_alert_history()
    
    def show_alert_details(self, alert_id):
        """Display details of a specific alert"""
        alert = self.alert_service.get_alert(alert_id)
        if alert:
            dialog = AlertDetailsDialog(alert, self)
            dialog.exec_()
    
    def on_alert_received(self, alert_data):
        """Handle incoming ROS2 alert data (in a ROS thread)"""
        try:
            # Transfer processing to the main thread
            QTimer.singleShot(0, lambda: self._handle_alert(alert_data))
        except Exception as e:
            logger.error(f"Error transferring thread: {e}")

    def _handle_alert(self, alert_data):
        """Executed in the Qt main thread"""
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
        """Clear the contents of a layout"""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                self.clear_layout(item.layout())
    
    def closeEvent(self, event):
        """Handle window close event"""
        logger.info("Closing AlertsScreen and stopping services")
        self.alert_bridge.stop()
        event.accept()
        # Close the alert service
        self.alert_service.close()
        # Close the database service
        self.alert_service.close_db()
    
    def export_alert_history(self):
        """Export the alert history to a CSV file"""
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
            """Filtrer l’historique selon date & type, et recharger la liste."""
            all_history = self.alert_service.get_alert_history()
            sel_date = self.date_filter.date().toPyDate()
            sel_type = self.type_filter.currentText()

            def keep(a):
                # filtre date
                if a.timestamp.date() != sel_date:
                    return False
                # filtre type
                if sel_type != "Type":
                    txt = a.type if isinstance(a.type, str) else a.type.value
                    if txt != sel_type:
                        return False
                return True

            filtered = [a for a in all_history if keep(a)]

            # on repeuple la zone d’historique
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
        """Filtre la liste des alertes en temps-réel ET l'historique par type ou message."""
        pattern = text.lower().strip()

        # 1) Filtrer alertes non acquittées
        raw = self.alert_service.get_unacknowledged_alerts()
        filtered_rt = [
            a for a in raw
            if pattern in (a.type if isinstance(a.type, str) else a.type.value).lower()
               or pattern in a.message.lower()
        ]
        # Repeupler la liste RT
        self.clear_layout(self.rt_alerts_list)
        if filtered_rt:
            for a in filtered_rt:
                w = AlertItem(a, show_actions=True)
                w.acknowledge_clicked.connect(self.acknowledge_alert)
                w.archive_clicked.connect(self.archive_alert)
                self.rt_alerts_list.addWidget(w)
        else:
            lbl = QLabel("No matching real-time alerts")
            lbl.setObjectName("emptyStateMessage")
            lbl.setAlignment(Qt.AlignCenter)
            self.rt_alerts_list.addWidget(lbl)

        # 2) Filtrer historique
        hist = self.alert_service.get_alert_history()
        filtered_hist = [
            a for a in hist
            if pattern in (a.type if isinstance(a.type, str) else a.type.value).lower()
               or pattern in a.message.lower()
        ]
        # Repeupler l’historique
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
            self.history_list.addWidget(lbl)


class AlertItem(QFrame):
    """Un item d’alerte stylé comme dans le dashboard"""
    acknowledge_clicked = pyqtSignal(int)
    archive_clicked    = pyqtSignal(int)
    details_clicked    = pyqtSignal(int)

    def __init__(self, alert, show_actions=True, show_details=True):
        super().__init__()
        self.alert        = alert
        self.show_actions = show_actions
        self.show_details = show_details
        self.init_ui()

    def init_ui(self):
        # même cadre flouté que dashboard
        from src.components.dashboard import SectionFrame
        container = SectionFrame(self)
        container.setObjectName("alertItem")
        container.setMaximumHeight(70)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(12)

        # --- Gauche : infos
        info = QVBoxLayout()
        info.setSpacing(2)

        # 1) Type / classe de détection
        title = QLabel(self.alert.detection_class.title())  # ex: “Swimmer”
        title.setObjectName("alertType")
        f = title.font(); f.setBold(True); title.setFont(f)
        info.addWidget(title)

        # 2) Bref message
        brief = QLabel(self.alert.message.split('\n')[0])   # première ligne
        brief.setObjectName("alertDescription")
        info.addWidget(brief)

        # 3) Horodatage relatif
        ago = f"{(QDateTime.currentDateTime().secsTo(self.alert.timestamp) * -1) // 60} mins ago"
        time = QLabel(ago)
        time.setObjectName("alertTimestamp")
        info.addWidget(time)

        layout.addLayout(info)
        layout.addStretch()

        # --- Droite : boutons
        if self.show_actions:
            btn_ack = QPushButton("Acknowledge")
            btn_ack.setObjectName("acknowledgeButton")
            btn_ack.setCursor(Qt.PointingHandCursor)
            btn_ack.setFixedWidth(100)
            btn_ack.clicked.connect(lambda: self.acknowledge_clicked.emit(self.alert.id))
            layout.addWidget(btn_ack)

        if self.show_details:
            btn_det = QPushButton("Details")
            btn_det.setObjectName("outlineButton")
            btn_det.setCursor(Qt.PointingHandCursor)
            btn_det.clicked.connect(lambda: self.details_clicked.emit(self.alert.id))
            layout.addWidget(btn_det)

        # replace self par container pour que l’item soit stylé
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)



