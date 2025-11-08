# 🔍 Advanced Search System

**Sistema de búsqueda avanzado para contenido de Patreon**

---

## 📋 Descripción

Sistema de búsqueda full-text de última generación que indexa TODO el contenido extraído:

✅ **Títulos de posts**
✅ **Contenido completo** (no solo 500 caracteres)
✅ **Tags de Patreon**
✅ **Comentarios** (incluyendo respuestas)
✅ **Subtítulos de videos** (archivos .vtt)
✅ **Ranking por relevancia** (BM25)
✅ **Búsqueda fuzzy** (tolerante a errores)
✅ **Búsqueda instantánea** con debouncing

---

## 🚀 Instalación

### 1. Instalar Dependencias

```bash
cd /mnt/c/Users/javif/proyectos/astrologia/patreon
source venv/bin/activate

# Instalar nuevas dependencias
pip install -r requirements.txt
```

**Nuevas dependencias añadidas:**
- `whoosh>=2.7.4` - Búsqueda full-text (opcional)
- `webvtt-py>=0.5.0` - Parser de subtítulos VTT

### 2. Construir el Índice de Búsqueda

**IMPORTANTE**: Debes construir el índice antes de usar la búsqueda avanzada.

```bash
cd web
python search_indexer.py
```

**Output esperado:**
```
============================================================
🔍 Advanced Search Indexer
============================================================

1. Creating search index...
✓ Search index created

2. Indexing posts...

Processing headonhistory_posts_detailed.json...
  ✓ 123456: Indexed with subtitles (15234 chars)
  ✓ 123457: Indexed with subtitles (8921 chars)
✓ Indexed 150 posts from headonhistory_posts_detailed.json

Processing astrobymax_posts_detailed.json...
✓ Indexed 200 posts from astrobymax_posts_detailed.json

Processing horoiproject_posts_detailed.json...
✓ Indexed 100 posts from horoiproject_posts_detailed.json

3. Index statistics:
  Total posts indexed: 450
  Posts with subtitles: 125
  Posts with comments: 320

4. Testing search...
  Found 23 results for 'astrology'

  Top 3 results:
    1. Introduction to Astrology Basics...
       Matched in: title, content, subtitles
       Score: -2.34

============================================================
✓ Indexing complete!
============================================================
```

**Nota**: El score es negativo en BM25 (menor = más relevante).

### 3. Iniciar el Servidor Web

```bash
python viewer.py
```

Abre: http://localhost:5000

---

## 🎯 Funcionalidades

### 1. **Búsqueda en Múltiples Campos**

El indexador busca en:

| Campo | Descripción | Icono Badge |
|-------|-------------|-------------|
| **Title** | Título del post | 📌 Title |
| **Text** | Contenido completo del post | 📄 Text |
| **Tags** | Tags de Patreon | 🏷️ Tags |
| **Comments** | Comentarios y respuestas | 💬 Comments |
| **Subtitles** | Transcripción de videos | 🎬 Video |

### 2. **Badges Mejorados**

Cuando buscas, cada resultado muestra **badges de colores** indicando dónde se encontró:

```
[📌 Title] [📄 Text] [🎬 Video]
```

- **Verde** (Title) - Encontrado en el título
- **Azul** (Text) - Encontrado en el contenido
- **Rojo** (Tags) - Encontrado en los tags
- **Naranja** (Comments) - Encontrado en comentarios
- **Púrpura** (Video) - Encontrado en subtítulos de video

### 3. **Búsqueda Inteligente**

- **Multi-término**: Busca varias palabras a la vez
  - Ejemplo: `moon astrology basics`
  - Encuentra posts que contengan todas las palabras

- **Ranking automático**: Los resultados más relevantes aparecen primero

- **Fuzzy matching**: Tolera errores tipográficos (usando prefijos)
  - `astrol*` encuentra: astrology, astrological, astrologer

### 4. **Filtros Combinados**

Puedes combinar búsqueda con:
- ✅ Filtro por creador
- ✅ Filtro por tipo de contenido (imágenes/videos/audio)
- ✅ Filtro por tags

### 5. **Búsqueda Rápida**

- **Debouncing**: Espera 300ms después de que dejes de escribir
- **Fallback**: Si el índice no está disponible, usa búsqueda del lado del cliente
- **Indicadores visuales**: Muestra inmediatamente mientras busca

---

## 🔧 Uso Avanzado

### API de Búsqueda

El sistema expone endpoints REST:

#### 1. **Búsqueda Principal**

```bash
GET /api/search?q=astrology&limit=50&creator=astrobymax
```

**Parámetros:**
- `q` (requerido): Query de búsqueda
- `limit` (opcional): Máximo de resultados (default: 50)
- `creator` (opcional): Filtrar por creator_id

**Response:**
```json
{
  "query": "astrology",
  "total_results": 23,
  "results": [
    {
      "post_id": "123456",
      "creator_id": "astrobymax",
      "creator_name": "AstroByMax",
      "title": "Introduction to Astrology",
      "rank": -2.34,
      "matched_in": ["title", "content", "subtitles"],
      "snippets": {
        "content": "Learn <mark>astrology</mark> basics in this...",
        "subtitles": "Today we discuss <mark>astrology</mark>..."
      },
      "counts": {
        "images": 3,
        "videos": 1,
        "comments": 15
      }
    }
  ]
}
```

#### 2. **Estadísticas del Índice**

```bash
GET /api/search/stats
```

**Response:**
```json
{
  "total_posts": 450,
  "posts_with_subtitles": 125,
  "posts_with_comments": 320
}
```

### Búsqueda desde Python

```python
from web.search_indexer import SearchIndexer

# Crear indexer
indexer = SearchIndexer()

# Buscar
results = indexer.search("astrology moon phases", limit=10)

for result in results:
    print(f"Title: {result['title']}")
    print(f"Matched in: {', '.join(result['matched_in'])}")
    print(f"Rank: {result['rank']:.2f}")
    print()

indexer.close()
```

---

## 🛠️ Mantenimiento

### Reconstruir el Índice

Cuando agregues nuevos posts:

```bash
cd web
python search_indexer.py
```

Esto:
1. Elimina el índice anterior
2. Re-indexa todos los posts
3. Incluye nuevo contenido y subtítulos

**Tiempo estimado**: 2-5 minutos para 500 posts

### Verificar el Índice

```bash
# Ver estadísticas
curl http://localhost:5000/api/search/stats

# Probar búsqueda
curl "http://localhost:5000/api/search?q=test"
```

### Limpiar el Índice

```bash
cd web
rm search_index.db
```

Luego reconstruye con `python search_indexer.py`

---

## 📊 Tecnología

### SQLite FTS5

El sistema usa **SQLite FTS5** (Full-Text Search 5):

**Ventajas:**
- ✅ Ya incluido en Python (no requiere instalación)
- ✅ Extremadamente rápido (< 10ms para búsquedas típicas)
- ✅ Ranking automático con BM25 (estándar de la industria)
- ✅ Búsqueda por prefijos integrada
- ✅ Snippets con highlights automáticos
- ✅ No requiere servidor adicional
- ✅ Tamaño del índice: ~30% del tamaño de los datos originales

**Tokenización:**
- `porter`: Stemming en inglés (astrology → astrolog)
- `unicode61`: Soporte Unicode completo

### Arquitectura

```
┌─────────────────┐
│  JSON Posts     │
│  data/processed │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│ search_indexer  │────▶│ search_index │
│     .py         │     │     .db      │
└─────────────────┘     └──────┬───────┘
                                │
                                ▼
                        ┌──────────────┐
                        │   viewer.py  │
                        │   /api/search│
                        └──────┬───────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   Frontend   │
                        │   index.html │
                        └──────────────┘
```

---

## 🐛 Troubleshooting

### 1. "Search index not built"

**Error:**
```json
{"error": "Search index not built. Run: python web/search_indexer.py"}
```

**Solución:**
```bash
cd web
python search_indexer.py
```

### 2. "No posts found in data/processed"

**Error:**
```
Warning: No post files found in data/processed
```

**Solución:**
Asegúrate de haber ejecutado Phase 2 primero:
```bash
python src/phase2_detail_extractor.py --all --headless
```

### 3. Subtítulos no se indexan

**Síntoma**: No aparece el badge "Video" en búsquedas.

**Verificar:**
```bash
# Comprobar si hay archivos .vtt
find data/media -name "*.vtt" | wc -l

# Ver si webvtt está instalado
python -c "import webvtt; print('OK')"
```

**Solución:**
```bash
pip install webvtt-py
cd web
python search_indexer.py  # Re-indexar
```

### 4. Búsqueda lenta

**Si la búsqueda tarda más de 1 segundo:**

1. Verifica el tamaño del índice:
```bash
ls -lh web/search_index.db
```

2. Limita los resultados:
```javascript
// En index.html, línea ~1628
const response = await fetch(`/api/search?q=${query}&limit=50`);
                                                          ^^^ reduce a 20-30
```

3. Reconstruye el índice:
```bash
cd web
rm search_index.db
python search_indexer.py
```

### 5. Frontend no muestra badges

**Verificar en consola del navegador:**
```
✓ Advanced search available
```

**Si dice:**
```
⚠ Advanced search not available, using client-side search
```

Reconstruye el índice y reinicia el servidor.

---

## 📈 Mejoras Futuras

Ideas para v2:

- [ ] **Búsqueda por fecha**: Rango de fechas
- [ ] **Búsqueda booleana**: AND, OR, NOT operators
- [ ] **Búsqueda por frase exacta**: "phrase in quotes"
- [ ] **Autocompletado**: Sugerencias mientras escribes
- [ ] **Búsqueda de imágenes**: Por OCR de texto en imágenes
- [ ] **Búsqueda semántica**: Embeddings con AI
- [ ] **Exportar resultados**: CSV, JSON
- [ ] **Historial de búsquedas**: Guardar búsquedas recientes
- [ ] **Búsqueda avanzada UI**: Formulario con operadores
- [ ] **Índice incremental**: Actualización sin rebuild completo

---

## 🎓 Ejemplos de Búsqueda

### Búsqueda Simple

```
astrology
```
→ Encuentra posts sobre astrología

### Multi-término

```
moon phases astrology
```
→ Encuentra posts que mencionen las tres palabras

### Por Creador + Búsqueda

1. Click en el creador "AstroByMax"
2. Escribe: `basics`
3. → Solo posts de AstroByMax con "basics"

### Con Filtros

1. Escribe: `history`
2. Click en "With Videos"
3. → Solo posts con video que mencionen "history"

### Búsqueda en Subtítulos

```
introduction transcript
```
→ Si algún video dice "introduction" en su transcripción, aparecerá con badge 🎬 Video

---

## 📝 Notas Técnicas

### Campos Indexados

```python
# En search_indexer.py
CREATE VIRTUAL TABLE posts_fts USING fts5(
    post_id UNINDEXED,      # No buscar en ID
    creator_id UNINDEXED,   # No buscar en creator ID
    title,                  # ✓ Buscar en título
    content,                # ✓ Buscar en contenido
    tags,                   # ✓ Buscar en tags
    comments,               # ✓ Buscar en comentarios
    subtitles,              # ✓ Buscar en subtítulos
    published_date UNINDEXED
)
```

### Scoring (BM25)

BM25 es un algoritmo de ranking que considera:
- **TF (Term Frequency)**: Cuántas veces aparece el término
- **IDF (Inverse Document Frequency)**: Qué tan raro es el término
- **Longitud del documento**: Normaliza por tamaño

**Score más bajo = más relevante** (por convención de FTS5)

### Parsing de Subtítulos

El indexador soporta dos métodos:

1. **Con webvtt-py** (recomendado):
```python
import webvtt
captions = webvtt.read('subtitle.vtt')
text = ' '.join(c.text for c in captions)
```

2. **Fallback simple** (si webvtt no está instalado):
```python
# Lee el archivo y elimina timestamps
```

---

**Última actualización**: 2025-11-05
**Versión**: 1.0.0
**Autor**: Claude + Javier
