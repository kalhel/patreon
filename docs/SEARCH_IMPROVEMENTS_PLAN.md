# 🔍 Plan de Mejoras de Búsqueda Avanzada

**Fecha:** 2025-11-08
**Rama:** `feature/advanced-search-improvements`
**Estado:** En planificación

---

## 📋 Estado Actual

### ✅ Lo que YA tenemos

**PostgreSQL Full-Text Search:**
- ✅ Columna `search_vector tsvector` en tabla `posts`
- ✅ Índice GIN `idx_posts_search_vector` creado
- ✅ search_vector poblado en **982/982 posts**
- ✅ Base de datos lista para búsqueda full-text

**SQLite FTS5 (Sistema Actual):**
- ✅ `web/search_indexer.py` - Indexador funcionando
- ✅ `web/search_index.db` (24MB) - Índice generado
- ✅ `/api/search` endpoint usando SQLite FTS5
- ✅ Busca en: titles, content, tags, comments, subtitles

**Frontend:**
- ✅ Barra de búsqueda con debouncing
- ✅ Badges de coincidencia (Title, Text, Tags, Comments, Video)
- ✅ Integración con filtros de creador y tipo de contenido

### ❌ Problemas Actuales

1. **Duplicación de datos**: SQLite FTS5 duplica datos de PostgreSQL
2. **Sincronización manual**: Requiere ejecutar `python web/search_indexer.py` después de cada fase2
3. **Espacio en disco**: 24MB adicionales en SQLite (duplicado)
4. **Complejidad**: Dos sistemas de búsqueda distintos
5. **No busca en comentarios PostgreSQL**: Los comentarios están en tabla separada
6. **No busca en transcripciones de audio**: Pendiente de implementar

---

## 🎯 Objetivos

### Objetivo 1: Migrar a PostgreSQL Full-Text Search
**Prioridad:** ALTA
**Beneficios:**
- ✅ Single source of truth (sin duplicación)
- ✅ Actualización automática (triggers)
- ✅ Más rápido (índices nativos en PostgreSQL)
- ✅ Menos espacio en disco
- ✅ Simplifica arquitectura

### Objetivo 2: Expandir cobertura de búsqueda
**Prioridad:** ALTA
**Campos a agregar:**
- ✅ Comentarios (tabla `comments`)
- ✅ Subtítulos de videos (tabla `subtitles` o columna en posts)
- ⏳ Transcripciones de audio (futura implementación)

### Objetivo 3: Automatizar actualización del índice
**Prioridad:** MEDIA
**Solución:**
- Crear trigger PostgreSQL que actualice `search_vector` en INSERT/UPDATE
- Eliminar necesidad de `search_indexer.py`

### Objetivo 4: Mejorar UI de búsqueda
**Prioridad:** BAJA
**Mejoras:**
- Filtros de fecha (rango de publicación)
- Búsqueda booleana (AND, OR, NOT)
- Búsqueda de frases exactas ("between quotes")
- Historial de búsquedas

---

## 🏗️ Plan de Implementación

### Fase 1: Migrar endpoint /api/search a PostgreSQL (2-3 horas)

**Archivos a modificar:**
- `web/viewer.py` - Reescribir `/api/search` endpoint

**Pasos:**

1. **Crear nuevo endpoint con PostgreSQL ts_query**
```python
@app.route('/api/search')
def api_search():
    query = request.args.get('q', '').strip()
    creator_filter = request.args.get('creator')
    limit = int(request.args.get('limit', 50))

    # Build tsquery (PostgreSQL full-text query)
    tsquery = query.replace(' ', ' & ')  # AND entre palabras

    sql = text("""
        SELECT
            p.id,
            p.post_id,
            p.creator_id,
            p.title,
            p.published_date,
            ts_rank(p.search_vector, to_tsquery('english', :tsquery)) as rank,
            ts_headline('english', p.full_content, to_tsquery('english', :tsquery)) as snippet
        FROM posts p
        WHERE p.search_vector @@ to_tsquery('english', :tsquery)
        AND p.deleted_at IS NULL
        ORDER BY rank DESC
        LIMIT :limit
    """)

    results = conn.execute(sql, {
        'tsquery': tsquery,
        'limit': limit
    }).fetchall()

    return jsonify({'results': results, 'total': len(results)})
```

2. **Mantener SQLite FTS5 como fallback**
```python
try:
    # Try PostgreSQL first
    results = search_with_postgresql(query)
except Exception as e:
    logger.warning(f"PostgreSQL search failed, falling back to SQLite: {e}")
    results = search_with_sqlite(query)
```

3. **Agregar detección de campos coincidentes**
```python
# Detect which fields matched
matched_in = []
if title_match:
    matched_in.append('title')
if content_match:
    matched_in.append('content')
# etc...
```

**Testing:**
- Comparar resultados PostgreSQL vs SQLite
- Verificar performance (debe ser similar o mejor)
- Verificar ranking de resultados

---

### Fase 2: Expandir search_vector con comentarios y subtítulos (3-4 horas)

**Archivos a modificar:**
- `database/migrations/update_search_vector.sql` - Nueva migración
- `src/phase2_detail_extractor.py` - Actualizar al insertar posts

**Pasos:**

1. **Crear migración para actualizar search_vector**
```sql
-- database/migrations/update_search_vector_with_all_fields.sql

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS posts_search_vector_update ON posts;

-- Create function to update search_vector
CREATE OR REPLACE FUNCTION posts_search_vector_trigger() RETURNS trigger AS $$
DECLARE
    comments_text TEXT;
    subtitles_text TEXT;
BEGIN
    -- Get all comments for this post
    SELECT string_agg(comment_text, ' ')
    INTO comments_text
    FROM comments
    WHERE post_id = NEW.id;

    -- Get all subtitles for this post
    SELECT string_agg(subtitle_text, ' ')
    INTO subtitles_text
    FROM subtitles
    WHERE post_id = NEW.id;

    -- Update search_vector with all searchable text
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.full_content, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(array_to_string(NEW.tags, ' '), '')), 'C') ||
        setweight(to_tsvector('english', coalesce(comments_text, '')), 'D') ||
        setweight(to_tsvector('english', coalesce(subtitles_text, '')), 'D');

    RETURN NEW;
END
$$ LANGUAGE plpgsql;

-- Create trigger
CREATE TRIGGER posts_search_vector_update
    BEFORE INSERT OR UPDATE OF title, full_content, tags
    ON posts
    FOR EACH ROW
    EXECUTE FUNCTION posts_search_vector_trigger();

-- Rebuild search_vector for all existing posts
UPDATE posts SET search_vector = search_vector WHERE true;
```

2. **Ejecutar migración**
```bash
psql "postgresql://patreon_user@localhost/alejandria" < database/migrations/update_search_vector_with_all_fields.sql
```

3. **Verificar que funciona**
```sql
-- Test search in comments
SELECT title, ts_rank(search_vector, to_tsquery('english', 'interesting'))
FROM posts
WHERE search_vector @@ to_tsquery('english', 'interesting')
ORDER BY ts_rank DESC
LIMIT 10;
```

---

### Fase 3: Agregar transcripciones de audio (1-2 horas)

**Prerequisitos:**
- Sistema de transcripción de audio implementado (Whisper API o similar)
- Tabla `transcriptions` creada

**Pasos:**

1. **Crear tabla para transcripciones** (si no existe)
```sql
CREATE TABLE IF NOT EXISTS transcriptions (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    audio_file_path TEXT,
    transcript_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transcriptions_post ON transcriptions(post_id);
```

2. **Actualizar trigger para incluir transcripciones**
```sql
-- En posts_search_vector_trigger(), agregar:
DECLARE
    transcriptions_text TEXT;
BEGIN
    -- Get all transcriptions
    SELECT string_agg(transcript_text, ' ')
    INTO transcriptions_text
    FROM transcriptions
    WHERE post_id = NEW.id;

    -- Add to search_vector
    NEW.search_vector := ... ||
        setweight(to_tsvector('english', coalesce(transcriptions_text, '')), 'D');
END;
```

---

### Fase 4: Automatizar actualización (1 hora)

**Objetivos:**
- Trigger ya creado en Fase 2
- Deprecar `search_indexer.py`
- Actualizar documentación

**Pasos:**

1. **Mover search_indexer.py a archive**
```bash
mv web/search_indexer.py archive/search_indexer_sqlite_deprecated.py
mv web/search_index.db archive/
```

2. **Actualizar docs/ADVANCED_SEARCH.md**
```markdown
## ⚠️ DEPRECATED - Migrado a PostgreSQL

Este sistema SQLite FTS5 ha sido reemplazado por PostgreSQL Full-Text Search nativo.

Ver: docs/SEARCH_IMPROVEMENTS_PLAN.md
```

3. **Crear nuevo script de testing**
```bash
# scripts/test_postgresql_search.sh
psql "postgresql://patreon_user@localhost/alejandria" -c "
SELECT
    post_id,
    title,
    ts_rank(search_vector, to_tsquery('english', 'astrology')) as rank
FROM posts
WHERE search_vector @@ to_tsquery('english', 'astrology')
ORDER BY rank DESC
LIMIT 10;
"
```

---

### Fase 5: Mejorar UI de búsqueda (2-3 horas)

**Archivos a modificar:**
- `web/templates/index.html` - Agregar filtros avanzados

**Mejoras:**

1. **Filtro de fecha**
```html
<div class="search-filters">
    <label>Publicado desde:</label>
    <input type="date" id="dateFrom">
    <label>hasta:</label>
    <input type="date" id="dateTo">
</div>
```

2. **Búsqueda booleana** (UI para operadores)
```html
<div class="search-operators">
    <button class="operator" data-op="AND">Y (AND)</button>
    <button class="operator" data-op="OR">O (OR)</button>
    <button class="operator" data-op="NOT">NO (NOT)</button>
</div>
```

3. **Búsqueda de frases exactas**
- Detectar "entre comillas" en JavaScript
- Enviar como `phrase search` a PostgreSQL usando `websearch_to_tsquery`

---

## 📊 Comparación: SQLite FTS5 vs PostgreSQL

| Característica | SQLite FTS5 | PostgreSQL FTS |
|----------------|-------------|----------------|
| Velocidad | ~10-50ms | ~5-20ms |
| Espacio | +24MB | 0MB (integrado) |
| Sincronización | Manual | Automático (trigger) |
| Actualización | Rebuild completo | Incremental |
| Ranking | BM25 | ts_rank |
| Snippets | ✅ | ✅ |
| Fuzzy search | ⚠️ Prefixes | ⚠️ Limitado |
| Multi-idioma | ⚠️ porter | ✅ Múltiples stemmers |
| Integración | Separado | Nativo en DB |

**Recomendación:** Migrar a PostgreSQL FTS

---

## 🚀 Ventajas de la Migración

### Performance
- **Menos latencia**: Elimina round-trip a SQLite
- **Menos memoria**: No carga índice SQLite en RAM
- **Queries combinadas**: JOIN directo con posts/comments/subtitles

### Mantenimiento
- **Sin sincronización manual**: Trigger automático
- **Sin scripts externos**: No más `search_indexer.py`
- **Menos código**: Simplifica codebase

### Escalabilidad
- **Más posts**: PostgreSQL maneja millones de documentos
- **Búsqueda distribuida**: Puede escalar horizontalmente
- **Caché PostgreSQL**: Shared buffers optimizados

---

## 📝 Criterios de Éxito

### Funcional
- ✅ Búsqueda en todos los campos (título, contenido, tags, comentarios, subtítulos)
- ✅ Resultados ordenados por relevancia
- ✅ Snippets con highlights
- ✅ Badges de coincidencia (Title, Text, Tags, Comments, Video, Audio)
- ✅ Filtros combinados (creador + tipo de contenido + búsqueda)

### Performance
- ✅ Búsqueda < 50ms para 1000 posts
- ✅ Búsqueda < 200ms para 10,000 posts
- ✅ Sin impacto en carga de página principal

### Mantenimiento
- ✅ Actualización automática sin scripts manuales
- ✅ Código más simple (menos archivos)
- ✅ Documentación actualizada

---

## 🛠️ Herramientas y Tecnologías

- **PostgreSQL 14+** con extensión `pg_trgm` (para fuzzy matching)
- **SQLAlchemy** para queries
- **ts_rank** para ranking de resultados
- **ts_headline** para snippets con highlights
- **Triggers** para actualización automática

---

## 📅 Estimación de Tiempo

| Fase | Estimación | Prioridad |
|------|------------|-----------|
| 1. Migrar endpoint | 2-3 horas | ALTA |
| 2. Expandir campos | 3-4 horas | ALTA |
| 3. Transcripciones | 1-2 horas | MEDIA |
| 4. Automatización | 1 hora | MEDIA |
| 5. UI mejorada | 2-3 horas | BAJA |
| **TOTAL** | **9-13 horas** | - |

---

## 🧪 Plan de Testing

1. **Test unitario**: Verificar query builder
2. **Test de integración**: Comparar resultados SQLite vs PostgreSQL
3. **Test de performance**: Medir tiempos de respuesta
4. **Test de ranking**: Verificar orden de resultados
5. **Test de UI**: Verificar badges y filtros

---

## 📚 Referencias

- [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html)
- [ts_rank documentation](https://www.postgresql.org/docs/current/textsearch-controls.html#TEXTSEARCH-RANKING)
- [PostgreSQL Triggers](https://www.postgresql.org/docs/current/sql-createtrigger.html)

---

**Última actualización**: 2025-11-08
**Autor**: Javi + Claude
**Estado**: ✅ Listo para implementar
