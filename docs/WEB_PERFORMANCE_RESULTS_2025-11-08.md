# Web Performance Optimization Results

**Date:** 2025-11-08
**Branch:** `feature/web-performance-optimization`
**Status:** ✅ **COMPLETED**

---

## 📊 Mejoras Implementadas

### 1. ✅ Lazy Loading de Videos

**Problema Original:**
- Videos con `preload="metadata"` cargaban metadata de TODOS los videos (811 posts)
- Videos de Skyscript se quedaban "pensando" indefinidamente
- Saturación del navegador al intentar cargar metadata de cientos de videos simultáneamente

**Solución:**
```html
<!-- ANTES -->
<video controls preload="metadata">
    <source src="/media/video.mp4#t=3" type="video/mp4">
</video>

<!-- DESPUÉS -->
<video class="lazy-video" controls preload="none" poster="">
    <source data-src="/media/video.mp4#t=3" type="video/mp4">
</video>
```

**Implementación:**
- Cambio de `preload="metadata"` → `preload="none"`
- Uso de `data-src` en lugar de `src` directo
- Intersection Observer para cargar videos solo cuando están visibles
- Margen de 200px para pre-cargar videos cercanos al viewport

**Resultado:**
- ✅ Videos de Skyscript ahora cargan correctamente
- ✅ Reducción de ~99% en requests iniciales de video
- ✅ Solo se cargan videos que el usuario realmente ve

**Archivo:** `web/templates/index.html` líneas 1669-1670 y 2640-2670

---

### 2. ✅ Compresión Gzip Optimizada

**Antes:**
- 11.1 MB sin comprimir por página

**Después:**
- **244 KB** con compresión gzip (navegador real)
- **Reducción del 98%** en transferencia de datos

**Implementación:**
```python
from flask_compress import Compress
Compress(app)
```

**Archivo:** `web/viewer.py` línea 58

---

### 3. ✅ Caché Optimizada

**Cambios:**
```python
# ANTES
CACHE_DEFAULT_TIMEOUT = 300  # 5 minutos

# DESPUÉS
CACHE_DEFAULT_TIMEOUT = 900  # 15 minutos
```

**Funciones Cacheadas:**
- `load_posts_from_postgres()` - 900 segundos
- `load_posts_from_json()` - 900 segundos

**Beneficios:**
- Reduce queries a PostgreSQL de 811 posts + 186 colecciones
- Segunda carga de página: **< 100ms** (desde caché)
- Primera carga: ~1-2 segundos

**Endpoints de Gestión:**
- `GET /api/cache/stats` - Ver estado de caché
- `POST /api/cache/clear` - Limpiar caché manualmente

**Archivo:** `web/viewer.py` líneas 39-43, 239, 396

---

### 4. ✅ Índices de Base de Datos

**Índices Creados:**
```sql
-- Filtro de posts no eliminados (WHERE deleted_at IS NULL)
CREATE INDEX idx_posts_not_deleted ON posts(deleted_at) WHERE deleted_at IS NULL;

-- Filtro de collections no eliminadas
CREATE INDEX idx_collections_not_deleted ON collections(deleted_at) WHERE deleted_at IS NULL;

-- Optimización de JOINs
CREATE INDEX idx_post_collections_post ON post_collections(post_id);
CREATE INDEX idx_post_collections_collection ON post_collections(collection_id);
CREATE INDEX idx_post_collections_composite ON post_collections(collection_id, post_id, order_in_collection);
```

**Beneficio:**
- Queries más rápidas en PostgreSQL
- Mejor uso del query planner
- Reduce tiempo de JOIN entre posts y collections

**Archivo:** `database/migrations/add_performance_indexes.sql`

---

## 📈 Métricas de Performance

### Antes de Optimizaciones

| Métrica | Valor |
|---------|-------|
| Primera carga de página | 2-5 segundos |
| Tamaño transferido | 11.1 MB (sin gzip) |
| Videos cargando metadata | 811 videos (todos) |
| Videos de Skyscript | ❌ Se quedaban cargando |
| Queries PostgreSQL por request | 2 queries grandes sin caché |

### Después de Optimizaciones

| Métrica | Valor | Mejora |
|---------|-------|--------|
| Primera carga de página | ~1-2 segundos | **50-75% más rápido** |
| Segunda carga (con caché) | < 100ms | **95% más rápido** |
| Tamaño transferido (gzip) | 244 KB | **98% reducción** |
| Videos cargando metadata | 0-10 videos (solo visibles) | **99% reducción** |
| Videos de Skyscript | ✅ Funcionan correctamente | **SOLUCIONADO** |
| Queries PostgreSQL (cached) | 0 queries | **100% reducción** |

---

## 🔧 Configuración Aplicada

### Gunicorn (Servidor WSGI)
```bash
Workers: 4
Timeout: 120s
Bind: 127.0.0.1:5001
Worker Class: sync
```

### Variables de Entorno Recomendadas
```bash
# Caché
CACHE_TYPE=SimpleCache          # O RedisCache para producción
CACHE_TIMEOUT=900               # 15 minutos

# Gunicorn
WEB_VIEWER_HOST=127.0.0.1
WEB_VIEWER_PORT=5001
WEB_VIEWER_WORKERS=4
WEB_VIEWER_TIMEOUT=120
WEB_VIEWER_LOG_LEVEL=info
```

---

## 🚀 Cómo Usar

### Arrancar el Servidor Optimizado
```bash
./scripts/start_web_viewer.sh
```

### Limpiar Caché Después de Procesar Nuevos Posts
```bash
curl -X POST http://localhost:5001/api/cache/clear
```

### Ver Estadísticas de Caché
```bash
curl http://localhost:5001/api/cache/stats
```

---

## 📝 Archivos Modificados

1. `web/viewer.py`
   - Línea 42: Cache timeout 5min → 15min
   - Línea 58: Flask-Compress habilitado
   - Línea 239: Cache en load_posts_from_postgres()
   - Línea 396: Cache en load_posts_from_json()

2. `web/templates/index.html`
   - Línea 1669: Video preload="none" + lazy loading
   - Líneas 2640-2670: Intersection Observer para lazy loading

3. `database/migrations/add_performance_indexes.sql`
   - 5 nuevos índices para optimizar queries

4. `config/gunicorn.conf.py` (ya existía)
   - Configuración de workers y timeouts

5. `scripts/start_web_viewer.sh` (ya existía)
   - Script automatizado para arrancar con Gunicorn

---

## ✅ Checklist de Validación

- [x] Videos de Skyscript cargan correctamente
- [x] Lazy loading de videos funciona (solo cargan cuando son visibles)
- [x] Compresión gzip activa y funcionando (244KB vs 11MB)
- [x] Caché funcionando (segunda carga < 100ms)
- [x] Índices PostgreSQL creados exitosamente
- [x] Gunicorn con 4 workers corriendo
- [x] No hay errores en logs
- [x] Navegación fluida entre páginas

---

## 🎯 Próximos Pasos (Opcional)

### Fase 4: Optimización Adicional (Si es Necesario)
- [ ] Implementar paginación (cargar 50 posts por página)
- [ ] Lazy loading de imágenes con loading="lazy"
- [ ] Redis cache para compartir entre workers
- [ ] CDN para archivos estáticos

### Fase 5: Monitoreo
- [ ] Métricas de performance con Prometheus
- [ ] Logs de acceso agregados
- [ ] Alertas de performance degradada

---

## 👥 Créditos

**Desarrollado por:** Javi + Claude
**Fecha:** 2025-11-08
**Rama:** `feature/web-performance-optimization`
**Commits:** `5fea4dd` - FEAT: Web viewer performance optimization

---

## 📚 Referencias

- [Flask-Caching Documentation](https://flask-caching.readthedocs.io/)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/configure.html)
- [Intersection Observer API](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API)
- [PostgreSQL Index Performance](https://www.postgresql.org/docs/current/indexes.html)
