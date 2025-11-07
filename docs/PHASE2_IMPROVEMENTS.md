# 🚀 Phase 2 Improvements - Detail Extractor Enhancements

**Estado**: 📋 Planificado
**Prioridad**: Alta (después de migración básica a PostgreSQL)
**Fecha**: 2025-11-07

---

## 🎯 Objetivo

Mejorar `phase2_detail_extractor.py` con optimizaciones de rendimiento, deduplicación, y gestión inteligente de media según la fuente.

---

## 📋 Requirements del Usuario

### 1. **NO Descargar Imágenes** 🚫🖼️

**Razón**: Las imágenes no son necesarias para el propósito del sistema, solo ocupan espacio en disco.

**Implementación**:
```python
# EN: phase2_detail_extractor.py
# Comentar o eliminar código de descarga de imágenes
# Solo guardar URLs de imágenes en la base de datos

# ANTES:
download_image(url, path)

# DESPUÉS:
# Solo guardar URL, no descargar
post_data['images'] = [{'url': url, 'downloaded': False}]
```

**Beneficios**:
- ✅ Ahorro de espacio en disco
- ✅ Scraping más rápido
- ✅ Menor ancho de banda

---

### 2. **Deduplicación de Media** 🔄

**Problema**: Si un post se reprocesa, los archivos (videos, audios) se descargan de nuevo, duplicando en disco.

**Solución**: Usar tabla `media_files` con hash SHA256 (ya existe en schema_v2.sql)

**Flujo**:
```python
# 1. Calcular hash del archivo antes/después de descargar
file_hash = hashlib.sha256(file_content).hexdigest()

# 2. Verificar si ya existe en media_files
existing = session.execute(text("""
    SELECT file_path FROM media_files WHERE file_hash = :hash
"""), {"hash": file_hash}).fetchone()

if existing:
    # Usar archivo existente
    file_path = existing[0]
    logger.info(f"✓ Media already exists: {file_path}")
else:
    # Descargar nuevo
    file_path = download_and_save(url)
    # Insertar en media_files
    session.execute(text("""
        INSERT INTO media_files (file_hash, file_path, file_type, file_size)
        VALUES (:hash, :path, :type, :size)
    """), {...})
```

**Tabla media_files** (ya en schema_v2.sql):
```sql
CREATE TABLE media_files (
    id SERIAL PRIMARY KEY,
    file_hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA256
    file_path TEXT NOT NULL,
    file_size BIGINT,
    reference_count INTEGER DEFAULT 0,
    ...
)
```

**Beneficios**:
- ✅ No duplicar archivos
- ✅ Ahorrar espacio (un video puede aparecer en múltiples posts)
- ✅ Tracking de referencias

---

### 3. **Settings para Videos de Patreon** ⚙️

**Requirement**: Permitir configurar si videos de Patreon se descargan o solo se indica "ver en Patreon".

**Opciones**:

#### Opción A: Descargar (comportamiento actual)
```python
if settings['patreon']['download_videos']:
    video_path = download_patreon_video(url)
    post_data['video_file'] = video_path
```

#### Opción B: Solo indicar "ver en Patreon"
```python
else:
    post_data['video_url'] = url
    post_data['video_note'] = "Ver en Patreon"
    post_data['requires_patreon'] = True
```

**Configuración** (`config/settings.json`):
```json
{
  "media": {
    "patreon": {
      "download_videos": true,      // true = descargar, false = solo URL
      "download_audios": true,
      "download_images": false       // Ya NO descargar
    },
    "youtube": {
      "mode": "embed",               // "embed" o "download"
      "download_subtitles": true,
      "subtitle_languages": ["en", "es"]
    }
  }
}
```

**Implementación**:
```python
# Cargar settings
with open('config/settings.json') as f:
    settings = json.load(f)

# Aplicar según configuración
if post_source == 'patreon':
    if settings['media']['patreon']['download_videos']:
        # Descargar
        pass
    else:
        # Solo URL
        pass
```

---

### 4. **YouTube Videos - Dual Mode** 🎥

**Requirement**: Soportar 2 modos para videos de YouTube según configuración.

#### **Modo A: Embed** (Simple, recomendado)
```python
if settings['media']['youtube']['mode'] == 'embed':
    post_data['youtube_embed'] = {
        'video_id': extract_youtube_id(url),
        'url': url,
        'embed_html': f'<iframe src="https://youtube.com/embed/{video_id}"></iframe>'
    }
```

**Ventajas**:
- ✅ Instantáneo (no descarga)
- ✅ Siempre disponible
- ✅ No ocupa espacio
- ✅ Subtítulos nativos de YouTube

**Desventajas**:
- ❌ Requiere conexión a internet
- ❌ YouTube puede borrar el video

#### **Modo B: Download con yt-dlp** (Complejo, para archivos)
```python
elif settings['media']['youtube']['mode'] == 'download':
    try:
        result = download_youtube_video(
            url,
            subtitles=['en', 'es'],
            quality='best'
        )
        post_data['video_file'] = result['video_path']
        post_data['subtitles'] = result['subtitles']  # {en: path, es: path}
    except DownloadError as e:
        # Si falla, enviar a cola de reintentos
        enqueue_youtube_download(url, post_id)
        post_data['video_status'] = 'queued'
```

**Ventajas**:
- ✅ Archivo local (permanente)
- ✅ Subtítulos descargados (English + Spanish)
- ✅ Funciona sin internet

**Desventajas**:
- ❌ Lento (puede tardar minutos)
- ❌ Ocupa espacio (videos grandes)
- ❌ Puede fallar (video privado, borrado, etc.)

**Dependencia**:
```bash
pip install yt-dlp
```

**Código ejemplo**:
```python
import yt_dlp

def download_youtube_video(url, subtitles=['en', 'es'], quality='best'):
    """Download YouTube video with subtitles"""

    ydl_opts = {
        'format': quality,
        'outtmpl': 'media/youtube/%(id)s.%(ext)s',
        'writesubtitles': True,
        'subtitleslangs': subtitles,
        'writeautomaticsub': True,  # Fallback to auto-generated
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

        return {
            'video_path': ydl.prepare_filename(info),
            'subtitles': {
                'en': f"media/youtube/{info['id']}.en.vtt",
                'es': f"media/youtube/{info['id']}.es.vtt"
            },
            'metadata': {
                'title': info['title'],
                'duration': info['duration'],
                'uploader': info['uploader']
            }
        }
```

---

### 5. **Sistema de Colas con Celery** 🔄⏰

**Problema**: Operaciones lentas (descargas, scraping) bloquean el script principal.

**Solución**: Implementar Celery para operaciones asíncronas.

#### **Qué debería ir a cola**:

1. **Phase 1: URL Collection**
   - Scraping de páginas de creator (puede tardar minutos)
   - Reintentos si falla

2. **Phase 2: Detail Extraction**
   - Descargas de videos (Patreon, YouTube)
   - Descargas de audios
   - Transcripciones (Whisper API puede tardar)
   - Reintentos si falla

3. **Phase 3: Collections**
   - Scraping de collections (múltiples páginas)
   - Asociar posts a collections

#### **Arquitectura propuesta**:

```
┌─────────────────┐
│  Main Script    │
│  (Orchestrator) │
└────────┬────────┘
         │
         ├─────────────┐
         │             │
         v             v
┌─────────────┐  ┌──────────────┐
│ Celery Task │  │ Celery Task  │
│ Phase 1     │  │ Phase 2      │
└──────┬──────┘  └──────┬───────┘
       │                │
       v                v
┌──────────────────────────┐
│   PostgreSQL Database     │
│   (scraping_status)       │
└──────────────────────────┘
```

#### **Implementación**:

**1. Definir tasks** (`src/celery_tasks.py`):
```python
from celery import Celery

app = Celery('patreon_scraper', broker='redis://localhost:6379/0')

@app.task(bind=True, max_retries=3)
def scrape_post_details(self, post_id, post_url):
    """Task: Extract post details"""
    try:
        # Scraping logic
        details = extract_post_details(post_url)

        # Save to database
        tracker = PostgresTracker()
        tracker.mark_details_extracted(post_id, success=True)

        return {'status': 'success', 'post_id': post_id}

    except Exception as e:
        # Retry with exponential backoff
        self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

@app.task(bind=True, max_retries=5)
def download_youtube_video_task(self, url, post_id):
    """Task: Download YouTube video with retries"""
    try:
        result = download_youtube_video(url)
        # Update database
        return result
    except Exception as e:
        self.retry(exc=e, countdown=300)  # 5 min retry
```

**2. Encolar tareas**:
```python
# EN: orchestrator.py o phase2_detail_extractor.py

from celery_tasks import scrape_post_details, download_youtube_video_task

# Encolar Phase 2 para todos los posts pendientes
for post in posts_needing_details:
    scrape_post_details.delay(post['post_id'], post['post_url'])

# Encolar descarga de YouTube
download_youtube_video_task.delay(youtube_url, post_id)
```

**3. Iniciar workers**:
```bash
# Terminal 1: Worker para Phase 1
celery -A celery_tasks worker --queue=phase1 -c 2

# Terminal 2: Worker para Phase 2 (descargas)
celery -A celery_tasks worker --queue=phase2 -c 1

# Terminal 3: Worker para Phase 3
celery -A celery_tasks worker --queue=phase3 -c 2
```

**Beneficios**:
- ✅ No bloqueante (continúa procesando otros posts)
- ✅ Reintentos automáticos si falla
- ✅ Paralelización (múltiples workers)
- ✅ Monitoreo con Flower (`celery flower`)

**⚠️ NOTA**: Sistema de colas NO está implementado actualmente. Es una mejora futura.

---

## 📊 Orden de Implementación

### **Paso 1: Migración Básica** (AHORA)
- [x] Crear PostgresTracker
- [ ] Migrar phase1/2/3 a PostgreSQL
- [ ] Probar que funciona básicamente

### **Paso 2: Optimizaciones de Media** (SIGUIENTE)
1. [ ] Deshabilitar descarga de imágenes
2. [ ] Implementar deduplicación con media_files table
3. [ ] Crear config/settings.json con opciones de media

### **Paso 3: YouTube Support** (DESPUÉS)
1. [ ] Implementar modo "embed" (simple)
2. [ ] Implementar modo "download" con yt-dlp
3. [ ] Descargar subtítulos (en, es)

### **Paso 4: Sistema de Colas** (FUTURO)
1. [ ] Setup Celery + Redis
2. [ ] Crear celery_tasks.py con tasks
3. [ ] Migrar operaciones lentas a tasks
4. [ ] Configurar workers y monitoring

---

## 🎛️ Configuración Propuesta

**Archivo**: `config/settings.json`

```json
{
  "media": {
    "images": {
      "download": false,
      "store_urls": true
    },
    "patreon": {
      "videos": {
        "download": true,
        "quality": "best",
        "format": "mp4"
      },
      "audios": {
        "download": true,
        "format": "mp3"
      }
    },
    "youtube": {
      "mode": "embed",
      "download_if_embed_fails": false,
      "download_settings": {
        "quality": "best",
        "subtitles": ["en", "es"],
        "auto_subtitles": true
      }
    },
    "deduplication": {
      "enabled": true,
      "hash_algorithm": "sha256"
    }
  },
  "celery": {
    "enabled": false,
    "broker": "redis://localhost:6379/0",
    "workers": {
      "phase1": 2,
      "phase2": 1,
      "phase3": 2
    }
  },
  "scraping": {
    "max_retries": 3,
    "retry_delay": 60,
    "timeout": 300
  }
}
```

---

## ✅ Validación del Plan por Usuario

Usuario confirma:
> "vale cuando abordemos el migrado de phase2 una vez que funcione bien con bbdd hay que mejorarlo"

✅ **Correcto**: Primero migrar, luego mejorar

> "Que no se descargen imagenes no son necesaria"

✅ **Implementar**: Deshabilitar descarga de imágenes

> "que no se dupliquen en disco si procesa de nuevo el post"

✅ **Implementar**: Deduplicación con media_files + SHA256

> "me gustaria en settings poder decir para patreon, si el video es de patreon si se descarga o se comenta que hay que verlo en patreon"

✅ **Implementar**: Config patreon.videos.download (true/false)

> "para los de youtube si se coge el enlace y se embembe en el post o se descarga el youtube con los dos subitulos english and spanish"

✅ **Implementar**: youtube.mode ("embed" o "download") + subtitles [en, es]

> "si no se pueden desrcargar deberia ir lal sistema de colas"

✅ **Implementar**: Celery tasks para descargas con reintentos

> "incluso la parte inicial de fase 1 y la de fase 3 deberian ir mediante la cola"

✅ **Implementar**: Celery para Phase 1, 2, y 3

> "corrigeme si voy mal"

✅ **RESPUESTA**: ¡Vas perfecto! El plan es sólido y arquitectónicamente correcto.

---

## 📝 Notas Finales

- **Prioridad 1**: Migración básica a PostgreSQL (funcional)
- **Prioridad 2**: Optimizaciones de media (no imágenes, deduplicación)
- **Prioridad 3**: YouTube support (embed + download)
- **Prioridad 4**: Sistema de colas (Celery)

**Tiempo estimado**:
- Migración básica: 4-6 horas
- Optimizaciones media: 3-4 horas
- YouTube support: 4-5 horas
- Sistema de colas: 8-10 horas

**Total**: ~20-25 horas para Phase 2 completa con todas las mejoras

---

**Creado**: 2025-11-07
**Aprobado por**: Usuario
**Estado**: Pendiente de implementación (después de migración básica)
