#!/bin/bash

# Script para desplegar PillCare 360 desde /home/ubuntu/Api-pillcare
# Ejecutar como: sudo bash deploy_existing.sh

set -e

echo "🚀 Desplegando PillCare 360 desde /home/ubuntu/Api-pillcare"
echo "=========================================================="

# Variables
SOURCE_DIR="/home/ubuntu/Api-pillcare"
APP_USER="pillcare360"
APP_DIR="/opt/pillcare360"
VENV_DIR="${APP_DIR}/venv"
SERVICE_NAME="pillcare360"
DB_NAME="pillcare360"
DB_USER="pillcare360_user"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Verificar root
if [[ $EUID -ne 0 ]]; then
   log_error "Ejecutar como root: sudo bash deploy_existing.sh"
   exit 1
fi

# Verificar que existe el código fuente
if [ ! -d "${SOURCE_DIR}" ] || [ ! -f "${SOURCE_DIR}/app/main.py" ]; then
    log_error "No se encontró el código en ${SOURCE_DIR} o falta app/main.py"
    exit 1
fi

log_info "✅ Código fuente encontrado en ${SOURCE_DIR}"

# 1. Instalar dependencias del sistema si no están
log_info "Verificando dependencias del sistema..."
apt update
apt install -y \
    python3 python3-dev python3-venv python3-pip \
    mysql-server nginx supervisor git curl build-essential \
    pkg-config default-libmysqlclient-dev

# 2. Configurar MySQL si no está configurado
log_info "Configurando MySQL..."
systemctl start mysql
systemctl enable mysql

# Generar contraseñas si no existen
if [ ! -f "/opt/mysql_credentials.txt" ]; then
    DB_ROOT_PASSWORD=$(openssl rand -base64 32)
    DB_PASSWORD=$(openssl rand -base64 32)

    # Configurar MySQL
    mysql --execute="ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${DB_ROOT_PASSWORD}';" 2>/dev/null || true
    mysql -u root -p"${DB_ROOT_PASSWORD}" --execute="
    CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
    GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
    FLUSH PRIVILEGES;
    " 2>/dev/null || {
        # Si falla, asumir que MySQL no tiene contraseña aún
        DB_ROOT_PASSWORD=$(openssl rand -base64 32)
        DB_PASSWORD=$(openssl rand -base64 32)

        mysql --execute="ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${DB_ROOT_PASSWORD}';"
        mysql -u root -p"${DB_ROOT_PASSWORD}" --execute="
        CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
        GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
        FLUSH PRIVILEGES;
        "
    }

    # Guardar credenciales
    echo "DB_ROOT_PASSWORD=${DB_ROOT_PASSWORD}" > /opt/mysql_credentials.txt
    echo "DB_PASSWORD=${DB_PASSWORD}" >> /opt/mysql_credentials.txt
    chmod 600 /opt/mysql_credentials.txt

    log_info "✅ MySQL configurado con nuevas credenciales"
else
    log_info "✅ MySQL ya configurado, leyendo credenciales..."
    source /opt/mysql_credentials.txt
fi

# 3. Crear usuario de aplicación
log_info "Creando usuario de aplicación..."
useradd --system --shell /bin/bash --home-dir ${APP_DIR} --create-home ${APP_USER} 2>/dev/null || true

# 4. Crear estructura de directorios
mkdir -p ${APP_DIR}/{logs,backups,uploads,reports,app}

# 5. Copiar código fuente
log_info "Copiando código fuente..."
rsync -av --delete ${SOURCE_DIR}/ ${APP_DIR}/app/
chown -R ${APP_USER}:${APP_USER} ${APP_DIR}/app

# 6. Crear archivo .env
log_info "Creando configuración..."
cat > ${APP_DIR}/.env << EOF
PROJECT_NAME=PillCare_360_API
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000
SECRET_KEY=$(openssl rand -base64 64 | tr -d '\n')
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DB_HOST=localhost
DB_PORT=3306
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_CHARSET=utf8mb4
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=
EMAIL_PASSWORD=
FROM_EMAIL=noreply@pillcare360.com
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","https://tudominio.com"]
UPLOAD_FOLDER=${APP_DIR}/uploads
REPORTS_FOLDER=${APP_DIR}/reports
LOG_LEVEL=INFO
DEFAULT_TIMEZONE=America/Mexico_City
EOF

# Enlazar .env al directorio de la app
ln -sf ${APP_DIR}/.env ${APP_DIR}/app/.env

# 7. Crear y configurar entorno virtual
log_info "Configurando entorno virtual de Python..."
if [ -d "${VENV_DIR}" ]; then
    rm -rf "${VENV_DIR}"
fi

sudo -u ${APP_USER} python3 -m venv "${VENV_DIR}"
sudo -u ${APP_USER} "${VENV_DIR}/bin/pip" install --upgrade pip

# 8. Instalar dependencias de Python
log_info "Instalando dependencias de Python..."
if [ -f "${APP_DIR}/app/requirements.txt" ]; then
    sudo -u ${APP_USER} "${VENV_DIR}/bin/pip" install -r "${APP_DIR}/app/requirements.txt"
else
    log_warn "No se encontró requirements.txt, instalando dependencias básicas..."
    sudo -u ${APP_USER} "${VENV_DIR}/bin/pip" install \
        fastapi==0.104.1 \
        uvicorn[standard]==0.24.0 \
        sqlalchemy==2.0.23 \
        pymysql==1.1.0 \
        python-jose[cryptography]==3.3.0 \
        passlib[bcrypt]==1.7.4 \
        python-multipart==0.0.6 \
        pydantic==2.5.0 \
        pydantic-settings==2.1.0 \
        python-dotenv==1.0.0 \
        email-validator==2.1.0
fi

# 9. Probar conexión y crear tablas
log_info "Configurando base de datos..."
cd ${APP_DIR}/app

# Crear script temporal para probar la base de datos
cat > /tmp/test_db.py << 'EOF'
import sys
import os
sys.path.append('.')

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv('/opt/pillcare360/.env')

try:
    from app.core.database import create_tables, test_connection
    print('🔗 Probando conexión a MySQL...')
    if test_connection():
        print('✅ Conexión exitosa')
        print('🔨 Creando/verificando tablas...')
        create_tables()
        print('✅ Base de datos lista')
    else:
        print('❌ Error de conexión')
        sys.exit(1)
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

# Ejecutar el script
sudo -u ${APP_USER} "${VENV_DIR}/bin/python" /tmp/test_db.py

# Limpiar script temporal
rm -f /tmp/test_db.py

# 10. Crear servicio systemd
log_info "Configurando servicio systemd..."
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=PillCare 360 FastAPI Application
After=network.target mysql.service
Requires=mysql.service

[Service]
Type=exec
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}/app
Environment=PATH=${VENV_DIR}/bin
EnvironmentFile=${APP_DIR}/.env
ExecStart=${VENV_DIR}/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10

# Logging
StandardOutput=append:${APP_DIR}/logs/app.log
StandardError=append:${APP_DIR}/logs/error.log

[Install]
WantedBy=multi-user.target
EOF

# 11. Configurar Nginx
log_info "Configurando Nginx..."
cat > /etc/nginx/sites-available/pillcare360 << 'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 10M;

    # Logs
    access_log /opt/pillcare360/logs/nginx_access.log;
    error_log /opt/pillcare360/logs/nginx_error.log;

    # API
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS Headers
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;

        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' '*';
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS';
            add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization';
            add_header 'Access-Control-Max-Age' 1728000;
            add_header 'Content-Type' 'text/plain; charset=utf-8';
            add_header 'Content-Length' 0;
            return 204;
        }
    }
}
EOF

# Activar sitio de Nginx
ln -sf /etc/nginx/sites-available/pillcare360 /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t

# 12. Configurar firewall
log_info "Configurando firewall..."
ufw --force enable || true
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw allow 8000  # API directo (temporal)

# 13. Ajustar permisos finales
chown -R ${APP_USER}:${APP_USER} ${APP_DIR}
chmod 600 ${APP_DIR}/.env

# 14. Crear script de actualización
cat > ${APP_DIR}/update.sh << EOF
#!/bin/bash
echo "🔄 Actualizando PillCare 360..."

# Sincronizar código desde el directorio original
rsync -av --delete ${SOURCE_DIR}/ ${APP_DIR}/app/
chown -R ${APP_USER}:${APP_USER} ${APP_DIR}/app

# Reinstalar dependencias si cambió requirements.txt
if [ ${SOURCE_DIR}/requirements.txt -nt ${VENV_DIR}/pyvenv.cfg ]; then
    echo "📦 Actualizando dependencias..."
    sudo -u ${APP_USER} ${VENV_DIR}/bin/pip install -r ${APP_DIR}/app/requirements.txt
fi

# Reiniciar servicio
systemctl restart ${SERVICE_NAME}

echo "✅ Actualización completada"
systemctl status ${SERVICE_NAME}
EOF

chmod +x ${APP_DIR}/update.sh

# 15. Iniciar servicios
log_info "Iniciando servicios..."
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl start ${SERVICE_NAME}
systemctl reload nginx

# 16. Verificar servicios
sleep 5

echo ""
echo "🔍 VERIFICANDO SERVICIOS:"
echo "========================"

if systemctl is-active --quiet ${SERVICE_NAME}; then
    log_info "✅ PillCare 360: CORRIENDO"
else
    log_error "❌ PillCare 360: FALLÓ"
    echo "Ver logs: sudo journalctl -u ${SERVICE_NAME} -n 20"
fi

if systemctl is-active --quiet nginx; then
    log_info "✅ Nginx: CORRIENDO"
else
    log_error "❌ Nginx: FALLÓ"
fi

if systemctl is-active --quiet mysql; then
    log_info "✅ MySQL: CORRIENDO"
else
    log_error "❌ MySQL: FALLÓ"
fi

# Test de la API
log_info "Probando API..."
sleep 3
if curl -f -s http://localhost:8000/health > /dev/null; then
    log_info "✅ API respondiendo correctamente"
else
    log_warn "⚠️ API no responde - verificar logs"
fi

# 17. Información final
echo ""
echo "🎉 ¡DESPLIEGUE COMPLETADO!"
echo "========================"
echo ""
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "TU_IP_PUBLICA")
echo "🌐 Tu API está disponible en:"
echo "   http://${PUBLIC_IP}/"
echo "   http://${PUBLIC_IP}/docs"
echo "   http://${PUBLIC_IP}/health"
echo ""
echo "📋 COMANDOS ÚTILES:"
echo "   Actualizar desde ${SOURCE_DIR}:  sudo ${APP_DIR}/update.sh"
echo "   Ver logs:                        sudo tail -f ${APP_DIR}/logs/app.log"
echo "   Ver errores:                     sudo tail -f ${APP_DIR}/logs/error.log"
echo "   Reiniciar app:                   sudo systemctl restart ${SERVICE_NAME}"
echo "   Estado:                          sudo systemctl status ${SERVICE_NAME}"
echo ""
echo "🔐 CREDENCIALES MySQL (guardadas en /opt/mysql_credentials.txt):"
echo "   Root: ${DB_ROOT_PASSWORD}"
echo "   App:  ${DB_PASSWORD}"
echo ""
echo "📁 ESTRUCTURA:"
echo "   Código fuente: ${SOURCE_DIR}/ (tu ubicación original)"
echo "   App en producción: ${APP_DIR}/app/"
echo "   Configuración: ${APP_DIR}/.env"
echo "   Logs: ${APP_DIR}/logs/"
echo ""
echo "💡 PARA ACTUALIZAR:"
echo "   1. Haz cambios en ${SOURCE_DIR}/"
echo "   2. Ejecuta: sudo ${APP_DIR}/update.sh"
echo ""