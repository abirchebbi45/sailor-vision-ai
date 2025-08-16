"""
Composant de notification pour les nouvelles caméras détectées
Affiche une notification temporaire en haut de l'écran
"""

from PyQt5.QtWidgets import (QWidget, QLabel, QHBoxLayout, QPushButton, 
                           QGraphicsOpacityEffect, QFrame, QVBoxLayout)
from PyQt5.QtCore import QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QFont, QPalette
from PyQt5.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class CameraNotification(QFrame):
    """
    Widget de notification pour les nouvelles caméras détectées
    Affiche une barre de notification temporaire avec animation
    """
    
    # Signal émis quand l'utilisateur clique sur "Voir les caméras"
    view_cameras_clicked = pyqtSignal()
    # Signal émis quand la notification doit être supprimée du gestionnaire
    notification_finished = pyqtSignal(object)  # Envoie self comme paramètre
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_animation()
        self.auto_hide_timer = QTimer()
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide_notification)
    
    def setup_ui(self):
        """Configuration de l'interface utilisateur avec un style moderne et propre"""
        self.setFixedHeight(70)  # Hauteur ajustée pour un look plus propre
        self.setFrameStyle(QFrame.NoFrame)  # Pas de cadre par défaut
        
        # Style moderne inspiré des dialogues
        self.setStyleSheet("""
            CameraNotification {
                background-color: #e3f2fd;
                border-radius: 8px;
                border-left: 4px solid #2196F3;
                margin: 2px;
            }
            QLabel {
                background-color: rgba(0, 0, 0, 0);
                background: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton#viewButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton#viewButton:hover {
                background-color: #1976D2;
            }
            QPushButton#viewButton:pressed {
                background-color: #1565C0;
            }
            QPushButton#closeButton {
                background-color: #f5f5f5;
                color: #666;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
                min-width: 20px;
                max-width: 24px;
            }
            QPushButton#closeButton:hover {
                background-color: #e0e0e0;
                color: #333;
            }
            QHBoxLayout, QVBoxLayout {
                background-color: rgba(0, 0, 0, 0);
                background: transparent;
                border: none;
            }
        """)
        
        # Layout principal avec marges ajustées
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Icône d'information moderne
        icon_label = QLabel("ℹ️")
        icon_label.setFont(QFont("Arial", 16))
        icon_label.setFixedSize(24, 24)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # Container pour le texte
        text_container = QWidget()
        text_container.setStyleSheet("background-color: transparent; border: none;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        
        # Titre de la notification
        self.title_label = QLabel("📷 Nouvelle caméra détectée")
        self.title_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.title_label.setStyleSheet("color: #1565C0; font-weight: bold; background-color: transparent; border: none;")
        text_layout.addWidget(self.title_label)
        
        # Message détaillé
        self.message_label = QLabel("Une nouvelle caméra est disponible")
        self.message_label.setFont(QFont("Arial", 10))
        self.message_label.setStyleSheet("color: #424242; background-color: transparent; border: none;")
        text_layout.addWidget(self.message_label)
        
        layout.addWidget(text_container)
        
        # Spacer pour pousser les boutons à droite
        layout.addStretch()
        
        # Container pour les boutons
        buttons_container = QWidget()
        buttons_container.setStyleSheet("background-color: transparent; border: none;")
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)
        
        # Bouton "Voir les caméras"
        self.view_button = QPushButton("Voir les caméras")
        self.view_button.setObjectName("viewButton")  # Ajouter un nom d'objet spécifique
        # Style direct comme fallback
        self.view_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self.view_button.clicked.connect(self.view_cameras_clicked.emit)
        buttons_layout.addWidget(self.view_button)
        
        # Bouton fermer moderne
        self.close_button = QPushButton("×")
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(24, 24)
        self.close_button.clicked.connect(self.hide_notification)
        self.close_button.setToolTip("Fermer la notification")
        buttons_layout.addWidget(self.close_button)
        
        layout.addWidget(buttons_container)
        
        self.setLayout(layout)
        
        # Cacher initialement
        self.hide()
    
    def setup_animation(self):
        """Configuration des animations"""
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        
        # Animation de fondu
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.fade_animation.finished.connect(self._animation_finished)
        
        self._hiding = False
    
    def show_notification(self, camera_name: str, camera_ip: str, pending_count: int = 1):
        """
        Afficher la notification pour une nouvelle caméra
        
        Args:
            camera_name: Nom de la caméra détectée
            camera_ip: Adresse IP de la caméra
            pending_count: Nombre total de caméras en attente
        """
        try:
            # Mettre à jour le titre
            if pending_count == 1:
                title = "📷 Nouvelle caméra détectée"
            else:
                title = f"📷 {pending_count} caméras détectées"
            self.title_label.setText(title)
            
            # Mettre à jour le message détaillé
            message = f"{camera_name} ({camera_ip})"
            if pending_count > 1:
                message += f" et {pending_count - 1} autre(s)"
            self.message_label.setText(message)
            
            # Montrer le widget
            self.show()
            
            # Animation de fondu entrant
            self.fade_animation.setStartValue(0.0)
            self.fade_animation.setEndValue(1.0)
            self.fade_animation.start()
            
            # Auto-masquer après 10 secondes
            self.auto_hide_timer.start(10000)
            
            logger.info(f"[CameraNotification] Notification affichée: {camera_name}")
        except Exception as e:
            logger.error(f"Error showing notification: {e}")
    
    def hide_notification(self):
        """Masquer la notification avec animation"""
        try:
            if self._hiding:
                return
                
            self._hiding = True
            self.auto_hide_timer.stop()
            
            # Animation de fondu sortant
            self.fade_animation.setStartValue(1.0)
            self.fade_animation.setEndValue(0.0)
            self.fade_animation.start()
        except Exception as e:
            logger.error(f"Error hiding notification: {e}")
            # Fallback in case of animation failure
            self.hide()
            self._hiding = False
    
    def _animation_finished(self):
        """Appelé à la fin de l'animation"""
        try:
            if self._hiding:
                self.hide()
                self._hiding = False
                # Émettre le signal pour informer le gestionnaire de supprimer cette notification
                self.notification_finished.emit(self)
        except Exception as e:
            logger.error(f"Error in animation finished: {e}")
            # Force hide in case of error
            self.hide()
            self._hiding = False
            # Émettre le signal même en cas d'erreur
            self.notification_finished.emit(self)
    
    def update_pending_count(self, pending_count: int):
        """Mettre à jour le nombre de caméras en attente dans la notification"""
        try:
            if self.isVisible() and pending_count > 0:
                # Mettre à jour le titre
                if pending_count == 1:
                    title = "📷 Nouvelle caméra détectée"
                else:
                    title = f"📷 {pending_count} caméras détectées"
                self.title_label.setText(title)
                
                # Mettre à jour le message si nécessaire
                current_message = self.message_label.text()
                if " et " in current_message:
                    # Extraire le nom de la première caméra
                    base_camera = current_message.split(" et ")[0]
                    if pending_count > 1:
                        self.message_label.setText(f"{base_camera} et {pending_count - 1} autre(s)")
                    else:
                        self.message_label.setText(base_camera)
        except Exception as e:
            logger.error(f"Error updating pending count: {e}")


class NotificationManager(QWidget):
    """
    Gestionnaire de notifications qui peut être intégré dans la fenêtre principale
    """
    
    # Signal émis quand l'utilisateur veut voir les caméras en attente
    view_pending_cameras = pyqtSignal()
    # Signal for navigating to live feed
    navigate_to_live_feed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_notifications = []
    
    def setup_ui(self):
        """Configuration de l'interface utilisateur"""
        self.setFixedHeight(0)  # Hauteur dynamique
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(10, 5, 10, 5)
        self.setLayout(self.layout)
        
        # Style du conteneur
        self.setStyleSheet("""
            NotificationManager {
                background-color: transparent;
            }
        """)
    
    def show_camera_notification(self, camera_name: str, camera_ip: str, pending_count: int = 1):
        """
        Afficher une notification pour une nouvelle caméra
        """
        try:
            # Créer la notification
            notification = CameraNotification(self)
            notification.view_cameras_clicked.connect(self.view_pending_cameras.emit)
            
            # Connecter le signal de fin de notification pour suppression automatique
            notification.notification_finished.connect(self.remove_notification)
            
            # Ajouter au layout
            self.layout.addWidget(notification)
            self.current_notifications.append(notification)
            
            # Ajuster la hauteur
            self.setFixedHeight(75)  # Ajusté pour le nouveau style plus haut
            
            # Afficher la notification
            notification.show_notification(camera_name, camera_ip, pending_count)
            
            # Connecter le signal de fermeture manuelle
            notification.close_button.clicked.connect(
                lambda: self.remove_notification(notification)
            )
            
            logger.info(f"Camera notification shown for {camera_name} ({camera_ip})")
        except Exception as e:
            logger.error(f"Error showing camera notification: {e}")
    
    def show_approval_notification(self, camera_name: str):
        """
        Afficher une notification pour une caméra approuvée
        """
        try:
            # Créer la notification
            notification = CameraNotification(self)
            
            # Connecter le signal de fin de notification pour suppression automatique
            notification.notification_finished.connect(self.remove_notification)
            
            # Modifier le style pour le succès (style vert comme dans le dialogue)
            notification.setStyleSheet("""
                CameraNotification {
                    background-color: #e8f5e8;
                    border-radius: 8px;
                    border-left: 4px solid #4CAF50;
                    margin: 2px;
                }
                QLabel {
                    background-color: rgba(0, 0, 0, 0);
                    background: transparent;
                    border: none;
                    padding: 0px;
                }
                QPushButton#viewButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-weight: 500;
                    font-size: 12px;
                    min-width: 80px;
                }
                QPushButton#viewButton:hover {
                    background-color: #45a049;
                }
                QPushButton#viewButton:pressed {
                    background-color: #388e3c;
                }
                QPushButton#closeButton {
                    background-color: #f5f5f5;
                    color: #666;
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-size: 14px;
                    font-weight: bold;
                    min-width: 20px;
                    max-width: 24px;
                }
                QPushButton#closeButton:hover {
                    background-color: #e0e0e0;
                    color: #333;
                }
                QHBoxLayout, QVBoxLayout {
                    background-color: rgba(0, 0, 0, 0);
                    background: transparent;
                    border: none;
                }
            """)
            
            # Ajouter au layout
            self.layout.addWidget(notification)
            self.current_notifications.append(notification)
            
            # Ajuster la hauteur
            self.setFixedHeight(75)  # Légèrement plus haut pour le nouveau style
            
            # Personnaliser le contenu pour l'approbation
            notification.title_label.setText("✅ Caméra approuvée")
            notification.title_label.setStyleSheet("""
                color: #2e7d32; 
                font-weight: bold; 
                background-color: rgba(0, 0, 0, 0); 
                background: transparent;
                border: none;
                padding: 0px;
            """)
            notification.message_label.setText(f"{camera_name} est maintenant disponible")
            notification.message_label.setStyleSheet("""
                color: #424242; 
                background-color: rgba(0, 0, 0, 0); 
                background: transparent;
                border: none;
                padding: 0px;
            """)
            notification.view_button.setText("Voir Live Feed")
            notification.view_button.setObjectName("viewButton")  # S'assurer que l'objectName est défini
            
            # Changer l'icône
            icon_widget = notification.findChild(QLabel)
            if icon_widget and icon_widget.text() == "ℹ️":
                icon_widget.setText("✅")
            
            # Connecter pour naviguer vers le Live Feed
            notification.view_button.clicked.connect(
                lambda: self.navigate_to_live_feed.emit() if hasattr(self, 'navigate_to_live_feed') else None
            )
            
            # Afficher avec animation
            notification.show()
            notification.fade_animation.setStartValue(0.0)
            notification.fade_animation.setEndValue(1.0)
            notification.fade_animation.start()
            
            # Auto-masquer après 7 secondes
            notification.auto_hide_timer.start(7000)
            
            # Connecter le signal de fermeture
            notification.close_button.clicked.connect(
                lambda: self.remove_notification(notification)
            )
            
            logger.info(f"Camera approval notification shown for {camera_name}")
        except Exception as e:
            logger.error(f"Error showing approval notification: {e}")

    def remove_notification(self, notification: CameraNotification):
        """Supprimer une notification et ajuster l'espace"""
        try:
            if notification in self.current_notifications:
                self.current_notifications.remove(notification)
                
                # Supprimer du layout
                self.layout.removeWidget(notification)
                notification.deleteLater()
                
                # Ajuster la hauteur en fonction du nombre de notifications restantes
                if not self.current_notifications:
                    # Plus de notifications : hauteur 0
                    self.setFixedHeight(0)
                    logger.info("All notifications removed, height set to 0")
                else:
                    # Il reste des notifications : maintenir la hauteur
                    logger.info(f"Notification removed, {len(self.current_notifications)} remaining")
                
                # Forcer une mise à jour du layout
                self.layout.update()
                self.updateGeometry()
                
        except Exception as e:
            logger.error(f"Error removing notification: {e}")
            # Fallback: force height to 0 if no notifications remain
            if not self.current_notifications:
                self.setFixedHeight(0)
    
    def update_pending_count(self, pending_count: int):
        """Update the pending count in all active notifications"""
        try:
            for notification in self.current_notifications:
                notification.update_pending_count(pending_count)
        except Exception as e:
            logger.error(f"Error updating pending count: {e}")
    
    def clear_all_notifications(self):
        """Supprimer toutes les notifications"""
        try:
            for notification in self.current_notifications:
                notification.deleteLater()
            self.current_notifications.clear()
            self.setFixedHeight(0)
            logger.info("All notifications cleared")
        except Exception as e:
            logger.error(f"Error clearing notifications: {e}")
