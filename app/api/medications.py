"""
Endpoints de medicamentos
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    get_caregiver_user,
    get_pagination_params,
    PaginationParams
)
from app.models.user import User
from app.models.medication import Medication, MedicationUnit
from app.schemas.medication import (
    MedicationCreate,
    MedicationUpdate,
    MedicationResponse,
    MedicationDetail,
    MedicationSearch
)
from app.services.medication_service import MedicationService

router = APIRouter()


@router.get("/", response_model=List[MedicationResponse])
async def list_medications(
        pagination: PaginationParams = Depends(get_pagination_params),
        search: Optional[str] = Query(None, description="Buscar por nombre"),
        unit: Optional[MedicationUnit] = Query(None, description="Filtrar por unidad"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Listar medicamentos disponibles
    """
    medication_service = MedicationService(db)

    medications = medication_service.get_medications(
        skip=pagination.skip,
        limit=pagination.limit,
        search=search,
        unit=unit
    )

    return medications


@router.post("/", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
async def create_medication(
        medication_data: MedicationCreate,
        current_user: User = Depends(get_caregiver_user),
        db: Session = Depends(get_db)
):
    """
    Crear nuevo medicamento
    """
    medication_service = MedicationService(db)

    # Verificar que no exista un medicamento igual
    existing = medication_service.find_similar_medication(
        name=medication_data.name,
        dosage=medication_data.dosage,
        unit=medication_data.unit
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un medicamento similar: {existing.full_name}"
        )

    medication = medication_service.create_medication(medication_data)
    return medication


@router.get("/{medication_id}", response_model=MedicationDetail)
async def get_medication(
        medication_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Obtener detalles de un medicamento específico
    """
    medication_service = MedicationService(db)

    medication = medication_service.get_medication_by_id(medication_id)
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicamento no encontrado"
        )

    return medication


@router.put("/{medication_id}", response_model=MedicationResponse)
async def update_medication(
        medication_id: int,
        medication_update: MedicationUpdate,
        current_user: User = Depends(get_caregiver_user),
        db: Session = Depends(get_db)
):
    """
    Actualizar información del medicamento
    """
    medication_service = MedicationService(db)

    medication = medication_service.get_medication_by_id(medication_id)
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicamento no encontrado"
        )

    updated_medication = medication_service.update_medication(
        medication_id=medication_id,
        medication_update=medication_update
    )

    return updated_medication


@router.delete("/{medication_id}")
async def delete_medication(
        medication_id: int,
        current_user: User = Depends(get_caregiver_user),
        db: Session = Depends(get_db)
):
    """
    Eliminar medicamento
    """
    medication_service = MedicationService(db)

    medication = medication_service.get_medication_by_id(medication_id)
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicamento no encontrado"
        )

    # Verificar que no esté siendo usado en tratamientos activos
    if medication_service.is_medication_in_use(medication_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un medicamento que está siendo usado en tratamientos activos"
        )

    medication_service.delete_medication(medication_id)
    return {"message": "Medicamento eliminado exitosamente"}


@router.get("/search/by-name")
async def search_medications_by_name(
        q: str = Query(..., min_length=2, description="Término de búsqueda"),
        limit: int = Query(10, le=50, description="Límite de resultados"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Buscar medicamentos por nombre (para autocompletado)
    """
    medication_service = MedicationService(db)

    medications = medication_service.search_by_name(query=q, limit=limit)

    return [
        {
            "id": med.id,
            "name": med.name,
            "full_name": med.full_name,
            "dosage": med.dosage,
            "unit": med.unit
        }
        for med in medications
    ]


@router.get("/{medication_id}/interactions")
async def get_medication_interactions(
        medication_id: int,
        other_medication_ids: List[int] = Query([], description="IDs de otros medicamentos"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Verificar interacciones medicamentosas
    """
    medication_service = MedicationService(db)

    medication = medication_service.get_medication_by_id(medication_id)
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicamento no encontrado"
        )

    interactions = medication_service.check_interactions(
        medication_id=medication_id,
        other_medication_ids=other_medication_ids
    )

    return interactions


@router.get("/{medication_id}/treatments")
async def get_medication_treatments(
        medication_id: int,
        active_only: bool = Query(True, description="Solo tratamientos activos"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Obtener tratamientos que usan este medicamento
    """
    medication_service = MedicationService(db)

    treatments = medication_service.get_medication_treatments(
        medication_id=medication_id,
        active_only=active_only,
        caregiver_id=current_user.id if not current_user.is_admin else None
    )

    return treatments


@router.post("/{medication_id}/side-effects")
async def add_side_effect(
        medication_id: int,
        side_effect: str = Query(..., min_length=1, max_length=255),
        current_user: User = Depends(get_caregiver_user),
        db: Session = Depends(get_db)
):
    """
    Agregar efecto secundario al medicamento
    """
    medication_service = MedicationService(db)

    medication = medication_service.get_medication_by_id(medication_id)
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicamento no encontrado"
        )

    medication_service.add_side_effect(medication_id, side_effect)
    return {"message": "Efecto secundario agregado exitosamente"}


@router.delete("/{medication_id}/side-effects")
async def remove_side_effect(
        medication_id: int,
        side_effect: str = Query(..., min_length=1),
        current_user: User = Depends(get_caregiver_user),
        db: Session = Depends(get_db)
):
    """
    Remover efecto secundario del medicamento
    """
    medication_service = MedicationService(db)

    medication = medication_service.get_medication_by_id(medication_id)
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicamento no encontrado"
        )

    medication_service.remove_side_effect(medication_id, side_effect)
    return {"message": "Efecto secundario removido exitosamente"}


@router.get("/units/available")
async def get_available_units(
        current_user: User = Depends(get_current_user)
):
    """
    Obtener unidades de medicamento disponibles
    """
    return [
        {"value": unit.value, "label": unit.value.upper()}
        for unit in MedicationUnit
    ]


@router.get("/stats/usage")
async def get_medication_usage_stats(
        current_user: User = Depends(get_caregiver_user),
        db: Session = Depends(get_db)
):
    """
    Obtener estadísticas de uso de medicamentos
    """
    medication_service = MedicationService(db)

    stats = medication_service.get_usage_statistics(
        caregiver_id=current_user.id if not current_user.is_admin else None
    )

    return stats


@router.get("/api/medications/")
def get_medications(db: Session = Depends(get_db)):
    try:
        meds = db.query(Medication).order_by(Medication.name).limit(100).all()
        return meds
    except Exception as e:
        # Aquí imprime el error en consola y lanza HTTP 500 con detalle
        print("ERROR fetching medications:", e)
        raise HTTPException(status_code=500, detail=str(e))