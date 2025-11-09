# ÍNDICE MASTER - EXPLORACIÓN PROYECTO ASTROLOGÍA/PATREON

**Fecha**: 2025-11-09  
**Proyecto**: Alejandría - Multi-Source Content Aggregator  
**Estado**: Migración PostgreSQL en progreso (Phase 1.5 completada)  
**Ubicación**: `/home/javif/proyectos/astrologia/patreon/`

---

## ARCHIVOS DE EXPLORACIÓN GENERADOS

### 1. INFORME COMPLETO (641 líneas)
**Archivo**: `/home/javif/proyectos/astrologia/patreon/PROYECTO_ESTRUCTURA_COMPLETA_2025-11-09.md`

Contenido detallado:
- Resumen ejecutivo
- Estructura de directorios principal (con árbol completo)
- Listado EXHAUSTIVO de documentación (256 archivos)
- Scripts y herramientas (120+ archivos)
- Stack tecnológico completo con versiones
- Configuración de BD (14 tablas, 2 vistas, 44 índices)
- Patrones organizacionales observados
- Estadísticas del proyecto
- Flujo de datos general
- Estado actual y próximos pasos

**Ideal para**: Comprensión técnica profunda

---

### 2. RESUMEN RÁPIDO (366 líneas)
**Archivo**: `/home/javif/proyectos/astrologia/patreon/RESUMEN_RAPIDO_2025-11-09.txt`

Secciones:
- Exploración completa resumida
- Documentación encontrada (categorizada)
- Estructura de directorios
- Scripts y herramientas (tabulado)
- Stack tecnológico (por categoría)
- Configuración BD
- Creadores configurados
- Fases del proyecto
- Estadísticas proyecto
- Estado actual
- Patrones organizacionales
- Archivos clave a conocer
- Próximos pasos recomendados

**Ideal para**: Referencia rápida y visión general

---

### 3. ESTRUCTURA VISUAL (Mind Map)
**Archivo**: `/home/javif/proyectos/astrologia/patreon/ESTRUCTURA_VISUAL_2025-11-09.txt`

Árbol jerárquico:
- Proyecto completo en estructura visual
- Todas las carpetas principales
- Scraping pipeline
- Stack tecnológico desglosado
- Flujo de datos
- Progreso de fases
- Creadores
- Archivos clave
- Estadísticas

**Ideal para**: Visualización rápida de estructura

---

## DOCUMENTACIÓN EXISTENTE DEL PROYECTO

### Documentación Técnica Principal

| Archivo | Ubicación | Tamaño | Descripción |
|---------|-----------|--------|------------|
| README.md | Raíz | 8 KB | Entrada principal del proyecto |
| PROGRESS.md | Raíz | 35 KB | Tracking oficial de migración |
| ARCHITECTURE.md | docs/ | 53 KB | Diseño técnico completo |
| PHASE0_INSTALLATION.md | docs/ | 6 KB | Guía de instalación |
| PHASE2_CORE_BACKEND.md | docs/ | 24 KB | Especificación core backend |
| DATABASE_DESIGN_REVIEW.md | docs/ | 10 KB | Revisión de diseño DB |

### Documentación por Tema

- **Migración**: PHASE0_INSTALLATION.md, POSTGRESQL_MIGRATION_PLAN.md
- **Architecture**: ARCHITECTURE.md, MEDIA_ARCHITECTURE.md
- **Búsqueda**: SEARCH_IMPROVEMENTS_PLAN.md, SEARCH_USAGE_EXAMPLES.md
- **Performance**: WEB_PERFORMANCE_2025-11-08.md, PERFORMANCE_OPTIMIZATION_PROPOSAL.md
- **Bugs**: BUGFIXES_PHASE2.md, FIXES_DOCUMENTATION.md

---

## ESTRUCTURA PRINCIPAL DEL PROYECTO

```
/home/javif/proyectos/astrologia/patreon/
├── src/                  (~12,416 líneas Python)
├── web/                  (Flask viewer + search)
├── database/             (Schema PostgreSQL)
├── docs/                 (22 archivos técnicos)
├── scripts/              (12 scripts utilidad)
├── config/               (settings, creators, .env)
├── tools/                (40+ scripts debug)
├── data/                 (Media descargado)
├── archive/              (Código obsoleto)
├── requirements.txt
└── docker-compose.yml
```

---

## STACK TECNOLÓGICO EN UNA PÁGINA

| Categoría | Tecnología | Versión |
|-----------|-----------|---------|
| **Lenguaje** | Python | 3.10+ |
| **Base de Datos** | PostgreSQL | 16+ |
| **Cache** | Redis | 7+ |
| **Queue** | Celery | 5.3.4+ |
| **Web Framework** | Flask | 3.0.0+ |
| **Web Server** | Gunicorn | 21.2.0+ |
| **ORM** | SQLAlchemy | 2.0.23+ |
| **Scraping** | Selenium/BS4 | 4.15+/4.12+ |
| **Video Download** | yt-dlp | 2023.7.6+ |
| **IA (Tags)** | Gemini | 0.3.0+ |
| **Search** | Whoosh | 2.7.4+ |
| **Vector DB** | pgvector | 0.2.3+ |

---

## ESTADÍSTICAS CLAVE

- **Código**: 12,416 líneas Python en src/
- **Scripts**: 120+ scripts (Python + Bash)
- **Documentación**: 256 archivos (.md, .txt)
- **Base de Datos**: 14 tablas, 2 vistas, 44 índices
- **Posts migrados**: 982 (Firebase → PostgreSQL)
- **Creadores**: 4 configurados
- **Fases completadas**: 1.5 / 5
- **Tamaño total**: ~8.9 GB

---

## FASES DEL PROYECTO

- ✅ **Phase 0**: Infrastructure (PostgreSQL, Redis, Celery) - COMPLETADA
- ✅ **Phase 1**: Data Migration (982 posts) - COMPLETADA
- ✅ **Phase 1.5**: Schema Refactor - COMPLETADA
- 🔄 **Phase 2**: Core Backend - EN CURSO
- 📅 **Phase 3+**: Advanced Features - PENDIENTE

---

## CÓMO USAR ESTOS REPORTES

### Para entrada rápida (5 minutos)
1. Lee este archivo (INDICE_EXPLORACION)
2. Consulta RESUMEN_RAPIDO_2025-11-09.txt

### Para comprensión técnica (30 minutos)
1. Abre PROYECTO_ESTRUCTURA_COMPLETA_2025-11-09.md
2. Revisa ESTRUCTURA_VISUAL_2025-11-09.txt
3. Lee README.md del proyecto
4. Consulta docs/ARCHITECTURE.md

### Para desarrollo específico
- **Scraping**: Ver src/ y docs/ARCHITECTURE.md
- **Base de datos**: Ver database/schema.sql
- **Web**: Ver web/viewer.py
- **Configuración**: Ver config/settings.json y config/creators.json
- **Deployment**: Ver docs/PHASE0_INSTALLATION.md

---

## ARCHIVOS IMPORTANTES DEL PROYECTO

### Configuración
- `.env` - Variables de entorno (secreto, no en git)
- `.env.example` - Plantilla de variables
- `config/settings.json` - Parámetros de scraping y media
- `config/creators.json` - Creadores configurados
- `requirements.txt` - Dependencias Python

### Base de Datos
- `database/schema.sql` - Schema principal (14 tablas)
- `database/schema_v2.sql` - Schema multi-source
- Migraciones en `database/migrations/`

### Código Principal
- `src/phase2_detail_extractor.py` - Scraper principal
- `web/viewer.py` - Interfaz web Flask
- `src/content_parser.py` - Parser de contenido
- `src/media_downloader.py` - Descargas de multimedia

### Scripts
- `scripts/test_connections.py` - Verifica conexiones
- `scripts/setup_phase0.sh` - Setup inicial
- `scripts/backup_database.sh` - Backup de DB

---

## CREADORES CONFIGURADOS

1. **astrobymax** (AstroByMax)
2. **horoiproject** (HOROI Project)
3. **headonhistory** (Ali A Olomi)
4. **skyscript** (Skyscript)

Total: 982 posts en base de datos

---

## PRÓXIMOS PASOS (Según PROGRESS.md)

### Phase 2 (Actual)
- [ ] Migración completa de scripts a PostgreSQL
- [ ] PostgresTracker implementation
- [ ] Mejoras de búsqueda avanzada
- [ ] Setup Celery workers

### Phase 3+
- [ ] Búsqueda semántica con pgvector
- [ ] Transcripciones con Whisper
- [ ] Web app mejorada
- [ ] Extensión a otras plataformas

---

## RECURSOS ADICIONALES EN EL PROYECTO

### Documentación Técnica
- `docs/ARCHITECTURE.md` - Diseño completo
- `docs/DATABASE_DESIGN_REVIEW.md` - Diseño de BD
- `docs/MEDIA_ARCHITECTURE.md` - Arquitectura de media
- `docs/SEARCH_IMPROVEMENTS_PLAN.md` - Mejoras de búsqueda

### Documentación Histórica (archive/docs/)
- `WORKFLOW.md` - Workflow anterior
- `NOTION_DATABASE_DESIGN.md` - Integración Notion (legacy)
- `PROJECT_COMPLETE.md` - Estado anterior

### Tracking & Changelog
- `PROGRESS.md` - Tracking detallado de migración
- `CHANGELOG_2025.md` - Cambios recientes
- `FIXES_DOCUMENTATION.md` - Fixes aplicados
- `LESSONS_LEARNED.md` - Lecciones aprendidas

---

## NOTAS IMPORTANTES

1. **Migración en progreso**: El proyecto está migrando de Firebase a PostgreSQL
2. **Schema V2**: Se implementó arquitectura multi-source
3. **982 posts migrados**: Todos los datos de Firebase están en PostgreSQL
4. **Entorno limpio**: El repositorio Git está limpio (sin cambios pendientes)
5. **Documentación extensiva**: 256 archivos de documentación técnica
6. **4 creadores activos**: Scraping configurado para 4 creadores de Patreon
7. **Web viewer funcional**: Interfaz Flask con búsqueda está disponible

---

## REPOSITORIO GIT

- **Rama activa**: `main`
- **Estado**: Clean (sin cambios sin guardar)
- **Último commit**: FEAT: Advanced search improvements - image zoom, inline preview optimization, remote URLs support
- **Actualización**: Muy activa (múltiples commits diarios)

---

## ESTRUCTURA DE DATOS

### Base de Datos PostgreSQL (alejandria)
- 14 tablas (creators, posts, collections, media_files, etc.)
- 2 vistas (posts_with_media, collection_posts_view)
- 44 índices (full-text search, vectorial, etc.)
- Extensión pgvector para embeddings

### Media Descargada
- Imágenes: `/data/media/images/`
- Videos: `/data/media/videos/`
- Audio: `/data/media/audio/`
- Attachments: `/data/media/attachments/`
- Collections: `/data/media/collections/`

Organizada por creador:
- astrobymax/
- headonhistory/
- horoiproject/
- skyscript/

---

## GENERADO POR

**Herramienta**: Claude Code Exploration Tool  
**Fecha**: 2025-11-09  
**Directorio explorado**: `/home/javif/proyectos/astrologia/patreon/`  
**Archivos analizados**: 256+ archivos de documentación, 120+ scripts, múltiples directorios

**Archivos de salida generados**:
1. `PROYECTO_ESTRUCTURA_COMPLETA_2025-11-09.md` - Informe técnico detallado
2. `RESUMEN_RAPIDO_2025-11-09.txt` - Resumen ejecutivo
3. `ESTRUCTURA_VISUAL_2025-11-09.txt` - Mind map visual
4. `INDICE_EXPLORACION_2025-11-09.md` - Este archivo (índice)

---

## PREGUNTAS FRECUENTES

**P: ¿Por dónde empiezo?**
R: Lee `README.md` del proyecto, luego `RESUMEN_RAPIDO_2025-11-09.txt`.

**P: ¿Cómo está organizado el código?**
R: Ver `ESTRUCTURA_VISUAL_2025-11-09.txt` para un diagrama completo.

**P: ¿Qué bases de datos se usan?**
R: PostgreSQL 16 (principal), Firebase (legacy siendo migrado).

**P: ¿Cuántos posts hay?**
R: 982 posts migrados de Firebase a PostgreSQL.

**P: ¿En qué fase está el proyecto?**
R: Phase 1.5 completada, Phase 2 en progreso.

**P: ¿Dónde está la documentación técnica?**
R: Principalmente en `/docs/` y `PROGRESS.md`.

---

**Última actualización**: 2025-11-09  
**Próxima revisión recomendada**: Después de completar Phase 2
