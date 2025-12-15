"""
Configuración de base de datos MySQL con SQLAlchemy
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import logging

# Crear Base ANTES de importar config para evitar import circular
Base = declarative_base()

# Ahora importar config
from app.core.config import get_settings

logger = logging.getLogger(__name__)

def get_settings_safe():
    """Obtener settings de forma segura"""
    try:
        return get_settings()
    except Exception as e:
        logger.warning(f"No se pudo cargar configuración: {e}")
        # Configuración por defecto para desarrollo
        class DefaultSettings:
            def __init__(self):
                  self.DB_HOST = "localhost"
                  self.DB_PORT = 3306
                  self.DB_NAME = "pillcare360"
                  self.DB_USER = "pillcare_user"
                  self.DB_PASSWORD = "password123"
                  self.DB_CHARSET = "utf8mb4"
                  self.DB_CHARSET = "utf8mb4"
                  self.DEBUG = True

            @property
            def database_url(self):
                return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset={self.DB_CHARSET}"

        return DefaultSettings()

settings = get_settings_safe()

# Configurar engine de SQLAlchemy con pool de conexiones
try:
    engine = create_engine(
        settings.database_url,
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=3600,  # Reciclar conexiones cada hora
        echo=getattr(settings, 'DEBUG', False),  # Solo mostrar SQL en debug
    )
except Exception as e:
    logger.warning(f"No se pudo crear engine: {e}")
    # Engine dummy para evitar errores
    engine = None

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None

# Metadata para operaciones de esquema
metadata = MetaData()


def get_db():
    """
    Dependency para obtener sesión de base de datos
    """
    if not SessionLocal:
        raise Exception("Base de datos no configurada")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Crear todas las tablas si no existen
    """
    if not engine:
        raise Exception("Engine de base de datos no configurado")

    try:
        # Importar todos los modelos para que se registren
        from app.models import user, patient, medication, treatment
        # Importar modelos adicionales cuando los crees
        try:
            from app.models import alarm, dose_record, alert, compliance
        except ImportError:
            logger.warning("Algunos modelos no están disponibles todavía")

        # Crear todas las tablas
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tablas creadas/verificadas exitosamente")

    except Exception as e:
        logger.error(f"❌ Error al crear tablas: {e}")
        raise


def drop_tables():
    """
    Eliminar todas las tablas (usar con cuidado)
    """
    if not engine:
        raise Exception("Engine de base de datos no configurado")

    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("⚠️ Todas las tablas han sido eliminadas")
    except Exception as e:
        logger.error(f"❌ Error al eliminar tablas: {e}")
        raise


def test_connection():
    """
    Probar conexión a la base de datos
    """
    if not engine:
        logger.error("❌ Engine no configurado")
        return False

    try:
        with engine.connect() as conn:
            # Usar text() para consultas SQL raw
            from sqlalchemy import text
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("✅ Conexión a MySQL exitosa")
        return True
    except Exception as e:
        logger.error(f"❌ Error de conexión a MySQL: {e}")
        return False


def get_db_info():
    """
    Obtener información de la base de datos
    """
    if not engine:
        return None

    try:
        with engine.connect() as conn:
            from sqlalchemy import text

            result = conn.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]

            result = conn.execute(text("SELECT DATABASE()"))
            database = result.fetchone()[0]

            return {
                "mysql_version": version,
                "database_name": database,
                "host": settings.DB_HOST,
                "port": settings.DB_PORT,
                "charset": settings.DB_CHARSET
            }
    except Exception as e:
        logger.error(f"Error al obtener info de DB: {e}")
        return None