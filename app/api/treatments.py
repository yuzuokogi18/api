"""
Endpoints de tratamientos
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    get_caregiver_user,
    verify_treatment_access,
    verify_patient_access,
    get_pagination_params,
    get_date_range_params,
    PaginationParams,
    DateRangeParams
)
from app.models.user import User
from app.models.treatment import Treatment, TreatmentStatus
from app.schemas.treatment import (
    TreatmentCreate,
    TreatmentUpdate,
    TreatmentResponse,
    TreatmentDetail,
    TreatmentStats
)
from app.services.treatment_service import TreatmentService

router = APIRouter()


@router.get("/", response_model=List[TreatmentResponse])
async def list_treatments(
        pagination: PaginationParams = Depends(get_pagination_params),
        patient_id: Optional[int] = Query(None, description="Filtrar por paciente"),
        status: Optional[TreatmentStatus] = Query(None, description="Filtrar por estado"),
        medication_id: Optional[int] = Query(None, description="Filtrar por medicamento"),
        current_user: User = Depends(get_caregiver_user),
        db: Session = Depends(get_db)
):
    """
    Listar tratamientos del cuidador actual
    """
    treatment_service = TreatmentService(db)

    treatments = treatment_service.get_treatments_by_caregiver(
        caregiver_id=current_user.id,
        skip=pagination.skip,
        limit=pagination.limit,
        patient_id=patient_id,
        status=status,
        medication_id=medication_id
    )

    return treatments


@router.post("/", response_model=TreatmentResponse, status_code=status.HTTP_201_CREATED)
async def create_treatment(
        treatment_data: TreatmentCreate,
        current_user: User = Depends(get_caregiver_user),
        db: Session = Depends(get_db)
):
    """
    Crear nuevo tratamiento
    """
    treatment_service = TreatmentService(db)

    # Verificar acceso al paciente
    await verify_patient_access(treatment_data.patient_id, current_user, db)

    # Verificar que el medicamento existe
    if not treatment_service.medication_exists(treatment_data.medication_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicamento no encontrado"
        )

    # Validar fechas
    if treatment_data.start_date > treatment_data.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de inicio debe ser anterior a la fecha de fin"
        )

    # Verificar conflictos de medicamentos
    conflicts = treatment_service.check_medication_conflicts(
        patient_id=treatment_data.patient_id,
        medication_id=treatment_data.medication_id
    )

    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conflicto detectado: {conflicts['message']}"
        )

    treatment = treatment_service.create_treatment(
        treatment_data=treatment_data,
        created_by_id=current_user.id
    )

    return treatment


@router.get("/{treatment_id}", response_model=TreatmentDetail)
async def get_treatment(
        treatment_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_treatment_access)
):
    """
    Obtener detalles de un tratamiento específico
    """
    treatment_service = TreatmentService(db)

    treatment = treatment_service.get_treatment_detail(treatment_id)
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tratamiento no encontrado"
        )

    return treatment


@router.put("/{treatment_id}", response_model=TreatmentResponse)
async def update_treatment(
        treatment_id: int,
        treatment_update: TreatmentUpdate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_treatment_access)
):
    """
    Actualizar tratamiento
    """
    treatment_service = TreatmentService(db)

    treatment = treatment_service.get_treatment_by_id(treatment_id)
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tratamiento no encontrado"
        )

    # Validar fechas si se están actualizando
    if (treatment_update.start_date and treatment_update.end_date and
            treatment_update.start_date > treatment_update.end_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de inicio debe ser anterior a la fecha de fin"
        )

    updated_treatment = treatment_service.update_treatment(
        treatment_id=treatment_id,
        treatment_update=treatment_update
    )

    return updated_treatment


@router.delete("/{treatment_id}")
async def delete_treatment(
        treatment_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_treatment_access)
):
    """
    Eliminar/cancelar tratamiento
    """
    treatment_service = TreatmentService(db)

    treatment = treatment_service.get_treatment_by_id(treatment_id)
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tratamiento no encontrado"
        )

    # Cancelar en lugar de eliminar
    treatment_service.cancel_treatment(treatment_id)

    return {"message": "Tratamiento cancelado exitosamente"}


@router.post("/{treatment_id}/activate")
async def activate_treatment(
        treatment_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_treatment_access)
):
    """
    Activar tratamiento suspendido
    """
    treatment_service = TreatmentService(db)

    success = treatment_service.activate_treatment(treatment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo activar el tratamiento"
        )

    return {"message": "Tratamiento activado exitosamente"}


@router.post("/{treatment_id}/suspend")
async def suspend_treatment(
        treatment_id: int,
        reason: str = Query(..., description="Razón de la suspensión"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_treatment_access)
):
    """
    Suspender tratamiento temporalmente
    """
    treatment_service = TreatmentService(db)

    success = treatment_service.suspend_treatment(treatment_id, reason)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo suspender el tratamiento"
        )

    return {"message": "Tratamiento suspendido exitosamente"}


@router.post("/{treatment_id}/complete")
async def complete_treatment(
        treatment_id: int,
        notes: Optional[str] = Query(None, description="Notas de finalización"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_treatment_access)
):
    """
    Marcar tratamiento como completado
    """
    treatment_service = TreatmentService(db)

    success = treatment_service.complete_treatment(treatment_id, notes)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo completar el tratamiento"
        )

    return {"message": "Tratamiento completado exitosamente"}


@router.get("/{treatment_id}/alarms")
async def get_treatment_alarms(
        treatment_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_treatment_access)
):
    """
    Obtener alarmas del tratamiento
    """
    treatment_service = TreatmentService(db)

    alarms = treatment_service.get_treatment_alarms(treatment_id)
    return alarms


@router.post("/{treatment_id}/alarms")
async def create_treatment_alarm(
        treatment_id: int,
        alarm_data: dict,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_treatment_access)
):
    """
    Crear alarma para el tratamiento
    """
    treatment_service = TreatmentService(db)

    alarm = treatment_service.create_alarm(treatment_id, alarm_data)
    return alarm


@router.get("/{treatment_id}/dose-records")
async def get_treatment_dose_records(
        treatment_id: int,
        date_range: DateRangeParams = Depends(get_date_range_params),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_treatment_access)
):
    """
    Obtener registros de dosis del tratamiento
    """
    treatment_service = TreatmentService(db)

    dose_records = treatment_service.get_dose_records(
        treatment_id=treatment_id,
        start_date=date_range.start_date,
        end_date=date_range.end_date
    )

    return dose_records


@router.post("/{treatment_id}/dose-records")
async def record_dose_taken(
        treatment_id: int,
        dose_data: dict,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_treatment_access)
):
    """
    Registrar dosis tomada
    """
    treatment_service = TreatmentService(db)

    dose_record = treatment_service.record_dose(treatment_id, dose_data)
    return dose_record


@router.get("/{treatment_id}/compliance")
async def get_treatment_compliance(
        treatment_id: int,
        days: int = Query(30, description="Número de días para el reporte"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_treatment_access)
):
    """
    Obtener reporte de cumplimiento del tratamiento
    """
    treatment_service = TreatmentService(db)

    compliance = treatment_service.get_compliance_report(treatment_id, days)
    return compliance


@router.get("/{treatment_id}/stats", response_model=TreatmentStats)
async def get_treatment_statistics(
        treatment_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_treatment_access)
):
    """
    Obtener estadísticas del tratamiento
    """
    treatment_service = TreatmentService(db)

    stats = treatment_service.get_treatment_statistics(treatment_id)
    return stats


@router.get("/patient/{patient_id}/active")
async def get_patient_active_treatments(
        patient_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_patient_access)
):
    """
    Obtener tratamientos activos del paciente
    """
    treatment_service = TreatmentService(db)

    treatments = treatment_service.get_active_treatments_by_patient(patient_id)
    return treatments


@router.get("/expiring")
async def get_expiring_treatments(
        days_ahead: int = Query(7, description="Días hacia adelante para verificar"),
        current_user: User = Depends(get_caregiver_user),
        db: Session = Depends(get_db)
):
    """
    Obtener tratamientos que están por vencer
    """
    treatment_service = TreatmentService(db)

    expiring = treatment_service.get_expiring_treatments(
        caregiver_id=current_user.id,
        days_ahead=days_ahead
    )

    return expiring


@router.get("/dashboard/summary")
async def get_treatments_dashboard(
        current_user: User = Depends(get_caregiver_user),
        db: Session = Depends(get_db)
):
    """
    Obtener resumen de tratamientos para dashboard
    """
    treatment_service = TreatmentService(db)

    summary = treatment_service.get_dashboard_summary(current_user.id)
    return summary


@router.post("/bulk/create")
async def create_bulk_treatments(
        treatments_data: List[TreatmentCreate],
        current_user: User = Depends(get_caregiver_user),
        db: Session = Depends(get_db)
):
    """
    Crear múltiples tratamientos
    """
    treatment_service = TreatmentService(db)

    # Validar acceso a todos los pacientes
    for treatment_data in treatments_data:
        await verify_patient_access(treatment_data.patient_id, current_user, db)

    results = treatment_service.create_bulk_treatments(
        treatments_data=treatments_data,
        created_by_id=current_user.id
    )

    return {
        "created": len(results["success"]),
        "failed": len(results["errors"]),
        "treatments": results["success"],
        "errors": results["errors"]
    }


@router.get("/analytics/compliance")
async def get_compliance_analytics(
        date_range: DateRangeParams = Depends(get_date_range_params),
        patient_id: Optional[int] = Query(None, description="Filtrar por paciente"),
        current_user: User = Depends(get_caregiver_user),
        db: Session = Depends(get_db)
):
    """
    Obtener análisis de cumplimiento de tratamientos
    """
    treatment_service = TreatmentService(db)

    analytics = treatment_service.get_compliance_analytics(
        caregiver_id=current_user.id,
        start_date=date_range.start_date,
        end_date=date_range.end_date,
        patient_id=patient_id
    )

    return analytics


# AGREGAR este endpoint a tu archivo de endpoints de tratamientos:

@router.delete("/{treatment_id}/alarms/{alarm_id}")
async def delete_treatment_alarm(
        treatment_id: int,
        alarm_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_treatment_access)
):
    """
    Eliminar alarma específica del tratamiento
    """
    treatment_service = TreatmentService(db)

    try:
        success = treatment_service.delete_alarm(treatment_id, alarm_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alarma {alarm_id} no encontrada para el tratamiento {treatment_id}"
            )

        return {
            "message": "Alarma eliminada exitosamente",
            "alarm_id": alarm_id,
            "treatment_id": treatment_id
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error eliminando alarma: {str(e)}"
        )


# TAMBIÉN AGREGAR este endpoint de debugging (opcional):
@router.get("/{treatment_id}/alarms/debug")
async def debug_treatment_alarms(
        treatment_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_treatment_access)
):
    """
    Endpoint de debugging para verificar el estado de las alarmas
    """
    treatment_service = TreatmentService(db)
    debug_info = treatment_service.debug_treatment_alarms(treatment_id)
    return debug_info