# 🗄️ Revisión de Diseño de Base de Datos - Multi-Fuente

**Fecha:** 2025-11-09
**Contexto:** Antes de implementar Fase 2 de búsqueda

---

## 🎯 Objetivo

Revisar diseño de BD antes de agregar búsqueda en comentarios/subtítulos para asegurar que:
1. ✅ Soporte multi-fuente (Patreon, YouTube, libros, blogs)
2. ✅ Comentarios estén bien estructurados
3. ✅ Sea escalable y mantenible

---

## 📊 Estado Actual

### Schema Version: **V2 (Multi-Fuente)** ✅

```
creators (platform-agnostic)
   ↓
creator_sources (platform-specific: patreon, youtube, substack, etc)
   ↓
posts (content from all sources)
```

**Tablas existentes:**
- ✅ `creators` - Entidades (Ali A Olomi, AstroByMax)
- ✅ `creator_sources` - Fuentes por plataforma
- ✅ `posts` - Contenido de todas las fuentes

**Columnas en `posts`:**
- `source_id` → apunta a `creator_sources` ✅ (V2)
- `creator_id` → legacy string ⚠️ (V1 - deprecar)
- `content_blocks` → JSONB con comentarios
- `patreon_tags` → tags específicos de Patreon

---

## 🔍 Análisis: ¿Dónde Poner los Comentarios?

### Opción 1: Mantener en `content_blocks` JSONB (Actual)

**Estructura actual:**
```json
{
  "content_blocks": [
    {"type": "paragraph", "text": "...", "order": 1},
    {"type": "comment", "text": "...", "author": "John", "order": 8}
  ]
}
```

**Pros:**
- ✅ Ya implementado
- ✅ Mantiene orden de renderizado
- ✅ Flexible para diferentes plataformas
- ✅ Fácil de agregar a `comments_text` para búsqueda
- ✅ No requiere JOINs

**Contras:**
- ⚠️ Difícil de consultar comentarios específicos
- ⚠️ No se puede buscar "posts con >10 comentarios" eficientemente
- ⚠️ No se pueden hacer relaciones (likes en comentarios, respuestas anidadas)

**Casos de uso soportados:**
- ✅ Renderizar post completo con orden correcto
- ✅ Búsqueda full-text en comentarios
- ✅ Exportar/backup
- ❌ Análisis de comentarios (top commenters, etc)
- ❌ Relaciones entre comentarios
- ❌ Editar/moderar comentarios individualmente

---

### Opción 2: Tabla `comments` separada (Normalizado)

**Estructura propuesta:**
```sql
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,

    -- Content
    comment_text TEXT NOT NULL,
    author_name VARCHAR(255),
    author_id VARCHAR(255),  -- Platform-specific author ID

    -- Threading
    parent_comment_id INTEGER REFERENCES comments(id),  -- For nested replies
    thread_level INTEGER DEFAULT 0,

    -- Metadata
    platform VARCHAR(50),  -- 'patreon', 'youtube', etc
    platform_comment_id VARCHAR(255),  -- Original ID on platform
    like_count INTEGER DEFAULT 0,

    -- Ordering (for rendering)
    position_in_post INTEGER,  -- Orden dentro del post

    -- Timestamps
    created_at TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(platform, platform_comment_id)
);

CREATE INDEX idx_comments_post ON comments(post_id);
CREATE INDEX idx_comments_parent ON comments(parent_comment_id);
```

**Pros:**
- ✅ Queries eficientes ("posts con >10 comentarios")
- ✅ Relaciones (respuestas anidadas, likes)
- ✅ Análisis de comentadores top
- ✅ Moderación individual
- ✅ Multi-plataforma (YouTube comments, Patreon, etc)
- ✅ Se puede crear FTS index en `comments` directamente

**Contras:**
- ⚠️ Requiere JOIN para renderizar post completo
- ⚠️ Más complejo de mantener
- ⚠️ Migración de datos existentes

**Casos de uso soportados:**
- ✅ Renderizar post completo (con JOIN)
- ✅ Búsqueda full-text en comentarios
- ✅ Análisis avanzado de comentarios
- ✅ Respuestas anidadas
- ✅ Moderar comentarios individualmente
- ✅ Multi-plataforma nativo

---

### Opción 3: Híbrido (RECOMENDADO para ahora) ⭐

**Estrategia:**
1. **Mantener `content_blocks`** para renderizado rápido
2. **Agregar columna `comments_text`** para búsqueda
3. **Considerar tabla `comments`** cuando sea necesario análisis

```sql
-- Fase 2 (ahora): Agregar columna para búsqueda
ALTER TABLE posts ADD COLUMN comments_text TEXT;

-- Poblar desde content_blocks
UPDATE posts SET comments_text = (
    SELECT string_agg(block->>'text', ' ')
    FROM jsonb_array_elements(content_blocks) AS block
    WHERE block->>'type' = 'comment'
);

-- Incluir en search_vector
UPDATE posts SET search_vector =
    ... || setweight(to_tsvector('english', COALESCE(comments_text, '')), 'D');
```

**Pros:**
- ✅ Simple de implementar (Fase 2)
- ✅ Búsqueda rápida
- ✅ No rompe nada existente
- ✅ Deja puerta abierta para tabla separada después

**Contras:**
- ⚠️ Duplicación (comments en content_blocks Y comments_text)
- ⚠️ No resuelve análisis avanzado

---

## 🌐 Multi-Fuente: ¿Funciona el diseño actual?

### Casos de Uso

#### 1. **Posts de Patreon** (Actual) ✅
```
creator: Ali A Olomi
source: patreon (creator_sources.platform = 'patreon')
posts: 342 posts de Patreon
```

#### 2. **Videos de YouTube** (Futuro)
```
creator: Ali A Olomi
source: youtube (creator_sources.platform = 'youtube')
posts: videos de YouTube como posts
content_blocks: descripción + timestamps + comentarios
```

**Adaptaciones necesarias:**
- `platform_post_id` → YouTube video ID
- `content_blocks` → descripción formateada
- `comments_text` → comentarios de YouTube
- `patreon_tags` → renombrar a `tags` (platform-agnostic)

#### 3. **Artículos de Blog** (Futuro)
```
creator: Ali A Olomi
source: substack (creator_sources.platform = 'substack')
posts: artículos de blog
```

**Adaptaciones necesarias:**
- `platform_post_id` → Substack post slug
- `content_blocks` → HTML parseado
- ✅ Ya funciona con diseño actual

#### 4. **Libros** (Futuro)
```
creator: Abu Ma'shar
source: goodreads (creator_sources.platform = 'goodreads')
posts: capítulos o libros completos
```

**Pregunta:** ¿Un libro es un `post`?

**Opciones:**
- **A)** Un libro = 1 post con capítulos en `content_blocks`
- **B)** Un libro = collection, cada capítulo = 1 post
- **C)** Crear tabla `books` separada

**Recomendación:** Opción B (usar `collections`)
- `collections.title` = "Libro: On the Great Conjunctions"
- `posts` = capítulos individuales
- ✅ Reutiliza infraestructura existente

---

## 📋 Columnas a Renombrar/Generalizar

### Para ser platform-agnostic:

| Columna Actual | Mejor Nombre | Razón |
|----------------|--------------|-------|
| `patreon_tags` | `tags` | Todas las plataformas tienen tags |
| `creator_id` (string) | **Eliminar** | Usar `source_id` (FK a creator_sources) |
| `creator_name` | **Deprecar** | Obtener de JOIN con creators |
| `creator_avatar` | **Deprecar** | Obtener de creators.avatar_filename |

**Migración sugerida (futura):**
```sql
-- Renombrar
ALTER TABLE posts RENAME COLUMN patreon_tags TO tags;

-- Deprecar (mantener temporalmente para compatibilidad)
-- creator_id, creator_name, creator_avatar
-- → Obtener via JOIN:
-- SELECT p.*, c.name, c.avatar_filename
-- FROM posts p
-- JOIN creator_sources cs ON p.source_id = cs.id
-- JOIN creators c ON cs.creator_id = c.id
```

---

## 🎯 Recomendaciones

### Inmediato (Fase 2):
1. ✅ **Agregar columna `comments_text`** a `posts`
2. ✅ **Agregar columna `subtitles_text`** a `posts`
3. ✅ **Incluir en `search_vector`**
4. ⏳ **No cambiar estructura** de `content_blocks`

### Corto Plazo (próximos meses):
1. ⚠️ **Renombrar `patreon_tags` → `tags`**
2. ⚠️ **Deprecar `creator_id` (string)** - usar solo `source_id`
3. ⚠️ **Deprecar `creator_name`, `creator_avatar`** - JOIN con `creators`

### Largo Plazo (cuando agregues otras fuentes):
1. **Tabla `comments` separada** si necesitas:
   - Análisis de comentarios
   - Respuestas anidadas
   - Moderación
2. **Usar `collections`** para libros (capítulos = posts)
3. **Generalizar scrapers** para multi-fuente

---

## ✅ Decisión para Fase 2

**Proceder con Opción 3 (Híbrido):**

```sql
-- 1. Agregar columnas
ALTER TABLE posts ADD COLUMN comments_text TEXT;
ALTER TABLE posts ADD COLUMN subtitles_text TEXT;

-- 2. Poblar comments_text desde content_blocks
UPDATE posts SET comments_text = (
    SELECT string_agg(block->>'text', ' ')
    FROM jsonb_array_elements(content_blocks) AS block
    WHERE block->>'type' = 'comment'
);

-- 3. Poblar subtitles_text (Python script para leer .vtt)
-- (Fase 2b)

-- 4. Actualizar search_vector
UPDATE posts SET search_vector =
    setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(full_content, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(array_to_string(patreon_tags, ' '), '')), 'C') ||
    setweight(to_tsvector('english', COALESCE(comments_text, '')), 'D') ||
    setweight(to_tsvector('english', COALESCE(subtitles_text, '')), 'D');
```

**Ventajas:**
- ✅ Simple y rápido
- ✅ No rompe nada
- ✅ Búsqueda funcional
- ✅ Deja opciones abiertas

**Desventajas:**
- ⚠️ Duplicación de datos (comments en 2 lugares)
- ⚠️ No resuelve análisis de comentarios (pero no es necesario ahora)

---

## 🚀 Próximos Pasos

1. **Implementar Fase 2** con diseño híbrido
2. **Documentar** estructura multi-fuente
3. **Planear migración** de columnas legacy cuando agregues otra fuente
4. **Evaluar tabla `comments`** cuando necesites análisis

---

**Conclusión:** El diseño actual (Schema V2) **SÍ soporta multi-fuente**. Solo necesitas:
- Renombrar `patreon_tags` → `tags`
- Deprecar columnas legacy (`creator_id`, `creator_name`, `creator_avatar`)
- Mantener `content_blocks` flexible por plataforma

**¿Proceder con Fase 2 usando Opción 3 (Híbrido)?**
