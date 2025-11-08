#!/bin/bash
# Script para ejecutar el análisis del post 141632966
# Lee las credenciales del archivo .env

# Cargar variables de entorno
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ Archivo .env no encontrado"
    exit 1
fi

# Valores por defecto si no están en .env
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-alejandria}
DB_USER=${DB_USER:-postgres}

echo "Conectando a PostgreSQL:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""
echo "Ejecutando análisis SQL..."
echo ""

# Ejecutar el script SQL
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f analyze_post_141632966_order.sql

echo ""
echo "====================================================================="
echo ""
echo "Ejecutando análisis Python detallado..."
echo ""

# Ejecutar el script Python
python3 analyze_content_order.py
