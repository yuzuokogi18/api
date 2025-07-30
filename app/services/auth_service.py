"""
Servicio de autenticación
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password


class AuthService:
    """Servicio para manejo de autenticación"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Obtener usuario por email"""
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Obtener usuario por ID"""
        return self.db.query(User).filter(User.id == user_id).first()

    def create_user(self, user_data: UserCreate) -> User:
        """Crear nuevo usuario"""
        hashed_password = get_password_hash(user_data.password)

        db_user = User(
            email=user_data.email,
            name=user_data.name,
            hashed_password=hashed_password,
            role=user_data.role,
            phone=user_data.phone
        )

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        return db_user

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Autenticar usuario"""
        user = self.get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def update_last_login(self, user_id: int):
        """Actualizar último login"""
        user = self.get_user_by_id(user_id)
        if user:
            user.last_login = datetime.utcnow()
            self.db.commit()

    def update_user(self, user_id: int, user_data: dict) -> Optional[User]:
        """Actualizar usuario"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        for field, value in user_data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    def update_password(self, user_id: int, new_password: str):
        """Actualizar contraseña"""
        user = self.get_user_by_id(user_id)
        if user:
            user.hashed_password = get_password_hash(new_password)
            self.db.commit()

    def get_users(self, skip: int = 0, limit: int = 100):
        """Obtener lista de usuarios"""
        return self.db.query(User).offset(skip).limit(limit).all()

    def toggle_user_status(self, user_id: int):
        """Activar/desactivar usuario"""
        user = self.get_user_by_id(user_id)
        if user:
            user.is_active = not user.is_active
            self.db.commit()