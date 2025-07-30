"""
Esquemas Pydantic para Tratamientos
"""
from pydantic import BaseModel, validator, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from app.models.treatment import TreatmentStatus


# Esquemas base
class TreatmentBase(BaseModel):
    """Base para esquemas de tratamiento"""
    patient_id: int = Field(..., description="ID del paciente")
    medication_id: int = Field(..., description="ID del medicamento")
    dosage: str = Field(..., min_length=1, max_length=100, description="Dosis (ej: 2 tabletas, 500mg)")
    frequency: int = Field(..., ge=1, le=24, description="Frecuencia por día (1-24)")
    duration_days: int = Field(..., ge=1, le=3650, description="Duración en días (1-3650)")
    start_date: date = Field(..., description="Fecha de inicio")
    end_date: date = Field(..., description="Fecha de fin")
    instructions: Optional[str] = Field(None, max_length=1000, description="Instrucciones especiales")
    notes: Optional[str] = Field(None, max_length=1000, description="Notas adicionales")

    @validator('end_date')
    def validate_end_date(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('La fecha de fin debe ser posterior a la fecha de inicio')
        return v

    @validator('start_date')
    def validate_start_date(cls, v):
        # Permitir fechas pasadas para tratamientos ya iniciados
        return v

    @validator('dosage')
    def validate_dosage(cls, v):
        if not v or not v.strip():
            raise ValueError('La dosis es requerida')
        return v.strip()


class TreatmentCreate(TreatmentBase):
    """Esquema para crear tratamiento"""

    @property
    def calculated_end_date(self) -> date:
        """Calcular fecha de fin basada en duración"""
        from datetime import timedelta
        return self.start_date + timedelta(days=self.duration_days - 1)

    @validator('duration_days')
    def validate_duration(cls, v, values):
        if 'start_date' in values and 'end_date' in values:
            calculated_duration = (values['end_date'] - values['start_date']).days + 1
            if abs(v - calculated_duration) > 1:  # Permitir 1 día de diferencia
                raise ValueError('La duración no coincide con las fechas de inicio y fin')
        return v


class TreatmentUpdate(BaseModel):
    """Esquema para actualizar tratamiento"""
    dosage: Optional[str] = Field(None, min_length=1, max_length=100)
    frequency: Optional[int] = Field(None, ge=1, le=24)
    duration_days: Optional[int] = Field(None, ge=1, le=3650)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    instructions: Optional[str] = Field(None, max_length=1000)
    notes: Optional[str] = Field(None, max_length=1000)
    status: Optional[TreatmentStatus] = None

    @validator('end_date')
    def validate_end_date(cls, v, values):
        if v and 'start_date' in values and values['start_date'] and v <= values['start_date']:
            raise ValueError('La fecha de fin debe ser posterior a la fecha de inicio')
        return v


class TreatmentResponse(TreatmentBase):
    """Esquema de respuesta básica de tratamiento"""
    id: int
    status: TreatmentStatus
    created_by_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Información relacionada
    patient_name: Optional[str] = None
    medication_name: Optional[str] = None
    medication_unit: Optional[str] = None

    class Config:
        from_attributes = True

    @property
    def is_active(self) -> bool:
        """Verificar si el tratamiento está activo"""
        return self.status == TreatmentStatus.ACTIVE and self.end_date >= date.today()

    @property
    def days_remaining(self) -> int:
        """Días restantes del tratamiento"""
        if self.end_date < date.today():
            return 0
        return (self.end_date - date.today()).days


class TreatmentDetail(TreatmentResponse):
    """Esquema detallado de tratamiento con información adicional"""
    # Información del paciente
    patient: Optional[Dict[str, Any]] = None

    # Información del medicamento
    medication: Optional[Dict[str, Any]] = None

    # Estadísticas
    total_doses_scheduled: Optional[int] = 0
    total_doses_taken: Optional[int] = 0
    total_doses_missed: Optional[int] = 0
    compliance_rate: Optional[float] = 0.0

    # Alarmas y registros
    alarms_count: Optional[int] = 0
    active_alarms_count: Optional[int] = 0
    dose_records_count: Optional[int] = 0

    # Fechas importantes
    last_dose_time: Optional[datetime] = None
    next_dose_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class TreatmentSummary(BaseModel):
    """Esquema resumido para listas"""
    id: int
    patient_id: int
    patient_name: str
    medication_name: str
    dosage: str
    frequency: int
    status: TreatmentStatus
    start_date: date
    end_date: date
    days_remaining: int
    compliance_rate: float = 0.0

    class Config:
        from_attributes = True


class TreatmentStats(BaseModel):
    """Estadísticas del tratamiento"""
    treatment_id: int
    total_days: int
    days_completed: int
    days_remaining: int

    # Dosis
    total_doses_scheduled: int = 0
    total_doses_taken: int = 0
    total_doses_missed: int = 0
    total_doses_pending: int = 0

    # Cumplimiento
    compliance_rate: float = 0.0
    weekly_compliance: List[float] = []

    # Tendencias
    recent_compliance_trend: str = "stable"  # improving, declining, stable
    consecutive_missed_days: int = 0
    best_compliance_week: float = 0.0
    worst_compliance_week: float = 0.0

    # Timing
    average_delay_minutes: float = 0.0
    on_time_percentage: float = 0.0
    early_doses_percentage: float = 0.0
    late_doses_percentage: float = 0.0


class DoseRecord(BaseModel):
    """Registro de dosis"""
    id: int
    treatment_id: int
    patient_id: int
    scheduled_time: datetime
    actual_time: Optional[datetime] = None
    status: str  # taken, missed, pending, snoozed
    notes: Optional[str] = None
    delay_minutes: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TreatmentAlarm(BaseModel):
    """Alarma de tratamiento"""
    id: int
    treatment_id: int
    time: str  # HH:MM format
    is_active: bool = True
    sound_enabled: bool = True
    visual_enabled: bool = True
    description: Optional[str] = None

    class Config:
        from_attributes = True


class TreatmentConflict(BaseModel):
    """Conflicto de tratamiento"""
    type: str  # medication_interaction, allergy, duplicate
    severity: str  # low, medium, high
    message: str
    existing_treatment_id: Optional[int] = None
    existing_medication_name: Optional[str] = None
    recommendations: List[str] = []


class TreatmentValidation(BaseModel):
    """Validación de tratamiento"""
    is_valid: bool
    warnings: List[str] = []
    conflicts: List[TreatmentConflict] = []
    recommendations: List[str] = []


# Esquemas para reportes y análisis
class ComplianceReport(BaseModel):
    """Reporte de cumplimiento"""
    treatment_id: int
    patient_id: int
    period_start: date
    period_end: date
    total_days: int

    # Estadísticas generales
    scheduled_doses: int
    taken_doses: int
    missed_doses: int
    compliance_rate: float

    # Análisis temporal
    daily_compliance: List[Dict[str, Any]] = []
    weekly_averages: List[float] = []
    monthly_trend: str = "stable"

    # Patrones
    best_day_of_week: Optional[str] = None
    worst_day_of_week: Optional[str] = None
    best_time_of_day: Optional[str] = None
    most_missed_time: Optional[str] = None


class TreatmentDashboard(BaseModel):
    """Dashboard de tratamientos"""
    total_treatments: int = 0
    active_treatments: int = 0
    completed_treatments: int = 0
    suspended_treatments: int = 0

    # Próximos eventos
    expiring_soon: List[TreatmentSummary] = []
    doses_today: int = 0
    missed_doses_today: int = 0

    # Cumplimiento general
    overall_compliance_rate: float = 0.0
    patients_with_high_compliance: int = 0
    patients_needing_attention: int = 0

    # Alertas
    critical_alerts: int = 0
    medication_conflicts: int = 0


class BulkTreatmentResult(BaseModel):
    """Resultado de creación en lote"""
    success_count: int
    error_count: int
    created_treatments: List[TreatmentResponse] = []
    errors: List[Dict[str, Any]] = []


# Esquemas para filtros
class TreatmentFilter(BaseModel):
    """Filtros para búsqueda de tratamientos"""
    patient_id: Optional[int] = None
    medication_id: Optional[int] = None
    status: Optional[TreatmentStatus] = None
    start_date_from: Optional[date] = None
    start_date_to: Optional[date] = None
    end_date_from: Optional[date] = None
    end_date_to: Optional[date] = None
    compliance_rate_min: Optional[float] = Field(None, ge=0, le=100)
    compliance_rate_max: Optional[float] = Field(None, ge=0, le=100)