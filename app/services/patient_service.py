"""
Servicio de gestión de pacientes
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import date, datetime, timedelta

from app.models.patient import Patient, Gender
from app.models.treatment import Treatment, TreatmentStatus
from app.models.alert import Alert
from app.models.dose_record import DoseRecord, DoseStatus
from app.models.compliance import ComplianceRecord
from app.schemas.patient import PatientCreate, PatientUpdate
import logging

logger = logging.getLogger(__name__)


class PatientService:
    """Servicio para gestión de pacientes"""

    def __init__(self, db: Session):
        self.db = db

    def get_patients_by_caregiver(
            self,
            caregiver_id: int,
            skip: int = 0,
            limit: int = 100,
            search: Optional[str] = None,
            gender: Optional[Gender] = None
    ) -> List[Patient]:
        """Obtener pacientes de un cuidador con filtros"""

        query = self.db.query(Patient).filter(Patient.caregiver_id == caregiver_id)

        # Filtro de búsqueda
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Patient.name).like(search_term),
                    func.lower(Patient.email).like(search_term)
                )
            )

        # Filtro por género
        if gender:
            query = query.filter(Patient.gender == gender)

        return query.offset(skip).limit(limit).all()

    def get_patient_by_id(self, patient_id: int) -> Optional[Patient]:
        """Obtener paciente por ID con relaciones"""
        return self.db.query(Patient).options(
            joinedload(Patient.treatments),
            joinedload(Patient.alerts)
        ).filter(Patient.id == patient_id).first()

    def get_patient_by_email(self, email: str) -> Optional[Patient]:
        """Obtener paciente por email"""
        return self.db.query(Patient).filter(Patient.email == email).first()

    def create_patient(self, patient_data: PatientCreate, caregiver_id: int) -> Patient:
        """Crear nuevo paciente"""

        db_patient = Patient(
            name=patient_data.name,
            email=patient_data.email,
            phone=patient_data.phone,
            date_of_birth=patient_data.date_of_birth,
            gender=patient_data.gender,
            address=patient_data.address,
            emergency_contact=patient_data.emergency_contact.dict(),
            medical_history=patient_data.medical_history,
            allergies=patient_data.allergies,
            caregiver_id=caregiver_id,
            timezone=patient_data.timezone,
            preferred_language=patient_data.preferred_language
        )

        self.db.add(db_patient)
        self.db.commit()
        self.db.refresh(db_patient)

        logger.info(f"Paciente creado: {db_patient.name} (ID: {db_patient.id})")
        return db_patient

    def update_patient(self, patient_id: int, patient_update: PatientUpdate) -> Optional[Patient]:
        """Actualizar paciente"""

        patient = self.get_patient_by_id(patient_id)
        if not patient:
            return None

        update_data = patient_update.dict(exclude_unset=True)

        # Manejar contacto de emergencia
        if 'emergency_contact' in update_data and update_data['emergency_contact']:
            update_data['emergency_contact'] = update_data['emergency_contact'].dict()

        for field, value in update_data.items():
            if hasattr(patient, field):
                setattr(patient, field, value)

        self.db.commit()
        self.db.refresh(patient)

        logger.info(f"Paciente actualizado: {patient.name} (ID: {patient.id})")
        return patient

    def delete_patient(self, patient_id: int) -> bool:
        """Eliminar paciente"""

        patient = self.get_patient_by_id(patient_id)
        if not patient:
            return False

        self.db.delete(patient)
        self.db.commit()

        logger.info(f"Paciente eliminado: {patient.name} (ID: {patient.id})")
        return True

    def has_active_treatments(self, patient_id: int) -> bool:
        """Verificar si el paciente tiene tratamientos activos"""

        active_count = self.db.query(Treatment).filter(
            and_(
                Treatment.patient_id == patient_id,
                Treatment.status == TreatmentStatus.ACTIVE,
                Treatment.end_date >= date.today()
            )
        ).count()

        return active_count > 0

    def get_patient_treatments(self, patient_id: int) -> List[Treatment]:
        """Obtener tratamientos del paciente"""

        return self.db.query(Treatment).options(
            joinedload(Treatment.medication)
        ).filter(Treatment.patient_id == patient_id).all()

    def get_patient_active_treatments(self, patient_id: int) -> List[Treatment]:
        """Obtener tratamientos activos del paciente"""

        return self.db.query(Treatment).options(
            joinedload(Treatment.medication)
        ).filter(
            and_(
                Treatment.patient_id == patient_id,
                Treatment.status == TreatmentStatus.ACTIVE,
                Treatment.end_date >= date.today()
            )
        ).all()

    def get_patient_alerts(self, patient_id: int, unread_only: bool = False) -> List[Alert]:
        """Obtener alertas del paciente"""

        query = self.db.query(Alert).filter(Alert.patient_id == patient_id)

        if unread_only:
            query = query.filter(Alert.is_read == False)

        return query.order_by(Alert.created_at.desc()).all()

    def get_patient_compliance_report(self, patient_id: int, days: int = 30) -> dict:
        """Generar reporte de cumplimiento del paciente"""

        start_date = date.today() - timedelta(days=days)
        end_date = date.today()

        # Obtener registros de cumplimiento
        compliance_records = self.db.query(ComplianceRecord).filter(
            and_(
                ComplianceRecord.patient_id == patient_id,
                ComplianceRecord.date >= start_date,
                ComplianceRecord.date <= end_date
            )
        ).all()

        # Calcular estadísticas
        total_scheduled = sum(record.scheduled_doses for record in compliance_records)
        total_taken = sum(record.taken_doses for record in compliance_records)
        total_missed = sum(record.missed_doses for record in compliance_records)

        compliance_rate = (total_taken / total_scheduled * 100) if total_scheduled > 0 else 0

        # Obtener datos por día
        daily_compliance = []
        for record in compliance_records:
            daily_compliance.append({
                "date": record.date.isoformat(),
                "scheduled": record.scheduled_doses,
                "taken": record.taken_doses,
                "missed": record.missed_doses,
                "rate": record.compliance_rate
            })

        return {
            "patient_id": patient_id,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "summary": {
                "total_scheduled_doses": total_scheduled,
                "total_taken_doses": total_taken,
                "total_missed_doses": total_missed,
                "overall_compliance_rate": round(compliance_rate, 2)
            },
            "daily_compliance": daily_compliance
        }

    def add_patient_note(self, patient_id: int, note_data: dict, created_by: int) -> dict:
        """Agregar nota al historial del paciente"""

        # Por ahora, esto es un placeholder. En una implementación real,
        # tendrías una tabla de notas separada
        patient = self.get_patient_by_id(patient_id)
        if not patient:
            return None

        note = {
            "id": len(patient.medical_history) + 1,  # Temporal
            "content": note_data.get("content", ""),
            "note_type": note_data.get("note_type", "general"),
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat()
        }

        # Agregar a historial médico (temporal)
        if not patient.medical_history:
            patient.medical_history = []

        patient.medical_history.append(f"[{note['created_at']}] {note['content']}")
        self.db.commit()

        logger.info(f"Nota agregada al paciente {patient_id}")
        return note

    def get_patient_statistics(self, patient_id: int) -> dict:
        """Obtener estadísticas del paciente"""

        # Tratamientos
        total_treatments = self.db.query(Treatment).filter(
            Treatment.patient_id == patient_id
        ).count()

        active_treatments = self.db.query(Treatment).filter(
            and_(
                Treatment.patient_id == patient_id,
                Treatment.status == TreatmentStatus.ACTIVE,
                Treatment.end_date >= date.today()
            )
        ).count()

        completed_treatments = self.db.query(Treatment).filter(
            and_(
                Treatment.patient_id == patient_id,
                Treatment.status == TreatmentStatus.COMPLETED
            )
        ).count()

        # Dosis
        dose_stats = self.db.query(
            func.count(DoseRecord.id).label('total'),
            func.sum(func.case([(DoseRecord.status == DoseStatus.TAKEN, 1)], else_=0)).label('taken'),
            func.sum(func.case([(DoseRecord.status == DoseStatus.MISSED, 1)], else_=0)).label('missed')
        ).filter(DoseRecord.patient_id == patient_id).first()

        total_doses = dose_stats.total or 0
        taken_doses = dose_stats.taken or 0
        missed_doses = dose_stats.missed or 0

        compliance_rate = (taken_doses / total_doses * 100) if total_doses > 0 else 0

        # Última y próxima dosis
        last_dose = self.db.query(DoseRecord).filter(
            and_(
                DoseRecord.patient_id == patient_id,
                DoseRecord.status == DoseStatus.TAKEN
            )
        ).order_by(DoseRecord.actual_time.desc()).first()

        next_dose = self.db.query(DoseRecord).filter(
            and_(
                DoseRecord.patient_id == patient_id,
                DoseRecord.status == DoseStatus.PENDING,
                DoseRecord.scheduled_time > datetime.utcnow()
            )
        ).order_by(DoseRecord.scheduled_time.asc()).first()

        return {
            "treatments": {
                "total": total_treatments,
                "active": active_treatments,
                "completed": completed_treatments
            },
            "doses": {
                "total_scheduled": total_doses,
                "taken": taken_doses,
                "missed": missed_doses,
                "compliance_rate": round(compliance_rate, 2)
            },
            "timing": {
                "last_dose_time": last_dose.actual_time.isoformat() if last_dose else None,
                "next_dose_time": next_dose.scheduled_time.isoformat() if next_dose else None
            }
        }

    def search_patients(self, caregiver_id: int, query: str) -> List[Patient]:
        """Buscar pacientes por texto"""

        search_term = f"%{query.lower()}%"

        return self.db.query(Patient).filter(
            and_(
                Patient.caregiver_id == caregiver_id,
                or_(
                    func.lower(Patient.name).like(search_term),
                    func.lower(Patient.email).like(search_term),
                    func.lower(Patient.phone).like(search_term)
                )
            )
        ).all()

    def get_patients_needing_attention(self, caregiver_id: int) -> List[dict]:
        """Obtener pacientes que necesitan atención"""

        # Pacientes con alertas no leídas
        patients_with_alerts = self.db.query(Patient).join(Alert).filter(
            and_(
                Patient.caregiver_id == caregiver_id,
                Alert.is_read == False
            )
        ).distinct().all()

        # Pacientes con dosis perdidas
        patients_with_missed_doses = self.db.query(Patient).join(DoseRecord).filter(
            and_(
                Patient.caregiver_id == caregiver_id,
                DoseRecord.status == DoseStatus.MISSED,
                DoseRecord.scheduled_time >= datetime.utcnow() - timedelta(days=1)
            )
        ).distinct().all()

        attention_needed = []

        for patient in patients_with_alerts:
            unread_alerts = self.db.query(Alert).filter(
                and_(Alert.patient_id == patient.id, Alert.is_read == False)
            ).count()

            attention_needed.append({
                "patient": patient,
                "reason": "unread_alerts",
                "details": f"{unread_alerts} alertas sin leer"
            })

        for patient in patients_with_missed_doses:
            if not any(item["patient"].id == patient.id for item in attention_needed):
                missed_count = self.db.query(DoseRecord).filter(
                    and_(
                        DoseRecord.patient_id == patient.id,
                        DoseRecord.status == DoseStatus.MISSED,
                        DoseRecord.scheduled_time >= datetime.utcnow() - timedelta(days=1)
                    )
                ).count()

                attention_needed.append({
                    "patient": patient,
                    "reason": "missed_doses",
                    "details": f"{missed_count} dosis perdidas en 24h"
                })

        return attention_needed