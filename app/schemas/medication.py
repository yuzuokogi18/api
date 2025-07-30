"""
Esquemas Pydantic para Medicamentos
"""
from pydantic import BaseModel, validator, Field
from typing import Optional, List
from datetime import datetime
from app.models.medication import MedicationUnit


# Esquemas base
class MedicationBase(BaseModel):
    """Base para esquemas de medicamento"""
    name: str = Field(..., min_length=1, max_length=255, description="Nombre del medicamento")
    description: Optional[str] = Field(None, max_length=1000, description="Descripción del medicamento")
    dosage: str = Field(..., min_length=1, max_length=100, description="Dosis (ej: 500, 100)")
    unit: MedicationUnit = Field(..., description="Unidad de medida")
    instructions: Optional[str] = Field(None, max_length=1000, description="Instrucciones de uso")

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('El nombre del medicamento es requerido')
        return v.strip().title()

    @validator('dosage')
    def validate_dosage(cls, v):
        if not v or not v.strip():
            raise ValueError('La dosis es requerida')
        return v.strip()


class MedicationCreate(MedicationBase):
    """Esquema para crear medicamento"""
    side_effects: List[str] = Field(default=[], description="Efectos secundarios conocidos")
    contraindications: List[str] = Field(default=[], description="Contraindicaciones")
    brand_name: Optional[str] = Field(None, max_length=255, description="Nombre comercial")
    generic_name: Optional[str] = Field(None, max_length=255, description="Nombre genérico")
    manufacturer: Optional[str] = Field(None, max_length=255, description="Fabricante")

    @validator('side_effects', 'contraindications')
    def validate_lists(cls, v):
        if v:
            # Remover duplicados y elementos vacíos
            return list(set(filter(None, [item.strip() for item in v])))
        return []


class MedicationUpdate(BaseModel):
    """Esquema para actualizar medicamento"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    dosage: Optional[str] = Field(None, min_length=1, max_length=100)
    unit: Optional[MedicationUnit] = None
    instructions: Optional[str] = Field(None, max_length=1000)
    side_effects: Optional[List[str]] = None
    contraindications: Optional[List[str]] = None
    brand_name: Optional[str] = Field(None, max_length=255)
    generic_name: Optional[str] = Field(None, max_length=255)
    manufacturer: Optional[str] = Field(None, max_length=255)

    @validator('side_effects', 'contraindications')
    def validate_lists(cls, v):
        if v is not None:
            return list(set(filter(None, [item.strip() for item in v])))
        return v


class MedicationResponse(MedicationBase):
    """Esquema de respuesta básica de medicamento"""
    id: int
    side_effects: List[str]
    contraindications: List[str]
    brand_name: Optional[str] = None
    generic_name: Optional[str] = None
    manufacturer: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @property
    def full_name(self) -> str:
        """Nombre completo del medicamento"""
        return f"{self.name} {self.dosage}{self.unit.value}"


class MedicationDetail(MedicationResponse):
    """Esquema detallado de medicamento con información adicional"""
    treatments_count: Optional[int] = 0
    active_treatments_count: Optional[int] = 0
    patients_using_count: Optional[int] = 0

    class Config:
        from_attributes = True


class MedicationSummary(BaseModel):
    """Esquema resumido para listas y autocompletado"""
    id: int
    name: str
    dosage: str
    unit: MedicationUnit
    full_name: str
    brand_name: Optional[str] = None

    class Config:
        from_attributes = True


class MedicationSearch(BaseModel):
    """Esquema para búsqueda de medicamentos"""
    query: str = Field(..., min_length=2, max_length=100)
    unit: Optional[MedicationUnit] = None
    brand_only: bool = False
    generic_only: bool = False


class MedicationInteraction(BaseModel):
    """Esquema para interacciones medicamentosas"""
    medication1_id: int
    medication1_name: str
    medication2_id: int
    medication2_name: str
    interaction_type: str = Field(..., description="Tipo de interacción")
    severity: str = Field(..., description="Severidad: low, medium, high")
    description: str = Field(..., description="Descripción de la interacción")
    recommendation: Optional[str] = Field(None, description="Recomendación médica")


class MedicationUsageStats(BaseModel):
    """Estadísticas de uso de medicamentos"""
    medication_id: int
    medication_name: str
    total_treatments: int = 0
    active_treatments: int = 0
    total_patients: int = 0
    total_doses_prescribed: int = 0
    compliance_rate: float = 0.0


class MedicationInventory(BaseModel):
    """Inventario de medicamento (para futuras expansiones)"""
    medication_id: int
    medication_name: str
    current_stock: int = 0
    min_stock_alert: int = 10
    expiration_dates: List[str] = []
    needs_reorder: bool = False


# Esquemas para reportes
class MedicationReport(BaseModel):
    """Reporte de medicamentos"""
    total_medications: int
    most_prescribed: List[MedicationUsageStats]
    least_prescribed: List[MedicationUsageStats]
    by_unit: dict
    compliance_by_medication: List[dict]


class MedicationConflict(BaseModel):
    """Conflicto de medicamento con alergias del paciente"""
    medication_id: int
    medication_name: str
    patient_id: int
    patient_name: str
    conflicting_allergies: List[str]
    severity: str = "medium"


# Esquemas para validaciones
class MedicationValidation(BaseModel):
    """Validación de medicamento para un paciente"""
    medication_id: int
    patient_id: int
    is_safe: bool
    warnings: List[str] = []
    allergies_conflict: List[str] = []
    interactions: List[MedicationInteraction] = []
    recommendations: List[str] = []


class MedicationDosageValidation(BaseModel):
    """Validación de dosis"""
    medication_id: int
    patient_age: int
    patient_weight: Optional[float] = None
    proposed_dosage: str
    is_appropriate: bool
    recommendations: List[str] = []
    min_dosage: Optional[str] = None
    max_dosage: Optional[str] = None