"""
Configuración de la aplicación para MySQL y AWS EC2
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field
import secrets
import os


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # Información del proyecto
    PROJECT_NAME: str = Field(default="PillCare 360 API", env="PROJECT_NAME")
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")

    # Configuración del servidor
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8081, env="PORT")  # 👈 PUERTO MODIFICADO

    # Seguridad
    SECRET_KEY: str = Field(env="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # Base de datos MySQL
    DB_HOST: str = Field(default="localhost", env="DB_HOST")
    DB_PORT: int = Field(default=3306, env="DB_PORT")
    DB_NAME: str = Field(default="pillcare360", env="DB_NAME")
    DB_USER: str = Field(env="DB_USER")
    DB_PASSWORD: str = Field(env="DB_PASSWORD")
    DB_CHARSET: str = Field(default="utf8mb4", env="DB_CHARSET")

    # Email
    EMAIL_HOST: str = Field(default="localhost", env="EMAIL_HOST")
    EMAIL_PORT: int = Field(default=587, env="EMAIL_PORT")
    EMAIL_USER: str = Field(default="", env="EMAIL_USER")
    EMAIL_PASSWORD: str = Field(default="", env="EMAIL_PASSWORD")
    FROM_EMAIL: str = Field(default="noreply@pillcare360.com", env="FROM_EMAIL")

    # AWS
    AWS_ACCESS_KEY_ID: str = Field(default="", env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = Field(default="", env="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173"
        ],
        env="CORS_ORIGINS"
    )

    # Alarmas
    ALARM_CHECK_INTERVAL: int = Field(default=60, env="ALARM_CHECK_INTERVAL")
    COMPLIANCE_THRESHOLD: float = Field(default=75.0, env="COMPLIANCE_THRESHOLD")
    MAX_SNOOZE_ATTEMPTS: int = Field(default=3, env="MAX_SNOOZE_ATTEMPTS")

    # Archivos
    UPLOAD_FOLDER: str = Field(default="uploads", env="UPLOAD_FOLDER")
    REPORTS_FOLDER: str = Field(default="reports", env="REPORTS_FOLDER")
    MAX_FILE_SIZE: int = Field(default=5*1024*1024, env="MAX_FILE_SIZE")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # Timezone
    DEFAULT_TIMEZONE: str = Field(default="America/Mexico_City", env="DEFAULT_TIMEZONE")

    @property
    def database_url(self) -> str:
        """Construir URL de conexión MySQL"""
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset={self.DB_CHARSET}"
        )

    @property
    def is_production(self) -> bool:
        """Verificar si estamos en producción"""
        return self.ENVIRONMENT.lower() == "production"

    class Config:
        env_file = "../.env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Obtener configuración con cache"""
    return Settings()
