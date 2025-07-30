from fastapi import APIRouter

router = APIRouter()

@router.get("/dashboard")
async def dashboard():
    return {"message": "Dashboard de monitoreo - Por implementar"}