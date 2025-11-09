# 🔬 Fase 5: Búsqueda Dual Mode (Normal + Avanzada)

**Fecha:** 2025-11-09
**Branch:** feature/advanced-search-improvements (futuro)
**Prioridad:** Media
**Prerequisitos:** Fase 2 completada

---

## 🎯 Objetivo

Implementar un sistema de búsqueda con **dos modos intercambiables**:

1. **Modo Normal (📚):** Grid visual actual - para browsing y exploración
2. **Modo Avanzado (🔬):** Vista de resultados detallados - para búsquedas precisas

**Razón:** Combinar lo mejor de ambos mundos:
- Mantener experiencia visual hermosa para exploración
- Agregar búsqueda precisa para encontrar contenido específico

---

## 🎨 Diseño UI

### **Toggle de Modo**

```
┌─────────────────────────────────────────────────────┐
│ 🔍 [Buscar posts...]                    [🔬 Avanzada]│ ← Toggle button
│                                                      │
│ 👤 Ali A Olomi  📸 Con imágenes  🏷️ Tag: astrology   │
└─────────────────────────────────────────────────────┘
```

### **Modo 1: Vista Normal (Default)**

**Grid visual hermoso (como está ahora):**

```
┌──────────┐ ┌──────────┐ ┌──────────┐
│ [Imagen] │ │ [Imagen] │ │ [Imagen] │
│ Post 1   │ │ Post 2   │ │ Post 3   │
│ 💬 52    │ │ 🏷️ magic │ │ 📌 Title │
└──────────┘ └──────────┘ └──────────┘
```

**Características:**
- ✅ Grid responsivo 3-4 columnas
- ✅ Preview de imágenes/videos
- ✅ Badges de coincidencia (📌 Title, 💬 Comments, etc)
- ✅ Comportamiento actual sin cambios

### **Modo 2: Vista Avanzada**

**Click en [🔬 Avanzada] → Vista detallada con snippets:**

```
┌─────────────────────────────────────────────────────┐
│ 🔍 [magic moon]                         [📚 Normal] │ ← Toggle
│                                                      │
│ 📊 Filtros avanzados:                               │
│ ☐ Solo en títulos  ☐ Solo en comentarios           │
│ ☐ Solo en subtítulos  ☐ Fecha: últimos 30 días     │
└─────────────────────────────────────────────────────┘

Resultados (lista vertical):

┌─────────────────────────────────────────────┐
│ 📄 Magic in the Islamic World               │
│ Ali A Olomi • 29 Aug 2025 • 52 comments     │
├─────────────────────────────────────────────┤
│ 🔍 3 coincidencias encontradas:             │
│                                             │
│ 📌 En título:                               │
│ "...traditions of <mark>magic</mark>..."    │
│ [→ Ir al inicio del post]                  │
│                                             │
│ 💬 En comentarios (2 matches):              │
│ "...balance of the <mark>moon</mark>..."    │
│ [→ Ir a comentario #1] [→ #2]              │
│                                             │
│ 📄 En contenido:                            │
│ "...Islamic <mark>magic</mark> traditions..."│
│ [→ Ir a esta sección]                      │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 📄 Otro Post...                             │
│ ...                                         │
└─────────────────────────────────────────────┘
```

**Características:**
- ✅ Vista de lista vertical (más compacta)
- ✅ Snippets con highlights `<mark>`
- ✅ Contador de matches por tipo
- ✅ Deep links a secciones específicas
- ✅ Filtros adicionales visibles

---

## 🛠️ Implementación Técnica

### **1. HTML: Toggle Button**

```html
<!-- En search header -->
<div class="search-header">
    <div class="search-input-container">
        <input type="search" id="searchInput" placeholder="Buscar posts...">
        <button id="searchButton">🔍</button>
    </div>

    <button id="toggleSearchMode" class="mode-toggle" title="Cambiar a vista avanzada">
        <span class="icon">🔬</span>
        <span class="text">Avanzada</span>
    </button>
</div>

<!-- Filtros avanzados (ocultos por defecto) -->
<div id="advancedFilters" class="advanced-filters" style="display: none;">
    <!-- Buscar en campos específicos -->
    <div class="filter-group">
        <label class="filter-label">Buscar solo en:</label>
        <label><input type="checkbox" name="searchIn" value="title"> 📌 Títulos</label>
        <label><input type="checkbox" name="searchIn" value="content"> 📄 Contenido</label>
        <label><input type="checkbox" name="searchIn" value="comments"> 💬 Comentarios</label>
        <label><input type="checkbox" name="searchIn" value="subtitles"> 🎬 Subtítulos</label>
    </div>

    <!-- Rango de fechas -->
    <div class="filter-group">
        <label class="filter-label">Fecha de publicación:</label>
        <input type="date" id="dateFrom" class="date-input">
        <span>hasta</span>
        <input type="date" id="dateTo" class="date-input">
    </div>

    <!-- Tipo de contenido -->
    <div class="filter-group">
        <label class="filter-label">Con:</label>
        <label><input type="checkbox" name="hasContent" value="video"> 🎥 Videos</label>
        <label><input type="checkbox" name="hasContent" value="images"> 📸 Imágenes</label>
        <label><input type="checkbox" name="hasContent" value="comments"> 💬 Comentarios</label>
    </div>
</div>

<!-- Contenedor de posts (cambia layout según modo) -->
<div id="postsContainer" class="posts-grid">
    <!-- Posts renderizados aquí -->
</div>
```

### **2. CSS: Dual Layout**

```css
/* ===================================
   Modo Normal (Grid)
   =================================== */
.posts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
    transition: all 0.3s ease;
}

.post-card {
    /* Diseño actual de cards */
}

/* ===================================
   Modo Avanzado (Lista con snippets)
   =================================== */
body.search-advanced-mode .posts-grid {
    display: flex;
    flex-direction: column;
    gap: 15px;
    max-width: 900px;
    margin: 0 auto;
}

body.search-advanced-mode .post-card {
    display: flex;
    flex-direction: column;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    background: white;
}

/* Header del post en modo avanzado */
.post-card .post-header {
    margin-bottom: 15px;
}

.post-card .post-header h3 {
    margin: 0 0 5px 0;
    font-size: 1.3em;
}

.post-card .post-meta {
    color: #666;
    font-size: 0.9em;
}

/* Detalles de búsqueda (solo visible en modo avanzado) */
.search-results-detail {
    display: none;
}

body.search-advanced-mode .search-results-detail {
    display: block;
    background: #f8f9fa;
    border-radius: 6px;
    padding: 15px;
    margin-top: 10px;
}

.match-count {
    font-weight: bold;
    margin-bottom: 10px;
    color: #333;
}

/* Snippet de cada coincidencia */
.match-snippet {
    margin: 10px 0;
    padding: 10px;
    background: white;
    border-left: 3px solid #4CAF50;
    border-radius: 4px;
}

.match-snippet .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.85em;
    font-weight: bold;
    margin-bottom: 5px;
    background: #e3f2fd;
    color: #1976d2;
}

.match-snippet p {
    margin: 8px 0;
    line-height: 1.5;
}

.match-snippet mark {
    background: #ffeb3b;
    padding: 2px 4px;
    border-radius: 2px;
    font-weight: bold;
}

.jump-link {
    display: inline-block;
    margin-top: 5px;
    color: #1976d2;
    text-decoration: none;
    font-size: 0.9em;
    transition: color 0.2s;
}

.jump-link:hover {
    color: #0d47a1;
    text-decoration: underline;
}

/* Filtros avanzados */
.advanced-filters {
    background: #f5f5f5;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;
}

.filter-group {
    margin-bottom: 10px;
}

.filter-group:last-child {
    margin-bottom: 0;
}

.filter-label {
    font-weight: bold;
    margin-right: 10px;
}

.filter-group label {
    margin-right: 15px;
    cursor: pointer;
}

.date-input {
    padding: 5px;
    border: 1px solid #ddd;
    border-radius: 4px;
}

/* Toggle button */
.mode-toggle {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 8px 15px;
    border: 1px solid #ddd;
    border-radius: 20px;
    background: white;
    cursor: pointer;
    transition: all 0.2s;
}

.mode-toggle:hover {
    background: #f5f5f5;
    border-color: #1976d2;
}

body.search-advanced-mode .mode-toggle {
    background: #1976d2;
    color: white;
    border-color: #1976d2;
}
```

### **3. JavaScript: Mode Toggle Logic**

```javascript
// Estado global
let searchMode = 'normal'; // 'normal' o 'advanced'
let currentQuery = '';
let searchResults = [];

// Toggle mode
document.getElementById('toggleSearchMode').addEventListener('click', () => {
    searchMode = searchMode === 'normal' ? 'advanced' : 'normal';
    updateSearchMode();
});

function updateSearchMode() {
    const button = document.getElementById('toggleSearchMode');
    const filters = document.getElementById('advancedFilters');

    if (searchMode === 'advanced') {
        // Activar modo avanzado
        document.body.classList.add('search-advanced-mode');
        button.innerHTML = '<span class="icon">📚</span><span class="text">Normal</span>';
        button.title = 'Cambiar a vista normal';
        filters.style.display = 'block';

        // Re-render con vista avanzada
        renderSearchResults(searchResults, 'advanced');
    } else {
        // Volver a modo normal
        document.body.classList.remove('search-advanced-mode');
        button.innerHTML = '<span class="icon">🔬</span><span class="text">Avanzada</span>';
        button.title = 'Cambiar a vista avanzada';
        filters.style.display = 'none';

        // Re-render con vista normal (grid)
        renderSearchResults(searchResults, 'normal');
    }

    // Guardar preferencia en localStorage
    localStorage.setItem('searchMode', searchMode);
}

// Cargar preferencia al iniciar
window.addEventListener('DOMContentLoaded', () => {
    const savedMode = localStorage.getItem('searchMode');
    if (savedMode === 'advanced') {
        searchMode = 'advanced';
        updateSearchMode();
    }
});
```

### **4. JavaScript: Renderizado Dual**

```javascript
function renderSearchResults(results, mode = 'normal') {
    const container = document.getElementById('postsContainer');

    if (mode === 'normal') {
        // Modo grid (actual)
        container.innerHTML = results.map(post => renderNormalCard(post)).join('');
    } else {
        // Modo avanzado (con snippets)
        container.innerHTML = results.map(post => renderAdvancedCard(post)).join('');
    }
}

function renderNormalCard(post) {
    // Renderizado actual de cards (sin cambios)
    return `
        <div class="post-card" data-post-id="${post.post_id}">
            ${post.has_images ? `<img src="${post.images[0]}" alt="${post.title}">` : ''}
            <h3>${post.title}</h3>
            <div class="badges">
                ${renderBadges(post.matched_in)}
            </div>
        </div>
    `;
}

function renderAdvancedCard(post) {
    return `
        <div class="post-card advanced" data-post-id="${post.post_id}">
            <div class="post-header">
                <h3>${post.title}</h3>
                <div class="post-meta">
                    ${post.creator_name} • ${post.published_date}
                    ${post.counts.comments > 0 ? `• ${post.counts.comments} comentarios` : ''}
                </div>
            </div>

            <div class="search-results-detail">
                <div class="match-count">
                    ${getTotalMatches(post)} coincidencia${getTotalMatches(post) !== 1 ? 's' : ''} encontrada${getTotalMatches(post) !== 1 ? 's' : ''}:
                </div>

                ${renderMatchesByType(post)}
            </div>
        </div>
    `;
}

function getTotalMatches(post) {
    return post.matched_in.length;
}

function renderMatchesByType(post) {
    let html = '';

    // Título
    if (post.matched_in.includes('title') && post.snippets.title) {
        html += `
            <div class="match-snippet">
                <span class="badge">📌 En título</span>
                <p>${post.snippets.title}</p>
                <a href="/post/${post.post_id}#title" class="jump-link">→ Ir al inicio del post</a>
            </div>
        `;
    }

    // Contenido
    if (post.matched_in.includes('content') && post.snippets.content) {
        html += `
            <div class="match-snippet">
                <span class="badge">📄 En contenido</span>
                <p>${post.snippets.content}</p>
                <a href="/post/${post.post_id}?q=${encodeURIComponent(currentQuery)}#content" class="jump-link">→ Ir a esta sección</a>
            </div>
        `;
    }

    // Comentarios
    if (post.matched_in.includes('comments') && post.snippets.comments) {
        html += `
            <div class="match-snippet">
                <span class="badge">💬 En comentarios</span>
                <p>${post.snippets.comments}</p>
                <a href="/post/${post.post_id}?q=${encodeURIComponent(currentQuery)}#comments" class="jump-link">→ Ir a comentarios</a>
            </div>
        `;
    }

    // Subtítulos
    if (post.matched_in.includes('subtitles') && post.snippets.subtitles) {
        html += `
            <div class="match-snippet">
                <span class="badge">🎬 En subtítulos de video</span>
                <p>${post.snippets.subtitles}</p>
                <a href="/post/${post.post_id}?q=${encodeURIComponent(currentQuery)}#video" class="jump-link">→ Ir al video</a>
            </div>
        `;
    }

    // Tags
    if (post.matched_in.includes('tags')) {
        html += `
            <div class="match-snippet">
                <span class="badge">🏷️ En tags</span>
                <p>Tags: ${post.patreon_tags.join(', ')}</p>
            </div>
        `;
    }

    return html || '<p>Sin coincidencias específicas detectadas</p>';
}
```

### **5. Deep Links y Navegación**

```javascript
// Al cargar un post desde búsqueda
window.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const searchQuery = urlParams.get('q');
    const targetSection = window.location.hash;

    if (searchQuery) {
        // Highlight términos buscados
        highlightSearchTerms(searchQuery);

        // Scroll a sección específica
        if (targetSection) {
            scrollToSection(targetSection);
        }

        // Mostrar navegación entre matches
        showMatchNavigation(searchQuery);
    }
});

function highlightSearchTerms(query) {
    const terms = query.split(' ').filter(t => t.length > 0);
    const bodyText = document.body.innerHTML;

    terms.forEach(term => {
        const regex = new RegExp(`(${term})`, 'gi');
        document.body.innerHTML = bodyText.replace(regex, '<mark>$1</mark>');
    });
}

function scrollToSection(hash) {
    const element = document.querySelector(hash);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        element.classList.add('highlight-section');
    }
}

function showMatchNavigation(query) {
    const matches = document.querySelectorAll('mark');
    if (matches.length === 0) return;

    let currentMatch = 0;

    const nav = document.createElement('div');
    nav.className = 'match-navigation';
    nav.innerHTML = `
        <button id="prevMatch">↑ Anterior</button>
        <span id="matchCounter">1 / ${matches.length}</span>
        <button id="nextMatch">↓ Siguiente</button>
    `;
    document.body.appendChild(nav);

    // Navegación
    document.getElementById('nextMatch').addEventListener('click', () => {
        currentMatch = (currentMatch + 1) % matches.length;
        scrollToMatch(matches[currentMatch], currentMatch, matches.length);
    });

    document.getElementById('prevMatch').addEventListener('click', () => {
        currentMatch = (currentMatch - 1 + matches.length) % matches.length;
        scrollToMatch(matches[currentMatch], currentMatch, matches.length);
    });
}

function scrollToMatch(element, index, total) {
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    element.classList.add('current-match');
    document.getElementById('matchCounter').textContent = `${index + 1} / ${total}`;
}
```

---

## 📋 Tareas de Implementación

### **Paso 1: UI Básica (2-3 horas)**
- [ ] Agregar toggle button en header
- [ ] Implementar cambio de layout (grid ↔️ lista)
- [ ] CSS para ambos modos
- [ ] Guardar preferencia en localStorage

### **Paso 2: Vista Avanzada (3-4 horas)**
- [ ] Renderizar snippets con highlights
- [ ] Mostrar contador de matches
- [ ] Agrupar coincidencias por tipo (title, comments, etc)
- [ ] Links directos a secciones

### **Paso 3: Filtros Avanzados (2-3 horas)**
- [ ] UI de filtros (campos, fechas, tipo)
- [ ] Aplicar filtros a query de búsqueda
- [ ] Actualizar endpoint para soportar filtros

### **Paso 4: Deep Linking (2-3 horas)**
- [ ] Detectar query en URL (?q=...)
- [ ] Highlight automático de términos
- [ ] Scroll a sección específica (#comments, #video, etc)
- [ ] Navegación prev/next entre matches

### **Paso 5: Testing y Refinamiento (1-2 horas)**
- [ ] Probar ambos modos
- [ ] Verificar deep links
- [ ] Mobile responsive
- [ ] Performance con muchos resultados

**Total estimado:** 10-15 horas

---

## 🎯 Criterios de Éxito

### **Funcional**
- ✅ Toggle funciona sin recargar página
- ✅ Ambos modos renderizan correctamente
- ✅ Deep links llevan a sección correcta
- ✅ Highlights visibles y precisos
- ✅ Filtros aplican correctamente

### **UX**
- ✅ Transición suave entre modos
- ✅ Preferencia persiste entre sesiones
- ✅ Snippets con contexto útil
- ✅ Navegación intuitiva entre matches

### **Performance**
- ✅ Cambio de modo < 100ms
- ✅ Renderizado de 50 resultados < 500ms
- ✅ Smooth scroll sin lag

---

## 📊 Ventajas de Este Diseño

| Aspecto | Ventaja |
|---------|---------|
| **UX** | Usuarios eligen su experiencia preferida |
| **Compatibilidad** | No rompe nada existente |
| **Flexibilidad** | Modo normal para browsing, avanzado para búsqueda precisa |
| **Progresivo** | Funcionalidades se pueden agregar gradualmente |
| **Educativo** | Usuarios descubren modo avanzado cuando lo necesitan |

---

## 🚀 Próximos Pasos

1. **Completar Fase 2** (comentarios y subtítulos) ✅
2. **Implementar Fase 4** (triggers automáticos)
3. **Implementar Fase 5** (dual mode) según este plan
4. **Opcional: Fase 6** (fuzzy search con pg_trgm)

---

**Última actualización:** 2025-11-09
**Autor:** Javi + Claude
**Estado:** 📝 Planificado - Pendiente de implementación
