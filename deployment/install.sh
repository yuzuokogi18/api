#!/bin/bash

# Script de instalación para PillCare 360 en EC2 Ubuntu con git clone
# Preparar el servidor para clonar el repositorio

set -e

echo "🚀 Preparando EC2 Ubuntu para PillCare 360"
echo "=========================================="

# Variables de configuración
APP_NAME="pillcare360"
APP_USER="pillcare360"
APP_DIR="/opt/pillcare360"
DB_NAME="pillcare360"
DB_USER="pillcare360_user"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Verificar root
if [[ $EUID -ne 0 ]]; then
   log_error "Ejecutar como root: sudo bash install.sh"
   exit 1
fi

# 1. Actualizar sistema
log_info "Actualizando sistema Ubuntu..."
apt update && apt upgrade -y

# 2. Instalar dependencias
log_info "Instalando dependencias básicas..."
apt install -y \
    curl wget git vim htop unzip \
    build-essential software-properties-common \
    python3.11 python3.11-dev python3.11-venv \
    python3-pip mysql-server nginx supervisor ufw

# 3. Configurar MySQL
log_info "Configurando MySQL..."
DB_ROOT_PASSWORD=$(openssl rand -base64 32)
DB_PASSWORD=$(openssl rand -base64 32)

systemctl start mysql
systemctl enable mysql

# Configurar MySQL de forma segura
mysql --execute="ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${DB_ROOT_PASSWORD}';"
mysql --execute="DELETE FROM mysql.user WHERE User='';"
mysql --execute="DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');"
mysql --execute="DROP DATABASE IF EXISTS test;"
mysql --execute="FLUSH PRIVILEGES;"

# Crear base de datos y usuario para la app
mysql -u root -p"${DB_ROOT_PASSWORD}" --execute="
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
"

# 4. Crear usuario de aplicación
log_info "Creando usuario ${APP_USER}..."
useradd --system --shell /bin/bash --home-dir ${APP_DIR} --create-home ${APP_USER} || true

# 5. Configurar firewall
log_info "Configurando firewall..."
ufw --force enable
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw allow 8000  # API (desarrollo)

# 6. Crear estructura de directorios
mkdir -p ${APP_DIR}/{logs,backups,uploads,reports}

# 7. Crear archivo .env
log_info "Creando archivo de configuración..."
cat > ${APP_DIR}/.env << EOF
# PillCare 360 - Configuración de Producción
PROJECT_NAME="PillCare 360 API"
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Seguridad
SECRET_KEY=$(openssl rand -base64 64)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Base de datos MySQL
DB_HOST=localhost
DB_PORT=3306
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_CHARSET=utf8mb4

# Email (configurar después)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=
EMAIL_PASSWORD=
FROM_EMAIL=noreply@pillcare360.com

# CORS - Ajustar según tu frontend
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","https://tudominio.com"]

# Configuraciones adicionales
UPLOAD_FOLDER=${APP_DIR}/uploads
REPORTS_FOLDER=${APP_DIR}/reports
LOG_LEVEL=INFO
DEFAULT_TIMEZONE=America/Mexico_City
EOF

# 8. Ajustar permisos
chown -R ${APP_USER}:${APP_USER} ${APP_DIR}
chmod 600 ${APP_DIR}/.env

# 9. Configurar git (global para que cualquier usuario pueda clonar)
log_info "Configurando Git..."
git config --global init.defaultBranch main
git config --global pull.rebase false

# 10. Información final
log_info "¡Servidor preparado!"
echo ""
echo "🎯 PRÓXIMOS PASOS:"
echo "=================="
echo ""
echo "1️⃣ Clona tu repositorio:"
echo "   cd ${APP_DIR}"
echo "   sudo -u ${APP_USER} git clone https://github.com/tu-usuario/tu-repo.git app"
echo ""
echo "2️⃣ Ejecuta el despliegue:"
echo "   sudo bash ${APP_DIR}/app/deployment/deploy.sh"
echo ""
echo "🔐 CREDENCIALES MySQL:"
echo "   Root: ${DB_ROOT_PASSWORD}"
echo "   App:  ${DB_PASSWORD}"
echo ""
echo "📁 DIRECTORIOS:"
echo "   App: ${APP_DIR}/app (aquí va tu código)"
echo "   Config: ${APP_DIR}/.env"
echo "   Logs: ${APP_DIR}/logs"
echo ""

# Guardar info importante
cat > ${APP_DIR}/README.txt << EOF
PillCare 360 - Información del Servidor
======================================

INSTALACIÓN: $(date)

CREDENCIALES MySQL:
- Root password: ${DB_ROOT_PASSWORD}
- App password: ${DB_PASSWORD}
- Base de datos: ${DB_NAME}
- Usuario: ${DB_USER}

COMANDOS ÚTILES:
- Clonar repo: cd ${APP_DIR} && sudo -u ${APP_USER} git clone TU_REPO app
- Desplegar: sudo bash ${APP_DIR}/app/deployment/deploy.sh
- Ver logs: sudo tail -f ${APP_DIR}/logs/app.log
- Reiniciar app: sudo systemctl restart pillcare360

ARCHIVOS IMPORTANTES:
- Configuración: ${APP_DIR}/.env
- Código: ${APP_DIR}/app/
- Logs: ${APP_DIR}/logs/
- Backups: ${APP_DIR}/backups/
EOF

chown ${APP_USER}:${APP_USER} ${APP_DIR}/README.txt

echo "📋 Info guardada en: ${APP_DIR}/README.txt"
echo ""