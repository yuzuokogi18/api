# app/models/dose_record.py
"""
Modelo de Registro de Dosis
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class DoseStatus(str, enum.Enum):
    """Estados de dosis"""
    TAKEN = "taken"
    MISSED = "missed"
    PENDING = "pending"
    SNOOZED = "snoozed"


class DoseRecord(Base):
    """Modelo de Registro de Dosis"""
    __tablename__ = "dose_records"

    id = Column(Integer, primary_key=True, index=True)
    treatment_id = Column(Integer, ForeignKey("treatments.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    actual_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(DoseStatus), default=DoseStatus.PENDING)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    treatment = relationship("Treatment", back_populates="dose_records")
    patient = relationship("Patient", back_populates="dose_records")
