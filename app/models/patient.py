"""
Modelo de Paciente
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Enum, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class Gender(str, enum.Enum):
    """Géneros disponibles"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class Patient(Base):
    """Modelo de Paciente"""
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)

    # Información personal
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(Enum(Gender), nullable=False)

    # Dirección
    address = Column(Text, nullable=False)

    # Contacto de emergencia (JSON)
    emergency_contact = Column(JSON, nullable=False)
    # Estructura: {"name": "...", "phone": "...", "relationship": "..."}

    # Historial médico y alergias (JSON arrays)
    medical_history = Column(JSON, default=list)
    allergies = Column(JSON, default=list)

    # Relación con cuidador
    caregiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Configuraciones específicas del paciente
    timezone = Column(String(50), default="America/Mexico_City")
    preferred_language = Column(String(10), default="es")

    # Metadatos
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    caregiver = relationship("User", back_populates="patients")
    treatments = relationship("Treatment", back_populates="patient", cascade="all, delete-orphan")
    dose_records = relationship("DoseRecord", back_populates="patient", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="patient", cascade="all, delete-orphan")
    compliance_records = relationship("ComplianceRecord", back_populates="patient", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Patient(id={self.id}, name='{self.name}', email='{self.email}')>"

    @property
    def age(self) -> int:
        """Calcular edad del paciente"""
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    @property
    def full_address(self) -> str:
        """Dirección completa formateada"""
        return self.address

    def get_emergency_contact_info(self) -> dict:
        """Obtener información del contacto de emergencia"""
        return self.emergency_contact or {}

    def add_medical_condition(self, condition: str):
        """Agregar condición médica"""
        if not self.medical_history:
            self.medical_history = []
        if condition not in self.medical_history:
            self.medical_history.append(condition)

    def remove_medical_condition(self, condition: str):
        """Remover condición médica"""
        if self.medical_history and condition in self.medical_history:
            self.medical_history.remove(condition)

    def add_allergy(self, allergy: str):
        """Agregar alergia"""
        if not self.allergies:
            self.allergies = []
        if allergy not in self.allergies:
            self.allergies.append(allergy)

    def remove_allergy(self, allergy: str):
        """Remover alergia"""
        if self.allergies and allergy in self.allergies:
            self.allergies.remove(allergy)