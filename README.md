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

## 🚀 Flujo de Trabajo

### Fase 1: Scraping de Patreon ✅ (En desarrollo)

1. **Autenticación**
   - Login con email/password
   - Obtener session cookie
   - Validar acceso a creadores suscritos

2. **Scraping de Posts**
   - Extraer todos los posts de cada creador
   - Capturar: título, fecha, texto completo, multimedia
   - Guardar en JSON raw

3. **Descarga de Multimedia**
   - Detectar y descargar imágenes
   - Detectar y descargar videos
   - Detectar y descargar audios
   - Organizar por creador y fecha

4. **Generación de Tags**
   - Análisis de contenido con IA
   - Extracción de temas principales
   - Categorización automática

### Fase 2: Integración con Notion (Pendiente)

5. **Crear Bases de Datos en Notion**
   - DB de Posts (título, contenido, fecha, creador, tags, multimedia)
   - DB de Tags (nombre, descripción, color)
   - DB de Creadores (nombre, URL, stats)

6. **Subir Contenido**
   - Crear páginas para cada post
   - Relaciones entre posts y tags
   - Relaciones entre posts y creadores
   - Subir multimedia a Notion

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

- [x] Estructura de proyecto creada
- [x] Configuración de credenciales
- [x] Implementar autenticación Patreon
- [x] Implementar scraper de posts
- [x] Implementar descargador de multimedia
- [x] Implementar generador de tags
- [ ] Crear bases de datos en Notion
- [ ] Implementar integración Notion
- [ ] Testing completo

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
