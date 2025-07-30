"""
Endpoints de pacientes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    get_caregiver_user,
    verify_patient_access,
    get_pagination_params,
    PaginationParams
)
from app.models.user import User
from app.models.patient import Patient, Gender
from app.schemas.patient import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientDetail
)
from app.services.patient_service import PatientService

router = APIRouter()


@router.get("/", response_model=List[PatientResponse])
async def list_patients(
        pagination: PaginationParams = Depends(get_pagination_params),
        search: Optional[str] = Query(None, description="Buscar por nombre o email"),
        gender: Optional[Gender] = Query(None, description="Filtrar por género"),
        current_user: User = Depends(get_caregiver_user),
        db: Session = Depends(get_db)
):
    """
    Listar pacientes del cuidador actual
    """
    patient_service = PatientService(db)

    patients = patient_service.get_patients_by_caregiver(
        caregiver_id=current_user.id,
        skip=pagination.skip,
        limit=pagination.limit,
        search=search,
        gender=gender
    )

    return patients


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
        patient_data: PatientCreate,
        current_user: User = Depends(get_caregiver_user),
        db: Session = Depends(get_db)
):
    """
    Crear nuevo paciente
    """
    patient_service = PatientService(db)

    # Verificar que el email no esté en uso
    if patient_service.get_patient_by_email(patient_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )

    patient = patient_service.create_patient(
        patient_data=patient_data,
        caregiver_id=current_user.id
    )

    return patient


@router.get("/{patient_id}", response_model=PatientDetail)
async def get_patient(
        patient_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_patient_access)
):
    """
    Obtener detalles de un paciente específico
    """
    patient_service = PatientService(db)

    patient = patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado"
        )

    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
        patient_id: int,
        patient_update: PatientUpdate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_patient_access)
):
    """
    Actualizar información del paciente
    """
    patient_service = PatientService(db)

    patient = patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado"
        )

    # Si se está actualizando el email, verificar que no esté en uso
    if patient_update.email and patient_update.email != patient.email:
        if patient_service.get_patient_by_email(patient_update.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )

    updated_patient = patient_service.update_patient(
        patient_id=patient_id,
        patient_update=patient_update
    )

    return updated_patient


@router.delete("/{patient_id}")
async def delete_patient(
        patient_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_patient_access)
):
    """
    Eliminar paciente
    """
    patient_service = PatientService(db)

    patient = patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado"
        )

    # Verificar que no tenga tratamientos activos
    if patient_service.has_active_treatments(patient_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un paciente con tratamientos activos"
        )

    patient_service.delete_patient(patient_id)

    return {"message": "Paciente eliminado exitosamente"}


@router.get("/{patient_id}/treatments")
async def get_patient_treatments(
        patient_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_patient_access)
):
    """
    Obtener tratamientos del paciente
    """
    patient_service = PatientService(db)

    treatments = patient_service.get_patient_treatments(patient_id)

    return treatments


@router.get("/{patient_id}/compliance")
async def get_patient_compliance(
        patient_id: int,
        days: int = Query(30, description="Número de días para el reporte"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_patient_access)
):
    """
    Obtener reporte de cumplimiento del paciente
    """
    patient_service = PatientService(db)

    compliance = patient_service.get_patient_compliance_report(
        patient_id=patient_id,
        days=days
    )

    return compliance


@router.post("/{patient_id}/notes")
async def add_patient_note(
        patient_id: int,
        note_data: dict,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_patient_access)
):
    """
    Agregar nota al historial del paciente
    """
    patient_service = PatientService(db)

    note = patient_service.add_patient_note(
        patient_id=patient_id,
        note_data=note_data,
        created_by=current_user.id
    )

    return note


@router.get("/{patient_id}/alerts")
async def get_patient_alerts(
        patient_id: int,
        unread_only: bool = Query(False, description="Solo alertas no leídas"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        _: bool = Depends(verify_patient_access)
):
    """
    Obtener alertas del paciente
    """
    patient_service = PatientService(db)

    alerts = patient_service.get_patient_alerts(
        patient_id=patient_id,
        unread_only=unread_only
    )

    return alerts