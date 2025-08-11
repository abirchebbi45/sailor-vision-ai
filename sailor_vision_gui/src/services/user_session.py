import logging
import traceback
from typing import Dict, List, Optional
from .permission_service import PermissionService, Permission

logger = logging.getLogger(__name__)

# Instance globale unique au niveau du module - plus robuste que le singleton classique
_global_user_session = None

class UserSession:
    """
    Classe singleton pour gérer la session utilisateur courante
    Permet un accès global à l'état de l'utilisateur connecté et ses permissions
    """
    
    def __init__(self):
        """Initialise une session utilisateur vide"""
        self.user_data = None
        self.token = None
        self.permissions = []
        self.is_authenticated = False
        logger.info("Session utilisateur initialisée")
    
    @classmethod
    def get_instance(cls):
        """Récupère l'instance unique du singleton - utilise une variable globale"""
        global _global_user_session
        if _global_user_session is None:
            _global_user_session = cls()
            logger.info("Instance globale UserSession créée")
        return _global_user_session
        
    def reset(self):
        """Réinitialise la session utilisateur (logout)"""
        # Ajouter un log avec stack trace pour déboguer
        logger.info("Session utilisateur réinitialisée")
        logger.info(f"Stack trace de la réinitialisation:\n{traceback.format_stack()}")
        
        self.user_data = None
        self.token = None
        self.permissions = []
        self.is_authenticated = False
    
    def set_user(self, user_data: Dict, token: Optional[str] = None):
        """
        Configure la session avec les données utilisateur
        
        Args:
            user_data: Données utilisateur (id, username, email, role, etc.)
            token: Token d'authentification optionnel
        """
        self.user_data = user_data
        self.token = token
        self.is_authenticated = user_data is not None
        
        # Charger les permissions en une seule fois pour optimiser les performances
        if user_data:
            self.permissions = PermissionService.get_user_permissions(user_data)
            logger.info(f"Session utilisateur initialisée: {user_data.get('username')} (rôle: {user_data.get('role')}) - {len(self.permissions)} permissions chargées")
        
    def get_user_id(self) -> Optional[int]:
        """Récupère l'ID de l'utilisateur connecté"""
        return self.user_data.get('id') if self.user_data else None
    
    def get_username(self) -> Optional[str]:
        """Récupère le nom d'utilisateur"""
        return self.user_data.get('username') if self.user_data else None
    
    def get_role(self) -> Optional[str]:
        """Récupère le rôle de l'utilisateur"""
        return self.user_data.get('role') if self.user_data else None
    
    def is_admin(self) -> bool:
        """Vérifie si l'utilisateur est un administrateur - optimisé avec cache"""
        # Utiliser le cache des permissions au lieu d'appeler le service à chaque fois
        if not hasattr(self, 'permissions') or self.permissions is None:
            return False
        return Permission.EDIT_SYSTEM_SETTINGS in self.permissions
    
    def is_operator(self) -> bool:
        """Vérifie si l'utilisateur est un opérateur - optimisé avec cache"""
        # Utiliser le cache des permissions au lieu d'appeler le service à chaque fois
        role = self.get_role()
        return role == 'Operator' if role else False
    
    def has_permission(self, permission: Permission) -> bool:
        """Vérifie si l'utilisateur possède une permission spécifique"""
        # Vérification de sécurité pour éviter les erreurs d'attribut manquant
        if not hasattr(self, 'permissions'):
            logger.warning("Permissions attribute missing in UserSession - initializing empty permissions")
            self.permissions = []
        if self.permissions is None:
            logger.warning("Permissions not initialized in UserSession")
            return False
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Vérifie si l'utilisateur possède au moins une des permissions spécifiées"""
        if not hasattr(self, 'permissions') or self.permissions is None:
            return False
        return any(permission in self.permissions for permission in permissions)
    
    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Vérifie si l'utilisateur possède toutes les permissions spécifiées"""
        if not hasattr(self, 'permissions') or self.permissions is None:
            return False
        return all(permission in self.permissions for permission in permissions)
    
    def get_user_data(self) -> Dict:
        """Récupère une copie des données utilisateur"""
        return self.user_data.copy() if self.user_data else {}
