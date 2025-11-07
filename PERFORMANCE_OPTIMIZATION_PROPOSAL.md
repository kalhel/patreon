# 🚀 Performance Optimization Proposal - Web Viewer

## 📊 Current Problems

### 1. **Load All Posts (982 posts de golpe)**
- **Problema**: `load_all_posts()` carga TODOS los posts en memoria
- **Impacto**:
  - Tiempo de carga inicial: ~2-3 segundos
  - Memoria usada: ~50-100MB por request
  - Browser rendering: Crea 982 DOM elements de golpe

### 2. **No Paginación**
- **Problema**: Templates iteran `{% for post in posts %}` sin límite
- **Afectado**: index.html, collection.html, tag.html, creator.html
- **Impacto**: Browser se congela renderizando 982 tarjetas

### 3. **Imágenes no lazy-loaded**
- **Problema**: Todas las imágenes se cargan al inicio
- **Impacto**: ~200-500 imágenes cargando simultáneamente

### 4. **WaveSurfer crea instancias para TODOS los audios**
- **Problema**: Inicializa WaveSurfer para cada audio aunque no se reproduzca
- **Impacto**: ~50-100 instancias de WaveSurfer en memoria

### 5. **Búsqueda en Frontend**
- **Problema**: No usa el índice full-text de PostgreSQL
- **Impacto**: Búsquedas lentas en JavaScript

### 6. **No Cache**
- **Problema**: Cada request ejecuta SELECT * FROM posts
- **Impacto**: 100-200ms por query

---

## ✅ Optimizations to Implement

### 🎯 Priority 1: Paginación con PostgreSQL

**Backend (viewer.py)**:
```python
@app.route('/')
@app.route('/page/<int:page>')
def index(page=1):
    """Homepage with pagination"""
    per_page = 30  # 30 posts por página
    offset = (page - 1) * per_page

    # Query con LIMIT y OFFSET
    posts = load_posts_paginated(
        limit=per_page,
        offset=offset,
        creator_filter=request.args.get('creator'),
        tag_filter=request.args.get('tag')
    )

    total_posts = get_total_posts_count()
    total_pages = (total_posts + per_page - 1) // per_page

    return render_template('index.html',
        posts=posts,
        page=page,
        total_pages=total_pages
    )

def load_posts_paginated(limit=30, offset=0, creator_filter=None, tag_filter=None):
    """Load posts with pagination"""
    query = text("""
        SELECT
            post_id, creator_id, title, published_at,
            image_local_paths, video_local_paths, audio_local_paths,
            like_count, comment_count, patreon_tags
        FROM posts
        WHERE deleted_at IS NULL
        {filters}
        ORDER BY published_at DESC
        LIMIT :limit OFFSET :offset
    """)

    filters = []
    params = {'limit': limit, 'offset': offset}

    if creator_filter:
        filters.append("AND creator_id = :creator")
        params['creator'] = creator_filter

    if tag_filter:
        filters.append("AND :tag = ANY(patreon_tags)")
        params['tag'] = tag_filter

    query_str = str(query).format(filters=' '.join(filters))
    # Execute query...
```

**Frontend (index.html)**:
```html
<!-- Pagination controls -->
<div class="pagination">
    {% if page > 1 %}
        <a href="/?page={{ page - 1 }}">← Previous</a>
    {% endif %}

    <span>Page {{ page }} of {{ total_pages }}</span>

    {% if page < total_pages %}
        <a href="/?page={{ page + 1 }}">Next →</a>
    {% endif %}
</div>
```

**Beneficio**:
- ✅ Reduce load time de 2-3s a 200-300ms
- ✅ Solo carga 30 posts en memoria
- ✅ Browser renderiza solo 30 tarjetas

---

### 🎯 Priority 2: Infinite Scroll (alternativa a paginación)

**Frontend (index.html)**:
```javascript
let currentPage = 1;
let loading = false;

window.addEventListener('scroll', async () => {
    if (loading) return;

    // Si llegamos al 80% del scroll
    const scrollPercent = (window.scrollY + window.innerHeight) / document.body.scrollHeight;

    if (scrollPercent > 0.8) {
        loading = true;
        currentPage++;

        const response = await fetch(`/api/posts?page=${currentPage}`);
        const data = await response.json();

        // Append posts to grid
        data.posts.forEach(post => {
            const postCard = createPostCard(post);
            document.getElementById('posts-grid').appendChild(postCard);
        });

        loading = false;
    }
});
```

**Backend**:
```python
@app.route('/api/posts')
def api_posts():
    """API endpoint for infinite scroll"""
    page = int(request.args.get('page', 1))
    per_page = 30

    posts = load_posts_paginated(limit=per_page, offset=(page-1)*per_page)

    return jsonify({
        'posts': posts,
        'has_more': len(posts) == per_page
    })
```

**Beneficio**:
- ✅ Mejor UX que paginación tradicional
- ✅ Carga progresiva de contenido

---

### 🎯 Priority 3: Lazy Loading de Imágenes

**Frontend (index.html)**:
```html
<!-- Añadir loading="lazy" a todas las imágenes -->
<img src="{{ url_for('media_file', filename=img_path) }}"
     loading="lazy"
     alt="Post image">

<!-- O usar Intersection Observer para más control -->
<script>
const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.classList.remove('lazy');
            observer.unobserve(img);
        }
    });
});

document.querySelectorAll('img.lazy').forEach(img => {
    imageObserver.observe(img);
});
</script>
```

**Beneficio**:
- ✅ Solo carga imágenes visibles
- ✅ Reduce ancho de banda inicial en ~80%

---

### 🎯 Priority 4: Lazy Loading de Audios (WaveSurfer)

**Current**: Crea WaveSurfer para TODOS los audios al cargar página
**Fixed**: Solo crear al hacer click en play

**Frontend (post.html)**:
```javascript
function playPause(id) {
    // Si no existe, crear WaveSurfer ahora
    if (!wavesurfers[id]) {
        const container = document.getElementById('waveform-' + id);
        const audioSrc = container.getAttribute('data-audio-src');

        wavesurfers[id] = WaveSurfer.create({
            container: '#waveform-' + id,
            waveColor: '#e0e0e0',
            progressColor: '#1a1a1a',
            cursorColor: '#1a1a1a',
            url: audioSrc,  // Load audio directly
            barWidth: 3,
            height: 70,
            normalize: true
        });

        wavesurfers[id].on('ready', () => {
            wavesurfers[id].play();
        });
    } else {
        wavesurfers[id].playPause();
    }
}
```

**Beneficio**:
- ✅ Reduce load time inicial en ~1 segundo
- ✅ Reduce memoria usada en ~50MB
- ✅ Solo carga audio cuando usuario hace click

---

### 🎯 Priority 5: Full-Text Search en PostgreSQL

**Backend**:
```python
@app.route('/search')
def search():
    """Full-text search using PostgreSQL"""
    query = request.args.get('q', '')

    if not query:
        return redirect('/')

    search_results = search_posts_fulltext(query)

    return render_template('search.html',
        posts=search_results,
        query=query
    )

def search_posts_fulltext(query_text, limit=50):
    """Search using PostgreSQL full-text search"""
    sql = text("""
        SELECT
            post_id, creator_id, title, full_content,
            image_local_paths, published_at,
            ts_rank(search_vector, plainto_tsquery('english', :query)) as rank
        FROM posts
        WHERE search_vector @@ plainto_tsquery('english', :query)
        AND deleted_at IS NULL
        ORDER BY rank DESC, published_at DESC
        LIMIT :limit
    """)

    # Execute query...
```

**Frontend (navbar)**:
```html
<form action="/search" method="GET" class="search-form">
    <input type="text" name="q" placeholder="Search posts..."
           autocomplete="off">
    <button type="submit">🔍</button>
</form>
```

**Beneficio**:
- ✅ Búsquedas instantáneas (<50ms)
- ✅ Búsqueda en título, contenido y tags
- ✅ Ranking por relevancia

---

### 🎯 Priority 6: Cache en Memoria (Flask-Caching)

**Install**:
```bash
pip install Flask-Caching
```

**Backend (viewer.py)**:
```python
from flask_caching import Cache

cache = Cache(app, config={
    'CACHE_TYPE': 'SimpleCache',  # O 'RedisCache' para producción
    'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutos
})

@app.route('/')
@cache.cached(timeout=60, query_string=True)
def index():
    """Homepage with cache"""
    posts = load_all_posts()
    return render_template('index.html', posts=posts)

@cache.memoize(timeout=300)
def load_posts_paginated(limit, offset, creator_filter=None):
    """Cache posts by page"""
    # Query posts...
    return posts

# Clear cache when new posts are added
def clear_posts_cache():
    cache.delete_memoized(load_posts_paginated)
```

**Beneficio**:
- ✅ Reduce query time de 200ms a <10ms
- ✅ Reduce carga en PostgreSQL

---

### 🎯 Priority 7: Índices Adicionales

**SQL**:
```sql
-- Índice para búsqueda por creator + tag
CREATE INDEX idx_posts_creator_tag ON posts (creator_id, patreon_tags);

-- Índice para ordenar por likes
CREATE INDEX idx_posts_likes ON posts (like_count DESC) WHERE deleted_at IS NULL;

-- Índice para post_metadata (nuevo campo)
CREATE INDEX idx_posts_metadata ON posts USING GIN(post_metadata);
```

**Beneficio**:
- ✅ Queries de filtrado más rápidas

---

## 📈 Expected Performance Improvements

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| **Initial load time** | 2-3s | 200-300ms | **10x faster** |
| **Memory per request** | 50-100MB | 5-10MB | **10x less** |
| **Images loaded** | 200-500 | 30-50 | **10x less** |
| **Audio instances** | 50-100 | 1-5 | **20x less** |
| **Search time** | 500ms+ | <50ms | **10x faster** |
| **Cache hit time** | 200ms | <10ms | **20x faster** |

---

## 🎯 Implementation Order

1. **Week 1**: Paginación + Lazy loading de imágenes
2. **Week 2**: Lazy loading de audios + Full-text search
3. **Week 3**: Cache + Índices adicionales
4. **Week 4**: Infinite scroll (opcional)

---

## 🧪 Testing Checklist

- [ ] Load time < 500ms en index
- [ ] Lazy loading funciona en todas las vistas
- [ ] Audios solo se cargan al reproducir
- [ ] Búsqueda encuentra resultados relevantes
- [ ] Cache invalida correctamente
- [ ] Paginación funciona con filtros
- [ ] Mobile performance OK

---

## 💡 Additional Ideas

### Virtual Scrolling
Para colecciones muy grandes (1000+ posts), usar virtual scrolling:
```javascript
// Solo renderiza elementos visibles + buffer
// Librerías: react-virtualized, vue-virtual-scroller
```

### Service Worker para Cache Offline
```javascript
// Cache assets y posts para offline mode
navigator.serviceWorker.register('/sw.js');
```

### Progressive Web App (PWA)
```json
// manifest.json
{
  "name": "Patreon Viewer",
  "short_name": "Viewer",
  "start_url": "/",
  "display": "standalone"
}
```
