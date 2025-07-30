"""
Archivo principal de la aplicación FastAPI - PillCare 360
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import create_tables, test_connection, get_db_info
from app.api import api_router
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    # Startup
    logger.info("🚀 Iniciando PillCare 360 API...")
    logger.info(f"🌍 Ambiente: {settings.ENVIRONMENT}")
    logger.info(f"🔑 Debug: {settings.DEBUG}")

    # Verificar conexión a la base de datos
    if test_connection():
        logger.info("✅ Conexión a MySQL exitosa")

        # Mostrar información de la base de datos
        db_info = get_db_info()
        if db_info:
            logger.info(f"📊 MySQL {db_info['mysql_version']} - DB: {db_info['database_name']}")

        # Crear tablas si no existen
        try:
            create_tables()
            logger.info("✅ Esquema de base de datos verificado")
        except Exception as e:
            logger.error(f"❌ Error al verificar esquema: {e}")
    else:
        logger.error("❌ Error de conexión a MySQL")
        logger.warning("⚠️ La aplicación continuará pero sin base de datos")

    logger.info("🎯 PillCare 360 API lista para recibir requests")
    yield

    # Shutdown
    logger.info("🛑 Cerrando PillCare 360 API...")


def create_application() -> FastAPI:
    """Factory function para crear la aplicación FastAPI"""

    # Configuración de la aplicación
    app_config = {
        "title": settings.PROJECT_NAME,
        "description": """
## PillCare 360 API

API REST para la gestión inteligente de medicamentos y tratamientos médicos.

### Características principales:
- 👥 Gestión de pacientes y cuidadores
- 💊 Catálogo de medicamentos
- 📋 Tratamientos personalizados
- ⏰ Alarmas y recordatorios
- 📊 Monitoreo de cumplimiento
- 🚨 Sistema de alertas
- 📈 Reportes y analíticas

### Seguridad:
- Autenticación JWT
- Control de acceso basado en roles
- Encriptación de datos sensibles
        """,
        "version": "1.0.0",
        "contact": {
            "name": "PillCare 360 Support",
            "email": "support@pillcare360.com",
        },
        "license_info": {
            "name": "MIT License",
        },
        "lifespan": lifespan,
    }

    # En producción, mantener docs disponibles pero solo para debugging
    # if settings.is_production:
    #     app_config.update({
    #         "docs_url": None,
    #         "redoc_url": None,
    #         "openapi_url": None
    #     })

    app = FastAPI(**app_config)

    # Configurar middlewares
    setup_middlewares(app)

    # Configurar rutas
    setup_routes(app)

    return app


def setup_middlewares(app: FastAPI):
    """Configurar middlewares de la aplicación"""

    # CORS - Configuración universal que funciona en desarrollo y producción
    cors_config = {
        "allow_origins": [
            # Desarrollo local
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
            # Producción - IP específica
            "http://18.209.162.34",
            "https://18.209.162.34",
            "http://34.195.77.140",
            "https://34.195.77.140",
            "*"
        ],
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["*"],
        "expose_headers": ["*"]
    }

    # Si está en settings.CORS_ORIGINS, usar esos también
    if hasattr(settings, 'CORS_ORIGINS') and settings.CORS_ORIGINS:
        try:
            # CORS_ORIGINS puede ser string o list
            if isinstance(settings.CORS_ORIGINS, str):
                import json
                additional_origins = json.loads(settings.CORS_ORIGINS)
            else:
                additional_origins = settings.CORS_ORIGINS

            # Combinar orígenes sin duplicados
            all_origins = list(set(cors_config["allow_origins"] + additional_origins))
            cors_config["allow_origins"] = all_origins
        except Exception as e:
            logger.warning(f"Error procesando CORS_ORIGINS: {e}")

    logger.info("🔧 CORS configurado")
    logger.info(f"🌐 Orígenes permitidos: {cors_config['allow_origins']}")

    app.add_middleware(CORSMiddleware, **cors_config)

    # Trusted hosts middleware - más permisivo en producción para debugging
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[
                "*.pillcare360.com",
                "pillcare360.com",
                "localhost",
                "127.0.0.1",
                "18.234.171.119",  # Tu IP específica
                "*"  # Temporalmente permisivo para debugging
            ]
        )
        logger.info("🛡️ TrustedHost middleware configurado")


def setup_routes(app: FastAPI):
    """Configurar rutas de la aplicación"""

    # Endpoint raíz
    @app.get("/")
    async def root():
        return {
            "message": "🏥 PillCare 360 API",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "documentation": "/docs",  # Siempre disponible
            "health": "/health",
            "api": "/api"
        }

    # Health check general
    @app.get("/health")
    async def health_check():
        """Health check completo de la aplicación"""
        db_status = "connected" if test_connection() else "disconnected"

        health_status = {
            "status": "healthy" if db_status == "connected" else "degraded",
            "service": "PillCare 360 API",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "database": {
                "status": db_status,
                "type": "MySQL"
            },
            "timestamp": "2025-01-01T00:00:00Z"  # En implementación real, usar datetime.utcnow()
        }

        # Información adicional en desarrollo
        if settings.DEBUG:
            db_info = get_db_info()
            if db_info:
                health_status["database"].update(db_info)

        return health_status

    # CORS preflight para todas las rutas de la API
    @app.options("/api/{path:path}")
    async def options_handler():
        """Manejo explícito de preflight CORS para todas las rutas de la API"""
        return {"message": "OK"}

    # Incluir router principal de la API
    app.include_router(
        api_router,
        prefix="/api"
    )

    logger.info("🛣️ Rutas configuradas correctamente")


# Crear la aplicación
app = create_application()


# Solo para desarrollo con uvicorn run
if __name__ == "__main__":
    import uvicorn

    # Configuración para desarrollo
    uvicorn_config = {
        "app": "app.main:app",
        "host": settings.HOST,
        "port": settings.PORT,
        "reload": settings.DEBUG,
        "log_level": settings.LOG_LEVEL.lower(),
        "access_log": settings.DEBUG,
    }

    logger.info("🚀 Iniciando servidor de desarrollo...")
    logger.info(f"🌐 URL: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"📚 Docs: http://{settings.HOST}:{settings.PORT}/docs")
    logger.info(f"📖 Redoc: http://{settings.HOST}:{settings.PORT}/redoc")
    logger.info(f"❤️ Health: http://{settings.HOST}:{settings.PORT}/health")

    uvicorn.run(**uvicorn_config)