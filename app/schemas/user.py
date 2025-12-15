"""
Esquemas Pydantic para Usuario y Autenticación
"""
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


# Esquemas base
class UserBase(BaseModel):
    """Base para esquemas de usuario"""
    email: EmailStr
    name: str
    role: UserRole = UserRole.CAREGIVER
    phone: Optional[str] = None
    timezone: str = "America/Mexico_City"
    language: str = "es"
    theme: str = "light"


class UserCreate(BaseModel):
    """Esquema para crear usuario"""
    email: EmailStr
    name: str
    password: str
    confirm_password: str
    role: str = "CAREGIVER"   # ⬅️ STRING, NO ENUM
    phone: Optional[str] = None

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Las contraseñas no coinciden')
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        return v


class UserUpdate(BaseModel):
    """Esquema para actualizar usuario"""
    name: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    theme: Optional[str] = None
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None


class UserResponse(UserBase):
    """Esquema de respuesta de usuario"""
    id: int
    is_active: bool
    email_notifications: bool
    sms_notifications: bool
    push_notifications: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """Esquema de perfil de usuario"""
    id: int
    email: str
    name: str
    role: UserRole
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: str
    language: str
    theme: str
    email_notifications: bool
    sms_notifications: bool
    push_notifications: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


# Esquemas de autenticación
class LoginRequest(BaseModel):
    """Esquema para login"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Esquema de respuesta de login"""
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


class TokenData(BaseModel):
    """Datos del token"""
    user_id: Optional[int] = None
    email: Optional[str] = None


class PasswordChange(BaseModel):
    """Esquema para cambio de contraseña"""
    current_password: str
    new_password: str
    confirm_password: str

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        return v


class PasswordReset(BaseModel):
    """Esquema para reset de contraseña"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Esquema para confirmar reset de contraseña"""
    token: str
    new_password: str
    confirm_password: str

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v


# Esquemas de configuración de usuario
class NotificationSettings(BaseModel):
    """Configuración de notificaciones"""
    email_notifications: bool = True
    sms_notifications: bool = False
    push_notifications: bool = True


class UserSettings(BaseModel):
    """Configuración general del usuario"""
    timezone: str = "America/Mexico_City"
    language: str = "es"
    theme: str = "light"
    notifications: NotificationSettings = NotificationSettings()


class UserSettingsUpdate(BaseModel):
    """Actualización de configuración"""
    timezone: Optional[str] = None
    language: Optional[str] = None
    theme: Optional[str] = None
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None