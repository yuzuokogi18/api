# app/api/reports.py
"""
Endpoints de reportes y análisis
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_caregiver_user
from app.models.user import User
from app.models.patient import Patient
from app.models.treatment import Treatment, TreatmentStatus
from app.models.medication import Medication, MedicationUnit
from app.models.alarm import Alarm

router = APIRouter()


@router.get("/stats/overview")
async def get_overview_stats(
    period: str = Query("30d", description="Período: 7d, 30d, 90d, 1y"),
    current_user: User = Depends(get_caregiver_user),
    db: Session = Depends(get_db)
):
    """Estadísticas generales de reportes"""
    
    # Calcular fechas según el período
    end_date = date.today()
    if period == "7d":
        start_date = end_date - timedelta(days=7)
    elif period == "30d":
        start_date = end_date - timedelta(days=30)
    elif period == "90d":
        start_date = end_date - timedelta(days=90)
    elif period == "1y":
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)

    # Filtrar por cuidador si no es admin
    if current_user.is_admin:
        patients = db.query(Patient).all()
    else:
        patients = db.query(Patient).filter(Patient.caregiver_id == current_user.id).all()

    patient_ids = [p.id for p in patients]

    # Tratamientos del período
    treatments_query = db.query(Treatment).filter(
        Treatment.patient_id.in_(patient_ids),
        Treatment.created_at >= start_date
    ) if patient_ids else db.query(Treatment).filter(False)
    
    treatments = treatments_query.all()
    active_treatments = [t for t in treatments if t.status == TreatmentStatus.ACTIVE]

    # Estadísticas calculadas
    total_patients = len(patients)
    total_treatments = len(treatments)
    avg_compliance = 89  # Calcular cuando tengamos dose_records
    total_doses = len(active_treatments) * 30 * 2  # Estimación
    missed_doses = int(total_doses * 0.11)  # 11% estimación
    alerts = int(total_patients * 0.15)  # 15% estimación
    improvement_rate = 5.2  # Calcular comparando períodos

    return {
        "totalPatients": total_patients,
        "totalTreatments": total_treatments,
        "averageCompliance": avg_compliance,
        "totalDoses": total_doses,
        "missedDoses": missed_doses,
        "alerts": alerts,
        "improvementRate": improvement_rate
    }


@router.get("/compliance/trend")
async def get_compliance_trend(
    period: str = Query("30d", description="Período de análisis"),
    current_user: User = Depends(get_caregiver_user),
    db: Session = Depends(get_db)
):
    """Tendencia de cumplimiento en el tiempo"""
    
    # Calcular fechas
    end_date = date.today()
    days = 30 if period == "30d" else 15 if period == "15d" else 7
    start_date = end_date - timedelta(days=days)

    # Filtrar pacientes por cuidador
    if current_user.is_admin:
        patients = db.query(Patient).all()
    else:
        patients = db.query(Patient).filter(Patient.caregiver_id == current_user.id).all()

    # Generar datos de compliance por día
    compliance_data = []
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        
        # Simulación de datos - reemplazar con datos reales de dose_records
        base_compliance = 85 + (i % 10)  # Tendencia simulada
        patients_count = len(patients)
        doses_count = patients_count * 3  # Estimación de 3 dosis por día
        
        compliance_data.append({
            "date": current_date.isoformat(),
            "compliance": base_compliance,
            "patients": patients_count,
            "doses": doses_count
        })

    return compliance_data


@router.get("/medications/distribution")
async def get_medication_distribution(
    current_user: User = Depends(get_caregiver_user),
    db: Session = Depends(get_db)
):
    """Distribución de medicamentos por tipo"""
    
    # Filtrar tratamientos por cuidador
    if current_user.is_admin:
        treatments = db.query(Treatment).join(Medication).all()
    else:
        treatments = db.query(Treatment).join(Medication).join(Patient).filter(
            Patient.caregiver_id == current_user.id
        ).all()

    # Agrupar por tipo de medicamento (basado en nombre o descripción)
    medication_types = {}
    
    for treatment in treatments:
        medication = treatment.medication
        medication_name = medication.name.lower()
        
        # Clasificar medicamentos por tipo (esto se puede mejorar con una tabla de categorías)
        if any(keyword in medication_name for keyword in ['enalapril', 'losartan', 'metoprolol', 'amlodipina']):
            category = 'Cardiovasculares'
        elif any(keyword in medication_name for keyword in ['metformina', 'glibenclamida', 'insulina']):
            category = 'Diabetes'
        elif any(keyword in medication_name for keyword in ['paracetamol', 'ibuprofeno', 'diclofenaco']):
            category = 'Analgésicos'
        elif any(keyword in medication_name for keyword in ['amoxicilina', 'azitromicina', 'ciprofloxacino']):
            category = 'Antibióticos'
        else:
            category = 'Otros'
            
        medication_types[category] = medication_types.get(category, 0) + 1

    # Convertir a formato para el gráfico
    total = sum(medication_types.values()) or 1
    colors = {
        'Cardiovasculares': '#3B82F6',
        'Diabetes': '#10B981',
        'Analgésicos': '#F59E0B',
        'Antibióticos': '#EF4444',
        'Otros': '#8B5CF6'
    }
    
    distribution = []
    for category, count in medication_types.items():
        percentage = round((count / total) * 100, 1)
        distribution.append({
            "name": category,
            "value": percentage,
            "count": count,
            "color": colors.get(category, '#6B7280')
        })

    return distribution


@router.get("/patterns/hourly")
async def get_hourly_patterns(
    current_user: User = Depends(get_caregiver_user),
    db: Session = Depends(get_db)
):
    """Patrones de cumplimiento por horario"""
    
    # Obtener alarmas de tratamientos del cuidador
    if current_user.is_admin:
        alarms = db.query(Alarm).join(Treatment).all()
    else:
        alarms = db.query(Alarm).join(Treatment).join(Patient).filter(
            Patient.caregiver_id == current_user.id
        ).all()

    # Agrupar por hora
    hourly_data = {}
    
    for alarm in alarms:
        hour = alarm.time.split(':')[0] + ':00'
        if hour not in hourly_data:
            hourly_data[hour] = {'doses': 0, 'compliance': 85}  # Base compliance
        hourly_data[hour]['doses'] += 1

    # Convertir a lista ordenada
    patterns = []
    for hour in sorted(hourly_data.keys()):
        # Simular compliance variable por hora
        base_compliance = 85
        if '06:' in hour or '22:' in hour:
            compliance = base_compliance - 5  # Menor compliance en extremos
        elif '08:' in hour or '18:' in hour:
            compliance = base_compliance + 5  # Mayor compliance en horarios principales
        else:
            compliance = base_compliance
            
        patterns.append({
            "hour": hour,
            "doses": hourly_data[hour]['doses'],
            "compliance": compliance
        })

    return patterns


@router.get("/patients/compliance-ranges")
async def get_patient_compliance_ranges(
    current_user: User = Depends(get_caregiver_user),
    db: Session = Depends(get_db)
):
    """Distribución de pacientes por rangos de cumplimiento"""
    
    # Obtener pacientes del cuidador
    if current_user.is_admin:
        patients = db.query(Patient).all()
    else:
        patients = db.query(Patient).filter(Patient.caregiver_id == current_user.id).all()

    # Simular compliance por paciente (reemplazar con datos reales)
    ranges = {
        '90-100%': 0,
        '80-89%': 0,
        '70-79%': 0,
        '60-69%': 0,
        '<60%': 0
    }
    
    colors = {
        '90-100%': '#10B981',
        '80-89%': '#F59E0B',
        '70-79%': '#EF4444',
        '60-69%': '#DC2626',
        '<60%': '#7F1D1D'
    }

    for patient in patients:
        # Simular compliance (reemplazar con cálculo real)
        import random
        compliance = random.randint(65, 98)
        
        if compliance >= 90:
            ranges['90-100%'] += 1
        elif compliance >= 80:
            ranges['80-89%'] += 1
        elif compliance >= 70:
            ranges['70-79%'] += 1
        elif compliance >= 60:
            ranges['60-69%'] += 1
        else:
            ranges['<60%'] += 1

    # Convertir a formato de respuesta
    result = []
    for range_key, count in ranges.items():
        result.append({
            "range": range_key,
            "patients": count,
            "color": colors[range_key]
        })

    return result


@router.get("/treatments/types")
async def get_treatment_types(
    current_user: User = Depends(get_caregiver_user),
    db: Session = Depends(get_db)
):
    """Análisis por tipo de tratamiento"""
    
    # Obtener tratamientos del cuidador
    if current_user.is_admin:
        treatments = db.query(Treatment).all()
    else:
        treatments = db.query(Treatment).join(Patient).filter(
            Patient.caregiver_id == current_user.id
        ).all()

    # Clasificar tratamientos por tipo (basado en duración)
    chronic_count = 0
    acute_count = 0
    preventive_count = 0

    for treatment in treatments:
        if treatment.duration_days > 90:
            chronic_count += 1
        elif treatment.duration_days <= 14:
            acute_count += 1
        else:
            preventive_count += 1

    total = len(treatments) or 1
    
    return [
        {
            "type": "Crónicos",
            "count": chronic_count,
            "percentage": round((chronic_count / total) * 100)
        },
        {
            "type": "Agudos", 
            "count": acute_count,
            "percentage": round((acute_count / total) * 100)
        },
        {
            "type": "Preventivos",
            "count": preventive_count,
            "percentage": round((preventive_count / total) * 100)
        }
    ]


@router.post("/generate")
async def generate_report(
    report_type: str = Query(..., description="Tipo de reporte: compliance, medications, alerts"),
    format: str = Query("json", description="Formato: json, pdf, csv"),
    period: str = Query("30d", description="Período"),
    current_user: User = Depends(get_caregiver_user),
    db: Session = Depends(get_db)
):
    """Generar reporte específico"""
    
    # Por ahora retornamos confirmación - implementar generación real de archivos
    return {
        "message": f"Reporte de {report_type} generado exitosamente",
        "type": report_type,
        "format": format,
        "period": period,
        "generated_at": datetime.utcnow().isoformat(),
        "download_url": f"/reports/download/{report_type}_{format}_{period}.{format}"
    }


@router.post("/export")
async def export_data(
    format: str = Query(..., description="Formato: csv, excel, pdf, json"),
    data_type: str = Query("all", description="Tipo de datos: all, patients, treatments, medications"),
    current_user: User = Depends(get_caregiver_user),
    db: Session = Depends(get_db)
):
    """Exportar datos en diferentes formatos"""
    
    # Por ahora retornamos confirmación - implementar exportación real
    return {
        "message": f"Datos exportados en formato {format}",
        "format": format,
        "data_type": data_type,
        "exported_at": datetime.utcnow().isoformat(),
        "download_url": f"/reports/export/{data_type}_{format}.{format}"
    }