"""
Esquemas Pydantic para Pacientes
"""
from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from app.models.patient import Gender


# Esquemas base
class PatientBase(BaseModel):
    """Base para esquemas de paciente"""
    name: str = Field(..., min_length=1, max_length=255, description="Nombre completo del paciente")
    email: EmailStr = Field(..., description="Email del paciente")
    phone: str = Field(..., min_length=10, max_length=20, description="Teléfono del paciente")
    date_of_birth: date = Field(..., description="Fecha de nacimiento")
    gender: Gender = Field(..., description="Género del paciente")
    address: str = Field(..., min_length=1, description="Dirección completa")
    timezone: str = Field(default="America/Mexico_City", description="Zona horaria")
    preferred_language: str = Field(default="es", description="Idioma preferido")

    @validator('date_of_birth')
    def validate_birth_date(cls, v):
        if v > date.today():
            raise ValueError('La fecha de nacimiento no puede ser futura')

        # Calcular edad
        age = date.today().year - v.year
        if date.today().month < v.month or (date.today().month == v.month and date.today().day < v.day):
            age -= 1

        if age > 120:
            raise ValueError('Edad no válida')

        return v

    @validator('phone')
    def validate_phone(cls, v):
        # Remover espacios y caracteres especiales
        clean_phone = ''.join(filter(str.isdigit, v))
        if len(clean_phone) < 10:
            raise ValueError('Número de teléfono inválido')
        return v


class EmergencyContact(BaseModel):
    """Esquema para contacto de emergencia"""
    name: str = Field(..., min_length=1, max_length=255, description="Nombre del contacto")
    phone: str = Field(..., min_length=10, max_length=20, description="Teléfono del contacto")
    relationship: str = Field(..., min_length=1, max_length=100, description="Relación con el paciente")
    email: Optional[EmailStr] = Field(None, description="Email del contacto")


class PatientCreate(PatientBase):
    """Esquema para crear paciente"""
    emergency_contact: EmergencyContact = Field(..., description="Contacto de emergencia")
    medical_history: List[str] = Field(default=[], description="Historial médico")
    allergies: List[str] = Field(default=[], description="Alergias conocidas")

    @validator('medical_history', 'allergies')
    def validate_lists(cls, v):
        # Remover duplicados y elementos vacíos
        return list(set(filter(None, v)))


class PatientUpdate(BaseModel):
    """Esquema para actualizar paciente"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    address: Optional[str] = Field(None, min_length=1)
    emergency_contact: Optional[EmergencyContact] = None
    medical_history: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    timezone: Optional[str] = None
    preferred_language: Optional[str] = None

    @validator('medical_history', 'allergies')
    def validate_lists(cls, v):
        if v is not None:
            return list(set(filter(None, v)))
        return v


class PatientResponse(PatientBase):
    """Esquema de respuesta básica de paciente"""
    id: int
    emergency_contact: Dict[str, Any]
    medical_history: List[str]
    allergies: List[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @property
    def age(self) -> int:
        """Calcular edad"""
        today = date.today()
        return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class PatientDetail(PatientResponse):
    """Esquema detallado de paciente con información adicional"""
    caregiver_id: int
    active_treatments_count: Optional[int] = 0
    total_alerts_count: Optional[int] = 0
    unread_alerts_count: Optional[int] = 0
    compliance_rate: Optional[float] = 0.0

    class Config:
        from_attributes = True


class PatientSummary(BaseModel):
    """Esquema resumido para listas"""
    id: int
    name: str
    email: str
    age: int
    gender: Gender
    active_treatments: int = 0
    last_dose_time: Optional[datetime] = None
    compliance_rate: float = 0.0

    class Config:
        from_attributes = True


class PatientStats(BaseModel):
    """Estadísticas del paciente"""
    total_treatments: int = 0
    active_treatments: int = 0
    completed_treatments: int = 0
    total_doses_scheduled: int = 0
    total_doses_taken: int = 0
    total_doses_missed: int = 0
    compliance_rate: float = 0.0
    last_dose_time: Optional[datetime] = None
    next_dose_time: Optional[datetime] = None


class PatientNote(BaseModel):
    """Nota del paciente"""
    id: int
    content: str
    created_by: int
    created_by_name: str
    created_at: datetime
    note_type: str = "general"

    class Config:
        from_attributes = True


class PatientNoteCreate(BaseModel):
    """Crear nota del paciente"""
    content: str = Field(..., min_length=1, max_length=1000)
    note_type: str = Field(default="general", max_length=50)


# Esquemas para filtros y búsquedas
class PatientFilter(BaseModel):
    """Filtros para búsqueda de pacientes"""
    search: Optional[str] = None
    gender: Optional[Gender] = None
    age_min: Optional[int] = Field(None, ge=0, le=120)
    age_max: Optional[int] = Field(None, ge=0, le=120)
    has_active_treatments: Optional[bool] = None