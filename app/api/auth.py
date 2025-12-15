"""
Endpoints de autenticación
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.dependencies import get_current_user
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate, UserResponse, LoginResponse,
    PasswordChange, PasswordReset, UserProfile
)
from app.services.auth_service import AuthService

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


# =========================
# REGISTER
# =========================
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

    # 🔥 NORMALIZAR ROLE (a MAYÚSCULAS DEL ENUM)
    try:
        user_data.role = UserRole[user_data.role.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rol inválido"
        )

    # Crear usuario
    user = auth_service.create_user(user_data)
    return user


# =========================
# LOGIN
# =========================
@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login de usuario
    """
    auth_service = AuthService(db)

    user = auth_service.authenticate_user(
        form_data.username,
        form_data.password
    )

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

    auth_service.update_last_login(user.id)

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


# =========================
# PERFIL
# =========================
@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.put("/me", response_model=UserProfile)
async def update_profile(
    user_update: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)
    return auth_service.update_user(current_user.id, user_update)


# =========================
# PASSWORD
# =========================
@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)

    if not verify_password(
        password_data.current_password,
        current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta"
        )

    auth_service.update_password(
        current_user.id,
        password_data.new_password
    )

    return {"message": "Contraseña actualizada exitosamente"}


# =========================
# PASSWORD RESET
# =========================
@router.post("/forgot-password")
async def forgot_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)

    user = auth_service.get_user_by_email(reset_data.email)

    return {
        "message": "Si el email existe, recibirás instrucciones para resetear tu contraseña"
    }


# =========================
# LOGOUT
# =========================
@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    return {"message": "Logout exitoso"}


# =========================
# VERIFY TOKEN
# =========================
@router.get("/verify-token")
async def verify_token(
    current_user: User = Depends(get_current_user)
):
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role.value
    }


# =========================
# ADMIN
# =========================
@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos"
        )

    auth_service = AuthService(db)
    return auth_service.get_users(skip=skip, limit=limit)
