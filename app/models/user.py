"""
Modelo de Usuario para el sistema
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    """Roles de usuario"""
    ADMIN = "admin"
    CAREGIVER = "caregiver"
    PATIENT = "patient"


class User(Base):
    """Modelo de Usuario"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CAREGIVER, nullable=False)
    is_active = Column(Boolean, default=True)
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Configuraciones de usuario
    timezone = Column(String(50), default="America/Mexico_City")
    language = Column(String(10), default="es")
    theme = Column(String(20), default="light")

    # Configuraciones de notificaciones
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    push_notifications = Column(Boolean, default=True)

    # Metadatos
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relaciones
    patients = relationship("Patient", back_populates="caregiver", cascade="all, delete-orphan")
    created_treatments = relationship("Treatment", back_populates="created_by", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"

    @property
    def is_admin(self) -> bool:
        """Verificar si el usuario es administrador"""
        return self.role == UserRole.ADMIN

    @property
    def is_caregiver(self) -> bool:
        """Verificar si el usuario es cuidador"""
        return self.role == UserRole.CAREGIVER

    @property
    def is_patient(self) -> bool:
        """Verificar si el usuario es paciente"""
        return self.role == UserRole.PATIENT