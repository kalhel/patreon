# 🌐 Web Viewer - Local Flask Server

**Visualización local del contenido extraído de Patreon**

---

## 📋 Descripción

El Web Viewer es un servidor Flask local que permite previsualizar y navegar por todo el contenido extraído de Patreon antes de subirlo a Notion. Ofrece una interfaz web elegante con diseño tradicional en blanco y negro.

---

## 🚀 Inicio Rápido

### Iniciar el Servidor

```bash
cd /home/javif/proyectos/astrologia/patreon
source venv/bin/activate

python web/viewer.py
```

El servidor se iniciará en: **http://localhost:5000**

---

## 🎨 Vistas Disponibles

### 1. **Index / Biblioteca** (`/`)

Vista principal que muestra todos los posts de todos los creadores.

**Características**:
- Grid responsive con tarjetas de posts
- Header negro con avatar del creador y metadata
- Preview de contenido (video, imagen o texto)
- Badge de collection si el post pertenece a una
- Filtros por:
  - Búsqueda de texto (título, contenido, creador)
  - Creador específico
  - Posts con imágenes
  - Posts con videos
  - Posts con audio
  - Tags (con vista expandible)

**Diseño de Tarjetas**:
```
┌─────────────────────────────────┐
│ [Negro] Avatar + Nombre Creador │
│         Iconos (📷 🎥 🎵 💬 ❤️)   │
├─────────────────────────────────┤
│ [Blanco]                        │
│ Título del Post                 │
│ Fecha                           │
│ Preview (video/imagen/texto)    │
│                                 │
├─────────────────────────────────┤
│ [Gris] 📁 Collection Badge      │
└─────────────────────────────────┘
```

---

### 2. **Post Individual** (`/post/<post_id>`)

Vista detallada de un post individual con todo su contenido.

**Características**:
- Header negro con información del creador y fecha
- Título del post
- **Collections** - Badges clickables debajo del título
- **Audio** - Reproductor con control de velocidad (si existe)
- **Tags** - Etiquetas clickables
- **Videos** - Reproductor con subtítulos si están disponibles
- Contenido completo estructurado en bloques:
  - Headings (H1, H2, H3)
  - Párrafos de texto
  - Imágenes
  - Videos embebidos (YouTube)
  - Audios
  - Listas
  - Links
  - Código
- **Comentarios** - Sección expandible al final

**Navegación Contextual**:
- Botón "Back to Library" (siempre visible)
- Botón "Back to Collection" (solo si vienes desde una collection)
- Link a post original en Patreon

**Orden del Contenido**:
```
1. Título (H1)
2. Collections (badges pequeños, clickables)
3. Audio (reproductor compacto)
4. Tags (etiquetas clickables)
5. Videos (reproductor principal)
6. Contenido del post (bloques)
7. Comentarios (expandible)
```

---

### 3. **Vista de Collection** (`/collection/<creator_id>/<collection_id>`)

Vista dedicada a una collection específica.

**Características**:
- Header negro compacto con diseño horizontal:
  - Imagen de collection (120x120px, redondeada)
  - Título de collection (lado derecho de la imagen)
  - Avatar pequeño del creador (32x32px)
  - Nombre del creador y contador de posts en línea
  - Botón "Back to Library"
- Grid de posts de esa collection
- Mismo diseño de tarjetas que el index
- Los posts incluyen `?from_collection=` en la URL para activar navegación contextual
- Previews de audio/video/YouTube funcionan igual que en index

**Diseño del Header** (Compacto y Horizontal):
```
┌─────────────────────────────────────────────────┐
│ [Negro Fondo - Padding reducido: 1.5rem]       │
│                                                 │
│  [Img 120px]  NOMBRE COLLECTION                │
│               [Avatar] Creador • 15 posts       │
│                                                 │
│  [← Back to Library]                            │
└─────────────────────────────────────────────────┘
```

---

### 4. **Vista de Tag** (`/tag/<tag_name>`)

Vista filtrada por un tag específico.

**Características**:
- Header negro con nombre del tag
- Contador de posts con ese tag
- Grid de posts filtrados
- Botón "Back to Library"
- Mismo diseño de tarjetas que index

---

## 🎯 Sistema de Navegación

### Flujo de Usuario

```
Index
  ├─→ Click en Post → Post View
  │                     ├─→ Back to Library → Index
  │                     └─→ Ver post
  │
  ├─→ Click en Collection → Collection View
  │                           ├─→ Click en Post → Post View (con "Back to Collection")
  │                           │                     ├─→ Back to Library → Index
  │                           │                     ├─→ Back to Collection → Collection View
  │                           │                     └─→ Ver post
  │                           └─→ Back to Library → Index
  │
  └─→ Click en Tag → Tag View
                       ├─→ Click en Post → Post View
                       │                     └─→ Back to Library → Index
                       └─→ Back to Library → Index
```

### Navegación Contextual

El viewer usa un sistema de **referrer tracking** para mantener contexto:

- **Desde Index/Tag** → Post solo muestra "Back to Library"
- **Desde Collection** → Post muestra "Back to Library" + "Back to Collection"

Implementación:
```python
# URL al abrir post desde collection
/post/12345?from_collection=843570

# El botón adicional solo aparece si hay from_collection
{% if from_collection_id and collection_info %}
  <a href="/collection/{{ from_creator_id }}/{{ from_collection_id }}">
    Back to {{ collection_info.collection_name }}
  </a>
{% endif %}
```

---

## 🎨 Diseño Visual

### Paleta de Colores

El viewer usa un diseño **tradicional en blanco y negro**:

```css
Backgrounds:
- Negro (#1a1a1a) - Headers, footers
- Blanco (#ffffff) - Contenido principal
- Gris claro (#f8f9fa) - Collection badges, footers de tarjetas

Textos:
- Negro (#1a1a1a, #2b2b2b) - Títulos, texto principal
- Gris (#666666, #999999) - Texto secundario, fechas
- Blanco (#ffffff) - Texto sobre fondos oscuros

Bordes:
- Gris (#e0e0e0, #dee2e6) - Bordes sutiles
- Negro (#000000) - Bordes enfáticos
```

### Efectos y Transiciones

- **Hover en tarjetas**: Elevación con sombra y translateY(-4px)
- **Hover en collections**: Borde negro, escala de imagen
- **Transiciones suaves**: 0.2s - 0.3s ease
- **Bordes redondeados**: 6px - 16px según elemento

---

## 📂 Estructura de Archivos

```
web/
├── viewer.py                 ← Servidor Flask principal
├── templates/
│   ├── index.html           ← Vista de biblioteca
│   ├── post.html            ← Vista de post individual
│   ├── collection.html      ← Vista de collection
│   ├── tag.html             ← Vista de tag
│   └── creator.html         ← Vista de creador
└── static/
    ├── style.css            ← Estilos globales
    ├── favicon.svg          ← Icono del sitio
    ├── headonhistory.jpg    ← Avatar creador 1
    ├── astrobymax.jpg       ← Avatar creador 2
    └── horoiproject.jpg     ← Avatar creador 3
```

---

## 🔧 Funcionalidades Técnicas

### Carga de Datos

El viewer carga datos de:
```python
data/processed/
├── {creator}_posts_detailed.json    ← Posts con contenido completo
├── {creator}_collections.json       ← Collections y mappings
└── {creator}_posts_tag_summary.json ← Resumen de tags
```

### Multimedia Local

El viewer sirve archivos multimedia desde:
```python
@app.route('/media/<path:filename>')
def media_file(filename):
    """Sirve archivos de data/media/"""
    return send_from_directory('data/media', filename)
```

Estructura de media:
```
data/media/
├── images/{creator}/
├── videos/{creator}/
├── audio/{creator}/
└── collections/{creator}/
```

### Sistema de Preview en Tarjetas

Las tarjetas de posts muestran un preview del contenido con el siguiente orden de prioridad:

**Orden de Prioridad** (el primero disponible se muestra):
1. **Videos locales** - Reproductor HTML5 con controles
2. **YouTube embeds** - Iframe embebido
3. **Audio files** - Reproductor de audio con controles
4. **Imágenes** - Primera imagen del post
5. **Texto** - Preview del contenido textual

**Implementación**:
```jinja
{# Se usa un namespace para tracking #}
{% set preview_shown = namespace(value=false) %}

{# 1. Videos locales #}
{% if not preview_shown.value and post.video_local_paths %}
  <!-- Mostrar video -->
{% endif %}

{# 2. YouTube embeds #}
{% if not preview_shown.value and post.content_blocks %}
  {% for block in post.content_blocks %}
    {% if block.type == 'youtube' %}
      <!-- Mostrar YouTube -->
    {% endif %}
  {% endfor %}
{% endif %}

{# 3. Audio (desde content_blocks primero, luego local) #}
{% if not preview_shown.value and post.content_blocks %}
  {% for block in post.content_blocks %}
    {% if block.type == 'audio' %}
      <!-- Mostrar reproductor audio -->
    {% endif %}
  {% endfor %}
{% endif %}

{# 4. Imágenes #}
{% if not preview_shown.value and post.image_local_paths %}
  <!-- Mostrar imagen -->
{% endif %}

{# 5. Texto (fallback) #}
{% if not preview_shown.value %}
  <!-- Mostrar preview de texto -->
{% endif %}
```

**Nota importante**: Este orden es consistente en todas las vistas (index, collection, tag) para mantener coherencia visual.

### Filtros Implementados

1. **Búsqueda de texto** - Busca en:
   - Título del post
   - Nombre del creador
   - Contenido del post
   - Tags

2. **Filtro por creador** - Dropdown con todos los creadores

3. **Filtro por tipo de contenido**:
   - Con imágenes (`data-has-images="true"`)
   - Con videos (`data-has-videos="true"`)
   - Con audio (`data-has-audio="true"`)

4. **Filtro por tags** - Vista expandible con todos los tags disponibles

### Ordenamiento

Posts ordenados por fecha de publicación (más reciente primero).

---

## 🎮 Controles Interactivos

### Reproductor de Audio

- Control de velocidad de reproducción: 1x, 1.25x, 1.5x, 1.75x, 2x
- Avatar del creador como thumbnail
- Controles nativos del navegador

### Reproductor de Video

- Controles nativos HTML5
- Soporte para subtítulos (si están disponibles)
- Preload metadata para carga rápida
- Crossorigin para compatibilidad con CORS

### Sección de Comentarios

- Toggle expandible/colapsable
- Contador de comentarios visible
- Información de usuario y fecha
- Likes en comentarios

---

## 📊 Estadísticas y Metadata

### En Index

- Total de posts por creador
- Iconos de tipo de contenido (activos/inactivos)
- Contador de likes
- Contador de comentarios

### En Post View

- Fecha de publicación formateada
- Contadores visuales en header
- Metadata del creador

---

## 🚀 Comandos Útiles

### Desarrollo

```bash
# Modo debug (auto-reload)
FLASK_DEBUG=1 python web/viewer.py

# Puerto personalizado
python web/viewer.py --port 8080

# Ver logs
tail -f logs/viewer.log
```

### Testing

```bash
# Verificar que carga datos correctamente
curl http://localhost:5000/api/posts

# Ver post específico
curl http://localhost:5000/api/post/12345

# Verificar media
curl http://localhost:5000/media/images/astrobymax/image1.jpg
```

---

## 🎯 Casos de Uso

### 1. Preview Antes de Notion

Revisa todo el contenido localmente antes de subirlo a Notion:
```bash
python web/viewer.py
# Navega por http://localhost:5000
# Verifica que todo se ve bien
# Luego ejecuta notion_integrator.py
```

### 2. Búsqueda y Filtrado

Encuentra contenido específico:
- Busca "astrology basics" en el buscador
- Filtra por creador "astrobymax"
- Activa filtro "With Videos"
- Resultado: Videos de astrobymax sobre astrology basics

### 3. Navegación por Collections

Explora contenido agrupado:
- Entra al index
- Click en badge de collection "The Great Introduction"
- Ve todos los posts de esa collection
- Click en un post
- Usa "Back to Collection" para volver

---

## 🛠️ Personalización

### Agregar Nuevo Creador

1. Agrega avatar a `web/static/{creator_id}.jpg`
2. Actualiza diccionario en `viewer.py`:
```python
CREATOR_AVATARS = {
    'headonhistory': 'headonhistory.jpg',
    'astrobymax': 'astrobymax.jpg',
    'horoiproject': 'horoiproject.jpg',
    'nuevocreador': 'nuevocreador.jpg',  # ← Agregar aquí
}
```

### Cambiar Colores

Edita variables CSS en cada template:
```css
/* Headers */
.header {
    background: #1a1a1a;  /* Negro */
}

/* Tarjetas */
.post-card-content {
    background: #ffffff;  /* Blanco */
}
```

---

## 🐛 Troubleshooting

### No se muestran imágenes

- Verifica que existen en `data/media/`
- Verifica rutas en JSON: deben ser relativas a `data/media/`
- Ejemplo correcto: `"images/astrobymax/img1.jpg"`

### Collections no aparecen

- Ejecuta Phase 3:
  ```bash
  python src/phase3_collections_scraper.py --creator astrobymax
  python src/phase3_collections_scraper.py --creator astrobymax --update-posts
  ```
- Verifica que existe `{creator}_collections.json`
- Verifica que posts tienen campo `collections`

### Videos no se reproducen

- Asegúrate que fueron descargados con Phase 2
- Verifica formato compatible (MP4, WebM)
- Verifica que el path es correcto en JSON

---

## 📝 Próximas Mejoras

- [ ] Modo oscuro toggle
- [ ] Export a PDF de posts individuales
- [ ] Comparación lado a lado de posts
- [ ] Timeline view por fecha
- [ ] Estadísticas y analytics
- [ ] Búsqueda avanzada con operadores
- [ ] Favoritos y bookmarks locales

---

**Última actualización**: 2025-11-05
