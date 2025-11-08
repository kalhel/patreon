# 🏗️ Arquitectura Técnica - Sistema Integrado

**Última actualización**: 2025-11-07
**Estado**: Propuesta de arquitectura integral y escalable

---

## 📋 Índice

1. [Visión General](#visión-general)
2. [Análisis de Componentes Clave](#análisis-de-componentes-clave)
3. [Arquitectura Propuesta](#arquitectura-propuesta)
4. [Stack Tecnológico](#stack-tecnológico)
5. [Plan de Migración](#plan-de-migración)
6. [Integración de Features del Roadmap](#integración-de-features-del-roadmap)

---

## 🎯 Visión General

### Situación Actual

El sistema actual funciona con:
- ✅ **Almacenamiento**: JSONs para datos, archivos locales para media
- ✅ **Scraping**: Scripts separados (fase 1, 2, 3) con Firebase para tracking
- ✅ **Web**: Flask simple con SQLite para búsqueda (FTS5)
- ✅ **Procesamiento**: Síncrono, secuencial, sin colas

### Problemas Identificados

1. **JSONs frágiles**: Corrupción ocasional, no escalables
2. **Sin sistema de colas**: Procesamiento síncrono, sin reintentos
3. **Deduplicación manual**: Archivos duplicados consumen espacio
4. **Búsqueda limitada**: Solo full-text, sin búsqueda semántica
5. **No multi-usuario**: Sin autenticación ni personalización
6. **Arquitectura monolítica**: Difícil añadir nuevas fuentes

### Visión Objetivo

Un sistema **modular, escalable y robusto** con:

- 🗄️ **Base de datos central** para todos los datos estructurados
- ⚙️ **Sistema de colas** para procesamiento asíncrono y resiliente
- 🔍 **Búsqueda multi-capa** (full-text + semántica + transcripciones)
- 👥 **Multi-usuario** con autenticación segura
- 🧩 **Arquitectura de plugins** para múltiples fuentes
- 📦 **Containerizado** y fácil de desplegar

---

## 🔍 Análisis de Componentes Clave

### 1. Base de Datos Central 🗄️

**¿Por qué es fundamental?**

La migración de JSONs a una base de datos es el **foundation** de todo. Afecta:

- ✅ Almacenamiento de posts, creators, collections
- ✅ Gestión de usuarios y autenticación
- ✅ Tracking de media (deduplicación)
- ✅ Estado de jobs en colas
- ✅ Configuración del sistema
- ✅ Datos de personalización de usuarios (listas, notas, estados)
- ✅ Índice de búsqueda

**Tecnología propuesta: PostgreSQL**

**¿Por qué PostgreSQL y no SQLite/otros?**

| Feature | SQLite | PostgreSQL | MongoDB |
|---------|--------|------------|---------|
| Multi-usuario concurrente | ❌ Limitado | ✅ Excelente | ✅ Bueno |
| Full-text search | ✅ FTS5 | ✅ tsvector/tsquery | ⚠️ Text indexes |
| JSON support | ✅ JSON1 | ✅ JSONB nativo | ✅ Nativo |
| Extensiones | ❌ Pocas | ✅ pgvector, etc | ❌ |
| Escalabilidad | ❌ Limitada | ✅ Excelente | ✅ Horizontal |
| Backup/restore | ✅ Simple | ✅ Robusto | ✅ Bueno |
| Complejidad setup | ✅ Cero | ⚠️ Media | ⚠️ Media |

**Decisión: PostgreSQL**
- ✅ Soporta todo lo que necesitamos ahora y futuro
- ✅ pgvector para embeddings (búsqueda semántica)
- ✅ JSONB para flexibilidad en datos no estructurados
- ✅ Full-text search robusto
- ✅ Perfecto para multi-usuario

**Esquema de base de datos propuesto:**

```sql
-- Core entities
CREATE TABLE creators (
    id SERIAL PRIMARY KEY,
    creator_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    avatar_url TEXT,
    patreon_url TEXT,
    active BOOLEAN DEFAULT true,
    scraper_enabled BOOLEAN DEFAULT true,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE collections (
    id SERIAL PRIMARY KEY,
    collection_id VARCHAR(100) UNIQUE NOT NULL,
    creator_id INTEGER REFERENCES creators(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    cover_image_url TEXT,
    post_count INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    post_id VARCHAR(100) UNIQUE NOT NULL,
    creator_id INTEGER REFERENCES creators(id),
    title VARCHAR(1000) NOT NULL,
    content TEXT,
    content_blocks JSONB,  -- Estructura de bloques
    published_at TIMESTAMP,
    patreon_url TEXT,

    -- Media counts
    image_count INTEGER DEFAULT 0,
    video_count INTEGER DEFAULT 0,
    audio_count INTEGER DEFAULT 0,

    -- Search
    search_vector tsvector,  -- Full-text search
    embedding vector(1536),  -- Semantic search (OpenAI embeddings)

    -- Metadata
    tags TEXT[],
    metadata JSONB,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Many-to-many: posts <-> collections
CREATE TABLE post_collections (
    post_id INTEGER REFERENCES posts(id),
    collection_id INTEGER REFERENCES collections(id),
    position INTEGER,
    PRIMARY KEY (post_id, collection_id)
);

-- Media management with deduplication
CREATE TABLE media_files (
    id SERIAL PRIMARY KEY,
    file_hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA256
    file_type VARCHAR(20) NOT NULL,  -- 'image', 'video', 'audio'
    file_path TEXT NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),

    -- Image specific
    width INTEGER,
    height INTEGER,

    -- Video/Audio specific
    duration FLOAT,

    -- Metadata
    metadata JSONB,

    -- Deduplication tracking
    reference_count INTEGER DEFAULT 0,
    first_seen_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE post_media (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id),
    media_id INTEGER REFERENCES media_files(id),
    media_type VARCHAR(20),
    position INTEGER,
    caption TEXT,
    is_cover BOOLEAN DEFAULT false,

    UNIQUE (post_id, media_id, position)
);

-- Transcriptions (audio/video)
CREATE TABLE transcriptions (
    id SERIAL PRIMARY KEY,
    media_id INTEGER REFERENCES media_files(id) UNIQUE,
    transcript_text TEXT NOT NULL,
    transcript_vtt TEXT,  -- WebVTT format with timestamps
    language VARCHAR(10),
    confidence_score FLOAT,
    transcribed_at TIMESTAMP DEFAULT NOW(),

    -- Search in transcriptions
    search_vector tsvector
);

-- User management
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',  -- 'admin', 'user', 'readonly'

    -- 2FA
    totp_secret VARCHAR(32),
    totp_enabled BOOLEAN DEFAULT false,

    -- Profile
    avatar_url TEXT,
    preferences JSONB,

    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- User personalization
CREATE TABLE user_lists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7),  -- Hex color
    position INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_post_data (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    post_id INTEGER REFERENCES posts(id),

    -- Lists
    lists INTEGER[],  -- Array of list IDs

    -- Custom status
    status VARCHAR(50),  -- 'unread', 'in-progress', 'completed', custom

    -- Notes
    notes TEXT,

    -- Highlights
    highlights JSONB,

    -- Tracking
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (user_id, post_id)
);

-- Jobs queue
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,  -- 'scrape_phase1', 'scrape_phase2', 'download_video', etc
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    priority INTEGER DEFAULT 0,

    -- Job data
    payload JSONB NOT NULL,
    result JSONB,
    error_message TEXT,

    -- Retry logic
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    next_retry_at TIMESTAMP,

    -- Tracking
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_jobs_status_priority ON jobs(status, priority DESC, created_at);

-- System configuration
CREATE TABLE system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Audit log
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INTEGER,
    changes JSONB,
    ip_address INET,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_posts_creator ON posts(creator_id);
CREATE INDEX idx_posts_published ON posts(published_at DESC);
CREATE INDEX idx_posts_search ON posts USING gin(search_vector);
CREATE INDEX idx_posts_embedding ON posts USING ivfflat(embedding vector_cosine_ops);
CREATE INDEX idx_media_hash ON media_files(file_hash);
CREATE INDEX idx_transcriptions_search ON transcriptions USING gin(search_vector);
```

---

### 2. Sistema de Colas ⚙️

**¿Por qué es crucial?**

Aparece en **múltiples features del roadmap**:

1. ✅ **Videos YouTube** - Reintentos cuando hay rate limiting
2. ✅ **Procesamiento de posts** - Fase 2 asíncrona
3. ✅ **Collections scraping** - Procesamiento en background
4. ✅ **Transcripciones** - Jobs largos sin bloquear
5. ✅ **Generación de thumbnails** - Procesamiento masivo
6. ✅ **Generación de embeddings** - Para búsqueda semántica
7. ✅ **Deduplicación de media** - Análisis de hashes

**Tecnología propuesta: Celery + Redis**

**¿Por qué Celery?**

| Opción | Pros | Contras | Veredicto |
|--------|------|---------|-----------|
| **Celery + Redis** | ✅ Maduro, robusto<br>✅ Retry automático<br>✅ Prioridades<br>✅ Monitoreo (Flower) | ⚠️ Algo complejo | ✅ **RECOMENDADO** |
| **RQ (Redis Queue)** | ✅ Simple<br>✅ Pythonic | ❌ Menos features<br>❌ Sin prioridades sofisticadas | ⚠️ Para proyectos simples |
| **PostgreSQL LISTEN/NOTIFY** | ✅ Sin dependencias extra | ❌ No diseñado para esto<br>❌ Sin retry automático | ❌ No recomendado |
| **Bull (Node.js)** | ✅ Muy bueno | ❌ Requiere Node.js | ❌ Stack diferente |

**Decisión: Celery + Redis**

**Configuración propuesta:**

```python
# celery_config.py
from celery import Celery
from celery.schedules import crontab

app = Celery('patreon_scraper')

app.config_from_object({
    'broker_url': 'redis://localhost:6379/0',
    'result_backend': 'redis://localhost:6379/1',

    # Serialization
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],

    # Task routing
    'task_routes': {
        'scraper.tasks.scrape_*': {'queue': 'scraping'},
        'media.tasks.download_*': {'queue': 'media'},
        'media.tasks.transcribe_*': {'queue': 'transcription'},
        'search.tasks.generate_*': {'queue': 'search'},
    },

    # Retry policy
    'task_acks_late': True,
    'task_reject_on_worker_lost': True,

    # Beat schedule (periodic tasks)
    'beat_schedule': {
        'daily-incremental-scrape': {
            'task': 'scraper.tasks.daily_incremental_scrape',
            'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        },
        'cleanup-old-jobs': {
            'task': 'maintenance.tasks.cleanup_completed_jobs',
            'schedule': crontab(hour=3, minute=0),  # 3 AM daily
        },
    },
})

# Task priorities
from celery import Task

class PrioritizedTask(Task):
    priority = 5  # Default priority (0-10, 10 = highest)
```

**Tipos de tareas:**

```python
# scraper/tasks.py
from celery import shared_task
import time

@shared_task(bind=True, max_retries=3, default_retry_delay=300)  # 5 min
def scrape_post_details(self, post_url, creator_id):
    """
    Scrape details of a single post.
    Retry up to 3 times with exponential backoff.
    """
    try:
        # Scraping logic here
        details = scrape_post(post_url)
        return {'status': 'success', 'data': details}
    except RateLimitError as exc:
        # Retry after longer delay
        raise self.retry(exc=exc, countdown=600)  # 10 min
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=5)
def download_youtube_video(self, video_url, post_id):
    """
    Download YouTube video with subtitles.
    More retries because YouTube can be flaky.
    """
    try:
        result = download_video_with_subs(video_url, ['es', 'en'])
        return result
    except YouTubeRateLimitError as exc:
        # Wait 1 hour before retry
        raise self.retry(exc=exc, countdown=3600)
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task
def transcribe_audio(media_id):
    """
    Transcribe audio file using Whisper.
    Long-running task.
    """
    media = get_media_by_id(media_id)
    transcript = whisper_transcribe(media.file_path)
    save_transcription(media_id, transcript)
    return {'media_id': media_id, 'status': 'completed'}

@shared_task
def generate_embeddings(post_id):
    """
    Generate embeddings for semantic search.
    """
    post = get_post_by_id(post_id)
    embedding = generate_embedding(post.content)
    update_post_embedding(post_id, embedding)
    return {'post_id': post_id}

@shared_task
def deduplicate_media():
    """
    Find and deduplicate media files.
    """
    duplicates = find_duplicate_media()
    for dup in duplicates:
        create_hardlink_or_reference(dup)
    return {'duplicates_found': len(duplicates)}
```

**Monitoreo con Flower:**

```bash
# Iniciar Flower (web UI para Celery)
celery -A celery_app flower --port=5555
```

---

### 3. Sistema de Búsqueda Multi-Capa 🔍

**Tres niveles de búsqueda integrados:**

#### Nivel 1: Full-Text Search (PostgreSQL tsvector)

```sql
-- Actualizar vector de búsqueda automáticamente
CREATE FUNCTION posts_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('spanish', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('spanish', COALESCE(NEW.content, '')), 'B') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.tags, ' '), '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER posts_search_vector_trigger
BEFORE INSERT OR UPDATE ON posts
FOR EACH ROW EXECUTE FUNCTION posts_search_vector_update();

-- Búsqueda
SELECT * FROM posts
WHERE search_vector @@ to_tsquery('spanish', 'astrología & natal')
ORDER BY ts_rank(search_vector, to_tsquery('spanish', 'astrología & natal')) DESC;
```

#### Nivel 2: Búsqueda Semántica (pgvector)

```python
# search/semantic.py
import openai
from pgvector.psycopg import register_vector

def semantic_search(query: str, limit: int = 20):
    """
    Búsqueda semántica usando embeddings.
    """
    # Generate query embedding
    query_embedding = openai.Embedding.create(
        input=query,
        model="text-embedding-3-small"
    )['data'][0]['embedding']

    # Search similar posts
    with db.cursor() as cur:
        cur.execute("""
            SELECT id, title, content,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM posts
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, limit))

        return cur.fetchall()
```

#### Nivel 3: Búsqueda en Transcripciones

```python
def search_with_transcriptions(query: str):
    """
    Búsqueda que incluye transcripciones de audio/video.
    """
    results = db.execute("""
        SELECT
            p.id, p.title,
            ts_headline('spanish', p.content, query) as content_snippet,
            t.transcript_text,
            ts_headline('spanish', t.transcript_text, query) as transcript_snippet,
            m.file_path as media_path
        FROM posts p
        LEFT JOIN post_media pm ON pm.post_id = p.id
        LEFT JOIN media_files m ON m.id = pm.media_id
        LEFT JOIN transcriptions t ON t.media_id = m.id
        WHERE
            p.search_vector @@ query OR
            t.search_vector @@ query
        ORDER BY
            ts_rank(p.search_vector, query) +
            COALESCE(ts_rank(t.search_vector, query), 0) DESC
    """, {'query': to_tsquery(query)})

    return results
```

#### Búsqueda Híbrida (Combinando todo)

```python
def hybrid_search(query: str, mode: str = 'auto'):
    """
    Búsqueda inteligente que combina multiple métodos.

    mode: 'auto', 'fulltext', 'semantic', 'hybrid'
    """
    if mode == 'auto':
        # Detectar tipo de query
        if is_short_keyword_query(query):
            mode = 'fulltext'
        else:
            mode = 'hybrid'

    if mode == 'fulltext':
        return fulltext_search(query)

    elif mode == 'semantic':
        return semantic_search(query)

    elif mode == 'hybrid':
        # Combinar resultados de ambos
        ft_results = fulltext_search(query, limit=50)
        sem_results = semantic_search(query, limit=50)

        # Merge and re-rank
        combined = merge_and_rerank(ft_results, sem_results)
        return combined
```

---

### 4. Arquitectura Multi-Fuente (Plugins) 🧩

**Diseño modular para soportar múltiples fuentes:**

```python
# sources/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class ContentSource(ABC):
    """
    Base class for all content sources.
    """

    @abstractmethod
    def get_source_id(self) -> str:
        """Return unique source identifier (e.g., 'patreon', 'pdf', 'gumroad')"""
        pass

    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with the source"""
        pass

    @abstractmethod
    def list_creators(self) -> List[Dict]:
        """List available creators/authors"""
        pass

    @abstractmethod
    def scrape_posts(self, creator_id: str, limit: int = None) -> List[Dict]:
        """Scrape posts from a creator"""
        pass

    @abstractmethod
    def get_post_details(self, post_id: str) -> Dict:
        """Get detailed information about a post"""
        pass

    @abstractmethod
    def download_media(self, media_url: str, save_path: str) -> str:
        """Download media file"""
        pass

    def get_capabilities(self) -> Dict[str, bool]:
        """Return what this source supports"""
        return {
            'has_creators': True,
            'has_collections': False,
            'has_images': True,
            'has_videos': False,
            'has_audio': False,
            'supports_search': False,
        }


# sources/patreon.py
class PatreonSource(ContentSource):
    def get_source_id(self) -> str:
        return 'patreon'

    def authenticate(self, credentials):
        # Existing Patreon auth logic
        pass

    def list_creators(self):
        # Existing logic
        pass

    # ... implement all abstract methods


# sources/pdf.py
class PDFSource(ContentSource):
    def get_source_id(self) -> str:
        return 'pdf'

    def authenticate(self, credentials):
        # No authentication needed for local PDFs
        return True

    def list_creators(self):
        # In PDF context, "creators" are authors or books
        return self.list_pdf_files()

    def scrape_posts(self, pdf_path: str, limit=None):
        # Each page or chapter could be a "post"
        pages = extract_pdf_pages(pdf_path)
        return [{'content': page, 'page_num': i} for i, page in enumerate(pages)]

    def get_capabilities(self):
        return {
            'has_creators': True,  # Authors/books
            'has_collections': False,
            'has_images': True,  # Extracted images
            'has_videos': False,
            'has_audio': False,
            'supports_search': True,  # Full-text in PDFs
        }


# sources/registry.py
class SourceRegistry:
    """
    Central registry for all content sources.
    """
    _sources = {}

    @classmethod
    def register(cls, source: ContentSource):
        cls._sources[source.get_source_id()] = source

    @classmethod
    def get(cls, source_id: str) -> ContentSource:
        return cls._sources.get(source_id)

    @classmethod
    def list_all(cls) -> List[ContentSource]:
        return list(cls._sources.values())

# Register sources
SourceRegistry.register(PatreonSource())
SourceRegistry.register(PDFSource())
# SourceRegistry.register(GumroadSource())  # Future
```

**Uso:**

```python
# Scraping genérico
def scrape_from_source(source_id: str, creator_id: str):
    source = SourceRegistry.get(source_id)

    if not source:
        raise ValueError(f"Unknown source: {source_id}")

    # Authenticate if needed
    credentials = get_credentials(source_id)
    source.authenticate(credentials)

    # Scrape
    posts = source.scrape_posts(creator_id)

    # Store in database (normalized format)
    for post in posts:
        store_post(post, source_id=source_id)
```

---

## 🏛️ Arquitectura Propuesta

### Diagrama de Capas

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Web UI     │  │   REST API   │  │   Admin UI   │      │
│  │  (Flask)     │  │   (Flask)    │  │   (Flask)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ User Service │  │Search Service│  │ Auth Service │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │Content Svc   │  │ Media Svc    │  │ Admin Svc    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                          │
│  ┌──────────────────────────────────────────────────┐       │
│  │           CELERY WORKERS (Task Queue)            │       │
│  │                                                   │       │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐│       │
│  │  │Scraping │ │  Media  │ │  Search │ │Transcr.││       │
│  │  │ Worker  │ │ Worker  │ │ Worker  │ │ Worker ││       │
│  │  └─────────┘ └─────────┘ └─────────┘ └────────┘│       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ PostgreSQL   │  │    Redis     │  │ File Storage │      │
│  │ (Main DB)    │  │ (Cache+Queue)│  │   (Media)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    INTEGRATION LAYER                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Patreon    │  │     PDFs     │  │   Gumroad    │      │
│  │   Source     │  │   Source     │  │   Source     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                 (Plugin Architecture)                        │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Datos

#### 1. Scraping Flow

```
User/Cron → API → Create Job → Redis Queue
                      ↓
              Celery Worker picks job
                      ↓
              Source Plugin (Patreon/PDF/etc)
                      ↓
              Scrape content
                      ↓
              Store in PostgreSQL
                      ↓
              Create media download jobs
                      ↓
              Media Worker downloads files
                      ↓
              Calculate hash, check duplicates
                      ↓
              Store file or create reference
                      ↓
              Update database
                      ↓
              Create transcription job (if audio/video)
                      ↓
              Transcription Worker processes
                      ↓
              Create embedding job
                      ↓
              Search Worker generates embeddings
                      ↓
              Job complete
```

#### 2. Search Flow

```
User → Web UI → Search query
                      ↓
              Search Service
                      ↓
         ┌────────────┼────────────┐
         ↓            ↓            ↓
   Full-text     Semantic    Transcription
    Search        Search        Search
    (tsvector)   (pgvector)   (tsvector)
         ↓            ↓            ↓
         └────────────┴────────────┘
                      ↓
              Merge & Re-rank
                      ↓
              Cache in Redis
                      ↓
              Return results
```

#### 3. User Interaction Flow

```
User → Login → Auth Service
                      ↓
              JWT Token
                      ↓
              Browse posts
                      ↓
              Add to list / Add note / Change status
                      ↓
              Update user_post_data table
                      ↓
              Invalidate cache
                      ↓
              Return updated view
```

---

## 🔧 Stack Tecnológico

### Backend

| Componente | Tecnología | Versión | Propósito |
|------------|-----------|---------|-----------|
| **Lenguaje** | Python | 3.11+ | Core |
| **Web Framework** | Flask | 3.x | API + Web UI |
| **ORM** | SQLAlchemy | 2.x | Database |
| **Migrations** | Alembic | 1.x | DB migrations |
| **Task Queue** | Celery | 5.x | Async processing |
| **Message Broker** | Redis | 7.x | Queue + Cache |
| **Database** | PostgreSQL | 15+ | Main storage |
| **Vector Extension** | pgvector | 0.5+ | Embeddings |
| **Authentication** | Flask-Login<br>Flask-Security-Too | Latest | User auth |
| **2FA** | PyOTP | Latest | Two-factor |

### Scraping & Media

| Componente | Tecnología | Propósito |
|------------|-----------|-----------|
| **Browser Automation** | Selenium | Web scraping |
| **HTTP Client** | httpx / requests | API calls |
| **HTML Parsing** | BeautifulSoup4 | HTML parsing |
| **PDF Processing** | PyPDF2, pdfplumber | PDF extraction |
| **OCR** | Tesseract, EasyOCR | Image text extraction |
| **Video Download** | yt-dlp | YouTube videos |
| **Audio Transcription** | OpenAI Whisper | Audio → Text |
| **Image Processing** | Pillow | Thumbnails |

### Search & AI

| Componente | Tecnología | Propósito |
|------------|-----------|-----------|
| **Full-Text Search** | PostgreSQL tsvector | Keyword search |
| **Semantic Search** | pgvector + OpenAI | Vector search |
| **Embeddings** | OpenAI API<br>(text-embedding-3-small) | Generate vectors |
| **Alternative** | Sentence-Transformers | Local embeddings |

### DevOps

| Componente | Tecnología | Propósito |
|------------|-----------|-----------|
| **Containerization** | Docker + Docker Compose | Deployment |
| **Reverse Proxy** | Nginx | Production web server |
| **Monitoring** | Flower (Celery)<br>pg_stat_statements | Task & DB monitoring |
| **Backups** | pg_dump + cron | Automated backups |
| **Logging** | Python logging + file rotation | Centralized logs |

---

## 📅 Plan de Migración

> **📋 Plan Detallado de Implementación:**
> Ver [POSTGRESQL_MIGRATION_PLAN.md](./POSTGRESQL_MIGRATION_PLAN.md) para el plan detallado paso a paso con estrategia de rollback, testing, y progreso actual.

### Fase 0: Preparación (Semana 1-2)

**Objetivos:**
- ✅ Diseño de arquitectura completo
- ✅ Setup de infraestructura base

**Tareas:**

1. **Setup PostgreSQL**
   ```bash
   # Docker
   docker run -d \
     --name patreon-postgres \
     -e POSTGRES_PASSWORD=secure_password \
     -e POSTGRES_DB=patreon \
     -v pgdata:/var/lib/postgresql/data \
     -p 5432:5432 \
     postgres:15

   # Instalar pgvector
   docker exec -it patreon-postgres bash
   apt-get update && apt-get install -y postgresql-15-pgvector
   ```

2. **Setup Redis**
   ```bash
   docker run -d \
     --name patreon-redis \
     -p 6379:6379 \
     redis:7-alpine
   ```

3. **Crear esquema de base de datos**
   ```bash
   # Aplicar schema.sql
   psql -U postgres -d alejandria -f schema.sql
   ```

4. **Setup Celery**
   ```bash
   pip install celery[redis] flower
   ```

**Entregables:**
- ✅ PostgreSQL running con pgvector
- ✅ Redis running
- ✅ Schema de DB creado
- ✅ Celery configurado

---

### Fase 1: Migración de Datos (Semana 3-4)

**Objetivos:**
- Migrar datos de JSONs a PostgreSQL
- Mantener JSONs como backup temporal

**Tareas:**

1. **Script de migración**
   ```python
   # migrate_to_postgres.py

   def migrate_creators():
       """Migrate creators from config/creators.json"""
       with open('config/creators.json') as f:
           creators = json.load(f)

       for creator in creators:
           db.execute("""
               INSERT INTO creators (creator_id, name, patreon_url, metadata)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (creator_id) DO UPDATE
               SET name = EXCLUDED.name
           """, (creator['id'], creator['name'], creator['url'], json.dumps(creator)))

   def migrate_posts():
       """Migrate posts from data/processed/*_posts_detailed.json"""
       for json_file in glob('data/processed/*_posts_detailed.json'):
           with open(json_file) as f:
               posts = json.load(f)

           for post in posts:
               # Insert post
               post_id = db.execute("""
                   INSERT INTO posts (post_id, creator_id, title, content, ...)
                   VALUES (%s, %s, %s, %s, ...)
                   RETURNING id
               """, (...))

               # Insert media references
               for media in post.get('media', []):
                   migrate_media(post_id, media)

   def migrate_media(post_id, media_info):
       """Migrate media with deduplication"""
       file_path = media_info['local_path']
       file_hash = calculate_sha256(file_path)

       # Check if file already exists
       existing = db.execute(
           "SELECT id FROM media_files WHERE file_hash = %s",
           (file_hash,)
       ).fetchone()

       if existing:
           media_id = existing['id']
           # Increment reference count
           db.execute(
               "UPDATE media_files SET reference_count = reference_count + 1 WHERE id = %s",
               (media_id,)
           )
       else:
           # Insert new media
           media_id = db.execute("""
               INSERT INTO media_files (file_hash, file_type, file_path, ...)
               VALUES (%s, %s, %s, ...)
               RETURNING id
           """, (...))

       # Link to post
       db.execute("""
           INSERT INTO post_media (post_id, media_id, position, ...)
           VALUES (%s, %s, %s, ...)
       """, (post_id, media_id, ...))
   ```

2. **Validación**
   ```python
   def validate_migration():
       """Compare JSON counts with DB counts"""
       json_post_count = count_posts_in_jsons()
       db_post_count = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]

       assert json_post_count == db_post_count, "Post count mismatch!"

       # More validations...
   ```

**Entregables:**
- ✅ Todos los datos en PostgreSQL
- ✅ Validación exitosa
- ✅ JSONs mantenidos como backup

---

### Fase 2: Sistema de Colas (Semana 5-6)

**Objetivos:**
- Convertir scripts síncronos a tareas asíncronas
- Implementar sistema de reintentos

**Tareas:**

1. **Refactorizar scrapers como tareas Celery**
   ```python
   # tasks/scraping.py

   @shared_task(bind=True, max_retries=3)
   def scrape_post_task(self, post_url, creator_id):
       try:
           # Original scraping logic
           details = scrape_post_details(post_url)

           # Store in DB
           store_post(details, creator_id)

           return {'status': 'success'}
       except Exception as exc:
           raise self.retry(exc=exc, countdown=300)
   ```

2. **Adaptar scripts existentes**
   ```python
   # Before
   for post_url in post_urls:
       details = scrape_post_details(post_url)
       save_to_json(details)

   # After
   for post_url in post_urls:
       scrape_post_task.delay(post_url, creator_id)
   ```

3. **Setup Celery workers**
   ```bash
   # docker-compose.yml
   celery-worker:
     build: .
     command: celery -A celery_app worker --loglevel=info -Q scraping,media
     depends_on:
       - redis
       - postgres

   celery-beat:
     build: .
     command: celery -A celery_app beat --loglevel=info
     depends_on:
       - redis

   flower:
     build: .
     command: celery -A celery_app flower --port=5555
     ports:
       - "5555:5555"
   ```

**Entregables:**
- ✅ Scrapers como tareas Celery
- ✅ Workers funcionando
- ✅ Flower UI para monitoreo

---

### Fase 3: Web con PostgreSQL (Semana 7-8)

**Objetivos:**
- Migrar Flask app de JSONs a PostgreSQL
- Mantener funcionalidad existente

**Tareas:**

1. **Refactorizar rutas**
   ```python
   # Before (web/viewer.py)
   @app.route('/')
   def index():
       posts = load_from_json('data/processed/*_posts_detailed.json')
       return render_template('index.html', posts=posts)

   # After
   @app.route('/')
   def index():
       posts = db.execute("""
           SELECT p.*, c.name as creator_name
           FROM posts p
           JOIN creators c ON c.id = p.creator_id
           ORDER BY p.published_at DESC
           LIMIT 100
       """).fetchall()
       return render_template('index.html', posts=posts)
   ```

2. **Búsqueda mejorada**
   ```python
   @app.route('/search')
   def search():
       query = request.args.get('q')
       mode = request.args.get('mode', 'auto')

       results = hybrid_search(query, mode)
       return jsonify(results)
   ```

3. **Caché con Redis**
   ```python
   from flask_caching import Cache

   cache = Cache(app, config={
       'CACHE_TYPE': 'redis',
       'CACHE_REDIS_URL': 'redis://localhost:6379/2'
   })

   @app.route('/post/<post_id>')
   @cache.cached(timeout=300)
   def view_post(post_id):
       post = get_post_by_id(post_id)
       return render_template('post.html', post=post)
   ```

**Entregables:**
- ✅ Web app usando PostgreSQL
- ✅ Búsqueda funcional
- ✅ Cache implementado

---

### Fase 4: Autenticación y Multi-Usuario (Semana 9-10)

**Objetivos:**
- Sistema de login
- Roles y permisos
- 2FA opcional

**Tareas:**

1. **Setup Flask-Security-Too**
   ```python
   from flask_security import Security, SQLAlchemyUserDatastore

   user_datastore = SQLAlchemyUserDatastore(db, User, Role)
   security = Security(app, user_datastore)
   ```

2. **Rutas protegidas**
   ```python
   from flask_security import login_required, roles_required

   @app.route('/admin')
   @login_required
   @roles_required('admin')
   def admin_panel():
       return render_template('admin/dashboard.html')
   ```

3. **2FA con PyOTP**
   ```python
   import pyotp

   def enable_2fa(user):
       secret = pyotp.random_base32()
       user.totp_secret = secret
       user.totp_enabled = True
       db.session.commit()

       # Generate QR code
       uri = pyotp.totp.TOTP(secret).provisioning_uri(
           user.email,
           issuer_name="Patreon Scraper"
       )
       return uri  # Show QR to user
   ```

**Entregables:**
- ✅ Login/logout funcional
- ✅ Roles (admin, user, readonly)
- ✅ 2FA opcional

---

### Fase 5: Features de Usuario (Semana 11-12)

**Objetivos:**
- Listas personalizadas
- Notas privadas
- Estados custom

**Tareas:**

1. **API para listas**
   ```python
   @app.route('/api/lists', methods=['POST'])
   @login_required
   def create_list():
       data = request.json
       list_id = db.execute("""
           INSERT INTO user_lists (user_id, name, description, color)
           VALUES (%s, %s, %s, %s)
           RETURNING id
       """, (current_user.id, data['name'], data['description'], data['color']))

       return jsonify({'id': list_id})

   @app.route('/api/posts/<post_id>/lists', methods=['POST'])
   @login_required
   def add_post_to_lists(post_id):
       list_ids = request.json['lists']

       db.execute("""
           INSERT INTO user_post_data (user_id, post_id, lists)
           VALUES (%s, %s, %s)
           ON CONFLICT (user_id, post_id)
           DO UPDATE SET lists = EXCLUDED.lists
       """, (current_user.id, post_id, list_ids))

       return jsonify({'status': 'ok'})
   ```

2. **Notas**
   ```python
   @app.route('/api/posts/<post_id>/notes', methods=['POST'])
   @login_required
   def save_note(post_id):
       notes = request.json['notes']

       db.execute("""
           INSERT INTO user_post_data (user_id, post_id, notes)
           VALUES (%s, %s, %s)
           ON CONFLICT (user_id, post_id)
           DO UPDATE SET notes = EXCLUDED.notes, updated_at = NOW()
       """, (current_user.id, post_id, notes))

       return jsonify({'status': 'ok'})
   ```

**Entregables:**
- ✅ Listas funcionales
- ✅ Notas privadas
- ✅ Estados personalizables

---

### Fase 6: Transcripciones y Búsqueda Avanzada (Semana 13-14)

**Objetivos:**
- Transcribir audios con Whisper
- Búsqueda en transcripciones
- Embeddings para búsqueda semántica

**Tareas:**

1. **Setup Whisper**
   ```python
   import whisper

   @shared_task
   def transcribe_audio_task(media_id):
       media = get_media_by_id(media_id)

       # Load Whisper model
       model = whisper.load_model("medium")

       # Transcribe
       result = model.transcribe(
           media.file_path,
           language='es',  # or auto-detect
           task='transcribe'
       )

       # Save transcription
       db.execute("""
           INSERT INTO transcriptions (media_id, transcript_text, language)
           VALUES (%s, %s, %s)
       """, (media_id, result['text'], result['language']))

       return {'status': 'completed', 'media_id': media_id}
   ```

2. **Generar embeddings**
   ```python
   import openai

   @shared_task
   def generate_embedding_task(post_id):
       post = get_post_by_id(post_id)

       # Generate embedding
       response = openai.Embedding.create(
           input=post.content,
           model="text-embedding-3-small"
       )

       embedding = response['data'][0]['embedding']

       # Save to DB
       db.execute("""
           UPDATE posts
           SET embedding = %s
           WHERE id = %s
       """, (embedding, post_id))
   ```

3. **Procesar backlog**
   ```python
   # One-time script to process existing content
   def backfill_transcriptions():
       audio_videos = db.execute("""
           SELECT id FROM media_files
           WHERE file_type IN ('audio', 'video')
           AND id NOT IN (SELECT media_id FROM transcriptions)
       """).fetchall()

       for media in audio_videos:
           transcribe_audio_task.delay(media.id)

   def backfill_embeddings():
       posts = db.execute("""
           SELECT id FROM posts
           WHERE embedding IS NULL
       """).fetchall()

       for post in posts:
           generate_embedding_task.delay(post.id)
   ```

**Entregables:**
- ✅ Whisper funcionando
- ✅ Transcripciones almacenadas
- ✅ Embeddings generados
- ✅ Búsqueda semántica funcional

---

### Fase 7: Optimización y Deduplicación (Semana 15-16)

**Objetivos:**
- Deduplicar media existente
- Optimizar rendimiento web
- Generar thumbnails

**Tareas:**

1. **Deduplicación de media**
   ```python
   @shared_task
   def deduplicate_media_task():
       # Find all media files
       files = db.execute("""
           SELECT id, file_path, file_hash
           FROM media_files
       """).fetchall()

       hash_map = {}

       for file in files:
           if not file.file_hash:
               # Calculate hash if missing
               hash_val = calculate_sha256(file.file_path)
               db.execute("""
                   UPDATE media_files SET file_hash = %s WHERE id = %s
               """, (hash_val, file.id))
           else:
               hash_val = file.file_hash

           if hash_val in hash_map:
               # Duplicate found
               original_id = hash_map[hash_val]
               merge_media_references(file.id, original_id)
               # Optionally delete physical file
           else:
               hash_map[hash_val] = file.id
   ```

2. **Generar thumbnails**
   ```python
   from PIL import Image

   @shared_task
   def generate_thumbnails_task(media_id):
       media = get_media_by_id(media_id)

       if media.file_type != 'image':
           return

       sizes = [(150, 150), (300, 300), (600, 600)]

       img = Image.open(media.file_path)

       for size in sizes:
           thumb = img.copy()
           thumb.thumbnail(size, Image.LANCZOS)

           thumb_path = f"{media.file_path}.thumb_{size[0]}x{size[1]}.webp"
           thumb.save(thumb_path, 'WEBP', quality=85)

       # Update metadata
       db.execute("""
           UPDATE media_files
           SET metadata = jsonb_set(metadata, '{has_thumbnails}', 'true')
           WHERE id = %s
       """, (media_id,))
   ```

3. **Optimización web**
   ```python
   # Lazy loading images
   @app.route('/api/posts')
   def api_posts():
       page = request.args.get('page', 1, type=int)
       per_page = 20

       posts = db.execute("""
           SELECT id, title, published_at, creator_id,
                  (SELECT file_path FROM media_files mf
                   JOIN post_media pm ON pm.media_id = mf.id
                   WHERE pm.post_id = p.id AND pm.is_cover = true
                   LIMIT 1) as cover_image
           FROM posts p
           ORDER BY published_at DESC
           LIMIT %s OFFSET %s
       """, (per_page, (page-1)*per_page))

       return jsonify(posts)
   ```

**Entregables:**
- ✅ Media deduplicado
- ✅ Thumbnails generados
- ✅ Web optimizada

---

### Fase 8: Multi-Fuente (Semana 17-18)

**Objetivos:**
- Implementar arquitectura de plugins
- Añadir soporte para PDFs
- Diseño UI para múltiples fuentes

**Tareas:**

1. **Implementar PDFSource**
   ```python
   # sources/pdf.py
   class PDFSource(ContentSource):
       # Implementation from earlier in this doc
       pass

   SourceRegistry.register(PDFSource())
   ```

2. **UI para gestionar fuentes**
   ```python
   @app.route('/admin/sources')
   @roles_required('admin')
   def manage_sources():
       sources = SourceRegistry.list_all()

       source_status = []
       for source in sources:
           status = {
               'id': source.get_source_id(),
               'name': source.get_name(),
               'enabled': is_source_enabled(source.get_source_id()),
               'capabilities': source.get_capabilities(),
               'item_count': count_items_from_source(source.get_source_id())
           }
           source_status.append(status)

       return render_template('admin/sources.html', sources=source_status)
   ```

3. **Integración en búsqueda**
   ```html
   <!-- Filter by source -->
   <select name="source">
       <option value="">All Sources</option>
       <option value="patreon">Patreon</option>
       <option value="pdf">PDFs</option>
       <option value="gumroad">Gumroad</option>
   </select>
   ```

**Entregables:**
- ✅ Plugin system funcional
- ✅ PDF source implementado
- ✅ UI para gestionar fuentes

---

### Fase 9: Dockerización (Semana 19-20)

**Objetivos:**
- Docker Compose completo
- Fácil deployment
- Documentación

**Tareas:**

1. **docker-compose.yml completo**
   ```yaml
   version: '3.8'

   services:
     postgres:
       image: postgres:15
       environment:
         POSTGRES_DB: alejandria
         POSTGRES_USER: patreon
         POSTGRES_PASSWORD: ${DB_PASSWORD}
       volumes:
         - pgdata:/var/lib/postgresql/data
         - ./init.sql:/docker-entrypoint-initdb.d/init.sql
       ports:
         - "5432:5432"

     redis:
       image: redis:7-alpine
       volumes:
         - redisdata:/data
       ports:
         - "6379:6379"

     web:
       build: .
       command: gunicorn -w 4 -b 0.0.0.0:5000 web.viewer:app
       environment:
         DATABASE_URL: postgresql://patreon:${DB_PASSWORD}@postgres:5432/patreon
         REDIS_URL: redis://redis:6379/0
       volumes:
         - ./data:/app/data
       ports:
         - "5000:5000"
       depends_on:
         - postgres
         - redis

     celery-worker:
       build: .
       command: celery -A celery_app worker -Q scraping,media,transcription,search -l info
       environment:
         DATABASE_URL: postgresql://patreon:${DB_PASSWORD}@postgres:5432/patreon
         REDIS_URL: redis://redis:6379/0
       volumes:
         - ./data:/app/data
       depends_on:
         - postgres
         - redis

     celery-beat:
       build: .
       command: celery -A celery_app beat -l info
       environment:
         DATABASE_URL: postgresql://patreon:${DB_PASSWORD}@postgres:5432/patreon
         REDIS_URL: redis://redis:6379/0
       depends_on:
         - redis

     flower:
       build: .
       command: celery -A celery_app flower --port=5555
       environment:
         CELERY_BROKER_URL: redis://redis:6379/0
       ports:
         - "5555:5555"
       depends_on:
         - redis

     nginx:
       image: nginx:alpine
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf
         - ./data/media:/usr/share/nginx/html/media:ro
       ports:
         - "80:80"
         - "443:443"
       depends_on:
         - web

   volumes:
     pgdata:
     redisdata:
   ```

2. **Dockerfile**
   ```dockerfile
   FROM python:3.11-slim

   # System dependencies
   RUN apt-get update && apt-get install -y \
       postgresql-client \
       ffmpeg \
       tesseract-ocr \
       && rm -rf /var/lib/apt/lists/*

   WORKDIR /app

   # Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # App code
   COPY . .

   CMD ["python", "web/viewer.py"]
   ```

**Entregables:**
- ✅ Docker Compose completo
- ✅ One-command deployment
- ✅ Documentación de Docker

---

### Fase 10: Testing y Producción (Semana 21-22)

**Objetivos:**
- Tests automatizados
- Monitoring
- Backups
- Docs finales

**Tareas:**

1. **Tests**
   ```python
   # tests/test_scraping.py
   def test_scrape_post():
       result = scrape_post_task('https://patreon.com/posts/123')
       assert result['status'] == 'success'

   def test_deduplication():
       # Upload same file twice
       media1 = upload_media('test.jpg')
       media2 = upload_media('test.jpg')

       # Should reference same file
       assert get_media(media1).file_hash == get_media(media2).file_hash
   ```

2. **Backups**
   ```bash
   # backup.sh
   #!/bin/bash
   DATE=$(date +%Y%m%d_%H%M%S)

   # Backup PostgreSQL
   docker exec patreon-postgres pg_dump -U patreon alejandria | \
       gzip > backups/db_$DATE.sql.gz

   # Backup media
   tar -czf backups/media_$DATE.tar.gz data/media/

   # Keep only last 30 days
   find backups/ -mtime +30 -delete
   ```

3. **Monitoring**
   ```python
   # monitoring/healthcheck.py
   @app.route('/health')
   def healthcheck():
       checks = {
           'database': check_db_connection(),
           'redis': check_redis_connection(),
           'celery': check_celery_workers(),
           'disk_space': check_disk_space(),
       }

       status = 'healthy' if all(checks.values()) else 'unhealthy'

       return jsonify({
           'status': status,
           'checks': checks
       }), 200 if status == 'healthy' else 503
   ```

**Entregables:**
- ✅ Tests passing
- ✅ Backups automáticos
- ✅ Monitoring activo
- ✅ Docs completos

---

## 🔗 Integración de Features del Roadmap

Veamos cómo cada feature del ROADMAP.md encaja en esta arquitectura:

| Feature Roadmap | Componente Arquitectura | Fase |
|-----------------|-------------------------|------|
| **Deduplicación de imágenes** | Media Service + DB | Fase 7 |
| **Sistema de colas para videos** | Celery + Redis | Fase 2 |
| **Automatización escaneo diario** | Celery Beat + Flower | Fase 2 |
| **Migración a PostgreSQL** | Database Layer | Fase 1 |
| **Búsqueda vectorial** | Search Service + pgvector | Fase 6 |
| **Transcripción de audios** | Processing Layer + Whisper | Fase 6 |
| **Optimización web** | Presentation Layer + Cache | Fase 7 |
| **Sistema de usuarios** | Auth Service + DB | Fase 4 |
| **Panel de administración** | Admin UI | Fase 4 |
| **Dockerización** | DevOps | Fase 9 |
| **Multi-fuente (PDFs, etc)** | Integration Layer + Plugins | Fase 8 |
| **Listas y notas personales** | User Service | Fase 5 |

**Todo está conectado y planificado en 22 semanas (~5-6 meses)**

---

## 📊 Estimación de Recursos

### Hardware Recomendado

**Desarrollo:**
- CPU: 4 cores
- RAM: 16 GB
- Disk: 100 GB SSD

**Producción (small):**
- CPU: 8 cores
- RAM: 32 GB
- Disk: 500 GB SSD
- GPU: Opcional (para Whisper, acelera 10x)

**Producción (medium):**
- CPU: 16 cores
- RAM: 64 GB
- Disk: 1 TB SSD
- GPU: NVIDIA T4 o mejor (para Whisper)

### Costos Estimados

**Self-hosted (NAS Synology):**
- Hardware: Ya tienes
- Electricidad: ~$10-20/mes
- **Total: ~$15/mes**

**VPS (Hetzner CPX41):**
- 8 vCPU, 32 GB RAM, 240 GB SSD
- **$53/mes**

**Cloud Managed (Railway/Render):**
- Web + Workers + DB
- **$50-100/mes** (depende de uso)

### APIs Externas

- **OpenAI Embeddings**: ~$0.02 / 1,000 posts (one-time)
- **OpenAI Whisper API**: $0.006/min (o gratis con local Whisper)

---

## 🎯 Conclusión

Esta arquitectura proporciona:

✅ **Base sólida**: PostgreSQL + Redis + Celery
✅ **Escalabilidad**: Añadir workers, sharding DB si crece mucho
✅ **Modularidad**: Plugin system para nuevas fuentes
✅ **Robustez**: Colas con reintentos, backups, monitoring
✅ **Performance**: Caché, thumbnails, índices optimizados
✅ **Multi-usuario**: Auth segura, datos personalizados
✅ **Búsqueda avanzada**: Full-text + semántica + transcripciones

**Todo el roadmap encaja en esta arquitectura de forma coherente.**

---

**Próximos pasos:**
1. ✅ Revisar y aprobar esta arquitectura
2. Comenzar Fase 0: Setup de infraestructura
3. Iteración por fases con validación continua

**¿Preguntas? ¿Ajustes necesarios?**
