"""
Servicio de gestión de medicamentos
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.medication import Medication, MedicationUnit
from app.models.treatment import Treatment, TreatmentStatus
from app.models.patient import Patient
from app.schemas.medication import MedicationCreate, MedicationUpdate
import logging

logger = logging.getLogger(__name__)


class MedicationService:
    """Servicio para gestión de medicamentos"""

    def __init__(self, db: Session):
        self.db = db

    def get_medications(
            self,
            skip: int = 0,
            limit: int = 100,
            search: Optional[str] = None,
            unit: Optional[MedicationUnit] = None
    ) -> List[Medication]:
        """Obtener medicamentos con filtros"""

        query = self.db.query(Medication)

        # Filtro de búsqueda
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Medication.name).like(search_term),
                    func.lower(Medication.brand_name).like(search_term),
                    func.lower(Medication.generic_name).like(search_term),
                    func.lower(Medication.description).like(search_term)
                )
            )

        # Filtro por unidad
        if unit:
            query = query.filter(Medication.unit == unit)

        return query.order_by(Medication.name).offset(skip).limit(limit).all()

    def get_medication_by_id(self, medication_id: int) -> Optional[Medication]:
        """Obtener medicamento por ID"""
        return self.db.query(Medication).filter(Medication.id == medication_id).first()

    def find_similar_medication(
            self,
            name: str,
            dosage: str,
            unit: MedicationUnit
    ) -> Optional[Medication]:
        """Buscar medicamento similar"""
        return self.db.query(Medication).filter(
            and_(
                func.lower(Medication.name) == name.lower(),
                Medication.dosage == dosage,
                Medication.unit == unit
            )
        ).first()

    def create_medication(self, medication_data: MedicationCreate) -> Medication:
        """Crear nuevo medicamento"""

        db_medication = Medication(
            name=medication_data.name,
            description=medication_data.description,
            dosage=medication_data.dosage,
            unit=medication_data.unit,
            instructions=medication_data.instructions,
            side_effects=medication_data.side_effects,
            contraindications=medication_data.contraindications,
            brand_name=medication_data.brand_name,
            generic_name=medication_data.generic_name,
            manufacturer=medication_data.manufacturer
        )

        self.db.add(db_medication)
        self.db.commit()
        self.db.refresh(db_medication)

        logger.info(f"Medicamento creado: {db_medication.full_name} (ID: {db_medication.id})")
        return db_medication

    def update_medication(
            self,
            medication_id: int,
            medication_update: MedicationUpdate
    ) -> Optional[Medication]:
        """Actualizar medicamento"""

        medication = self.get_medication_by_id(medication_id)
        if not medication:
            return None

        update_data = medication_update.dict(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(medication, field):
                setattr(medication, field, value)

        self.db.commit()
        self.db.refresh(medication)

        logger.info(f"Medicamento actualizado: {medication.full_name} (ID: {medication.id})")
        return medication

    def delete_medication(self, medication_id: int) -> bool:
        """Eliminar medicamento"""

        medication = self.get_medication_by_id(medication_id)
        if not medication:
            return False

        self.db.delete(medication)
        self.db.commit()

        logger.info(f"Medicamento eliminado: {medication.full_name} (ID: {medication.id})")
        return True

    def is_medication_in_use(self, medication_id: int) -> bool:
        """Verificar si el medicamento está siendo usado en tratamientos activos"""

        active_treatments = self.db.query(Treatment).filter(
            and_(
                Treatment.medication_id == medication_id,
                Treatment.status == TreatmentStatus.ACTIVE
            )
        ).count()

        return active_treatments > 0

    def search_by_name(self, query: str, limit: int = 10) -> List[Medication]:
        """Buscar medicamentos por nombre (para autocompletado)"""

        search_term = f"%{query.lower()}%"

        return self.db.query(Medication).filter(
            or_(
                func.lower(Medication.name).like(search_term),
                func.lower(Medication.brand_name).like(search_term),
                func.lower(Medication.generic_name).like(search_term)
            )
        ).order_by(Medication.name).limit(limit).all()

    def check_interactions(
            self,
            medication_id: int,
            other_medication_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """Verificar interacciones medicamentosas"""

        # Esta es una implementación básica
        # En un sistema real, tendrías una base de datos de interacciones
        interactions = []

        medication = self.get_medication_by_id(medication_id)
        if not medication:
            return interactions

        for other_id in other_medication_ids:
            other_medication = self.get_medication_by_id(other_id)
            if other_medication:
                # Simulación de verificación de interacciones
                interaction = self._check_medication_pair(medication, other_medication)
                if interaction:
                    interactions.append(interaction)

        return interactions

    def _check_medication_pair(
            self,
            med1: Medication,
            med2: Medication
    ) -> Optional[Dict[str, Any]]:
        """Verificar interacción entre dos medicamentos específicos"""

        # Esta es una implementación de ejemplo
        # En un sistema real, consultarías una base de datos de interacciones

        # Ejemplo: medicamentos con mismo principio activo
        if (med1.generic_name and med2.generic_name and
                med1.generic_name.lower() == med2.generic_name.lower()):
            return {
                "medication1_id": med1.id,
                "medication1_name": med1.name,
                "medication2_id": med2.id,
                "medication2_name": med2.name,
                "interaction_type": "duplicate_therapy",
                "severity": "high",
                "description": "Medicamentos con el mismo principio activo",
                "recommendation": "Evitar uso simultáneo, consultar médico"
            }

        # Aquí agregarías más lógica de interacciones
        return None

    def get_medication_treatments(
            self,
            medication_id: int,
            active_only: bool = True,
            caregiver_id: Optional[int] = None
    ) -> List[Treatment]:
        """Obtener tratamientos que usan este medicamento"""

        query = self.db.query(Treatment).options(
            joinedload(Treatment.patient)
        ).filter(Treatment.medication_id == medication_id)

        if active_only:
            query = query.filter(Treatment.status == TreatmentStatus.ACTIVE)

        if caregiver_id:
            query = query.join(Patient).filter(Patient.caregiver_id == caregiver_id)

        return query.all()

    def add_side_effect(self, medication_id: int, side_effect: str):
        """Agregar efecto secundario al medicamento"""

        medication = self.get_medication_by_id(medication_id)
        if medication:
            medication.add_side_effect(side_effect)
            self.db.commit()
            logger.info(f"Efecto secundario agregado a {medication.name}: {side_effect}")

    def remove_side_effect(self, medication_id: int, side_effect: str):
        """Remover efecto secundario del medicamento"""

        medication = self.get_medication_by_id(medication_id)
        if medication:
            medication.remove_side_effect(side_effect)
            self.db.commit()
            logger.info(f"Efecto secundario removido de {medication.name}: {side_effect}")

    def add_contraindication(self, medication_id: int, contraindication: str):
        """Agregar contraindicación al medicamento"""

        medication = self.get_medication_by_id(medication_id)
        if medication:
            medication.add_contraindication(contraindication)
            self.db.commit()
            logger.info(f"Contraindicación agregada a {medication.name}: {contraindication}")

    def get_usage_statistics(self, caregiver_id: Optional[int] = None) -> Dict[str, Any]:
        """Obtener estadísticas de uso de medicamentos"""

        # Query base
        query = self.db.query(
            Medication.id,
            Medication.name,
            func.count(Treatment.id).label('total_treatments'),
            func.sum(func.case([(Treatment.status == TreatmentStatus.ACTIVE, 1)], else_=0)).label('active_treatments'),
            func.count(func.distinct(Treatment.patient_id)).label('total_patients')
        ).outerjoin(Treatment)

        if caregiver_id:
            query = query.join(Patient).filter(Patient.caregiver_id == caregiver_id)

        results = query.group_by(Medication.id, Medication.name).all()

        # Estadísticas por unidad
        unit_stats = self.db.query(
            Medication.unit,
            func.count(Medication.id).label('count')
        ).group_by(Medication.unit).all()

        # Medicamentos más prescritos
        most_prescribed = sorted(results, key=lambda x: x.total_treatments, reverse=True)[:10]

        return {
            "total_medications": len(results),
            "total_active_treatments": sum(r.active_treatments for r in results),
            "most_prescribed": [
                {
                    "medication_id": r.id,
                    "medication_name": r.name,
                    "total_treatments": r.total_treatments,
                    "active_treatments": r.active_treatments,
                    "total_patients": r.total_patients
                }
                for r in most_prescribed
            ],
            "by_unit": {
                unit.name: count for unit, count in unit_stats
            },
            "generated_at": datetime.utcnow().isoformat()
        }

    def validate_for_patient(
            self,
            medication_id: int,
            patient_id: int
    ) -> Dict[str, Any]:
        """Validar medicamento para un paciente específico"""

        medication = self.get_medication_by_id(medication_id)
        patient = self.db.query(Patient).filter(Patient.id == patient_id).first()

        if not medication or not patient:
            return {"is_safe": False, "warnings": ["Medicamento o paciente no encontrado"]}

        warnings = []
        allergies_conflict = []

        # Verificar alergias
        if patient.allergies:
            for allergy in patient.allergies:
                if (allergy.lower() in medication.name.lower() or
                        (medication.generic_name and allergy.lower() in medication.generic_name.lower())):
                    allergies_conflict.append(allergy)
                    warnings.append(f"Posible alergia a {allergy}")

        # Verificar con medicamentos actuales
        current_medications = self.db.query(Treatment).filter(
            and_(
                Treatment.patient_id == patient_id,
                Treatment.status == TreatmentStatus.ACTIVE
            )
        ).all()

        interactions = self.check_interactions(
            medication_id,
            [t.medication_id for t in current_medications]
        )

        if interactions:
            warnings.extend([f"Interacción con {i['medication2_name']}" for i in interactions])

        is_safe = len(allergies_conflict) == 0 and len([i for i in interactions if i['severity'] == 'high']) == 0

        return {
            "medication_id": medication_id,
            "patient_id": patient_id,
            "is_safe": is_safe,
            "warnings": warnings,
            "allergies_conflict": allergies_conflict,
            "interactions": interactions,
            "recommendations": self._generate_recommendations(medication, patient, warnings)
        }

    def _generate_recommendations(
            self,
            medication: Medication,
            patient: Patient,
            warnings: List[str]
    ) -> List[str]:
        """Generar recomendaciones basadas en el medicamento y paciente"""

        recommendations = []

        if warnings:
            recommendations.append("Consultar con médico antes de administrar")

        if medication.instructions:
            recommendations.append(f"Seguir instrucciones: {medication.instructions}")

        # Recomendaciones basadas en edad
        age = patient.age
        if age >= 65:
            recommendations.append("Monitorear cuidadosamente en paciente adulto mayor")
        elif age < 18:
            recommendations.append("Verificar dosis pediátrica apropiada")

        return recommendations

    def get_popular_medications(self, limit: int = 20) -> List[Medication]:
        """Obtener medicamentos más populares"""

        return self.db.query(Medication).join(Treatment).group_by(
            Medication.id
        ).order_by(
            func.count(Treatment.id).desc()
        ).limit(limit).all()

    def get_medications_by_category(self, category: str) -> List[Medication]:
        """Obtener medicamentos por categoría (basado en descripción)"""

        return self.db.query(Medication).filter(
            func.lower(Medication.description).like(f"%{category.lower()}%")
        ).all()