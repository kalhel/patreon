# 🚀 Phase 0 Installation Guide

**Objetivo**: Instalar PostgreSQL, Redis, y preparar el entorno para la migración.

---

## 📋 Prerequisitos

- Linux system (Ubuntu/Debian preferido)
- Python 3.10+
- sudo access
- ~5GB espacio libre

---

## 🎯 Opción 1: Instalación Automática (Recomendado)

### Paso 1: Ejecutar script de setup

```bash
cd /home/user/patreon

# Activar entorno virtual
source venv/bin/activate

# Ejecutar script automatizado
bash scripts/setup_phase0.sh
```

El script te guiará paso a paso para:
- ✅ Instalar PostgreSQL 15+
- ✅ Instalar pgvector extension
- ✅ Crear base de datos y usuario
- ✅ Aplicar schema.sql
- ✅ Instalar Redis
- ✅ Instalar dependencias Python
- ✅ Probar conexiones

### Paso 2: Verificar instalación

```bash
python3 scripts/test_connections.py
```

Deberías ver:
```
✅ PostgreSQL connected
✅ pgvector extension installed
✅ Redis connected
✅ Celery installed
✅ SQLAlchemy installed

🎉 All tests passed! You're ready to proceed with Phase 0
```

### Paso 3: Migrar datos de Firebase

```bash
python3 scripts/migrate_firebase_to_postgres.py
```

---

## 🎯 Opción 2: Instalación Manual

### Paso 1: Instalar PostgreSQL

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Verificar instalación
psql --version
```

### Paso 2: Instalar pgvector

```bash
# Opción A: Desde apt (si está disponible)
sudo apt install -y postgresql-15-pgvector

# Opción B: Compilar desde source
# Ver: https://github.com/pgvector/pgvector
```

### Paso 3: Configurar PostgreSQL

```bash
# Conectar como postgres
sudo -u postgres psql

# Dentro de psql:
CREATE DATABASE patreon;
CREATE USER patreon_user WITH PASSWORD 'TU_PASSWORD_AQUI';
GRANT ALL PRIVILEGES ON DATABASE patreon TO patreon_user;

\c patreon
CREATE EXTENSION vector;
GRANT ALL ON SCHEMA public TO patreon_user;

\q
```

### Paso 4: Aplicar schema

```bash
# Copiar .env.example a .env
cp .env.example .env

# Editar .env y añadir tu password
nano .env

# Aplicar schema
psql -U patreon_user -d patreon -h localhost -f database/schema.sql
```

### Paso 5: Instalar Redis

```bash
# Instalar Redis
sudo apt install -y redis-server

# Iniciar Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verificar
redis-cli ping
# Debe responder: PONG
```

### Paso 6: Instalar dependencias Python

```bash
# Activar entorno virtual
source venv/bin/activate

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt
```

### Paso 7: Verificar

```bash
python3 scripts/test_connections.py
```

---

## 🎯 Opción 3: Docker (Más fácil para desarrollo)

### Paso 1: Instalar Docker

```bash
# Instalar Docker y Docker Compose
sudo apt install -y docker.io docker-compose

# Añadir usuario al grupo docker
sudo usermod -aG docker $USER

# Re-login o ejecutar
newgrp docker
```

### Paso 2: Configurar .env

```bash
cp .env.example .env
nano .env
```

### Paso 3: Levantar servicios

```bash
# Iniciar PostgreSQL y Redis
docker-compose up -d postgres redis

# Verificar que estén corriendo
docker-compose ps
```

### Paso 4: Aplicar schema

```bash
# El schema se aplica automáticamente en el primer inicio
# Verificar:
docker-compose exec postgres psql -U patreon_user -d patreon -c "\dt"
```

### Paso 5: Instalar dependencias Python (local)

```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

## ✅ Verificación Final

Ejecuta todos los tests:

```bash
python3 scripts/test_connections.py
```

Deberías ver:

```
🔍 Testing PostgreSQL connection...
✅ PostgreSQL connected: PostgreSQL 15.x
✅ pgvector extension installed
✅ Found 12 tables:
   - creators
   - collections
   - posts
   - post_collections
   - media_files
   - post_media
   - transcriptions
   - users
   - user_lists
   - user_post_data
   - scraping_status
   - jobs
   - system_config
   - audit_log

🔍 Testing Redis connection...
✅ Redis connected
✅ Redis read/write working
✅ Redis version: 7.x.x

🔍 Testing Celery installation...
✅ Celery installed: 5.x.x

🔍 Testing SQLAlchemy installation...
✅ SQLAlchemy installed: 2.0.x
✅ SQLAlchemy can connect to PostgreSQL

📊 Summary
✅ PostgreSQL
✅ Redis
✅ Celery
✅ SQLAlchemy

4/4 tests passed

🎉 All tests passed! You're ready to proceed with Phase 0
```

---

## 🔄 Siguientes Pasos

1. **Backup de datos actuales**
   ```bash
   tar -czf backup_data_$(date +%Y%m%d).tar.gz data/
   ```

2. **Migrar Firebase a PostgreSQL**
   ```bash
   python3 scripts/migrate_firebase_to_postgres.py
   ```

3. **Actualizar PROGRESS.md**
   - Marca las tareas completadas
   - Anota cualquier problema encontrado

4. **Iniciar Phase 1**: Migración de datos de JSONs

---

## 🐛 Troubleshooting

### PostgreSQL no se conecta

```bash
# Verificar que esté corriendo
sudo systemctl status postgresql

# Ver logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log

# Reiniciar
sudo systemctl restart postgresql
```

### pgvector no se instala

Si no está en los repos de apt:

```bash
# Compilar desde source
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Luego en psql:
CREATE EXTENSION vector;
```

### Redis no responde

```bash
# Verificar que esté corriendo
sudo systemctl status redis-server

# Ver logs
sudo tail -f /var/log/redis/redis-server.log

# Reiniciar
sudo systemctl restart redis-server
```

### Error de permisos en PostgreSQL

```bash
# Conectar como postgres
sudo -u postgres psql -d patreon

# Dar permisos
GRANT ALL ON ALL TABLES IN SCHEMA public TO patreon_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO patreon_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO patreon_user;
```

---

## 📞 Ayuda

Si encuentras problemas:

1. Revisa los logs de cada servicio
2. Verifica que .env tiene las credenciales correctas
3. Asegúrate de que los puertos no están en uso (5432, 6379)
4. Documenta el problema en PROGRESS.md sección "Issues & Solutions"

---

**Siguiente**: [Phase 1 - Data Migration](PHASE1_MIGRATION.md)
