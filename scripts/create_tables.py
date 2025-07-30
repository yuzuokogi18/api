#!/usr/bin/env python3
"""
Script para crear tablas de la base de datos MySQL
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import create_tables, test_connection, get_db_info
from app.core.config import get_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Función principal"""
    settings = get_settings()

    logger.info("🚀 Iniciando creación de tablas para PillCare 360")
    logger.info(f"📊 Entorno: {settings.ENVIRONMENT}")
    logger.info(f"🗄️ Base de datos: {settings.DB_NAME} en {settings.DB_HOST}:{settings.DB_PORT}")

    # Probar conexión
    logger.info("🔗 Probando conexión a MySQL...")
    if not test_connection():
        logger.error("❌ No se pudo conectar a MySQL")
        return False

    # Mostrar información de la base de datos
    db_info = get_db_info()
    if db_info:
        logger.info(f"✅ Conectado a MySQL {db_info['mysql_version']}")
        logger.info(f"📂 Base de datos: {db_info['database_name']}")

    # Crear tablas
    try:
        logger.info("🔨 Creando tablas...")
        create_tables()
        logger.info("✅ ¡Tablas creadas exitosamente!")

        # Verificar tablas creadas
        verify_tables()

        return True

    except Exception as e:
        logger.error(f"❌ Error al crear tablas: {e}")
        return False


def verify_tables():
    """Verificar que las tablas se crearon correctamente"""
    from app.core.database import engine

    inspector = engine.dialect.get_inspector(engine.connect())
    tables = inspector.get_table_names()

    expected_tables = [
        'users', 'patients', 'medications', 'treatments',
        'alarms', 'dose_records', 'alerts', 'compliance_records'
    ]

    logger.info("📋 Verificando tablas creadas:")
    for table in expected_tables:
        if table in tables:
            logger.info(f"   ✅ {table}")
        else:
            logger.warning(f"   ⚠️ {table} - No encontrada")

    logger.info(f"📊 Total de tablas: {len(tables)}")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)