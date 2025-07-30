# app/api/alerts.py
"""
Endpoints básicos de alertas
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_alerts():
    return {"message": "Lista de alertas - Por implementar"}