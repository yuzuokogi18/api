"""
Modelo de Alerta
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class AlertType(str, enum.Enum):
    """Tipos de alerta"""
    MISSED_DOSE = "missed_dose"
    LATE_DOSE = "late_dose"
    LOW_COMPLIANCE = "low_compliance"
    TREATMENT_END = "treatment_end"


class AlertSeverity(str, enum.Enum):
    """Severidad de alerta"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Alert(Base):
    """Modelo de Alerta"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    treatment_id = Column(Integer, ForeignKey("treatments.id"), nullable=False)
    type = Column(Enum(AlertType), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    patient = relationship("Patient", back_populates="alerts")
    treatment = relationship("Treatment", back_populates="alerts")