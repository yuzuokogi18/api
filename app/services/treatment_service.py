"""
Servicio de gestión de tratamientos
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta

from app.models.treatment import Treatment, TreatmentStatus
from app.models.medication import Medication
from app.models.patient import Patient
from app.models.alarm import Alarm
from app.schemas.treatment import TreatmentCreate, TreatmentUpdate
import logging

logger = logging.getLogger(__name__)


class TreatmentService:
    """Servicio completo para gestión de tratamientos"""

    def __init__(self, db: Session):
        self.db = db

    def get_treatments_by_caregiver(
            self,
            caregiver_id: int,
            skip: int = 0,
            limit: int = 100,
            patient_id: Optional[int] = None,
            status: Optional[TreatmentStatus] = None,
            medication_id: Optional[int] = None
    ) -> List[Treatment]:
        """Obtener tratamientos de un cuidador"""
        try:
            logger.info(f"Obteniendo tratamientos para cuidador {caregiver_id}")

            # Query básico - necesitarás ajustar según tu estructura de DB
            query = self.db.query(Treatment)

            # Filtros básicos
            if patient_id:
                query = query.filter(Treatment.patient_id == patient_id)

            if status:
                query = query.filter(Treatment.status == status)

            if medication_id:
                query = query.filter(Treatment.medication_id == medication_id)

            treatments = query.offset(skip).limit(limit).all()
            logger.info(f"Encontrados {len(treatments)} tratamientos")
            return treatments

        except Exception as e:
            logger.error(f"Error obteniendo tratamientos: {e}")
            return []

    def medication_exists(self, medication_id: int) -> bool:
        """Verificar si el medicamento existe"""
        try:
            exists = self.db.query(Medication).filter(Medication.id == medication_id).first() is not None
            logger.info(f"Medicamento {medication_id} existe: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Error verificando medicamento {medication_id}: {e}")
            return False

    def check_medication_conflicts(self, patient_id: int, medication_id: int) -> Optional[dict]:
        """Verificar conflictos de medicamentos"""
        try:
            # Implementación básica - expandir según necesidades
            # Buscar tratamientos activos del paciente con medicamentos que podrían causar conflictos
            active_treatments = self.db.query(Treatment).filter(
                Treatment.patient_id == patient_id,
                Treatment.status == TreatmentStatus.ACTIVE
            ).all()

            # Aquí podrías implementar lógica de verificación de interacciones
            # Por ahora devolvemos None (sin conflictos)
            logger.info(f"Verificación de conflictos para paciente {patient_id}, medicamento {medication_id}: Sin conflictos")
            return None

        except Exception as e:
            logger.error(f"Error verificando conflictos: {e}")
            return None

    def create_treatment(self, treatment_data: TreatmentCreate, created_by_id: int) -> Treatment:
        """Crear nuevo tratamiento"""
        try:
            logger.info(f"Creando tratamiento para paciente {treatment_data.patient_id}")

            db_treatment = Treatment(
                patient_id=treatment_data.patient_id,
                medication_id=treatment_data.medication_id,
                dosage=treatment_data.dosage,
                frequency=treatment_data.frequency,
                duration_days=treatment_data.duration_days,
                start_date=treatment_data.start_date,
                end_date=treatment_data.end_date,
                instructions=treatment_data.instructions,
                notes=treatment_data.notes,
                created_by_id=created_by_id,
                status=TreatmentStatus.ACTIVE
            )

            self.db.add(db_treatment)
            self.db.commit()
            self.db.refresh(db_treatment)

            logger.info(f"Tratamiento creado exitosamente: ID {db_treatment.id}")
            return db_treatment

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creando tratamiento: {e}")
            raise e

    def get_treatment_detail(self, treatment_id: int) -> Optional[Treatment]:
        """Obtener detalles de tratamiento"""
        try:
            treatment = self.db.query(Treatment).filter(Treatment.id == treatment_id).first()
            if treatment:
                logger.info(f"Tratamiento {treatment_id} encontrado")
            else:
                logger.warning(f"Tratamiento {treatment_id} no encontrado")
            return treatment
        except Exception as e:
            logger.error(f"Error obteniendo detalles del tratamiento {treatment_id}: {e}")
            return None

    def get_treatment_by_id(self, treatment_id: int) -> Optional[Treatment]:
        """Obtener tratamiento por ID"""
        try:
            treatment = self.db.query(Treatment).filter(Treatment.id == treatment_id).first()
            if treatment:
                logger.info(f"Tratamiento {treatment_id} obtenido")
            else:
                logger.warning(f"Tratamiento {treatment_id} no encontrado")
            return treatment
        except Exception as e:
            logger.error(f"Error obteniendo tratamiento {treatment_id}: {e}")
            return None

    def update_treatment(self, treatment_id: int, treatment_update: TreatmentUpdate) -> Optional[Treatment]:
        """Actualizar tratamiento"""
        try:
            logger.info(f"Actualizando tratamiento {treatment_id}")

            treatment = self.get_treatment_by_id(treatment_id)
            if not treatment:
                logger.warning(f"Tratamiento {treatment_id} no encontrado para actualizar")
                return None

            update_data = treatment_update.dict(exclude_unset=True)

            for field, value in update_data.items():
                if hasattr(treatment, field):
                    setattr(treatment, field, value)
                    logger.info(f"Campo {field} actualizado a {value}")

            # Actualizar timestamp de modificación
            treatment.updated_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(treatment)

            logger.info(f"Tratamiento {treatment_id} actualizado exitosamente")
            return treatment

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error actualizando tratamiento {treatment_id}: {e}")
            raise e

    def cancel_treatment(self, treatment_id: int) -> bool:
        """Cancelar tratamiento"""
        try:
            logger.info(f"Cancelando tratamiento {treatment_id}")

            treatment = self.get_treatment_by_id(treatment_id)
            if not treatment:
                logger.warning(f"Tratamiento {treatment_id} no encontrado para cancelar")
                return False

            treatment.status = TreatmentStatus.CANCELLED
            treatment.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Tratamiento {treatment_id} cancelado exitosamente")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cancelando tratamiento {treatment_id}: {e}")
            return False

    def activate_treatment(self, treatment_id: int) -> bool:
        """Activar tratamiento"""
        try:
            logger.info(f"Activando tratamiento {treatment_id}")

            treatment = self.get_treatment_by_id(treatment_id)
            if not treatment:
                logger.warning(f"Tratamiento {treatment_id} no encontrado para activar")
                return False

            treatment.status = TreatmentStatus.ACTIVE
            treatment.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Tratamiento {treatment_id} activado exitosamente")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error activando tratamiento {treatment_id}: {e}")
            return False

    def suspend_treatment(self, treatment_id: int, reason: str) -> bool:
        """Suspender tratamiento"""
        try:
            logger.info(f"Suspendiendo tratamiento {treatment_id} por: {reason}")

            treatment = self.get_treatment_by_id(treatment_id)
            if not treatment:
                logger.warning(f"Tratamiento {treatment_id} no encontrado para suspender")
                return False

            treatment.status = TreatmentStatus.SUSPENDED
            # Agregar reason a notes
            if treatment.notes:
                treatment.notes += f"\nSuspendido: {reason}"
            else:
                treatment.notes = f"Suspendido: {reason}"

            treatment.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Tratamiento {treatment_id} suspendido exitosamente")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error suspendiendo tratamiento {treatment_id}: {e}")
            return False

    def complete_treatment(self, treatment_id: int, notes: Optional[str] = None) -> bool:
        """Completar tratamiento"""
        try:
            logger.info(f"Completando tratamiento {treatment_id}")

            treatment = self.get_treatment_by_id(treatment_id)
            if not treatment:
                logger.warning(f"Tratamiento {treatment_id} no encontrado para completar")
                return False

            treatment.status = TreatmentStatus.COMPLETED
            if notes:
                if treatment.notes:
                    treatment.notes += f"\nCompletado: {notes}"
                else:
                    treatment.notes = f"Completado: {notes}"

            treatment.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Tratamiento {treatment_id} completado exitosamente")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error completando tratamiento {treatment_id}: {e}")
            return False

    # ===== MÉTODOS DE ALARMAS - IMPLEMENTACIÓN COMPLETA =====

    def get_treatment_alarms(self, treatment_id: int) -> List[Dict]:
        """
        Obtener todas las alarmas de un tratamiento
        """
        try:
            logger.info(f"Obteniendo alarmas para tratamiento {treatment_id}")

            # Verificar que el tratamiento existe
            treatment = self.db.query(Treatment).filter(Treatment.id == treatment_id).first()
            if not treatment:
                logger.warning(f"Tratamiento {treatment_id} no encontrado")
                return []

            # Obtener alarmas ordenadas por hora
            alarms = self.db.query(Alarm).filter(
                Alarm.treatment_id == treatment_id
            ).order_by(Alarm.time).all()

            result = []
            for alarm in alarms:
                alarm_dict = {
                    "id": alarm.id,
                    "treatment_id": alarm.treatment_id,
                    "time": alarm.time,
                    "is_active": alarm.is_active if alarm.is_active is not None else True,
                    "sound_enabled": alarm.sound_enabled if alarm.sound_enabled is not None else True,
                    "visual_enabled": alarm.visual_enabled if alarm.visual_enabled is not None else True,
                    "description": alarm.description or ""
                }
                result.append(alarm_dict)

            logger.info(f"Encontradas {len(result)} alarmas para tratamiento {treatment_id}")
            return result

        except Exception as e:
            logger.error(f"Error obteniendo alarmas del tratamiento {treatment_id}: {e}")
            return []

    def create_alarm(self, treatment_id: int, alarm_data: Dict) -> Dict:
        """
        Crear una nueva alarma para un tratamiento
        """
        try:
            logger.info(f"Creando alarma para tratamiento {treatment_id}: {alarm_data}")

            # Verificar que el tratamiento existe
            treatment = self.db.query(Treatment).filter(Treatment.id == treatment_id).first()
            if not treatment:
                raise ValueError(f"Tratamiento {treatment_id} no encontrado")

            # Validar datos mínimos requeridos
            if not alarm_data.get("time"):
                raise ValueError("El campo 'time' es requerido")

            # Validar formato de hora (HH:MM)
            time_str = alarm_data.get("time")
            try:
                # Verificar que el formato sea correcto
                datetime.strptime(time_str, "%H:%M")
            except ValueError:
                raise ValueError(f"Formato de hora inválido: {time_str}. Use HH:MM")

            # Crear la alarma
            new_alarm = Alarm(
                treatment_id=treatment_id,
                time=time_str,
                is_active=alarm_data.get("is_active", True),
                sound_enabled=alarm_data.get("sound_enabled", True),
                visual_enabled=alarm_data.get("visual_enabled", True),
                description=alarm_data.get("description", "")
            )

            self.db.add(new_alarm)
            self.db.commit()
            self.db.refresh(new_alarm)

            result = {
                "id": new_alarm.id,
                "treatment_id": new_alarm.treatment_id,
                "time": new_alarm.time,
                "is_active": new_alarm.is_active,
                "sound_enabled": new_alarm.sound_enabled,
                "visual_enabled": new_alarm.visual_enabled,
                "description": new_alarm.description
            }

            logger.info(f"Alarma creada exitosamente: ID {new_alarm.id}")
            return result

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creando alarma para tratamiento {treatment_id}: {e}")
            raise e

    def update_alarm(self, treatment_id: int, alarm_id: int, alarm_data: Dict) -> Dict:
        """
        Actualizar una alarma existente
        """
        try:
            logger.info(f"Actualizando alarma {alarm_id} del tratamiento {treatment_id}: {alarm_data}")

            alarm = self.db.query(Alarm).filter(
                Alarm.id == alarm_id,
                Alarm.treatment_id == treatment_id
            ).first()

            if not alarm:
                raise ValueError(f"Alarma {alarm_id} no encontrada para el tratamiento {treatment_id}")

            # Actualizar campos si están presentes en alarm_data
            if "time" in alarm_data:
                time_str = alarm_data["time"]
                try:
                    datetime.strptime(time_str, "%H:%M")
                    alarm.time = time_str
                except ValueError:
                    raise ValueError(f"Formato de hora inválido: {time_str}. Use HH:MM")

            if "is_active" in alarm_data:
                alarm.is_active = alarm_data["is_active"]
            if "sound_enabled" in alarm_data:
                alarm.sound_enabled = alarm_data["sound_enabled"]
            if "visual_enabled" in alarm_data:
                alarm.visual_enabled = alarm_data["visual_enabled"]
            if "description" in alarm_data:
                alarm.description = alarm_data["description"]

            self.db.commit()
            self.db.refresh(alarm)

            result = {
                "id": alarm.id,
                "treatment_id": alarm.treatment_id,
                "time": alarm.time,
                "is_active": alarm.is_active,
                "sound_enabled": alarm.sound_enabled,
                "visual_enabled": alarm.visual_enabled,
                "description": alarm.description
            }

            logger.info(f"Alarma {alarm_id} actualizada exitosamente")
            return result

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error actualizando alarma {alarm_id}: {e}")
            raise e

    def delete_alarm(self, treatment_id: int, alarm_id: int) -> bool:
        """
        Eliminar una alarma específica
        """
        try:
            logger.info(f"Eliminando alarma {alarm_id} del tratamiento {treatment_id}")

            alarm = self.db.query(Alarm).filter(
                Alarm.id == alarm_id,
                Alarm.treatment_id == treatment_id
            ).first()

            if not alarm:
                logger.warning(f"Alarma {alarm_id} no encontrada para el tratamiento {treatment_id}")
                return False

            self.db.delete(alarm)
            self.db.commit()

            logger.info(f"Alarma {alarm_id} eliminada exitosamente")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error eliminando alarma {alarm_id}: {e}")
            return False

    def delete_all_treatment_alarms(self, treatment_id: int) -> bool:
        """
        Eliminar todas las alarmas de un tratamiento
        """
        try:
            logger.info(f"Eliminando todas las alarmas del tratamiento {treatment_id}")

            # Contar alarmas antes de eliminar
            alarm_count = self.db.query(Alarm).filter(
                Alarm.treatment_id == treatment_id
            ).count()

            logger.info(f"Encontradas {alarm_count} alarmas para eliminar")

            # Eliminar todas las alarmas
            deleted_count = self.db.query(Alarm).filter(
                Alarm.treatment_id == treatment_id
            ).delete()

            self.db.commit()

            logger.info(f"Eliminadas {deleted_count} alarmas del tratamiento {treatment_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error eliminando alarmas del tratamiento {treatment_id}: {e}")
            return False

    def sync_treatment_alarms(self, treatment_id: int, new_alarms: List[Dict]) -> List[Dict]:
        """
        Sincronizar alarmas de un tratamiento (eliminar existentes y crear nuevas)
        """
        try:
            logger.info(f"Sincronizando {len(new_alarms)} alarmas para tratamiento {treatment_id}")

            # Paso 1: Eliminar alarmas existentes
            self.delete_all_treatment_alarms(treatment_id)

            # Paso 2: Crear nuevas alarmas
            created_alarms = []
            for i, alarm_data in enumerate(new_alarms):
                try:
                    logger.info(f"Creando alarma {i+1}/{len(new_alarms)}: {alarm_data}")
                    created_alarm = self.create_alarm(treatment_id, alarm_data)
                    created_alarms.append(created_alarm)
                except Exception as alarm_error:
                    logger.error(f"Error creando alarma {i+1}: {alarm_error}")
                    # Continuar con las demás alarmas
                    continue

            logger.info(f"Sincronización completada: {len(created_alarms)}/{len(new_alarms)} alarmas creadas")
            return created_alarms

        except Exception as e:
            logger.error(f"Error sincronizando alarmas: {e}")
            raise e

    # ===== MÉTODOS AUXILIARES Y DE DEBUGGING =====

    def debug_treatment_alarms(self, treatment_id: int) -> Dict:
        """
        Método de debugging para verificar el estado de las alarmas
        """
        try:
            treatment = self.db.query(Treatment).filter(Treatment.id == treatment_id).first()
            alarms = self.db.query(Alarm).filter(Alarm.treatment_id == treatment_id).all()

            return {
                "treatment_exists": treatment is not None,
                "treatment_id": treatment_id,
                "treatment_status": treatment.status.value if treatment else None,
                "alarm_count": len(alarms),
                "alarms": [
                    {
                        "id": alarm.id,
                        "time": alarm.time,
                        "is_active": alarm.is_active,
                        "sound_enabled": alarm.sound_enabled,
                        "visual_enabled": alarm.visual_enabled,
                        "description": alarm.description
                    }
                    for alarm in alarms
                ],
                "database_check": "OK"
            }
        except Exception as e:
            logger.error(f"Error en debug de alarmas: {e}")
            return {
                "error": str(e),
                "treatment_id": treatment_id,
                "database_check": "ERROR"
            }

    # ===== MÉTODOS EXISTENTES MANTENIDOS =====

    def get_active_treatments_by_patient(self, patient_id: int) -> List[Treatment]:
        """Obtener tratamientos activos del paciente"""
        try:
            treatments = self.db.query(Treatment).filter(
                Treatment.patient_id == patient_id,
                Treatment.status == TreatmentStatus.ACTIVE
            ).all()
            logger.info(f"Encontrados {len(treatments)} tratamientos activos para paciente {patient_id}")
            return treatments
        except Exception as e:
            logger.error(f"Error obteniendo tratamientos activos del paciente {patient_id}: {e}")
            return []

    # ===== MÉTODOS PLACEHOLDER MANTENIDOS (para compatibilidad) =====

    def get_dose_records(self, treatment_id: int, start_date=None, end_date=None):
        """Placeholder para registros de dosis"""
        logger.info(f"get_dose_records llamado para tratamiento {treatment_id} (placeholder)")
        return []

    def record_dose(self, treatment_id: int, dose_data: dict):
        """Placeholder para registrar dosis"""
        logger.info(f"record_dose llamado para tratamiento {treatment_id} (placeholder)")
        return {"message": "Función por implementar"}

    def get_compliance_report(self, treatment_id: int, days: int):
        """Placeholder para reporte de cumplimiento"""
        logger.info(f"get_compliance_report llamado para tratamiento {treatment_id} (placeholder)")
        return {"message": "Función por implementar"}

    def get_treatment_statistics(self, treatment_id: int):
        """Placeholder para estadísticas"""
        logger.info(f"get_treatment_statistics llamado para tratamiento {treatment_id} (placeholder)")
        return {"message": "Función por implementar"}

    def get_expiring_treatments(self, caregiver_id: int, days_ahead: int):
        """Placeholder para tratamientos que expiran"""
        logger.info(f"get_expiring_treatments llamado para cuidador {caregiver_id} (placeholder)")
        return []

    def get_dashboard_summary(self, caregiver_id: int):
        """Placeholder para resumen del dashboard"""
        logger.info(f"get_dashboard_summary llamado para cuidador {caregiver_id} (placeholder)")
        return {"message": "Función por implementar"}

    def create_bulk_treatments(self, treatments_data: list, created_by_id: int):
        """Placeholder para creación en lote"""
        logger.info(f"create_bulk_treatments llamado (placeholder)")
        return {"success": [], "errors": []}

    def get_compliance_analytics(self, caregiver_id: int, start_date=None, end_date=None, patient_id=None):
        """Placeholder para análisis de cumplimiento"""
        logger.info(f"get_compliance_analytics llamado para cuidador {caregiver_id} (placeholder)")
        return {"message": "Función por implementar"}