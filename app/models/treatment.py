"""
Modelo de Tratamiento
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Enum, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from datetime import date, timedelta

from app.core.database import Base


class TreatmentStatus(str, enum.Enum):
    """Estados del tratamiento"""
    ACTIVE = "active"
    COMPLETED = "completed"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class Treatment(Base):
    """Modelo de Tratamiento"""
    __tablename__ = "treatments"

    id = Column(Integer, primary_key=True, index=True)

    # Relaciones
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    medication_id = Column(Integer, ForeignKey("medications.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Información del tratamiento
    dosage = Column(String(100), nullable=False)  # ej: "500mg", "2 tabletas"
    frequency = Column(Integer, nullable=False)  # veces por día
    duration_days = Column(Integer, nullable=False)  # duración en días

    # Fechas
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Instrucciones
    instructions = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Estado
    status = Column(Enum(TreatmentStatus), default=TreatmentStatus.ACTIVE, nullable=False)

    # Metadatos
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    alarms = relationship("Alarm", back_populates="treatment", cascade="all, delete-orphan")

    # Relaciones
    patient = relationship("Patient", back_populates="treatments")
    medication = relationship("Medication", back_populates="treatments")
    created_by = relationship("User", back_populates="created_treatments")
    alarms = relationship("Alarm", back_populates="treatment", cascade="all, delete-orphan")
    dose_records = relationship("DoseRecord", back_populates="treatment", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="treatment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Treatment(id={self.id}, patient_id={self.patient_id}, medication_id={self.medication_id})>"

    @property
    def is_active(self) -> bool:
        """Verificar si el tratamiento está activo"""
        return self.status == TreatmentStatus.ACTIVE and self.end_date >= date.today()

    @property
    def is_expired(self) -> bool:
        """Verificar si el tratamiento ha expirado"""
        return self.end_date < date.today()

    @property
    def days_remaining(self) -> int:
        """Días restantes del tratamiento"""
        remaining = (self.end_date - date.today()).days
        return max(0, remaining)

    @property
    def total_doses_per_day(self) -> int:
        """Total de dosis por día"""
        return self.frequency

    @property
    def total_scheduled_doses(self) -> int:
        """Total de dosis programadas para todo el tratamiento"""
        return self.duration_days * self.frequency

    def get_doses_for_date(self, target_date: date) -> int:
        """Obtener número de dosis programadas para una fecha específica"""
        if target_date < self.start_date or target_date > self.end_date:
            return 0
        return self.frequency

    def is_dose_time_valid(self, dose_time: str) -> bool:
        """Validar si una hora de dosis es válida (formato HH:MM)"""
        try:
            hour, minute = dose_time.split(":")
            return 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59
        except:
            return False

    def calculate_compliance_rate(self) -> float:
        """Calcular tasa de cumplimiento del tratamiento"""
        # Esta función se implementaría con datos reales de dose_records
        # Por ahora retorna 0, se implementará en el servicio
        return 0.0