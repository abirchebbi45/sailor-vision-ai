import datetime
import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum, Text, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class UserRole(enum.Enum):
    ADMINISTRATOR = "Administrator"
    OPERATOR = "Operator"
    GUEST = "Guest"

class AlertType(enum.Enum):
    GENERAL_DETECTION = "Détection Générale"
    MOTION = "Motion Detected"
    INTRUSION = "Intrusion"
    CAMERA_OFFLINE = "Camera Offline"
    VESSEL_DETECTED = "Vessel Detected"
    SYSTEM_ERROR = "System Error"
    UNAUTHORIZED_SWIMMER = "Unauthorized Swimmer"
    SAFETY_COMPLIANT_SWIMMER = "Swimmer with Life Jacket"
    LIFE_JACKET_DETECTED = "Unattended Life Jacket"

class StorageType(enum.Enum):
    LOCAL = "Local"
    CLOUD = "Cloud"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    role = Column(Enum(UserRole), default=UserRole.GUEST)
    job_title = Column(String(100))
    profile_picture = Column(String)  # Path to profile picture
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    alerts = relationship("Alert", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.username}>"

class Camera(Base):
    __tablename__ = "cameras"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    ip_address = Column(String(50))
    port = Column(Integer)
    username = Column(String(50))
    password_hash = Column(String(256))
    location = Column(String(100))
    rtsp_url = Column(String(256))
    is_active = Column(Boolean, default=True)
    is_recording = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    last_online = Column(DateTime)
    
    # Relationships
    recordings = relationship("Recording", back_populates="camera")
    alerts = relationship("Alert", back_populates="camera")
    
    def __repr__(self):
        return f"<Camera {self.name}>"

class Recording(Base):
    __tablename__ = "recordings"
    
    id = Column(Integer, primary_key=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    file_path = Column(String(256), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration = Column(Float)  # Duration in seconds
    size = Column(Float)  # Size in bytes
    resolution = Column(String(20))  # e.g., "1920x1080"
    storage_type = Column(Enum(StorageType), default=StorageType.LOCAL)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    camera = relationship("Camera", back_populates="recordings")
    
    def __repr__(self):
        return f"<Recording {self.id} from Camera {self.camera_id}>"

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True)
    # Utilisation de String à la place de Enum pour éviter les conflits en base
    type = Column(String(50), nullable=False)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(Integer, ForeignKey("users.id"))
    acknowledged_at = Column(DateTime)
    is_archived = Column(Boolean, default=False)
    image_data = Column(String)  # Path to snapshot image
    detection_class = Column(String(50), default='non spécifié')
    notes = Column(Text, nullable=True)
    
    # Relationships
    camera = relationship("Camera", back_populates="alerts")
    user = relationship("User", back_populates="alerts")
    
    def __repr__(self):
        return f"<Alert {self.id} of type {self.type}>"

class Detection(Base):
    __tablename__ = "detections"
    
    id = Column(Integer, primary_key=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    recording_id = Column(Integer, ForeignKey("recordings.id"))
    object_type = Column(String(50), nullable=False)  # e.g., "boat", "person"
    confidence = Column(Float, nullable=False)
    x = Column(Float, nullable=False)  # Normalized coordinates (0-1)
    y = Column(Float, nullable=False)
    width = Column(Float, nullable=False)
    height = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<Detection {self.id} of {self.object_type}>"

class SystemLog(Base):
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True)
    level = Column(String(10), nullable=False)  # "INFO", "WARNING", "ERROR"
    source = Column(String(50), nullable=False)  # Component/module name
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<SystemLog {self.id} [{self.level}]>"

class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Setting {self.key}>"
