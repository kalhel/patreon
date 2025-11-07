# 🔄 Schema Refactor Plan: Multi-Source Creator Model

**Fecha de creación**: 2025-11-07
**Prioridad**: **CRÍTICA** - Debe hacerse ANTES de Phase 2
**Razón**: Diseño actual no soporta correctamente creadores con múltiples fuentes

---

## 🚨 Problema Identificado

### Diseño Actual (INCORRECTO)
```sql
CREATE TABLE creators (
    creator_id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    platform VARCHAR(100),  -- ❌ PROBLEMA: Un creador = Una plataforma
    platform_id VARCHAR(255),
    ...
);

CREATE TABLE posts (
    post_id SERIAL PRIMARY KEY,
    creator_id INTEGER REFERENCES creators(creator_id),
    ...
);
```

**Limitación**: Si "Astrobymax" tiene Patreon + YouTube, serían **2 registros separados** en `creators`.

### Caso de Uso Real
Un creador como **"Astrobymax"** puede tener:
- ✅ Patreon: https://patreon.com/astrobymax
- ✅ YouTube: https://youtube.com/@astrobymax
- ✅ Substack: https://astrobymax.substack.com
- ✅ Podcast en Spotify
- ✅ Blog personal

Con el schema actual:
- 5 registros en `creators` (uno por plataforma)
- No hay forma de saber que son el mismo creador
- Duplicación de datos (nombre, avatar, descripción)
- Imposible consultar "todos los posts de Astrobymax de todas las fuentes"

---

## ✅ Diseño Propuesto (CORRECTO)

### Nueva Estructura de Tablas

```sql
-- ==========================================
-- TABLA 1: CREATORS (Personas/Entidades)
-- ==========================================
CREATE TABLE creators (
    creator_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,  -- Nombre del creador (ej: "Astrobymax")
    display_name VARCHAR(255),          -- Nombre para mostrar (puede ser diferente)
    description TEXT,                   -- Bio del creador
    avatar_url VARCHAR(500),            -- Avatar principal del creador
    website_url VARCHAR(500),           -- Sitio web personal
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- TABLA 2: CREATOR_SOURCES (Plataformas/Canales)
-- ==========================================
CREATE TABLE creator_sources (
    source_id SERIAL PRIMARY KEY,
    creator_id INTEGER NOT NULL REFERENCES creators(creator_id) ON DELETE CASCADE,

    -- Identificación de la plataforma
    platform VARCHAR(100) NOT NULL,     -- 'patreon', 'youtube', 'substack', 'spotify', etc.
    platform_id VARCHAR(255) NOT NULL,  -- ID único en esa plataforma
    platform_url VARCHAR(500),          -- URL del perfil/canal
    platform_username VARCHAR(255),     -- Username en esa plataforma

    -- Metadatos específicos de plataforma (JSONB para flexibilidad)
    platform_metadata JSONB,            -- Datos específicos (tier levels, subscriber count, etc.)

    -- Estado
    is_active BOOLEAN DEFAULT true,     -- Si se debe scrapear esta fuente
    last_scraped_at TIMESTAMP,          -- Última vez que se scrapeó

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE(platform, platform_id)       -- No duplicar mismo perfil de plataforma
);

CREATE INDEX idx_creator_sources_creator ON creator_sources(creator_id);
CREATE INDEX idx_creator_sources_platform ON creator_sources(platform);
CREATE INDEX idx_creator_sources_active ON creator_sources(is_active);

-- ==========================================
-- TABLA 3: POSTS (Contenido de cada fuente)
-- ==========================================
CREATE TABLE posts (
    post_id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES creator_sources(source_id) ON DELETE CASCADE,

    -- Identificación del post
    platform_post_id VARCHAR(255) NOT NULL,  -- ID del post en la plataforma
    title VARCHAR(500),
    content TEXT,
    post_url VARCHAR(1000) NOT NULL,

    -- Metadatos del post
    published_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE(source_id, platform_post_id)  -- No duplicar posts de la misma fuente
);

CREATE INDEX idx_posts_source ON posts(source_id);
CREATE INDEX idx_posts_published ON posts(published_at DESC);

-- ==========================================
-- TABLA 4: SCRAPING_STATUS (Estado de scraping)
-- ==========================================
CREATE TABLE scraping_status (
    status_id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
    source_id INTEGER NOT NULL REFERENCES creator_sources(source_id),

    -- Estado de las fases
    phase1_status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'completed', 'failed'
    phase1_completed_at TIMESTAMP,

    phase2_status VARCHAR(50) DEFAULT 'pending',
    phase2_completed_at TIMESTAMP,

    phase3_status VARCHAR(50) DEFAULT 'pending',
    phase3_completed_at TIMESTAMP,

    -- Tracking
    attempt_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP,
    error_message TEXT,

    -- Migration flag
    firebase_migrated BOOLEAN DEFAULT false,
    firebase_data JSONB,  -- Datos originales de Firebase para referencia

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(post_id)  -- Un post solo tiene un registro de status
);

CREATE INDEX idx_scraping_status_post ON scraping_status(post_id);
CREATE INDEX idx_scraping_status_source ON scraping_status(source_id);
CREATE INDEX idx_scraping_status_phase1 ON scraping_status(phase1_status);
CREATE INDEX idx_scraping_status_phase2 ON scraping_status(phase2_status);
```

---

## 📊 Ejemplo de Datos

### Ejemplo 1: Astrobymax (Solo Patreon por ahora)
```sql
-- 1. Crear el creador
INSERT INTO creators (creator_id, name, description) VALUES
(1, 'Astrobymax', 'Astronomy content creator');

-- 2. Añadir su fuente de Patreon
INSERT INTO creator_sources (source_id, creator_id, platform, platform_id, platform_url) VALUES
(1, 1, 'patreon', 'astrobymax', 'https://www.patreon.com/astrobymax');

-- 3. Posts pertenecen a la fuente
INSERT INTO posts (source_id, platform_post_id, title, post_url) VALUES
(1, '12345', 'How Stars Form', 'https://www.patreon.com/posts/12345');
```

### Ejemplo 2: Astrobymax expande a YouTube
```sql
-- Solo añadir nueva fuente (el creador ya existe)
INSERT INTO creator_sources (creator_id, platform, platform_id, platform_url) VALUES
(1, 'youtube', 'UC_astrobymax', 'https://youtube.com/@astrobymax');

-- Posts de YouTube
INSERT INTO posts (source_id, platform_post_id, title, post_url) VALUES
(2, 'dQw4w9WgXcQ', 'Star Formation Video', 'https://youtube.com/watch?v=dQw4w9WgXcQ');
```

### Consultas Útiles
```sql
-- Todos los posts de Astrobymax de todas las fuentes
SELECT p.*, cs.platform, c.name
FROM posts p
JOIN creator_sources cs ON p.source_id = cs.source_id
JOIN creators c ON cs.creator_id = c.creator_id
WHERE c.name = 'Astrobymax'
ORDER BY p.published_at DESC;

-- Fuentes activas de cada creador
SELECT c.name, cs.platform, cs.platform_url, cs.is_active
FROM creators c
JOIN creator_sources cs ON c.creator_id = cs.creator_id
WHERE cs.is_active = true;

-- Posts por plataforma de un creador
SELECT cs.platform, COUNT(p.post_id) as post_count
FROM creators c
JOIN creator_sources cs ON c.creator_id = cs.creator_id
JOIN posts p ON cs.source_id = p.source_id
WHERE c.name = 'Astrobymax'
GROUP BY cs.platform;
```

---

## 🔧 Plan de Migración

### Paso 1: Crear Nuevas Tablas (Schema V2)
```bash
# Crear nuevo schema file
cp database/schema.sql database/schema_v2.sql

# Editar schema_v2.sql con el diseño correcto
```

### Paso 2: Migrar Datos Existentes (982 posts)
```sql
-- Script de migración (scripts/migrate_to_multisource_schema.py)

1. Extraer creadores únicos de tabla actual:
   SELECT DISTINCT name FROM creators;

2. Insertar en nueva tabla creators (sin platform):
   INSERT INTO creators (name, ...) VALUES (...);

3. Crear una fuente 'patreon' por cada creador antiguo:
   INSERT INTO creator_sources (creator_id, platform, platform_id, ...)
   SELECT creator_id, 'patreon', platform_id, ... FROM old_creators;

4. Re-mapear posts a las nuevas sources:
   UPDATE posts SET source_id = (
     SELECT source_id FROM creator_sources
     WHERE creator_id = old_creator_id
   );

5. Migrar scraping_status añadiendo source_id:
   UPDATE scraping_status SET source_id = (
     SELECT source_id FROM posts WHERE post_id = scraping_status.post_id
   );
```

### Paso 3: Actualizar Scripts Python
```python
# Antes (schema viejo):
creator = db.query(Creator).filter_by(name='Astrobymax', platform='patreon').first()

# Después (schema nuevo):
creator = db.query(Creator).filter_by(name='Astrobymax').first()
source = db.query(CreatorSource).filter_by(
    creator_id=creator.creator_id,
    platform='patreon'
).first()
```

### Paso 4: Actualizar Web Viewer
```python
# web/viewer.py - Actualizar queries
# Ahora posts vienen de sources que pertenecen a creators
```

---

## ✅ Ventajas del Nuevo Diseño

1. **Escalabilidad**: Fácil añadir YouTube, Substack, Spotify sin duplicar creadores
2. **Normalización**: Datos del creador (nombre, avatar, bio) en un solo lugar
3. **Consultas lógicas**: "Dame todos los posts de X de todas las plataformas"
4. **Flexibilidad**: Cada plataforma puede tener metadatos únicos (JSONB)
5. **Web viewer mejorado**: Filtrar por creador o por plataforma
6. **Analytics**: "¿Qué plataforma tiene más posts de este creador?"

---

## ⚠️ Consideraciones

### 1. Impacto en el Proyecto
- **Scripts Python**: Necesitan actualización (pero no han sido migrados aún ✅)
- **Web viewer**: Necesita actualización de queries
- **982 posts existentes**: Necesitan migración (script automatizado)

### 2. Timing Perfecto
Estamos en el **momento ideal** para hacer esto porque:
- ✅ Phase 0 y Phase 1 completos
- ✅ Phase 2 (migración de scripts) **NO ha empezado**
- ✅ Solo tenemos datos de prueba (982 posts)
- ✅ Mejor arreglarlo ahora que después de tener 10,000+ posts

### 3. Orden de Ejecución
```
ANTES de Phase 2:
1. Aprobar este diseño de schema
2. Crear schema_v2.sql
3. Crear script de migración de datos
4. Ejecutar migración (982 posts)
5. Verificar migración
6. Actualizar web viewer queries

DESPUÉS:
7. Continuar con Phase 2 (crear PostgresTracker con schema correcto)
```

---

## 📝 Respuestas a Preguntas de Diseño

### 1. **Nombres de creadores únicos** ✅ RESPONDIDO

**Decisión**: Usar `name` UNIQUE (sin slug adicional) porque:
- Los creadores son personas/entidades reales (no habrá duplicados)
- Si se necesita URL-friendly, se puede generar dinámicamente: `name.lower().replace(' ', '-')`
- Simplifica el schema

```sql
CREATE TABLE creators (
    creator_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,  -- "Astrobymax" (único globalmente)
    ...
);
```

### 2. **Avatares** ✅ RESPONDIDO

**Decisión**: **Opción C** - Avatar principal + avatar por plataforma (flexibilidad máxima)

**Razón**: Después de investigar `web/viewer.py`:
- Los avatares actualmente se guardan en `web/static/{creator_id}.jpg`
- Settings permite upload de avatar por creator
- Cada plataforma puede tener su propio avatar (YouTube vs Patreon pueden ser diferentes)

```sql
CREATE TABLE creators (
    ...
    avatar_filename VARCHAR(255),  -- Avatar principal (ej: "astrobymax.jpg")
);

CREATE TABLE creator_sources (
    ...
    platform_avatar_url VARCHAR(500),  -- Avatar específico de la plataforma (opcional)
);
```

**Lógica de display**: Si `platform_avatar_url` existe, usar ese. Si no, usar `creators.avatar_filename`.

**HALLAZGO IMPORTANTE**: Los 7 avatares en root directory (`astrobymax.jpg`, `horoi.jpg`, etc.) **NO son usados** por el web viewer actual. Son antiguos/backups y pueden moverse a `archive/` sin problema.

### 3. **Settings/Admin** ✅ RESPONDIDO

**Decisión**: El settings ya existe y es muy completo. Soporta:
- ✅ Crear creadores manualmente (ya implementado en `web/templates/settings.html`)
- ✅ Editar/eliminar creadores (ya implementado)
- ✅ Upload de avatares (ya implementado - se guarda en `web/static/`)
- ✅ Vista de estado de procesamiento (Phase 1, 2, 3)

**Lo que falta añadir después del refactor**:
- [ ] **CRUD de fuentes** (añadir/eliminar sources a un creator existente)
- [ ] **Toggle is_active** por source (activar/desactivar fuentes sin borrarlas)
- [ ] **Vista de todas las fuentes** de todos los creadores

### 4. **Migration strategy** ✅ RESPONDIDO

**Decisión**: **Opción A** - Migrar los 982 posts (preservar datos)

**Razón**:
- Los 982 posts son datos reales ya scrapeados
- Preservarlos ahorra tiempo de re-scraping
- Firebase data ya está preservado en `firebase_data` JSONB
- Script de migración será automatizado y reversible

```bash
# Migration será:
1. Crear schema_v2.sql con diseño correcto
2. Backup de datos actuales (pg_dump)
3. Script Python para migrar datos automáticamente
4. Verificación post-migración
5. Rollback plan si algo falla
```

---

## 🎯 Próximos Pasos Inmediatos

**Esperando aprobación del usuario para**:
1. Confirmar que este diseño tiene sentido
2. Responder las 4 preguntas arriba
3. Crear schema_v2.sql
4. Crear script de migración
5. Ejecutar migración
6. Continuar con Phase 2

---

**Última actualización**: 2025-11-07
**Estado**: Propuesta pendiente de aprobación
**Bloquea**: Phase 2 (debe resolverse primero)
