# 🎯 Patreon to Notion - Content Scraper & Organizer

**Proyecto**: Scraping completo de contenido de Patreon → Organización en Notion
**Fecha**: 2025-11-01

---

## 📋 Objetivo

Extraer TODO el contenido de múltiples creadores de Patreon y organizarlo automáticamente en Notion con:
- ✅ Textos completos
- ✅ Imágenes
- ✅ Videos
- ✅ Audios
- ✅ Sistema de tags automático
- ✅ Organización por creador

---

## 🎨 Creadores a Scrapear

1. **Head-On History** - https://www.patreon.com/c/headonhistory/posts
2. **AstroByMax** - https://www.patreon.com/c/astrobymax/posts
3. **Horoi Project** - https://www.patreon.com/cw/horoiproject

---

## 📁 Estructura del Proyecto

```
patreon/
├── src/
│   ├── patreon_auth.py          ← Autenticación con Patreon
│   ├── patreon_scraper.py       ← Scraper principal de posts
│   ├── media_downloader.py      ← Descarga de multimedia
│   ├── tag_generator.py         ← Generación automática de tags
│   ├── notion_integrator.py     ← Integración con Notion
│   └── main.py                  ← Script principal
├── data/
│   ├── raw/                     ← JSONs de posts sin procesar
│   ├── processed/               ← JSONs procesados con tags
│   └── media/
│       ├── images/              ← Imágenes descargadas
│       ├── videos/              ← Videos descargados
│       └── audio/               ← Audios descargados
├── config/
│   └── credentials.json         ← Credenciales Patreon + Notion
├── logs/                        ← Logs de ejecución
└── docs/                        ← Documentación

```

---

## 🔧 Tecnologías

- **Python 3.10+**
- **Requests** - HTTP requests
- **BeautifulSoup4** - HTML parsing
- **Selenium** (opcional) - Si es necesario JS rendering
- **Notion API** - Integración con Notion
- **Gemini AI** (opcional) - Generación inteligente de tags

---

## 🚀 Flujo de Trabajo - Sistema de 3 Fases

### Fase 1: Recolección de URLs ✅
**Script**: `src/phase1_url_collector.py`

- Navega por el feed de cada creador
- Recolecta URLs de todos los posts disponibles
- Guarda lista de URLs en `data/raw/{creator}_post_urls.json`
- Manejo de infinite scroll automático

### Fase 2: Extracción de Detalles ✅
**Script**: `src/phase2_detail_extractor.py`

- Lee URLs de Fase 1
- Extrae contenido completo de cada post:
  - Título, fecha, contenido en bloques estructurados
  - Metadata (likes, comments, fecha de publicación)
  - URLs de imágenes, videos, audios
  - Tags de Patreon
- Descarga automática de multimedia local
- Guarda en `data/processed/{creator}_posts_detailed.json`

### Fase 3: Collections y Organización ✅
**Script**: `src/phase3_collections_scraper.py`

- Extrae collections de cada creador
- Descarga imágenes de portada de collections
- Mapea qué posts pertenecen a qué collections
- Actualiza posts con información de collections
- Guarda en `data/processed/{creator}_collections.json`

### Web Viewer: Visualización Local 🌐
**Script**: `web/viewer.py`

- Servidor Flask local para previsualizar contenido
- Vista de biblioteca completa con filtros
- Vista individual de posts con contenido completo
- Vista de collections con posts agrupados
- Sistema de navegación intuitivo
- **Ver documentación completa**: `docs/WEB_VIEWER.md`

### Integración con Notion (Futuro)
**Script**: `src/notion_integrator.py`

- Subida automática a Notion
- Creación de bases de datos relacionadas
- Sistema de tags y relaciones

---

## 📊 Bases de Datos Notion

**Sistema Mejorado: 6 Bases de Datos Interrelacionadas**

### 1. Posts (Artículos Completos)
Contenido completo con texto enriquecido, tags híbridos (Patreon + IA), relaciones a media

### 2. Creators (Creadores)
Información de cada creador con estadísticas

### 3. Tags (Sistema de Etiquetado)
Tags de Patreon + Tags generados por IA, organizados por categoría

### 4. Images (Galería de Imágenes) ⭐ NUEVO
Metadata completa de cada imagen con relaciones a posts, creators y tags

### 5. Videos (Biblioteca de Videos) ⭐ NUEVO
Catálogo de videos con metadata y relaciones

### 6. Audio (Colección de Audio) ⭐ NUEVO
Archivos de audio catalogados con metadata

**Ventajas**:
- Búsqueda flexible (por post, por media, por tag, por creador)
- Reutilización de contenido
- Análisis y estadísticas avanzadas
- Gestión eficiente de media

**Ver diseño completo**: `docs/NOTION_DATABASE_DESIGN.md`

---

## ⚙️ Configuración

### 1. Setup Automático (Recomendado)

```bash
cd /home/javif/proyectos/astrologia/patreon

# Ejecutar script de setup
./setup.sh
```

Esto creará el entorno virtual e instalará todas las dependencias automáticamente.

### 2. Setup Manual

```bash
cd /home/javif/proyectos/astrologia/patreon

# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar Credenciales

Editar `config/credentials.json`:
- ✅ Patreon email/password (YA configurado)
- ⏳ Notion API key (pendiente)
- ⏳ Notion Database IDs (pendiente)

### 3. Activar Entorno Virtual

```bash
source venv/bin/activate
```

### 4. Ejecutar Scraping

**Ejemplos de uso**:

```bash
# Solo autenticarse y guardar cookies (primera vez)
python src/main.py --auth-only

# Scrapear todos los creadores (5 posts de prueba c/u)
python src/main.py --scrape-all --limit 5

# Scrapear UN creador específico
python src/main.py --creator headonhistory --limit 10

# Scrapear TODOS los posts de TODOS los creadores
python src/main.py --scrape-all

# Scrapear con detalles completos (imágenes, videos, audio)
python src/main.py --scrape-all --full-details

# Scrapear un creador con todos los detalles
python src/main.py --creator astrobymax --full-details
```

---

## 🎯 Estado Actual

### ✅ Completado

- [x] **Fase 1**: URL Collector - Recolección completa de URLs de posts
- [x] **Fase 2**: Detail Extractor - Extracción de contenido detallado
- [x] **Fase 3**: Collections Scraper - Sistema de collections implementado
- [x] **Web Viewer**: Servidor local Flask con navegación completa
  - [x] Vista de biblioteca (index) con filtros
  - [x] Vista individual de posts
  - [x] Vista de collections
  - [x] Vista por tags
  - [x] Sistema de navegación contextual
  - [x] Diseño responsive y elegante
- [x] Autenticación con Patreon (Selenium)
- [x] Descarga de multimedia local
- [x] Generación de tags con IA (Gemini)

### 🔄 En Progreso

- [ ] Integración con Notion
- [ ] Sistema de actualización incremental

### 📚 Documentación

- [x] README principal
- [x] Workflow completo (WORKFLOW.md)
- [x] Documentación de Web Viewer (docs/WEB_VIEWER.md)
- [x] Plan de Collections (COLLECTIONS_PLAN.md)
- [x] Diseño de base de datos Notion (docs/NOTION_DATABASE_DESIGN.md)

---

## 📝 Notas Importantes

### Patreon API

- **Session Cookie**: Válido por ~1 mes
- **API Key pública**: `1745177328c8a1d48100a9b14a1d38c1`
- **Endpoints principales**:
  - POST `/login` - Autenticación
  - GET `/current_user` - Usuario actual
  - GET `/post/:postid` - Post individual
  - GET `/post/:postid/attachments` - Media files

### Rate Limiting

- Implementar delays entre requests (1-2 segundos)
- Guardar progreso regularmente
- Reintentos automáticos en caso de error

### Legal

- Este scraper es para uso personal de contenido del cual eres suscriptor
- Respeta los derechos de autor de los creadores
- No redistribuyas contenido privado

---

## 🔄 Próximos Pasos

1. Implementar autenticación con Patreon
2. Probar scraping de un post individual
3. Escalar a todos los posts de un creador
4. Implementar descarga de multimedia
5. Crear sistema de tags con IA
6. Configurar Notion
7. Integración completa

---

**Desarrollado**: Claude + Javier
**Última actualización**: 2025-11-01
