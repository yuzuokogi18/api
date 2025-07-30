"""
Modelo de Medicamento
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class MedicationUnit(str, enum.Enum):
    mg = "mg"
    ml = "ml"
    tablets = "tablets"
    capsules = "capsules"
    drops = "drops"
    patches = "patches"



class Medication(Base):
    """Modelo de Medicamento"""
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)

    # Información básica
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    dosage = Column(String(100), nullable=False)  # ej: "500", "100"
    unit = Column(Enum(MedicationUnit), nullable=False)

    # Instrucciones y efectos
    instructions = Column(Text, nullable=True)
    side_effects = Column(JSON, default=list)  # Lista de efectos secundarios
    contraindications = Column(JSON, default=list)  # Lista de contraindicaciones

    # Información adicional
    brand_name = Column(String(255), nullable=True)
    generic_name = Column(String(255), nullable=True)
    manufacturer = Column(String(255), nullable=True)

    # Metadatos
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    treatments = relationship("Treatment", back_populates="medication", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Medication(id={self.id}, name='{self.name}', dosage='{self.dosage}{self.unit}')>"

    @property
    def full_name(self) -> str:
        """Nombre completo del medicamento"""
        return f"{self.name} {self.dosage}{self.unit}"

    def add_side_effect(self, effect: str):
        """Agregar efecto secundario"""
        if not self.side_effects:
            self.side_effects = []
        if effect not in self.side_effects:
            self.side_effects.append(effect)

    def remove_side_effect(self, effect: str):
        """Remover efecto secundario"""
        if self.side_effects and effect in self.side_effects:
            self.side_effects.remove(effect)

    def add_contraindication(self, contraindication: str):
        """Agregar contraindicación"""
        if not self.contraindications:
            self.contraindications = []
        if contraindication not in self.contraindications:
            self.contraindications.append(contraindication)

    def remove_contraindication(self, contraindication: str):
        """Remover contraindicación"""
        if self.contraindications and contraindication in self.contraindications:
            self.contraindications.remove(contraindication)