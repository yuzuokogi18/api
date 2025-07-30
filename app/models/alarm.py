"""
Modelo para alarmas de tratamientos
"""
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Alarm(Base):
    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    treatment_id = Column(Integer, ForeignKey("treatments.id"), nullable=False, index=True)
    time = Column(String(5), nullable=False)  # Formato HH:MM (ej: "08:30")
    is_active = Column(Boolean, default=True, nullable=True)
    sound_enabled = Column(Boolean, default=True, nullable=True)
    visual_enabled = Column(Boolean, default=True, nullable=True)
    description = Column(Text, nullable=True)

    # Relación con Treatment
    treatment = relationship("Treatment", back_populates="alarms")

    def __repr__(self):
        return f"<Alarm(id={self.id}, treatment_id={self.treatment_id}, time={self.time}, active={self.is_active})>"

    def to_dict(self):
        """Convertir a diccionario para serialización"""
        return {
            "id": self.id,
            "treatment_id": self.treatment_id,
            "time": self.time,
            "is_active": self.is_active if self.is_active is not None else True,
            "sound_enabled": self.sound_enabled if self.sound_enabled is not None else True,
            "visual_enabled": self.visual_enabled if self.visual_enabled is not None else True,
            "description": self.description or ""
        }