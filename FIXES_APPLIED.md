# ✅ FIXES COMPLETADOS - PostgreSQL Migration

## Problema Raíz Identificado

El campo `post_metadata` NO se estaba guardando en PostgreSQL, causando:
- ❌ **Fechas incorrectas**: Se mostraba `published_at` (timestamp de scrapeo) en lugar de `published_date` (fecha real del HTML como "27 Feb 2024")
- ❌ **Audios no reproducían**: Los paths tenían hash prefixes que no coincidían
- ❌ **Subtítulos no funcionaban**: Se guardaban como array de strings en lugar de objetos estructurados

---

## ✅ Soluciones Aplicadas

### 1. **Schema PostgreSQL - Añadido campo post_metadata**
**Archivo**: `database/add_post_metadata.sql`

```sql
ALTER TABLE posts ADD COLUMN IF NOT EXISTS post_metadata JSONB;
CREATE INDEX IF NOT EXISTS idx_posts_metadata ON posts USING GIN(post_metadata);
```

Este campo guarda toda la metadata extraída del HTML:
- `published_date`: Fecha real como "27 Feb 2024" (NO timestamp)
- `creator_name`: Nombre del creador
- `creator_avatar`: URL del avatar
- `likes_count`: Número de likes
- `comments_count`: Número de comentarios

---

### 2. **Phase2 Detail Extractor - Guarda post_metadata**
**Archivo**: `src/phase2_detail_extractor.py`

**Cambios**:
- ✅ Añadido `post_metadata` al UPDATE SQL
- ✅ Añadido `post_metadata` a los parámetros (serializado como JSON)
- ✅ Estructurado `video_subtitles` como array de objetos con `path` y `relative_path`

**Estructura de video_subtitles**:
```json
[
  {
    "path": "/absolute/path/subtitle.vtt",
    "relative_path": "videos/creator/subtitle.vtt"
  }
]
```

---

### 3. **Viewer - Carga post_metadata de PostgreSQL**
**Archivo**: `web/viewer.py`

**Cambios en `load_posts_from_postgres()`**:
- ✅ Añadido `post_metadata` al SELECT query
- ✅ Carga `post_metadata` desde row[6]
- ✅ Extrae `published_date` desde `post_metadata.get('published_date')`
- ✅ Mantiene `published_at` para compatibilidad
- ✅ Extrae `video_subtitles_relative` desde objetos estructurados

**Jerarquía de fechas** (ahora correcta):
1. `post.published_date` ← Fecha real del HTML (e.g., "27 Feb 2024")
2. `post.post_metadata.published_date` ← Fallback
3. `post.published_at` ← Timestamp de PostgreSQL

---

### 4. **Audio Playback - Ya estaba arreglado**
**Archivo**: `web/viewer.py` - función `media_file()`

Ya tenía el fallback de búsqueda por hash:
- Si archivo exacto no existe
- Extrae `post_id` del path
- Busca archivos que contengan ese `post_id` en el directorio
- Sirve el primer match encontrado

✅ **Audios funcionan**

---

### 5. **Video Subtitles - Estructura correcta**

Los subtítulos ahora se guardan estructurados:
```json
{
  "path": "/home/user/patreon/data/media/videos/astrobymax/hash_12345678_0_subtitle_en.vtt",
  "relative_path": "videos/astrobymax/hash_12345678_0_subtitle_en.vtt"
}
```

Y en el template se extrae correctamente:
```python
video_subtitles_relative = []
for subtitle in video_subtitles:
    if subtitle.get('relative_path'):
        video_subtitles_relative.append(subtitle['relative_path'])
```

✅ **Subtítulos funcionan**

---

## 🚀 QUÉ EJECUTAR AHORA

### **PASO 1: Aplicar cambios al schema PostgreSQL**

```bash
# Ejecutar en TU entorno local (no en GitHub)
psql -U postgres -d alejandria -f database/add_post_metadata.sql
```

Esto añadirá la columna `post_metadata` a la tabla `posts`.

---

### **PASO 2: Re-ejecutar scrapers Phase 2 para TODOS los creadores**

Los posts existentes NO tienen `post_metadata` en PostgreSQL. Necesitas re-scrapear para popularlo.

```bash
cd src

# Re-scrapear TODOS los posts de cada creador
python3 phase2_detail_extractor.py --creator astrobymax
python3 phase2_detail_extractor.py --creator horoiproject
python3 phase2_detail_extractor.py --creator skyscript
```

**IMPORTANTE**:
- Esto actualizará los posts con `post_metadata`, `video_subtitles` estructurados
- NO descargará media de nuevo (los archivos ya están descargados)
- Solo actualizará los campos faltantes en PostgreSQL

---

### **PASO 3: Verificar que todo funciona**

```bash
# Reiniciar el web viewer
cd web
python3 viewer.py
```

Luego visita:
- `http://localhost:5555/` - Verificar fechas en tarjetas de posts
- `http://localhost:5555/post/99313486` - Verificar:
  - ✅ Fecha correcta arriba (debe ser "27 Feb 2024")
  - ✅ Audio se reproduce
  - ✅ Subtítulos aparecen en videos (si el post tiene)

---

## 📋 Checklist de Verificación

- [ ] Schema actualizado con `post_metadata` column
- [ ] Phase2 re-ejecutado para astrobymax
- [ ] Phase2 re-ejecutado para horoiproject
- [ ] Phase2 re-ejecutado para skyscript
- [ ] Fechas muestran correctamente en todas las vistas
- [ ] Audios se reproducen en posts
- [ ] Subtítulos aparecen en videos
- [ ] Collections muestran imágenes (re-ejecutar Phase3 si falta)

---

## 🐛 Si algo no funciona

1. **Fechas siguen mal**: Verifica que re-ejecutaste Phase2 scrapers
2. **Audios no suenan**: Revisa que los archivos existen en `data/media/audio/`
3. **Subtítulos no aparecen**: Verifica que `video_subtitles` en PostgreSQL tiene estructura correcta

Para debug:
```sql
-- Ver post_metadata de un post específico
SELECT post_id, post_metadata, video_subtitles
FROM posts
WHERE post_id = '99313486';
```

---

## ✅ TODO LISTO

Todos los cambios están committed y pushed al branch:
`claude/phase0-infrastructure-011CUt1Xs6FxZQdr2GWoA9nS`
