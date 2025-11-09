# INFORME COMPLETO: PROYECTO ASTROLOGÍA/PATREON

## RESUMEN EJECUTIVO

**Nombre**: Alejandría - Multi-Source Content Aggregator  
**Tipo**: Sistema escalable de scraping y organización de contenido  
**Estado**: Migración Firebase → PostgreSQL en progreso (Phase 1.5 completada)  
**Fecha de Actualización**: 2025-11-09  
**Líneas de Código**: ~12,416 líneas en src/  
**Documentación**: 256 archivos .md/.txt  

---

## 1. ESTRUCTURA DE DIRECTORIOS PRINCIPAL

```
/home/javif/proyectos/astrologia/patreon/
├── src/                           # Código fuente Python (scrapers, procesamiento)
├── web/                           # Web viewer Flask (búsqueda, visualización)
├── database/                      # Schema PostgreSQL y migraciones
├── docs/                          # Documentación técnica completa
├── scripts/                       # Scripts de utilidad y migración
├── config/                        # Configuración y credenciales
├── data/                          # Datos y media (gitignored)
│   ├── media/                    # Archivos descargados
│   │   ├── images/              # Imágenes por creador
│   │   ├── videos/              # Videos descargados
│   │   ├── audio/               # Audio descargado
│   │   ├── attachments/         # Archivos adjuntos
│   │   └── collections/         # Media de colecciones
│   ├── raw/                     # Datos sin procesar
│   ├── processed/               # Datos procesados
│   └── backups/                 # Backups de base de datos
├── archive/                       # Código obsoleto y documentación anterior
│   ├── docs/                    # Docs de fases anteriores
│   ├── phase1-firebase/         # Scraper original Firebase
│   ├── phase2-firebase-tracker/ # Tracking Firebase
│   └── phase3-notion-upload/    # Integración Notion
├── tools/                         # Scripts de herramientas y debugging
├── backups/                       # Backups de datos
├── logs/                          # Archivos de log
├── venv/                          # Entorno virtual Python
├── .env                          # Variables de entorno (secreto)
├── requirements.txt              # Dependencias Python
├── docker-compose.yml            # Setup Docker
├── README.md                     # Documentación principal
├── PROGRESS.md                   # Tracking detallado de migración
└── CHANGELOG_2025.md             # Historial de cambios
```

---

## 2. ARCHIVOS DE DOCUMENTACIÓN ENCONTRADOS

### Documentación Activa (en docs/)

| Archivo | Descripción |
|---------|------------|
| `/home/javif/proyectos/astrologia/patreon/README.md` | Documentación principal del proyecto |
| `/home/javif/proyectos/astrologia/patreon/docs/ARCHITECTURE.md` | Diseño técnico completo (53KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/PHASE0_INSTALLATION.md` | Guía de instalación de infraestructura |
| `/home/javif/proyectos/astrologia/patreon/docs/PHASE2_CORE_BACKEND.md` | Especificación core backend (24KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/PHASE2_IMPROVEMENTS.md` | Mejoras de Phase 2 (22KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/PHASE2_PLAN.md` | Plan de Phase 2 (7KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/DATABASE_DESIGN_REVIEW.md` | Revisión de diseño DB (10KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/MEDIA_ARCHITECTURE.md` | Arquitectura de media (19KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/SCHEMA_REFACTOR_PLAN.md` | Plan de refactoring schema (12KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/POSTGRESQL_MIGRATION_PLAN.md` | Plan de migración PostgreSQL (11KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/SETTINGS_CONFIG.md` | Configuración de settings (14KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/SEARCH_IMPROVEMENTS_PLAN.md` | Mejoras de búsqueda (12KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/SEARCH_USAGE_EXAMPLES.md` | Ejemplos de uso de búsqueda (13KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/MIGRATION_LEGACY_V1_COLUMNS.md` | Migración de columnas legacy (10KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/BUGFIXES_PHASE2.md` | Correcciones de bugs Phase 2 (19KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/WEB_PERFORMANCE_2025-11-08.md` | Análisis de performance web (8KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/WEB_PERFORMANCE_RESULTS_2025-11-08.md` | Resultados de performance (7KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/VIMEO_FIX_2025-11-08.md` | Fix para Vimeo (6KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/FASE_5_DUAL_MODE_SEARCH_PLAN.md` | Plan búsqueda dual mode (20KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/PROJECTS_COMPARISON_2025-11-08.md` | Comparación de proyectos (19KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/INSTALL_WEB_PERFORMANCE.md` | Instalación web performance (3KB) |
| `/home/javif/proyectos/astrologia/patreon/docs/resumen.txt` | Resumen en texto (4KB) |

### Documentación Raíz

| Archivo | Descripción |
|---------|------------|
| `/home/javif/proyectos/astrologia/patreon/PROGRESS.md` | Tracking oficial de migración Phase 0-1.5 |
| `/home/javif/proyectos/astrologia/patreon/CHANGELOG_2025.md` | Historial de cambios 2025 |
| `/home/javif/proyectos/astrologia/patreon/FIXES_DOCUMENTATION.md` | Documentación de fixes aplicados |
| `/home/javif/proyectos/astrologia/patreon/FIXES_APPLIED.md` | Fixes aplicados |
| `/home/javif/proyectos/astrologia/patreon/TEST_PHASE2_README.md` | Guía testing Phase 2 |
| `/home/javif/proyectos/astrologia/patreon/PERFORMANCE_OPTIMIZATION_PROPOSAL.md` | Propuesta de optimización (11KB) |
| `/home/javif/proyectos/astrologia/patreon/LESSONS_LEARNED.md` | Lecciones aprendidas |

### Documentación Archivada (en archive/docs/)

| Archivo | Descripción |
|---------|------------|
| `/home/javif/proyectos/astrologia/patreon/archive/docs/WORKFLOW.md` | Workflow obsoleto |
| `/home/javif/proyectos/astrologia/patreon/archive/docs/ROADMAP.md` | Roadmap anterior |
| `/home/javif/proyectos/astrologia/patreon/archive/docs/TWO_PHASE_WORKFLOW.md` | Workflow 2 fases |
| `/home/javif/proyectos/astrologia/patreon/archive/docs/DAILY_AUTOMATION.md` | Automatización diaria |
| `/home/javif/proyectos/astrologia/patreon/archive/docs/PROJECT_COMPLETE.md` | Proyecto completado |
| `/home/javif/proyectos/astrologia/patreon/archive/docs/CHANGELOG.md` | Changelog anterior |
| `/home/javif/proyectos/astrologia/patreon/archive/docs/WEB_VIEWER.md` | Web viewer anterior |
| `/home/javif/proyectos/astrologia/patreon/archive/docs/QUICK_START.md` | Quick start anterior |
| `/home/javif/proyectos/astrologia/patreon/archive/docs/READY_TO_USE.md` | Listo para usar |
| `/home/javif/proyectos/astrologia/patreon/archive/docs/NOTION_DATABASE_DESIGN.md` | Diseño DB Notion |
| `/home/javif/proyectos/astrologia/patreon/archive/docs/COLLECTIONS_PLAN.md` | Plan de colecciones |
| `/home/javif/proyectos/astrologia/patreon/archive/docs/RESUMEN.md` | Resumen anterior |
| `/home/javif/proyectos/astrologia/patreon/archive/docs/STATUS.md` | Estado anterior |
| `/home/javif/proyectos/astrologia/patreon/archive/docs/README_UPDATES.md` | Actualizaciones README |
| `/home/javif/proyectos/astrologia/patreon/archive/docs/ADVANCED_SEARCH.md` | Búsqueda avanzada |

### Documentación en Herramientas

| Archivo | Descripción |
|---------|------------|
| `/home/javif/proyectos/astrologia/patreon/tools/README_YOUTUBE_THUMBNAILS.md` | Thumbnails YouTube |

### Archivos de Configuración

| Archivo | Descripción |
|---------|------------|
| `/home/javif/proyectos/astrologia/patreon/.env` | Variables de entorno activas |
| `/home/javif/proyectos/astrologia/patreon/.env.example` | Plantilla de variables de entorno |
| `/home/javif/proyectos/astrologia/patreon/.env.backup_complete` | Backup de .env |
| `/home/javif/proyectos/astrologia/patreon/config/settings.json` | Configuración de media y scraping |
| `/home/javif/proyectos/astrologia/patreon/config/creators.json` | Configuración de creadores |
| `/home/javif/proyectos/astrologia/patreon/config/credentials.json` | Credenciales |
| `/home/javif/proyectos/astrologia/patreon/config/patreon_cookies.json` | Cookies de Patreon |
| `/home/javif/proyectos/astrologia/patreon/config/gunicorn.conf.py` | Configuración Gunicorn |

### Archivos SQL

| Archivo | Descripción |
|---------|------------|
| `/home/javif/proyectos/astrologia/patreon/database/schema.sql` | Schema principal (16KB, 14 tablas) |
| `/home/javif/proyectos/astrologia/patreon/database/schema_posts.sql` | Schema posts específico (11KB) |
| `/home/javif/proyectos/astrologia/patreon/database/schema_v2.sql` | Schema V2 multi-source (23KB) |
| `/home/javif/proyectos/astrologia/patreon/database/add_post_metadata.sql` | Script agregar metadata |
| `/home/javif/proyectos/astrologia/patreon/database/add_collection_images.sql` | Script agregar imágenes colecciones |

---

## 3. SCRIPTS Y HERRAMIENTAS

### Scripts de Sistema (raíz)

| Script | Tipo | Descripción |
|--------|------|------------|
| `setup.sh` | Bash | Setup inicial del proyecto |
| `daily_scrape.sh` | Bash | Scraping diario (v1) |
| `daily_scrape_v2.sh` | Bash | Scraping diario (v2) |
| `run_analysis.sh` | Bash | Ejecuta análisis |

### Scripts de Configuración (scripts/)

| Script | Tipo | Descripción |
|--------|------|------------|
| `setup_phase0.sh` | Bash | Setup Phase 0 (infraestructura) |
| `test_connections.py` | Python | Verifica conexiones DB/Redis |
| `start_web_viewer.sh` | Bash | Inicia web viewer Flask |
| `backup_database.sh` | Bash | Backup de PostgreSQL |
| `restore_backup.sh` | Bash | Restaura backup de DB |
| `restore_oldest_backup.sh` | Bash | Restaura backup antiguo |
| `audit_codebase.sh` | Bash | Auditoría del código |
| `explore_structure.sh` | Bash | Explora estructura |
| `reorganize_docs.sh` | Bash | Reorganiza documentación |
| `verify_schema_v2.sh` | Bash | Verifica schema V2 |
| `migrate_firebase_to_postgres.py` | Python | Migración Firebase → PostgreSQL |
| `migrate_to_schema_v2.py` | Python | Migración a Schema V2 |

### Código Fuente Principal (src/)

**Scrapers (3 fases)**:
- `phase1_url_collector.py` - Recolecta URLs de posts
- `phase2_detail_extractor.py` - Extrae contenido completo
- `phase3_collections_scraper.py` - Organiza en colecciones

**Scrapers Incrementales** (actualizaciones diarias):
- `daily_incremental_scrape.py` - Solo posts nuevos
- `incremental_scraper.py` - Versión incremental base
- `incremental_collections_scraper.py` - Colecciones incrementales

**Autenticación & Scraping**:
- `patreon_auth.py` - Autenticación Patreon (requests)
- `patreon_auth_selenium.py` - Autenticación con Selenium
- `patreon_scraper.py` - Scraper principal
- `patreon_scraper_v2.py` - Scraper versión 2

**Procesamiento**:
- `content_parser.py` - Parser de contenido (52KB)
- `media_downloader.py` - Descargador de multimedia (86KB)
- `tag_generator.py` - Generador de tags con IA
- `migrate_json_to_postgres.py` - Migración JSON → PostgreSQL (22KB)
- `migrate_collections_to_postgres.py` - Migración colecciones (20KB)

**Utilidades**:
- `main.py` - Punto de entrada
- `orchestrator.py` - Orquestador de tareas
- `postgres_tracker.py` - Tracker con PostgreSQL
- `add_creator.py` - Agregar creadores
- `reset_creator.py` - Reset de creadores
- `fix_corrupted_json.py` - Fix JSON corrupto
- `debug_creators.py` - Debug creadores
- `diagnose_headonhistory.py` - Diagnóstico de creador específico

**Total en src/**: ~12,416 líneas de Python

### Herramientas de Debugging (tools/)

40+ scripts para análisis y debugging:
- `test_login.py` - Prueba de login
- `test_single_post.py` - Test post único
- `test_media_downloader.py` - Test descargas
- `validate_phase2_upsert.py` - Validar upsert
- `diagnose_phase2_data.py` - Diagnosticar datos
- `find_youtube_posts.py` - Buscar posts YouTube
- `inspect_horoi_posts.py` - Inspeccionar HOROI
- `fix_post_creator.py` - Fix creator post
- `reset_creator_postgresql.py` - Reset creator
- `reset_processed_posts.py` - Reset posts procesados
- `analyze_media_structure.py` - Analizar estructura media
- Y muchos más...

### Scripts Testing (raíz)

- `test_phase2_postgres.py` - Test Phase 2
- `test_phase3_postgres.py` - Test Phase 3
- `test_web_viewer_postgres.py` - Test web viewer

### Scripts Debugging (raíz)

- `debug_post.py` - Debug post genérico
- `debug_post_141632966.py` - Debug post específico
- `debug_post_attachments.py` - Debug attachments
- `debug_specific_post.py` - Debug post específico
- `check_post_video.py` - Verificar video en post
- `check_vimeo_embed.py` - Verificar embed Vimeo
- `check_creator_ids.py` - Verificar IDs creators
- `debug_attachment_download.py` - Debug descarga attachments
- `cleanup_mux_thumbnails.py` - Limpieza thumbnails Mux
- `debug_video_count.py` - Debug conteo videos
- `analyze_content_order.py` - Analizar orden contenido

### Queries SQL Sueltas (raíz)

- `check_collections_images.sql` - Verifica imágenes colecciones
- `check_collections_without_images.sql` - Colecciones sin imágenes
- `check_media_in_postgres.sql` - Verifica media en DB
- `verify_media_paths.sql` - Verifica rutas media
- `fix_creator_ids.sql` - Fix IDs creators
- `investigate_post_order.sql` - Investiga orden posts
- `analyze_post_141632966_order.sql` - Análisis post específico

---

## 4. STACK TECNOLÓGICO DETECTADO

### Backend - Lenguajes y Runtimes

- **Python 3.10+** - Lenguaje principal
- **Bash** - Scripts de sistema
- **SQL/PostgreSQL** - Base de datos

### Bases de Datos

- **PostgreSQL 16+** - Base de datos relacional principal
  - Extensiones: pgvector (embeddings)
  - Funcionalidades: Full-text search, JSON, arrays
  - Versión instalada: 16.x

- **Firebase** - Legacy (siendo migrado a PostgreSQL)
  - Estado: En deprecación
  - Usado para: Tracking de estado anterior

### Caché & Message Broker

- **Redis 7+** - Cache en memoria y message broker
  - Persistencia: Habilitada
  - Auto-start: Configurado

### Task Queue

- **Celery 5.3.4+** - Procesamiento asíncrono
  - Broker: Redis
  - Flower: Monitoreo
  - Estado: En setup (deshabilitado en dev)

### Web Framework

- **Flask 3.0.0+** - Framework web Python
- **Gunicorn 21.2.0+** - WSGI server (producción)
- **Flask-Compress 1.14** - Compresión Gzip
- **Flask-Login 0.6.3+** - Gestión de sesiones
- **Flask-Security-Too 5.3.2+** - Sistema seguridad completo
- **Flask-Caching 2.1.0** - Caché en Flask

### Web Scraping

- **Selenium 4.15.0+** - Automatización navegador
  - webdriver-manager: Gestión de drivers
- **BeautifulSoup4 4.12.0+** - Parsing HTML
- **lxml 4.9.0+** - Parser XML/HTML rápido
- **Requests 2.31.0+** - Cliente HTTP

### Descarga y Procesamiento de Media

- **yt-dlp 2023.7.6+** - Descargar videos YouTube/Vimeo
- **moviepy 1.0.3+** - Procesamiento de video
- **pydub 0.25.1+** - Procesamiento de audio
- **Pillow 10.0.0+** - Procesamiento de imágenes
- **numpy 1.24.0+** - Operaciones numéricas

### ORM & Migraciones

- **SQLAlchemy 2.0.23+** - ORM Python
- **Alembic 1.13.0+** - Migraciones de base de datos
- **psycopg2-binary 2.9.9+** - Adaptador PostgreSQL
- **pgvector 0.2.3+** - Vector search en PostgreSQL

### IA & NLP

- **google-generativeai 0.3.0+** - Gemini AI (generación de tags)
- Planned: OpenAI (embeddings, Whisper transcription)

### Búsqueda Avanzada

- **Whoosh 2.7.4** - Full-text search library
- **WebVTT-py 0.5.0** - Parsing subtítulos VTT

### Utilidades

- **python-dotenv 1.0.0+** - Gestión variables de entorno
- **tqdm 4.66.0+** - Barras de progreso
- **python-dateutil 2.8.0+** - Utilidades de fechas
- **bcrypt 4.1.2+** - Hashing de contraseñas
- **pyotp 2.9.0+** - TOTP para 2FA
- **notion-client 2.2.0+** - Cliente Notion API (legacy)

### Infraestructura

- **Docker Compose** - Orquestación de contenedores
- **Git** - Control de versiones

---

## 5. BASE DE DATOS - SCHEMA POSTGRE SQL

### Tablas Principales (14 tablas)

**Entidades Core**:
1. `creators` - Creadores de contenido
2. `posts` - Posts/contenido individual
3. `collections` - Colecciones/playlists
4. `post_collections` - Relación M2M posts-collections

**Media**:
5. `media_files` - Archivos multimedia con deduplicación
6. `post_media` - Relación M2M posts-media

**Búsqueda & IA**:
7. `transcriptions` - Transcripciones de audio/video

**Sistema**:
8. `scraping_status` - Tracking de scraping
9. `jobs` - Tareas/trabajos
10. `users` - Usuarios del sistema (futuro)
11. `user_lists` - Listas personalizadas (futuro)
12. `user_post_data` - Datos de usuario por post (futuro)
13. `system_config` - Configuración del sistema
14. `audit_log` - Auditoría de cambios

### Vistas (2 vistas)
- `posts_with_media` - Posts con conteos de media
- `collection_posts_view` - Colecciones con posts relacionados

### Índices (44 índices)
- Full-text search en posts
- Búsqueda vectorial (pgvector)
- Índices en foreign keys
- Índices en campos de búsqueda frecuente

### Triggers Automáticos
- Actualización automática de `updated_at`
- Trigger para full-text search

---

## 6. CONFIGURACIÓN APLICACIÓN

### Variables de Entorno (.env)

**Database**:
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `DATABASE_URL` (auto-construida)

**Redis**:
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
- `REDIS_URL` (auto-construida)

**Celery**:
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `CELERY_WORKERS`

**Patreon**:
- `PATREON_EMAIL`, `PATREON_PASSWORD`

**AI Services**:
- `GEMINI_API_KEY` (opcional, para tags)
- `OPENAI_API_KEY` (opcional, para embeddings)

**Flask**:
- `FLASK_APP`, `FLASK_ENV`, `FLASK_SECRET_KEY`

**Security**:
- `SECRET_KEY`, `SECURITY_PASSWORD_SALT`

**Logging**:
- `LOG_LEVEL`, `LOG_FILE`

**Misc**:
- `TZ` (timezone)

### Archivo settings.json

Configuración detallada de:
- Descarga de imágenes (min_size, deduplicación)
- Descarga de videos (Patreon, YouTube, Vimeo)
- Descarga de audio (deduplicación)
- Parámetros de scraping (retries, timeout)
- Configuración Celery (workers)
- Modo video (embed vs download)

### Archivo creators.json

Configuración de 4 creadores:
1. **astrobymax** - AstroByMax
2. **horoiproject** - HOROI Project
3. **headonhistory** - Ali A Olomi
4. **skyscript** - Skyscript

Cada creador con:
- URL de posts y colecciones
- Avatar
- Color de preview
- Estado de colecciones

---

## 7. PATRONES ORGANIZACIONALES OBSERVADOS

### Estructura por Fases

El proyecto está organizado en **5 fases principales**:

1. **Phase 0: Infrastructure** ✅ COMPLETADA
   - Setup PostgreSQL, Redis, Celery
   - Creación de schema base

2. **Phase 1: Data Migration** ✅ COMPLETADA
   - Migración de 982 posts de Firebase → PostgreSQL
   - Schema V1 → Schema V2

3. **Phase 1.5: Schema Refactor** ✅ COMPLETADA
   - Migración a multi-source
   - Normalización de datos

4. **Phase 2: Core Backend** 🔄 EN CURSO
   - Migración scripts a PostgreSQL
   - PostgresTracker implementation
   - Mejoras de búsqueda avanzada

5. **Phase 3+: Advanced Features** 📅 PENDIENTE
   - Búsqueda semántica con pgvector
   - Transcripciones (Whisper)
   - Web app completa
   - Otras plataformas (YouTube, Substack)

### Sistema de 3 Fases de Scraping

1. **Phase 1**: Recolecta URLs de posts
2. **Phase 2**: Extrae contenido detallado
3. **Phase 3**: Organiza en colecciones

Cada fase tiene:
- Versión "full" (reinicia desde cero)
- Versión "incremental" (solo nuevos - 10-100x más rápido)
- Soporte headless (sin UI del navegador)

### Separación de Responsabilidades

- `src/` - Lógica de scraping y procesamiento
- `web/` - Web viewer y búsqueda
- `scripts/` - Setup y utilidades
- `tools/` - Debugging y análisis
- `database/` - Schema y migraciones
- `config/` - Configuración
- `data/` - Datos y media
- `archive/` - Código obsoleto

### Estrategia de Versionado

- **Schema**: v1 (legacy Firebase) → v2 (PostgreSQL multi-source)
- **Scrapers**: v1, v2 (mejoras incrementales)
- **Configuración**: `.json` files para settings
- **Git branches**: Ramas por fase/característica

### Estrategia de Migraciones

- Migraciones documentadas paso a paso
- Backups automáticos antes de cambios
- Scripts de rollback disponibles
- Verificación post-migración

### Documentación Coexistente

- Docs activas en `/docs/`
- Docs archivadas en `/archive/docs/`
- PROGRESS.md para tracking detallado
- Inline comments en código
- README.md como entrada principal

### Manejo de Media

Estructura organizada por:
- Tipo: `images/`, `videos/`, `audio/`, `attachments/`, `collections/`
- Creador: `astrobymax/`, `headonhistory/`, `horoiproject/`, `skyscript/`

Features:
- Deduplicación por hash SHA256
- Configuración por tipo de media
- Backup automático

### Testing & Debugging

- Scripts de test para cada fase
- Scripts de debugging por creador/post
- Herramientas de análisis de datos
- Verificación de integridad

---

## 8. ESTADÍSTICAS DEL PROYECTO

| Métrica | Valor |
|---------|-------|
| **Líneas Python (src/)** | ~12,416 |
| **Archivos Documentación** | 256 |
| **Scripts Python** | ~100+ |
| **Scripts Bash** | ~20+ |
| **Tablas Base de Datos** | 14 |
| **Vistas Base de Datos** | 2 |
| **Índices Base de Datos** | 44 |
| **Creadores Configurados** | 4 |
| **Posts Migrados** | 982 |
| **Fases Completadas** | 1.5 |
| **Dependencias Python** | 40+ |

---

## 9. STACK TECNOLÓGICO RESUMEN

### Categoría | Tecnología | Versión
|-----------|-----------|---------|
| **Lenguaje** | Python | 3.10+ |
| **BD Principal** | PostgreSQL | 16+ |
| **Cache/Queue** | Redis | 7+ |
| **Task Queue** | Celery | 5.3.4+ |
| **Web Framework** | Flask | 3.0.0+ |
| **WSGI Server** | Gunicorn | 21.2.0+ |
| **ORM** | SQLAlchemy | 2.0.23+ |
| **Scraping** | Selenium/BS4 | 4.15+/4.12+ |
| **Media Download** | yt-dlp | 2023.7.6+ |
| **IA (Tags)** | Gemini AI | 0.3.0+ |
| **Búsqueda** | Whoosh | 2.7.4+ |
| **Vectores** | pgvector | 0.2.3+ |
| **Security** | Flask-Security | 5.3.2+ |
| **Orchestration** | Docker Compose | Latest |

---

## 10. FLUJO DE DATOS GENERAL

```
Patreon Website
    ↓
Selenium Browser Automation (patreon_auth.py)
    ↓
Phase 1: URL Collection (phase1_url_collector.py)
    ↓
Phase 2: Detail Extraction (phase2_detail_extractor.py)
    ├─→ Content Parsing (content_parser.py)
    └─→ Media Download (media_downloader.py)
    ↓
PostgreSQL Database (alejandria)
    ├─→ posts table
    ├─→ media_files table
    └─→ scraping_status table
    ↓
Phase 3: Collections (phase3_collections_scraper.py)
    ↓
Phase 4: Web Viewer (web/viewer.py)
    ├─→ Search Index (web/search_indexer.py)
    └─→ Display Results
    ↓
Frontend Web
```

---

## 11. ESTADO ACTUAL (2025-11-09)

- **Rama Activa**: `main`
- **Estado Git**: Clean (sin cambios pendientes)
- **Último Commit**: FEAT: Advanced search improvements - image zoom, inline preview optimization, remote URLs support (3297688)
- **Fase Actual**: Phase 1.5 Completada, Phase 2 En Progreso
- **Datos Mirados**: 982 posts migrados de Firebase → PostgreSQL
- **Creadores Activos**: 4 (astrobymax, horoiproject, headonhistory, skyscript)

---

## 12. PRÓXIMOS PASOS

### Phase 2 (En Progreso)
- [ ] Migración completa de scripts a PostgreSQL
- [ ] Implementación PostgresTracker
- [ ] Mejoras búsqueda avanzada
- [ ] Celery workers

### Phase 3 (Planeado)
- [ ] Búsqueda semántica con pgvector
- [ ] Transcripciones con Whisper
- [ ] Interfaz web mejorada

### Futuros
- [ ] Expansión a YouTube, Substack
- [ ] Sistema de usuarios
- [ ] Listas personalizadas
- [ ] Deployment en producción

