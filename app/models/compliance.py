# app/models/compliance.py
"""
Modelo de Cumplimiento
"""
from sqlalchemy import Column, Integer, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class ComplianceRecord(Base):
    """Modelo de Registro de Cumplimiento"""
    __tablename__ = "compliance_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    date = Column(Date, nullable=False)
    scheduled_doses = Column(Integer, default=0)
    taken_doses = Column(Integer, default=0)
    missed_doses = Column(Integer, default=0)
    compliance_rate = Column(Float, default=0.0)  # Porcentaje

    # Relaciones
    patient = relationship("Patient", back_populates="compliance_records")