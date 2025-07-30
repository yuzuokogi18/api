"""
Dependencias globales de la aplicación
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from typing import Optional

from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import verify_token
from app.models.user import User, UserRole
from app.services.auth_service import AuthService

settings = get_settings()

# Configurar OAuth2
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/auth/login",
    auto_error=False
)


async def get_current_user(
        token: Optional[str] = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> User:
    """
    Obtener usuario actual del token JWT
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = verify_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    auth_service = AuthService(db)
    user = auth_service.get_user_by_id(int(user_id))
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )

    return user


async def get_current_active_user(
        current_user: User = Depends(get_current_user)
) -> User:
    """
    Obtener usuario activo actual
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )
    return current_user


async def get_admin_user(
        current_user: User = Depends(get_current_user)
) -> User:
    """
    Verificar que el usuario sea administrador
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador"
        )
    return current_user


async def get_caregiver_user(
        current_user: User = Depends(get_current_user)
) -> User:
    """
    Verificar que el usuario sea cuidador o admin
    """
    if current_user.role not in [UserRole.CAREGIVER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de cuidador"
        )
    return current_user


async def get_optional_user(
        token: Optional[str] = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Obtener usuario actual si existe token, sino None
    """
    if not token:
        return None

    try:
        payload = verify_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            return None

        auth_service = AuthService(db)
        user = auth_service.get_user_by_id(int(user_id))
        return user if user and user.is_active else None
    except JWTError:
        return None


# Dependencias para validar permisos específicos
async def verify_patient_access(
        patient_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Verificar que el usuario tenga acceso al paciente
    """
    # Los admins tienen acceso a todo
    if current_user.is_admin:
        return True

    # Los cuidadores solo pueden acceder a sus pacientes
    if current_user.role == UserRole.CAREGIVER:
        from app.models.patient import Patient
        patient = db.query(Patient).filter(
            Patient.id == patient_id,
            Patient.caregiver_id == current_user.id
        ).first()

        if not patient:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a este paciente"
            )
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permisos para acceder a esta información"
    )


async def verify_treatment_access(
        treatment_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Verificar que el usuario tenga acceso al tratamiento
    """
    # Los admins tienen acceso a todo
    if current_user.is_admin:
        return True

    # Los cuidadores solo pueden acceder a tratamientos de sus pacientes
    if current_user.role == UserRole.CAREGIVER:
        from app.models.treatment import Treatment
        from app.models.patient import Patient

        treatment = db.query(Treatment).join(Patient).filter(
            Treatment.id == treatment_id,
            Patient.caregiver_id == current_user.id
        ).first()

        if not treatment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a este tratamiento"
            )
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permisos para acceder a esta información"
    )


# Dependencias para paginación
class PaginationParams:
    def __init__(self, skip: int = 0, limit: int = 100):
        self.skip = max(0, skip)
        self.limit = min(limit, 1000)  # Máximo 1000 registros por página


def get_pagination_params(skip: int = 0, limit: int = 100) -> PaginationParams:
    """
    Parámetros de paginación
    """
    return PaginationParams(skip=skip, limit=limit)


# Dependencias para filtros comunes
class DateRangeParams:
    def __init__(
            self,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None
    ):
        from datetime import datetime, date

        self.start_date = None
        self.end_date = None

        if start_date:
            try:
                self.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de fecha inválido. Use YYYY-MM-DD"
                )

        if end_date:
            try:
                self.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de fecha inválido. Use YYYY-MM-DD"
                )

        # Validar que start_date <= end_date
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha de inicio debe ser menor o igual a la fecha de fin"
            )


def get_date_range_params(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
) -> DateRangeParams:
    """
    Parámetros de rango de fechas
    """
    return DateRangeParams(start_date=start_date, end_date=end_date)


# Middleware dependencies
def get_request_id() -> str:
    """
    Generar ID único para la request
    """
    import uuid
    return str(uuid.uuid4())


def rate_limit_key(
        current_user: Optional[User] = Depends(get_optional_user)
) -> str:
    """
    Generar clave para rate limiting
    """
    if current_user:
        return f"user:{current_user.id}"
    return "anonymous"