"""
Endpoints de autenticación
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserResponse, LoginRequest, LoginResponse,
    PasswordChange, PasswordReset, UserProfile
)
from app.services.auth_service import AuthService

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
        user_data: UserCreate,
        db: Session = Depends(get_db)
):
    """
    Registrar nuevo usuario
    """
    auth_service = AuthService(db)

    # Verificar si el email ya existe
    if auth_service.get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )

    # Crear usuario
    user = auth_service.create_user(user_data)
    return user


@router.post("/login", response_model=LoginResponse)
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    """
    Login de usuario
    """
    auth_service = AuthService(db)

    # Verificar credenciales
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )

    # Actualizar último login
    auth_service.update_last_login(user.id)

    # Crear token
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
        current_user: User = Depends(get_current_user)
):
    """
    Obtener perfil del usuario actual
    """
    return current_user


@router.put("/me", response_model=UserProfile)
async def update_profile(
        user_update: dict,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Actualizar perfil del usuario
    """
    auth_service = AuthService(db)
    updated_user = auth_service.update_user(current_user.id, user_update)
    return updated_user


@router.post("/change-password")
async def change_password(
        password_data: PasswordChange,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Cambiar contraseña del usuario
    """
    auth_service = AuthService(db)

    # Verificar contraseña actual
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta"
        )

    # Actualizar contraseña
    auth_service.update_password(current_user.id, password_data.new_password)

    return {"message": "Contraseña actualizada exitosamente"}


@router.post("/forgot-password")
async def forgot_password(
        reset_data: PasswordReset,
        db: Session = Depends(get_db)
):
    """
    Solicitar reset de contraseña
    """
    auth_service = AuthService(db)

    # Verificar que el usuario existe
    user = auth_service.get_user_by_email(reset_data.email)
    if not user:
        # Por seguridad, no revelamos si el email existe o no
        return {"message": "Si el email existe, recibirás instrucciones para resetear tu contraseña"}

    # Generar token de reset (implementar según necesidades)
    # auth_service.generate_reset_token(user.id)

    # Enviar email (implementar según necesidades)
    # await send_password_reset_email(user.email, reset_token)

    return {"message": "Si el email existe, recibirás instrucciones para resetear tu contraseña"}


@router.post("/logout")
async def logout(
        current_user: User = Depends(get_current_user)
):
    """
    Logout del usuario
    """
    # En un sistema stateless con JWT, el logout se maneja en el frontend
    # eliminando el token. Aquí podríamos agregar el token a una blacklist
    return {"message": "Logout exitoso"}


@router.get("/verify-token")
async def verify_token(
        current_user: User = Depends(get_current_user)
):
    """
    Verificar si el token es válido
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role
    }


# Endpoints administrativos
@router.get("/users", response_model=list[UserResponse])
async def list_users(
        skip: int = 0,
        limit: int = 100,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Listar usuarios (solo admins)
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a esta información"
        )

    auth_service = AuthService(db)
    users = auth_service.get_users(skip=skip, limit=limit)
    return users


@router.put("/users/{user_id}/activate")
async def activate_user(
        user_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Activar/desactivar usuario (solo admins)
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar esta acción"
        )

    auth_service = AuthService(db)
    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    auth_service.toggle_user_status(user_id)
    return {"message": f"Usuario {'activado' if not user.is_active else 'desactivado'} exitosamente"}