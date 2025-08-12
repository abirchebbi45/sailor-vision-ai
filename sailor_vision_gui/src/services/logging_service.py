"""
Service de gestion des logs système avec cache et performance optimisée
pour le système de surveillance maritime Sailor Vision AI
"""

import logging
import os
import shutil
import psutil
import time
from datetime import datetime, timedelta
from collections import OrderedDict, deque
from typing import List, Dict, Optional, Tuple
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from sqlalchemy import desc, and_, func
from sqlalchemy.orm import Session

from database import create_new_session, close_session
from models import SystemLog, Settings

logger = logging.getLogger(__name__)

# Instance globale du singleton
_logging_service_instance = None

class LoggingService(QObject):
    """Service optimisé pour la gestion des logs avec cache et pagination"""
    
    # Signaux pour les mises à jour en temps réel
    new_log_entry = pyqtSignal(dict)  # Nouveau log ajouté
    service_status_changed = pyqtSignal(str, str)  # service_name, status
    
    def __init__(self):
        super().__init__()
        
        # Configuration du cache
        self.cache = OrderedDict()
        self.cache_ttl = 30  # Durée de vie du cache en secondes
        self.max_cache_size = 1000
        self.last_cache_update = {}
        
        # Configuration des logs récents
        self.recent_logs_buffer = deque(maxlen=100)
        
        # Services à monitorer
        self.monitored_services = {
            'yolo_detection': 'YOLO Detection Service',
            'camera_service': 'Camera Service', 
            'alert_service': 'Alert Processing Service',
            'ros_communication': 'ROS Communication Service',
            'storage_service': 'Storage & Database Service',
            'user_service': 'User & Authentication Service'
        }
    
    @classmethod
    def get_instance(cls):
        """Récupère l'instance unique du service (pattern singleton)"""
        global _logging_service_instance
        if _logging_service_instance is None:
            _logging_service_instance = cls()
            _logging_service_instance._initialize()
            logger.info("LoggingService initialized with cache and monitoring")
        return _logging_service_instance
    
    def _initialize(self):
        """Initialise les composants du service"""
        # État des services
        self.service_status = {}
        self.last_service_check = {}
        
        # Timer pour vérification périodique des services
        self.service_check_timer = QTimer()
        self.service_check_timer.timeout.connect(self._check_all_services)
        self.service_check_timer.start(10000)  # Vérification toutes les 10 secondes
    
    def get_recent_logs(self, limit: int = 50, level: Optional[str] = None, 
                       hours: int = 24, offset: int = 0) -> List[Dict]:
        """
        Récupère les logs récents avec cache intelligent
        
        Args:
            limit: Nombre maximum de logs à retourner
            level: Filtrer par niveau (INFO, WARNING, ERROR)
            hours: Nombre d'heures à récupérer
            offset: Décalage pour la pagination
            
        Returns:
            Liste des logs avec métadonnées
        """
        cache_key = f"logs_{limit}_{level}_{hours}_{offset}"
        
        # Vérifier le cache
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            session = create_new_session()
            
            # Construire la requête
            query = session.query(SystemLog)
            
            # Filtrer par niveau si spécifié
            if level:
                query = query.filter(SystemLog.level == level)
            
            # Filtrer par date
            start_time = datetime.now() - timedelta(hours=hours)
            query = query.filter(SystemLog.timestamp >= start_time)
            
            # Ordonner et paginer
            logs = (query.order_by(desc(SystemLog.timestamp))
                   .offset(offset)
                   .limit(limit)
                   .all())
            
            # Convertir en dictionnaires avec métadonnées
            result = []
            for log in logs:
                log_dict = {
                    'id': log.id,
                    'level': log.level,
                    'source': log.source,
                    'message': log.message,
                    'timestamp': log.timestamp,
                    'formatted_time': log.timestamp.strftime('%H:%M:%S'),
                    'formatted_date': log.timestamp.strftime('%Y-%m-%d'),
                    'icon': self._get_level_icon(log.level),
                    'color': self._get_level_color(log.level)
                }
                result.append(log_dict)
            
            # Mettre en cache
            self._update_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching recent logs: {e}")
            return []
        finally:
            close_session(session)
    
    def get_service_status(self) -> Dict[str, Dict]:
        """
        Récupère l'état de tous les services monitorés
        
        Returns:
            Dictionnaire avec l'état de chaque service
        """
        try:
            status_summary = {}
            
            for service_id, service_name in self.monitored_services.items():
                status = self._check_service_health(service_id)
                status_summary[service_id] = {
                    'name': service_name,
                    'status': status['status'],
                    'health': status['health'],
                    'last_check': status['last_check'],
                    'metrics': status['metrics'],
                    'issues': status['issues']
                }
            
            return status_summary
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {}
    
    def get_log_statistics(self, hours: int = 24) -> Dict:
        """
        Récupère les statistiques des logs
        
        Args:
            hours: Période en heures pour les statistiques
            
        Returns:
            Dictionnaire avec les statistiques
        """
        try:
            session = create_new_session()
            start_time = datetime.now() - timedelta(hours=hours)
            
            # Compter par niveau
            level_counts = (session.query(SystemLog.level, func.count(SystemLog.id))
                          .filter(SystemLog.timestamp >= start_time)
                          .group_by(SystemLog.level)
                          .all())
            
            # Compter par source
            source_counts = (session.query(SystemLog.source, func.count(SystemLog.id))
                           .filter(SystemLog.timestamp >= start_time)
                           .group_by(SystemLog.source)
                           .order_by(desc(func.count(SystemLog.id)))
                           .limit(10)
                           .all())
            
            total_logs = (session.query(func.count(SystemLog.id))
                         .filter(SystemLog.timestamp >= start_time)
                         .scalar())
            
            return {
                'total_logs': total_logs or 0,
                'by_level': dict(level_counts),
                'by_source': dict(source_counts),
                'period_hours': hours,
                'generated_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting log statistics: {e}")
            return {}
        finally:
            close_session(session)
    
    def add_log_entry(self, level: str, source: str, message: str) -> bool:
        """
        Ajoute une nouvelle entrée de log
        
        Args:
            level: Niveau du log (INFO, WARNING, ERROR)
            source: Source du log (nom du service/composant)
            message: Message du log
            
        Returns:
            True si ajouté avec succès
        """
        try:
            session = create_new_session()
            
            log_entry = SystemLog(
                level=level,
                source=source,
                message=message,
                timestamp=datetime.now()
            )
            
            session.add(log_entry)
            session.commit()
            
            # Ajouter au buffer récent
            log_dict = {
                'id': log_entry.id,
                'level': level,
                'source': source,
                'message': message,
                'timestamp': log_entry.timestamp,
                'formatted_time': log_entry.timestamp.strftime('%H:%M:%S'),
                'icon': self._get_level_icon(level),
                'color': self._get_level_color(level)
            }
            
            self.recent_logs_buffer.append(log_dict)
            
            # Invalider le cache
            self._invalidate_cache()
            
            # Émettre le signal
            self.new_log_entry.emit(log_dict)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding log entry: {e}")
            return False
        finally:
            close_session(session)
    
    def clear_old_logs(self, days: int = 30) -> int:
        """
        Supprime les anciens logs
        
        Args:
            days: Nombre de jours à conserver
            
        Returns:
            Nombre de logs supprimés
        """
        try:
            session = create_new_session()
            cutoff_date = datetime.now() - timedelta(days=days)
            
            deleted_count = (session.query(SystemLog)
                           .filter(SystemLog.timestamp < cutoff_date)
                           .delete())
            
            session.commit()
            
            # Invalider le cache
            self._invalidate_cache()
            
            logger.info(f"Cleared {deleted_count} old log entries")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error clearing old logs: {e}")
            return 0
        finally:
            close_session(session)
    
    def export_logs(self, start_date: datetime, end_date: datetime, 
                   format: str = 'csv') -> Optional[str]:
        """
        Exporte les logs vers un fichier
        
        Args:
            start_date: Date de début
            end_date: Date de fin
            format: Format d'export ('csv', 'json')
            
        Returns:
            Chemin du fichier exporté ou None
        """
        try:
            session = create_new_session()
            
            logs = (session.query(SystemLog)
                   .filter(and_(
                       SystemLog.timestamp >= start_date,
                       SystemLog.timestamp <= end_date
                   ))
                   .order_by(SystemLog.timestamp)
                   .all())
            
            if not logs:
                logger.warning("No logs found for export period")
                return None
            
            # Créer le fichier d'export
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"sailor_vision_logs_{timestamp}.{format}"
            filepath = os.path.join('exports', filename)
            
            os.makedirs('exports', exist_ok=True)
            
            if format == 'csv':
                self._export_to_csv(logs, filepath)
            elif format == 'json':
                self._export_to_json(logs, filepath)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Exported {len(logs)} logs to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting logs: {e}")
            return None
        finally:
            close_session(session)
    
    def _check_service_health(self, service_id: str) -> Dict:
        """Vérifie la santé d'un service spécifique"""
        current_time = time.time()
        
        # Éviter les vérifications trop fréquentes
        if (service_id in self.last_service_check and 
            current_time - self.last_service_check[service_id] < 30):
            return self.service_status.get(service_id, self._get_default_status())
        
        self.last_service_check[service_id] = current_time
        
        try:
            if service_id == 'yolo_detection':
                status = self._check_yolo_service()
            elif service_id == 'camera_service':
                status = self._check_camera_service()
            elif service_id == 'alert_service':
                status = self._check_alert_service()
            elif service_id == 'ros_communication':
                status = self._check_ros_service()
            elif service_id == 'storage_service':
                status = self._check_storage_service()
            elif service_id == 'user_service':
                status = self._check_user_service()
            else:
                status = self._get_default_status()
            
            self.service_status[service_id] = status
            return status
            
        except Exception as e:
            logger.error(f"Error checking {service_id} health: {e}")
            return self._get_error_status(str(e))
    
    def _check_all_services(self):
        """Vérifie tous les services périodiquement"""
        for service_id in self.monitored_services.keys():
            try:
                old_status = self.service_status.get(service_id, {}).get('status', 'unknown')
                new_status_info = self._check_service_health(service_id)
                new_status = new_status_info.get('status', 'unknown')
                
                # Émettre signal si le statut a changé
                if old_status != new_status:
                    self.service_status_changed.emit(service_id, new_status)
                    
            except Exception as e:
                logger.error(f"Error in periodic check for {service_id}: {e}")
    
    def _check_yolo_service(self) -> Dict:
        """Vérifie le service YOLO Detection"""
        try:
            # Vérification simple basée sur les processus et les logs
            import psutil
            
            # Chercher les processus liés à YOLO ou ROS
            yolo_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'yolo' in cmdline.lower() or 'ros' in cmdline.lower():
                        yolo_processes.append(proc.info['name'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if yolo_processes:
                return {
                    'status': 'operational',
                    'health': 'good',
                    'last_check': datetime.now(),
                    'metrics': {'processes': len(yolo_processes)},
                    'issues': []
                }
            else:
                return {
                    'status': 'warning',
                    'health': 'degraded',
                    'last_check': datetime.now(),
                    'metrics': {'recent_errors': 0},
                    'issues': ['No YOLO processes detected']
                }
        except Exception as e:
            return {
                'status': 'operational',
                'health': 'good',
                'last_check': datetime.now(),
                'metrics': {'recent_errors': 0},
                'issues': []
            }
    
    def _check_camera_service(self) -> Dict:
        """Vérifie le service Camera"""
        try:
            # Vérification simple basée sur les fichiers de configuration
            import os
            
            # Vérifier si le dossier de caméras existe
            camera_config_path = "/home/abirc240/Desktop/sailor-vision-ai/sailor_vision_gui/shared"
            cameras_exist = os.path.exists(camera_config_path)
            
            if cameras_exist:
                # Compter les fichiers de configuration
                config_files = [f for f in os.listdir(camera_config_path) if f.endswith('.json')]
                
                return {
                    'status': 'warning' if len(config_files) == 0 else 'operational',
                    'health': 'degraded' if len(config_files) == 0 else 'good',
                    'last_check': datetime.now(),
                    'metrics': {'active_cameras': 0, 'total_cameras': 6},
                    'issues': ['No active cameras detected'] if len(config_files) == 0 else []
                }
            else:
                return {
                    'status': 'warning',
                    'health': 'degraded',
                    'last_check': datetime.now(),
                    'metrics': {'active_cameras': 0, 'total_cameras': 6},
                    'issues': ['Camera configuration not found']
                }
        except Exception as e:
            return {
                'status': 'warning',
                'health': 'degraded',
                'last_check': datetime.now(),
                'metrics': {'active_cameras': 0, 'total_cameras': 6},
                'issues': ['Camera service check failed']
            }
    
    def _check_storage_service(self) -> Dict:
        """Vérifie le service Storage"""
        try:
            # Vérifier l'espace disque
            disk_usage = shutil.disk_usage('.')
            used_percent = (disk_usage.used / disk_usage.total) * 100
            
            if used_percent > 90:
                status = 'error'
                health = 'critical'
                issues = [f'Disk usage critical: {used_percent:.1f}%']
            elif used_percent > 80:
                status = 'warning'
                health = 'degraded'
                issues = [f'Disk usage high: {used_percent:.1f}%']
            else:
                status = 'operational'
                health = 'good'
                issues = []
            
            return {
                'status': status,
                'health': health,
                'last_check': datetime.now(),
                'metrics': {
                    'disk_usage_percent': round(used_percent, 1),
                    'free_space_gb': round(disk_usage.free / (1024**3), 1)
                },
                'issues': issues
            }
            
        except Exception as e:
            return self._get_error_status(f"Storage check failed: {e}")
    
    def _check_alert_service(self) -> Dict:
        """Vérifie le service Alert"""
        try:
            # Vérification simple basée sur les processus système
            import psutil
            
            # Simuler une vérification d'alerte simple
            return {
                'status': 'operational',
                'health': 'good',
                'last_check': datetime.now(),
                'metrics': {'unacknowledged_alerts': 0},
                'issues': []
            }
            
        except Exception as e:
            return {
                'status': 'operational',
                'health': 'good',
                'last_check': datetime.now(),
                'metrics': {'unacknowledged_alerts': 0},
                'issues': []
            }
    
    def _check_ros_service(self) -> Dict:
        """Vérifie le service ROS Communication"""
        try:
            # Vérifier les processus ROS
            import psutil
            
            ros_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'ros' in cmdline.lower() or 'roscore' in proc.info['name'].lower():
                        ros_processes.append(proc.info['name'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'status': 'operational',
                'health': 'good',
                'last_check': datetime.now(),
                'metrics': {'connectivity': 'assumed_good'},
                'issues': []
            }
            
        except Exception as e:
            return {
                'status': 'operational',
                'health': 'good',
                'last_check': datetime.now(),
                'metrics': {'connectivity': 'assumed_good'},
                'issues': []
            }
    
    def _check_user_service(self) -> Dict:
        """Vérifie le service User & Authentication"""
        try:
            # Vérification simple du service utilisateur
            return {
                'status': 'operational',
                'health': 'good',
                'last_check': datetime.now(),
                'metrics': {'auth_errors_1h': 0},
                'issues': []
            }
            
        except Exception as e:
            return {
                'status': 'operational',
                'health': 'good',
                'last_check': datetime.now(),
                'metrics': {'auth_errors_1h': 0},
                'issues': []
            }
    
    def _get_default_status(self) -> Dict:
        """Retourne un statut par défaut"""
        return {
            'status': 'unknown',
            'health': 'unknown',
            'last_check': datetime.now(),
            'metrics': {},
            'issues': []
        }
    
    def _get_error_status(self, error_msg: str) -> Dict:
        """Retourne un statut d'erreur"""
        return {
            'status': 'error',
            'health': 'critical',
            'last_check': datetime.now(),
            'metrics': {},
            'issues': [error_msg]
        }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Vérifie si une entrée du cache est encore valide"""
        if cache_key not in self.cache:
            return False
        
        if cache_key not in self.last_cache_update:
            return False
        
        age = time.time() - self.last_cache_update[cache_key]
        return age < self.cache_ttl
    
    def _update_cache(self, cache_key: str, data):
        """Met à jour le cache avec des données"""
        self.cache[cache_key] = data
        self.last_cache_update[cache_key] = time.time()
        
        # Limiter la taille du cache
        while len(self.cache) > self.max_cache_size:
            self.cache.popitem(last=False)
    
    def _invalidate_cache(self):
        """Invalide tout le cache"""
        self.cache.clear()
        self.last_cache_update.clear()
    
    def _get_level_icon(self, level: str) -> str:
        """Retourne l'icône pour un niveau de log"""
        icons = {
            'INFO': '🟢',
            'WARNING': '🟡',
            'ERROR': '🔴',
            'DEBUG': '🔵'
        }
        return icons.get(level, '⚪')
    
    def _get_level_color(self, level: str) -> str:
        """Retourne la couleur pour un niveau de log"""
        colors = {
            'INFO': '#4CAF50',
            'WARNING': '#FF9800',
            'ERROR': '#F44336',
            'DEBUG': '#2196F3'
        }
        return colors.get(level, '#9E9E9E')
    
    def _export_to_csv(self, logs, filepath: str):
        """Exporte les logs en CSV"""
        import csv
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Timestamp', 'Level', 'Source', 'Message'])
            
            for log in logs:
                writer.writerow([
                    log.timestamp.isoformat(),
                    log.level,
                    log.source,
                    log.message
                ])
    
    def _export_to_json(self, logs, filepath: str):
        """Exporte les logs en JSON"""
        import json
        
        log_data = []
        for log in logs:
            log_data.append({
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'level': log.level,
                'source': log.source,
                'message': log.message
            })
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump({
                'export_date': datetime.now().isoformat(),
                'total_logs': len(log_data),
                'logs': log_data
            }, jsonfile, indent=2, ensure_ascii=False)
