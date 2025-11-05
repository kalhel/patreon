# Collections Implementation Plan

## Overview

Implementar sistema de Collections para agrupar posts de Patreon.

## URLs de Collections por Creator

- astrobymax: https://www.patreon.com/cw/astrobymax/collections
- horoiproject: https://www.patreon.com/cw/horoiproject/collections
- headonhistory: https://www.patreon.com/c/headonhistory/collections

## Phase 3: Collections Scraper

### Archivo: `src/phase3_collections_scraper.py`

### Funcionalidad

1. **Visitar página de collections**
   - Navegar a `/c/{creator}/collections` o `/cw/{creator}/collections`
   - Esperar a que cargue la lista de collections

2. **Extraer cada collection**
   ```python
   {
     "collection_id": "12345",
     "collection_name": "Astrology Basics",
     "collection_url": "https://www.patreon.com/collection/12345",
     "collection_image": "https://...",
     "description": "Learn the basics of astrology",
     "post_count": 15,
     "post_ids": ["128693945", "129012345", ...],
     "scraped_at": "2025-11-05T..."
   }
   ```

3. **Guardar datos**
   - Archivo: `data/processed/{creator_id}_collections.json`
   - Estructura:
   ```json
   {
     "creator_id": "astrobymax",
     "scraped_at": "2025-11-05T...",
     "collections": [
       {
         "collection_id": "12345",
         "collection_name": "Astrology Basics",
         "collection_url": "https://...",
         "collection_image": "https://...",
         "description": "...",
         "post_count": 15,
         "post_ids": ["128693945", "129012345"]
       }
     ]
   }
   ```

4. **Actualizar posts existentes**
   - Leer `{creator_id}_posts_detailed.json`
   - Para cada post en una collection, añadir:
   ```json
   {
     "post_id": "128693945",
     "collections": [
       {
         "collection_id": "12345",
         "collection_name": "Astrology Basics"
       }
     ]
   }
   ```

### CLI Options

```bash
# Scrapear collections de todos los creadores
python src/phase3_collections_scraper.py --all

# Scrapear collections de un solo creador
python src/phase3_collections_scraper.py --creator astrobymax

# Actualizar posts con información de collections
python src/phase3_collections_scraper.py --all --update-posts
```

## Integración con Web Viewer

### Opción 1: Filtro por Collection (Simple)

En `web/viewer.py`:
```python
@app.route('/collection/<creator_id>/<collection_name>')
def view_collection(creator_id, collection_name):
    """Ver todos los posts de una collection"""
    # Cargar collections
    # Filtrar posts por collection
    # Mostrar en grid similar a tags
```

### Opción 2: Cards de Collections en Index (Avanzado)

Añadir sección en index.html:
```html
<div class="collections-section">
  <h2>Collections</h2>
  <div class="collections-grid">
    <!-- Card por cada collection -->
    <div class="collection-card">
      <img src="collection_image">
      <h3>Collection Name</h3>
      <span>15 posts</span>
    </div>
  </div>
</div>
```

### Opción 3: Badge en Post Cards (Mínimo)

Mostrar badge en tarjetas de posts que pertenecen a collections:
```html
<div class="post-card">
  <!-- contenido existente -->
  {% if post.collections %}
    <div class="collection-badges">
      {% for collection in post.collections %}
        <span class="badge">📁 {{ collection.collection_name }}</span>
      {% endfor %}
    </div>
  {% endif %}
</div>
```

## Firebase Integration

### Nueva estructura en Firebase:

```json
{
  "collections": {
    "astrobymax": {
      "12345": {
        "collection_id": "12345",
        "collection_name": "Astrology Basics",
        "post_count": 15,
        "last_scraped": "2025-11-05T..."
      }
    }
  },
  "posts": {
    "128693945": {
      "post_id": "128693945",
      "creator_id": "astrobymax",
      "collections": ["12345"],
      ...
    }
  }
}
```

## Timeline

### Paso 1: Implementar Scraper (1-2 horas)
- [x] Crear `phase3_collections_scraper.py`
- [x] Implementar navegación a collections page
- [x] Extraer lista de collections
- [x] Extraer post_ids de cada collection
- [x] Guardar JSON

### Paso 2: Actualizar Posts (30 min)
- [x] Script para actualizar posts existentes
- [x] Añadir campo `collections` a cada post

### Paso 3: Web Viewer - Mínimo (30 min)
- [ ] Cargar collections en viewer.py
- [ ] Mostrar badge en post cards

### Paso 4: Web Viewer - Completo (1-2 horas)
- [ ] Página de collection
- [ ] Grid de collections en index
- [ ] Filtrado por collection

## Notas Técnicas

### Detectar Collections en HTML

Posibles selectores:
```python
# Lista de collections
collections = driver.find_elements(By.CSS_SELECTOR, '[data-tag="collection-card"]')

# O buscar por hrefs
collection_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/collection/"]')

# Nombre
name = collection.find_element(By.CSS_SELECTOR, 'h2, h3, [data-tag="collection-title"]').text

# Imagen
img = collection.find_element(By.TAG_NAME, 'img').get_attribute('src')

# Click para ver posts de la collection
collection.click()
time.sleep(2)

# Extraer post IDs de la URL o elementos
post_elements = driver.find_elements(By.CSS_SELECTOR, '[data-tag="post-card"]')
```

### Estrategia de Extracción

**Opción A**: Desde página de collections (RECOMENDADO)
- Visitar `/collections`
- Extraer metadata de cada collection
- Click en cada una para ver los posts
- Extraer post_ids

**Opción B**: Desde cada post individual
- Al extraer post en Phase 2
- Buscar en HTML si tiene badge/enlace de collection
- Guardar collection_id en el post
- PROBLEMA: Menos eficiente, puede perder collections vacías

## Decisión Final

👉 **Usar Opción A: Scraper independiente en Phase 3**

Razones:
1. Más limpio y mantenible
2. No afecta Phase 2 existente
3. Captura todas las collections (incluso vacías)
4. Puede re-ejecutarse de forma independiente
5. Coincide con arquitectura de fases del proyecto

## Test Plan

```bash
# 1. Scrapear collections de un creador
python src/phase3_collections_scraper.py --creator astrobymax --headless

# 2. Verificar JSON generado
cat data/processed/astrobymax_collections.json | jq

# 3. Actualizar posts
python src/phase3_collections_scraper.py --creator astrobymax --update-posts

# 4. Verificar posts actualizados
cat data/processed/astrobymax_posts_detailed.json | jq '.[0].collections'

# 5. Ver en web viewer
python web/viewer.py
# Visitar http://localhost:5000 y verificar badges
```
