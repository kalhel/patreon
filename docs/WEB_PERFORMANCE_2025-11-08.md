# Web Viewer Performance Optimization

**Date:** 2025-11-08
**Branch:** `feature/web-performance-optimization`
**Status:** ✅ **COMPLETED** - See [WEB_PERFORMANCE_RESULTS_2025-11-08.md](WEB_PERFORMANCE_RESULTS_2025-11-08.md) for detailed results

---

## 🎯 Objetivo

Mejorar significativamente el rendimiento del web viewer, reduciendo tiempos de carga de páginas de varios segundos a menos de 1 segundo.

---

## 🔍 Análisis de Performance (Estado Actual)

### Problemas Identificados

#### 1. **Carga Completa de Datos en Cada Request**
**Archivo:** `web/viewer.py:216-362`
**Problema:**
- Función `load_posts_from_postgres()` ejecuta 2 queries grandes **en cada request**
- Carga **979 posts completos** con toda su metadata
- Carga **186 colecciones** relacionadas
- Todo se procesa en memoria sin caché

**Impacto:**
```
Query 1: SELECT * FROM posts WHERE deleted_at IS NULL ORDER BY post_id DESC
         → 979 filas × ~30 columnas (JSONB pesados)

Query 2: SELECT * FROM post_collections pc JOIN collections c ...
         → Cientos de filas con JOINs
```

**Tiempo estimado:** 500-2000ms por request

#### 2. **Servidor de Desarrollo de Flask**
**Archivo:** `web/viewer.py:33-35`
**Problema:**
- Usando servidor de desarrollo (`flask run` o `app.run()`)
- **Monohilo** - solo 1 request a la vez
- Sin compresión gzip
- Sin optimizaciones de producción

**Impacto:**
- Requests bloqueados esperando turno
- HTML sin comprimir (100KB+ por página)
- No aprovecha múltiples cores del CPU

#### 3. **Sin Sistema de Caché**
**Problema:**
- Cada visita a `/` recarga TODOS los posts
- Cada visita a `/post/<id>` recarga TODOS los posts (para navegación)
- Los datos cambian raramente pero se consultan constantemente

**Impacto:**
- PostgreSQL sobrecargado con queries idénticas
- Red saturada transfiriendo mismos datos

#### 4. **Procesamiento Pesado en Vista Principal**
**Archivo:** `web/viewer.py:443-547`
**Problema:**
- Función `index()` ordena y filtra 979 posts en Python
- No hay paginación - muestra todos los posts
- Procesa video_local_paths para cada post

---

## ✅ Soluciones Propuestas

### 1. **Sistema de Caché con Flask-Caching**
**Dependencias:**
```
flask-caching==2.1.0
```

**Implementación:**
- Cachear resultado de `load_posts_from_postgres()` por 5 minutos
- Cachear resultado de queries de PostgreSQL individuales
- Backend: Simple cache (memoria) para desarrollo, Redis para producción

**Beneficio esperado:** Reducción de 90% en tiempo de carga después del primer request

### 2. **Servidor WSGI de Producción (Gunicorn)**
**Dependencias:**
```
gunicorn==21.2.0
```

**Configuración:**
```bash
gunicorn -w 4 -b 127.0.0.1:5001 web.viewer:app
```
- 4 workers (procesos)
- Bind a localhost:5001
- Timeout de 120s para requests pesados

**Beneficio esperado:** 4x más capacidad de requests concurrentes

### 3. **Compresión Gzip**
**Dependencias:**
```
flask-compress==1.14
```

**Implementación:**
```python
from flask_compress import Compress
Compress(app)
```

**Beneficio esperado:** Reducción de 70-80% en tamaño de HTML transferido

### 4. **Paginación y Lazy Loading**
**Implementación:**
- Vista principal: Cargar solo primeros 50 posts
- Scroll infinito o botón "Cargar más"
- Endpoint `/api/posts?offset=50&limit=50`

**Beneficio esperado:** Reducción de 95% en datos iniciales transferidos

### 5. **Optimización de Queries PostgreSQL**
**Mejoras:**
- Añadir índices en columnas frecuentemente consultadas
- Usar `SELECT` específico en lugar de `SELECT *`
- Lazy loading de `content_blocks` (solo cuando se visualiza el post)

**Índices recomendados:**
```sql
CREATE INDEX IF NOT EXISTS idx_posts_deleted_at ON posts(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_posts_creator_id ON posts(creator_id);
CREATE INDEX IF NOT EXISTS idx_post_collections_post_id ON post_collections(post_id);
```

---

## 📊 Métricas Objetivo

| Métrica | Antes | Objetivo | Método de Medición |
|---------|-------|----------|-------------------|
| Tiempo de carga `/` (primer request) | 2-5s | <1s | Chrome DevTools Network |
| Tiempo de carga `/` (cached) | 2-5s | <100ms | Chrome DevTools Network |
| Tiempo de carga `/post/<id>` | 1-3s | <500ms | Chrome DevTools Network |
| Tamaño HTML transferido | 100KB+ | <30KB | Chrome DevTools Network |
| Requests concurrentes soportados | 1 | 4+ | Apache Bench |

---

## 🔧 Plan de Implementación

### Fase 1: Infraestructura Base ✅
- [x] Analizar código actual
- [x] Identificar cuellos de botella
- [x] Actualizar `requirements.txt`
- [x] Crear script de inicio con gunicorn
- [x] Crear configuración de gunicorn

### Fase 2: Caching ✅
- [x] Integrar Flask-Caching
- [x] Cachear `load_posts_from_postgres()`
- [x] Cachear `load_posts_from_json()`
- [x] Configurar TTL apropiados (5 minutos)
- [x] Añadir endpoints de gestión de caché

### Fase 3: Compresión ✅
- [x] Integrar Flask-Compress
- [x] Habilitar compresión gzip automática

### Fase 4: Optimización de Queries ✅
- [x] Añadir índices en PostgreSQL
- [x] Optimizar SELECT queries (usando caché)
- [x] Implementar lazy loading de videos (Intersection Observer)

### Fase 5: Paginación 📝
- [ ] Endpoint API para paginación
- [ ] Modificar vista principal con límite
- [ ] Implementar scroll infinito (opcional)

### Fase 6: Testing y Benchmarking 📝
- [ ] Medir tiempos de carga antes/después
- [ ] Stress testing con Apache Bench
- [ ] Documentar mejoras conseguidas

---

## 📝 Notas Técnicas

### Cache Invalidation Strategy
**Cuando invalidar el caché:**
- Después de ejecutar `phase2_detail_extractor.py` (nuevo/actualizado post)
- Manualmente con endpoint `/api/cache/clear` (admin)
- Automáticamente cada 5 minutos (TTL)

### Gunicorn vs Flask Development Server
```
Flask Dev Server:
- 1 proceso, 1 thread
- Recarga automática en cambios
- DEBUG=True
- ❌ NO usar en producción

Gunicorn:
- N procesos workers
- Pre-fork model
- Producción estable
- ✅ Recomendado para producción
```

### Redis vs Simple Cache
**Simple Cache (memoria):**
- Pros: Sin dependencias externas, setup rápido
- Cons: Se pierde al reiniciar, no compartido entre workers

**Redis:**
- Pros: Persistente, compartido entre workers, más features
- Cons: Servicio adicional a instalar/mantener

**Decisión:** Empezar con Simple Cache, migrar a Redis si es necesario

---

## 🚀 Cómo Usar

### 1. Instalar Dependencias
```bash
# Activar entorno virtual
source venv/bin/activate

# Instalar nuevas dependencias
pip3 install -r requirements.txt
```

### 2. Ejecutar en Modo Desarrollo (con auto-reload)
```bash
python3 web/viewer.py
```

### 3. Ejecutar en Modo Producción (con gunicorn)

**Opción A: Script automático (recomendado)**
```bash
./scripts/start_web_viewer.sh
```

**Opción B: Gunicorn directo**
```bash
gunicorn -w 4 -b 127.0.0.1:5001 --timeout 120 web.viewer:app
```

**Opción C: Con configuración personalizada**
```bash
gunicorn -c config/gunicorn.conf.py web.viewer:app
```

### 4. Gestión de Caché

**Limpiar caché manualmente:**
```bash
curl http://localhost:5001/api/cache/clear
```

**Ver estadísticas de caché:**
```bash
curl http://localhost:5001/api/cache/stats
```

### 5. Variables de Entorno (Opcionales)

Crear/editar `.env`:
```bash
# Tipo de caché (SimpleCache o RedisCache)
CACHE_TYPE=SimpleCache

# Timeout de caché en segundos (default: 300 = 5 minutos)
CACHE_TIMEOUT=300

# Redis (solo si CACHE_TYPE=RedisCache)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://localhost:6379/0

# Configuración de gunicorn
WEB_VIEWER_HOST=127.0.0.1
WEB_VIEWER_PORT=5001
WEB_VIEWER_WORKERS=4
WEB_VIEWER_TIMEOUT=120
WEB_VIEWER_LOG_LEVEL=info
```

---

## 📈 Resultados (Pendiente de Testing)

### Antes
```
[Pendiente benchmark inicial]
```

### Después
```
[Pendiente benchmark final]
```

---

**Autor:** Claude Code + Javi
**Reviewed by:** TBD
