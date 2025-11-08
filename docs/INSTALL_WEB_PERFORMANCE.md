# Instalación de Mejoras de Performance Web

## 📦 Instalar Dependencias

```bash
# 1. Activar entorno virtual
cd /home/javif/proyectos/astrologia/patreon
source venv/bin/activate

# 2. Instalar nuevas dependencias
pip3 install -r requirements.txt
```

Las nuevas dependencias son:
- `gunicorn>=21.2.0` - Servidor WSGI de producción
- `flask-compress>=1.14` - Compresión gzip automática
- `flask-caching>=2.1.0` - Sistema de caché (ya estaba en requirements)
- `redis>=5.0.1` - Backend de caché (ya estaba en requirements)

## 🧪 Probar las Mejoras

### Opción 1: Modo Desarrollo (Flask dev server)
```bash
python3 web/viewer.py
# Accede a: http://localhost:5000
```

### Opción 2: Modo Producción (Gunicorn - RECOMENDADO)
```bash
./scripts/start_web_viewer.sh
# Accede a: http://localhost:5001
```

## ✅ Verificar que Funciona

### 1. Verificar Compresión Gzip
```bash
curl -I -H "Accept-Encoding: gzip" http://localhost:5001/
# Busca header: Content-Encoding: gzip
```

### 2. Verificar Caché
```bash
# Ver stats de caché
curl http://localhost:5001/api/cache/stats

# Limpiar caché
curl http://localhost:5001/api/cache/clear
```

### 3. Medir Tiempo de Carga

**Primera carga (sin caché):**
```bash
time curl -s http://localhost:5001/ > /dev/null
```

**Segunda carga (con caché):**
```bash
time curl -s http://localhost:5001/ > /dev/null
```

La segunda debería ser **mucho más rápida** (< 100ms vs 1-2s)

## 🔧 Configuración Opcional

Edita `.env` para personalizar:

```bash
# Tipo de caché
CACHE_TYPE=SimpleCache  # o RedisCache para producción

# Timeout de caché (en segundos)
CACHE_TIMEOUT=300  # 5 minutos

# Gunicorn
WEB_VIEWER_PORT=5001
WEB_VIEWER_WORKERS=4
```

## 📊 Benchmarking (Opcional)

Instalar Apache Bench:
```bash
sudo apt-get install apache2-utils
```

Hacer benchmark:
```bash
# 100 requests, 10 concurrentes
ab -n 100 -c 10 http://localhost:5001/

# Con caché debería ser ~10-50 req/sec
# Sin caché era ~1-2 req/sec
```

## ⚠️ Troubleshooting

**Error: ModuleNotFoundError: No module named 'flask_compress'**
```bash
pip3 install flask-compress
```

**Error: ModuleNotFoundError: No module named 'flask_caching'**
```bash
pip3 install flask-caching
```

**Error: gunicorn: command not found**
```bash
pip3 install gunicorn
```

**El caché no funciona:**
- Verifica que esté activado: `curl http://localhost:5001/api/cache/stats`
- Limpia el caché: `curl http://localhost:5001/api/cache/clear`
- Revisa logs de gunicorn para errores

## 📝 Notas

- **Caché se invalida automáticamente** cada 5 minutos
- **Limpiar caché manualmente** después de procesar nuevos posts con phase2
- **Usar gunicorn en producción**, no el servidor de desarrollo de Flask
- **4 workers** es bueno para la mayoría de casos (1-2 por CPU core)
