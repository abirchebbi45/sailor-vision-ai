import logging
from enum import Enum
from typing import Dict, List, Union

logger = logging.getLogger(__name__)

class Permission(Enum):
    """Permissions disponibles dans l'application"""
    # Autorisations pour le Dashboard
    VIEW_DASHBOARD = "view_dashboard"
    
    # Autorisations pour les caméras
    VIEW_LIVE_FEED = "view_live_feed"
    MANAGE_CAMERAS = "manage_cameras"
    APPROVE_CAMERAS = "approve_cameras"
    
    # Autorisations pour les enregistrements
    VIEW_RECORDINGS = "view_recordings"
    DELETE_RECORDINGS = "delete_recordings"
    DOWNLOAD_RECORDINGS = "download_recordings"
    
    # Autorisations pour les alertes
    VIEW_ALERTS = "view_alerts"
    MANAGE_ALERTS = "manage_alerts"
    DISMISS_ALERTS = "dismiss_alerts"
    
    # Autorisations pour la gestion des utilisateurs
    VIEW_USERS = "view_users"
    CREATE_USER = "create_user"
    EDIT_USER = "edit_user"
    DELETE_USER = "delete_user"
    
    # Autorisations pour les paramètres
    VIEW_SETTINGS = "view_settings"
    EDIT_GENERAL_SETTINGS = "edit_general_settings"
    EDIT_SYSTEM_SETTINGS = "edit_system_settings"

class PermissionService:
    """
    Service pour gérer les permissions des utilisateurs selon leur rôle
    """
    # Mapping des rôles et des permissions associées
    _role_permissions = {
        "Administrator": [
            # L'administrateur a accès à toutes les permissions
            Permission.VIEW_DASHBOARD,
            Permission.VIEW_LIVE_FEED,
            Permission.MANAGE_CAMERAS,
            Permission.APPROVE_CAMERAS,
            Permission.VIEW_RECORDINGS,
            Permission.DELETE_RECORDINGS,
            Permission.DOWNLOAD_RECORDINGS,
            Permission.VIEW_ALERTS,
            Permission.MANAGE_ALERTS,
            Permission.DISMISS_ALERTS,
            Permission.VIEW_USERS,
            Permission.CREATE_USER,
            Permission.EDIT_USER,
            Permission.DELETE_USER,
            Permission.VIEW_SETTINGS,
            Permission.EDIT_GENERAL_SETTINGS,
            Permission.EDIT_SYSTEM_SETTINGS
        ],
        "Operator": [
            # L'opérateur a accès à un ensemble limité de permissions
            Permission.VIEW_DASHBOARD,
            Permission.VIEW_LIVE_FEED,
            Permission.VIEW_RECORDINGS,
            Permission.DOWNLOAD_RECORDINGS,
            Permission.VIEW_ALERTS,
            Permission.DISMISS_ALERTS,
            Permission.VIEW_SETTINGS,
        ]
    }
    
    @classmethod
    def has_permission(cls, user_data: Dict, permission: Permission) -> bool:
        """
        Vérifie si un utilisateur possède une permission spécifique
        
        Args:
            user_data: Dictionnaire contenant les données de l'utilisateur (doit inclure 'role')
            permission: Permission à vérifier
            
        Returns:
            bool: True si l'utilisateur a la permission, False sinon
        """
        if not user_data or 'role' not in user_data:
            logger.warning("Permission check failed: No valid user data provided")
            return False
            
        user_role = user_data.get('role')
        
        # Vérifier si le rôle existe dans notre mapping
        if user_role not in cls._role_permissions:
            logger.warning(f"Permission check failed: Unknown role '{user_role}'")
            return False
            
        # Vérifier si la permission existe dans le rôle
        has_perm = permission in cls._role_permissions[user_role]
        
        if not has_perm:
            logger.info(f"Permission denied: User with role '{user_role}' tried to access '{permission.value}'")
            
        return has_perm
    
    @classmethod
    def get_user_permissions(cls, user_data: Dict) -> List[Permission]:
        """
        Récupère toutes les permissions d'un utilisateur
        
        Args:
            user_data: Dictionnaire contenant les données de l'utilisateur
            
        Returns:
            Liste des permissions de l'utilisateur
        """
        if not user_data or 'role' not in user_data:
            return []
            
        user_role = user_data.get('role')
        return cls._role_permissions.get(user_role, [])
    
    @classmethod
    def is_admin(cls, user_data: Dict) -> bool:
        """Vérifie si l'utilisateur est un administrateur"""
        if not user_data:
            return False
        return user_data.get('role') == "Administrator"
    
    @classmethod
    def is_operator(cls, user_data: Dict) -> bool:
        """Vérifie si l'utilisateur est un opérateur"""
        if not user_data:
            return False
        return user_data.get('role') == "Operator"
        
    @staticmethod
    def require_permission(permission):
        """
        Décorateur pour vérifier les permissions avant d'exécuter une méthode
        
        Usage:
        @PermissionService.require_permission(Permission.MANAGE_CAMERAS)
        def methode_protegee(self, ...):
            # code nécessitant une permission spécifique
        """
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                # Vérifier si l'objet a un attribut user_data
                if not hasattr(self, 'user_data'):
                    logger.warning(f"L'objet n'a pas d'attribut user_data pour la vérification des permissions")
                    return None
                    
                if not PermissionService.has_permission(self.user_data, permission):
                    logger.warning(f"Tentative d'accès non autorisée à {func.__name__} (permission requise: {permission.value})")
                    # En PyQt, afficher un message si possible
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(None, "Accès refusé", 
                        f"Vous n'avez pas les permissions nécessaires pour effectuer cette action.")
                    return None
                    
                return func(self, *args, **kwargs)
            return wrapper
        return decorator
        
    @staticmethod
    def require_permission(permission):
        """
        Décorateur pour vérifier les permissions avant d'exécuter une méthode
        
        Usage:
        @PermissionService.require_permission(Permission.MANAGE_CAMERAS)
        def methode_protegee(self, ...):
            # code protégé
        """
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                # Vérifier si l'objet a un attribut user_data
                if not hasattr(self, 'user_data') or not PermissionService.has_permission(self.user_data, permission):
                    logger.warning(f"Accès non autorisé à {func.__name__}")
                    # Pour PyQt, afficher un message
                    if hasattr(self, 'show_permission_denied'):
                        self.show_permission_denied(permission)
                    elif hasattr(self, 'parent') and callable(self.parent) and hasattr(self.parent(), 'show_message'):
                        self.parent().show_message("Accès refusé", f"Vous n'avez pas l'autorisation nécessaire pour cette action.")
                    return None
                return func(self, *args, **kwargs)
            return wrapper
        return decorator
