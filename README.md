# 🏛️ Alejandría - Multi-Source Content Aggregator

**Sistema escalable de scraping y organización de contenido de múltiples plataformas (Patreon, YouTube, Substack, etc.)**

---

## 🚀 Estado Actual

**Fase**: Migración Firebase → PostgreSQL en progreso

- ✅ **Phase 0**: Infrastructure Setup (PostgreSQL 16, Redis, Celery) - **COMPLETO**
- ✅ **Phase 1**: Data Migration (982 posts migrados de Firebase) - **COMPLETO**
- 🔄 **Phase 2**: Core Backend (Migrar scripts a PostgreSQL) - **EN CURSO**

> 📊 **Tracking detallado**: Ver [PROGRESS.md](PROGRESS.md) para seguimiento completo de la migración

---

## 📋 Objetivo

Sistema multi-fuente para extraer, procesar y organizar contenido de plataformas como Patreon, YouTube, Substack, etc.

**Características principales**:
- 🔍 Scraping automatizado con sistema de 3 fases
- 🗄️ Base de datos PostgreSQL con pgvector (embeddings)
- 🎯 Sistema de tracking de estado por post
- 🏷️ Generación automática de tags con IA
- 📦 Descarga y almacenamiento de multimedia
- 🌐 Web viewer para previsualización local
- 🔄 Scrapers incrementales para actualizaciones diarias

---

## 🏗️ Arquitectura

### Stack Tecnológico Actual

**Backend**:
- PostgreSQL 16 + pgvector (vectores de embeddings)
- Redis 7 (caché y message broker)
- Celery (procesamiento asíncrono)
- SQLAlchemy 2.0 (ORM)
- Python 3.10+

**Scraping**:
- Selenium (autenticación y navegación)
- BeautifulSoup4 + lxml (parsing HTML)
- Requests (HTTP client)

**IA & Processing**:
- Gemini AI (generación de tags)
- Whisper (transcripción de audio - futuro)
- Sentence Transformers (embeddings - futuro)

> 📐 **Diseño completo**: Ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) para arquitectura detallada

---

## 📁 Estructura del Proyecto

```
patreon/
├── README.md                    ← Este archivo (entrada principal)
├── PROGRESS.md                  ← Tracking oficial de migración
├── src/                         ← Código fuente Python
│   ├── phase1_url_collector.py
│   ├── phase2_detail_extractor.py
│   ├── phase3_collections_scraper.py
│   └── ...
├── scripts/                     ← Scripts de utilidad y migración
│   ├── test_connections.py
│   ├── migrate_firebase_to_postgres.py
│   └── ...
├── database/                    ← Schema y migraciones PostgreSQL
│   ├── schema.sql              ← 14 tablas, 2 vistas, 44 índices
│   └── migrations/
├── docs/                        ← Documentación técnica
│   ├── ARCHITECTURE.md         ← Diseño técnico completo
│   └── PHASE0_INSTALLATION.md  ← Guía de instalación
├── data/                        ← Datos y media (gitignored)
│   ├── raw/
│   ├── processed/
│   └── media/
├── config/                      ← Configuración y credenciales
├── web/                         ← Web viewer (Flask)
├── docker-compose.yml           ← Setup de producción
└── archive/                     ← Código y docs obsoletos
```

---

## 🚀 Quick Start

### Prerequisitos

- Python 3.10+
- PostgreSQL 16+ con pgvector
- Redis 7+
- Git

### Instalación

```bash
# Clonar repositorio
git clone <repo-url>
cd patreon

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
nano .env  # Configurar credenciales
```

### Aplicar Schema PostgreSQL

```bash
# Crear base de datos
sudo -u postgres createdb alejandria
sudo -u postgres createuser patreon_user

# Aplicar schema
psql -U patreon_user -d alejandria -h 127.0.0.1 -f database/schema.sql
```

### Verificar Instalación

```bash
python3 scripts/test_connections.py
# Debe mostrar: ✅ 4/4 tests passed
```

> 📖 **Instalación completa**: Ver [docs/PHASE0_INSTALLATION.md](docs/PHASE0_INSTALLATION.md)

---

## 🔧 Uso

### Sistema de 3 Fases

**Fase 1: Recolección de URLs**
```bash
python src/phase1_url_collector.py --all
# Navega feeds y recolecta URLs de posts
```

**Fase 2: Extracción de Detalles**
```bash
python src/phase2_detail_extractor.py --all --headless
# Extrae contenido completo de cada post
```

**Fase 3: Collections**
```bash
python src/phase3_collections_scraper.py --all --headless
# Organiza posts en collections
```

### Scrapers Incrementales (Actualizaciones Diarias)

```bash
# Solo posts nuevos (10-100x más rápido)
python src/daily_incremental_scrape.py --all
python src/phase2_detail_extractor.py --all --headless
python src/incremental_collections_scraper.py --all --headless
```

### Web Viewer Local

```bash
cd web
python viewer.py
# Abrir http://localhost:5000
```

---

## 📊 Base de Datos PostgreSQL

### Tablas Principales

- **creators**: Creadores (con campo `platform` para multi-fuente)
- **posts**: Posts de todos los creadores
- **scraping_status**: Tracking de estado de scraping
- **media_files**: Archivos multimedia (imágenes, videos, audio)
- **collections**: Agrupaciones de posts
- **transcriptions**: Transcripciones de audio/video (con embeddings)
- **users**: Sistema de usuarios (futuro)
- **user_lists**: Listas personalizadas (futuro)

### Vistas

- **posts_with_media**: Posts con conteo de media
- **collection_posts_view**: Collections con posts relacionados

> 📐 **Schema completo**: Ver [database/schema.sql](database/schema.sql)

---

## 📚 Documentación

### Documentación Oficial (Actualizada)

- **[PROGRESS.md](PROGRESS.md)**: Tracking detallado de migración PostgreSQL
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Diseño técnico completo
- **[docs/PHASE0_INSTALLATION.md](docs/PHASE0_INSTALLATION.md)**: Guía de instalación

### Archivo de Documentación Obsoleta

- **[archive/docs/](archive/docs/)**: Docs pre-migración (Firebase, Notion, etc.)

---

## 🗺️ Roadmap

### Completado ✅

- [x] Phase 0: Infrastructure Setup (PostgreSQL, Redis, Celery)
- [x] Phase 1: Data Migration (982 posts de Firebase → PostgreSQL)
- [x] Sistema de scraping de 3 fases
- [x] Descarga de multimedia
- [x] Web viewer local
- [x] Scrapers incrementales

### En Progreso 🔄

- [ ] Phase 2: Core Backend (migrar scripts a PostgreSQL)
- [ ] Celery workers para procesamiento asíncrono
- [ ] Sistema de embeddings con pgvector

### Próximamente 📅

- [ ] Phase 3: Advanced Features (búsqueda semántica, transcripciones)
- [ ] Phase 4: Web App (interfaz web completa)
- [ ] Phase 5: Production Deployment
- [ ] Extensión a otras plataformas (YouTube, Substack, etc.)

---

## 🐛 Troubleshooting

### Problemas Comunes

**PostgreSQL no conecta**:
```bash
# Verificar que escucha en TCP
sudo ss -tulpn | grep 5432

# Usar 127.0.0.1 en vez de localhost
DB_HOST=127.0.0.1
```

**Redis no responde**:
```bash
sudo systemctl start redis-server
redis-cli ping  # Debe responder PONG
```

**Test de conexiones falla**:
```bash
python3 scripts/test_connections.py
# Revisar output para identificar el problema
```

> 🐛 **Issues resueltos**: Ver sección "Issues & Soluciones" en [PROGRESS.md](PROGRESS.md)

---

## 📝 Contribuir

Este proyecto está en migración activa. Para contribuir:

1. Lee [PROGRESS.md](PROGRESS.md) para entender el estado actual
2. Revisa [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) para el diseño técnico
3. Crea una rama desde `claude/phase0-infrastructure-011CUt1Xs6FxZQdr2GWoA9nS`
4. Haz tu PR apuntando a la misma rama

---

## 📄 Licencia

Uso personal. Respeta los derechos de autor de los creadores de contenido.

---

## 👥 Créditos

**Desarrollado por**: Javier + Claude
**Última actualización**: 2025-11-07
**Estado**: Phase 1 completa, Phase 2 en progreso

---

## 🔗 Enlaces Rápidos

- 📊 [Tracking de Migración](PROGRESS.md)
- 📐 [Arquitectura Técnica](docs/ARCHITECTURE.md)
- 🚀 [Guía de Instalación](docs/PHASE0_INSTALLATION.md)
- 📦 [Docs Obsoletas](archive/docs/)
