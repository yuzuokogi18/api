# app/api/settings.py
"""
Endpoints básicos de configuración
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_settings():
    return {"message": "Configuración - Por implementar"}