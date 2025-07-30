# app/api/alarms.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, validator

from app.core.database import get_db
from app.core.dependencies import get_current_user, verify_treatment_access
from app.models.user import User
from app.models.alarm import Alarm
from app.models.treatment import Treatment

router = APIRouter()


# Schemas Pydantic
class AlarmCreate(BaseModel):
    time: str  # Formato "HH:MM"
    is_active: bool = True
    sound_enabled: bool = True
    visual_enabled: bool = True
    description: Optional[str] = ""

    @validator('time')
    def validate_time_format(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
            return v
        except ValueError:
            raise ValueError('El tiempo debe estar en formato HH:MM')


class AlarmUpdate(BaseModel):
    time: Optional[str] = None
    is_active: Optional[bool] = None
    sound_enabled: Optional[bool] = None
    visual_enabled: Optional[bool] = None
    description: Optional[str] = None

    @validator('time')
    def validate_time_format(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, "%H:%M")
                return v
            except ValueError:
                raise ValueError('El tiempo debe estar en formato HH:MM')
        return v


class AlarmResponse(BaseModel):
    id: int
    treatment_id: int
    time: str
    is_active: bool
    sound_enabled: bool
    visual_enabled: bool
    description: str

    class Config:
        from_attributes = True


# ==== ENDPOINTS ====

@router.get("/treatments/{treatment_id}/alarms", response_model=List[AlarmResponse])
async def get_treatment_alarms(
        treatment_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        _: bool = Depends(verify_treatment_access)  # Usa tu verificación existente
):
    """Obtener todas las alarmas de un tratamiento"""

    # Obtener alarmas del tratamiento
    alarms = db.query(Alarm).filter(Alarm.treatment_id == treatment_id).all()

    return alarms


@router.post("/treatments/{treatment_id}/alarms", response_model=AlarmResponse)
async def create_treatment_alarm(
        treatment_id: int,
        alarm_data: AlarmCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        _: bool = Depends(verify_treatment_access)
):
    """Crear una nueva alarma para un tratamiento"""

    # Crear la alarma
    alarm = Alarm(
        treatment_id=treatment_id,
        time=alarm_data.time,
        is_active=alarm_data.is_active,
        sound_enabled=alarm_data.sound_enabled,
        visual_enabled=alarm_data.visual_enabled,
        description=alarm_data.description or ""
    )

    db.add(alarm)
    db.commit()
    db.refresh(alarm)

    return alarm


@router.put("/treatments/{treatment_id}/alarms/{alarm_id}", response_model=AlarmResponse)
async def update_treatment_alarm(
        treatment_id: int,
        alarm_id: int,
        alarm_data: AlarmUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        _: bool = Depends(verify_treatment_access)
):
    """Actualizar una alarma específica"""

    # Verificar que la alarma existe y pertenece al tratamiento
    alarm = db.query(Alarm).filter(
        Alarm.id == alarm_id,
        Alarm.treatment_id == treatment_id
    ).first()

    if not alarm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alarma no encontrada"
        )

    # Actualizar campos
    update_data = alarm_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alarm, field, value)

    db.commit()
    db.refresh(alarm)

    return alarm


@router.delete("/treatments/{treatment_id}/alarms/{alarm_id}")
async def delete_treatment_alarm(
        treatment_id: int,
        alarm_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        _: bool = Depends(verify_treatment_access)
):
    """Eliminar una alarma específica"""

    # Verificar que la alarma existe
    alarm = db.query(Alarm).filter(
        Alarm.id == alarm_id,
        Alarm.treatment_id == treatment_id
    ).first()

    if not alarm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alarma no encontrada"
        )

    # Eliminar alarma
    db.delete(alarm)
    db.commit()

    return {"message": "Alarma eliminada exitosamente"}


@router.post("/treatments/{treatment_id}/alarms/sync", response_model=List[AlarmResponse])
async def sync_treatment_alarms(
        treatment_id: int,
        alarms_data: List[AlarmCreate],
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        _: bool = Depends(verify_treatment_access)
):
    """Sincronizar alarmas (eliminar todas y crear nuevas)"""

    # Eliminar alarmas existentes
    db.query(Alarm).filter(Alarm.treatment_id == treatment_id).delete()

    # Crear nuevas alarmas
    created_alarms = []
    for alarm_data in alarms_data:
        alarm = Alarm(
            treatment_id=treatment_id,
            time=alarm_data.time,
            is_active=alarm_data.is_active,
            sound_enabled=alarm_data.sound_enabled,
            visual_enabled=alarm_data.visual_enabled,
            description=alarm_data.description or ""
        )
        db.add(alarm)
        created_alarms.append(alarm)

    db.commit()

    # Refresh all created alarms
    for alarm in created_alarms:
        db.refresh(alarm)

    return created_alarms