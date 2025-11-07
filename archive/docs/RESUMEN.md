# 📖 Resumen Completo - Patreon Scraper

Guía rápida de referencia con TODO lo que necesitas saber.

---

## 🚀 Configuración Inicial (PRIMERO)

### 1. Activar entorno virtual
```bash
source venv/bin/activate
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Verificar configuración
```bash
# Ver creators configurados
cat config/creators.json

# Ver credentials (NO compartir)
cat config/credentials.json
```

---

## 📂 Estructura del Proyecto

```
patreon/
├── src/                              ← Scripts principales
│   ├── phase1_url_collector.py      ← Recolectar URLs de posts
│   ├── phase2_detail_extractor.py   ← Extraer detalles completos
│   ├── phase3_collections_scraper.py ← Scrapear collections
│   ├── daily_incremental_scrape.py  ← ⚡ Actualizaciones diarias (RÁPIDO)
│   ├── add_creator.py               ← Añadir nuevos creadores
│   ├── reset_creator.py             ← Resetear datos de un creador
│   └── fix_corrupted_json.py        ← Reparar JSONs corruptos
│
├── tools/                            ← Utilidades y tests
│   ├── test_single_post.py
│   ├── clean_vtt_files.py
│   └── ...
│
├── web/                              ← Visor web local
│   ├── viewer.py                    ← Servidor Flask
│   └── templates/                   ← HTML templates
│
├── config/                           ← Configuración
│   ├── credentials.json             ← Patreon + Firebase (NO en git)
│   └── creators.json                ← Creators configurados
│
└── data/                             ← Datos scrapeados
    ├── raw/                         ← Posts sin procesar
    ├── processed/                   ← Posts procesados
    └── media/                       ← Multimedia descargado
```

---

## 🔄 Workflows

### ⚡ Actualización Diaria (RECOMENDADO - Rápido)

**Cuando:** Cada día para obtener posts nuevos

```bash
# 1. Solo posts NUEVOS (para en el primero conocido)
python src/daily_incremental_scrape.py --all

# 2. Procesar los pendientes
python src/phase2_detail_extractor.py --all --headless

# 3. Actualizar collections (solo nuevas/actualizadas)
python src/incremental_collections_scraper.py --all --headless
```

**Ventajas:**
- ⚡ 10-100x más rápido (segundos vs minutos)
- 💾 Ahorra ancho de banda
- 🎯 Solo scrapea lo nuevo
- 📚 Phase 3 también incremental (solo collections nuevas/actualizadas)

---

### 🆕 Añadir Nuevo Creator

**Cuando:** Primera vez con un creator

```bash
# 1. Añadir creator a config
python src/add_creator.py
# (Te preguntará: ID, nombre, URL, etc.)

# 2. Scrape completo inicial (primera vez)
python src/phase1_url_collector.py --creator CREATOR_NAME
python src/phase2_detail_extractor.py --creator CREATOR_NAME --headless
python src/phase3_collections_scraper.py --creator CREATOR_NAME --headless

# Actualizaciones diarias (después del inicial)
python src/daily_incremental_scrape.py --all
python src/phase2_detail_extractor.py --all --headless
python src/incremental_collections_scraper.py --all --headless
```

---

### 🔧 Resetear Creator (Si algo falla)

**Cuando:** JSON corrupto, errores, quieres empezar de cero

```bash
# Ver qué haría sin borrar nada
python src/reset_creator.py CREATOR_NAME --dry-run

# Resetear con backup + Firebase
python src/reset_creator.py CREATOR_NAME --firebase
```

**Hace:**
- ✅ Backup automático antes de borrar
- ✅ Borra archivos del creator
- ✅ Resetea Firebase (marca posts como pending)

---

## 🌐 Visor Web Local

```bash
# Iniciar servidor
python web/viewer.py

# Abrir en navegador
http://localhost:5000
```

**Funcionalidades:**
- 📄 Ver todos los posts organizados por creator
- 🔍 Búsqueda avanzada (FTS5)
- 📚 Vista de Collections (toggle)
- 🎨 Filtros por media (imágenes, videos, audio)
- 🏷️ Filtros por tags
- ⚙️ Settings (añadir creators, configurar Firebase)

---

## 📋 Comandos Útiles

### Ver estado de Firebase
```bash
python src/firebase_tracker.py
```

### Reparar JSON corrupto
```bash
python src/fix_corrupted_json.py data/processed/ARCHIVO.json
```

### Diagnosticar problemas
```bash
python src/debug_creators.py
python src/diagnose_headonhistory.py
```

### Limpiar subtítulos VTT
```bash
python tools/clean_vtt_files.py
```

---

## 🔑 Configuración Firebase

**Archivo:** `config/credentials.json`

```json
{
  "patreon": {
    "email": "tu_email@example.com",
    "password": "tu_password"
  },
  "firebase": {
    "database_url": "https://tu-proyecto.firebaseio.com",
    "database_secret": "TU_SECRET_AQUI"
  }
}
```

**Dónde obtener `database_secret`:**
1. Firebase Console → Tu proyecto
2. Settings (⚙️) → Service accounts
3. Database secrets → Copiar

---

## 🎯 Casos de Uso Comunes

### 1. Scrape diario automático
```bash
# Crear cron job (crontab -e)
0 2 * * * cd /ruta/patreon && source venv/bin/activate && python src/daily_incremental_scrape.py --all
```

### 2. Procesar solo un creator
```bash
python src/phase2_detail_extractor.py --creator headonhistory --headless
```

### 3. Limitar posts a procesar
```bash
python src/phase1_url_collector.py --creator skyscript --limit 10
python src/phase2_detail_extractor.py --all --limit 5
```

### 4. Ver con navegador visible (debug)
```bash
python src/phase1_url_collector.py --creator headonhistory --no-headless
```

---

## ⚠️ Errores Comunes y Soluciones

### Error: Creator no encontrado
```bash
# Verificar creators disponibles
cat config/creators.json | grep creator_id

# Añadir si falta
python src/add_creator.py
```

### Error: Firebase 403 Forbidden
```bash
# Verificar database_secret correcto
cat config/credentials.json

# Obtener nuevo secret de Firebase Console
```

### Error: JSON corrupto
```bash
# Intentar reparar
python src/fix_corrupted_json.py data/processed/ARCHIVO.json

# O resetear y volver a scrapear
python src/reset_creator.py CREATOR_NAME --firebase
```

### Error: Cookies expiradas
```bash
# Borrar cookies y volver a login
rm config/patreon_cookies.json

# Siguiente scrape hará login automático
```

---

## 📊 Fases del Scraping

### Phase 1: Recolección de URLs
- **Script:** `src/phase1_url_collector.py`
- **Qué hace:** Scrapea URLs de todos los posts
- **Output:** Firebase (tracking) + logs
- **Tiempo:** Depende de cantidad de posts

### Phase 2: Extracción de Detalles
- **Script:** `src/phase2_detail_extractor.py`
- **Qué hace:** Extrae contenido completo de cada post
- **Output:** `data/processed/{creator}_posts_detailed.json`
- **Descarga:** Imágenes, videos, audios

### Phase 3: Collections
- **Script:** `src/phase3_collections_scraper.py`
- **Qué hace:** Scrapea collections y asocia posts
- **Output:** `data/processed/{creator}_collections.json`

---

## 🆕 Novedades Recientes

### Incremental Scrapers (Phase 1 y 3)
- ⚡ **Phase 1**: `daily_incremental_scrape.py` - Solo posts nuevos (10-100x más rápido)
- ⚡ **Phase 3**: `incremental_collections_scraper.py` - Solo collections nuevas/actualizadas
- 🎯 Solo scrapea lo que cambió
- ⏹️ Para al encontrar contenido conocido
- 💾 Perfecto para cron jobs diarios
- ✅ Phase 2 ya funciona incremental (solo procesa posts "pending")

### Collections View en Web
- 📚 Toggle para ver collections
- 📊 Stats agregados por collection
- 🖼️ Imágenes cuadradas optimizadas

### Video Thumbnails
- 🎬 Videos muestran primer frame como thumbnail
- ✅ Ya no más pantalla negra

### Settings UI Mejorado
- ⚙️ Añadir creators desde web
- 🔒 Protección contra borrado accidental
- 💾 Backups automáticos

### Subtítulos Mejorados
- 📝 Auto-detección de archivos .vtt
- 🌐 Soporte para múltiples idiomas (ES, EN)
- ✨ Limpieza automática de parámetros de alineación

---

## 📖 Documentación Completa

- **README Principal:** [README.md](../README.md)
- **Roadmap:** [ROADMAP.md](../ROADMAP.md) 🆕 - Mejoras futuras y planificación
- **Arquitectura:** [ARCHITECTURE.md](ARCHITECTURE.md) 🆕 - Diseño técnico integral del sistema
- **Changelog:** [CHANGELOG.md](../CHANGELOG.md)
- **Quick Updates:** [README_UPDATES.md](../README_UPDATES.md)
- **Workflow Original:** [TWO_PHASE_WORKFLOW.md](TWO_PHASE_WORKFLOW.md)
- **Web Viewer:** [WEB_VIEWER.md](WEB_VIEWER.md)
- **Advanced Search:** [ADVANCED_SEARCH.md](ADVANCED_SEARCH.md)

---

## 💡 Tips y Mejores Prácticas

1. **Usa incremental para daily updates** - 100x más rápido
2. **Siempre usa --headless** en producción - Más estable
3. **Haz backup antes de resetear** - El script lo hace automático
4. **Revisa Firebase status** antes de procesar - Evita duplicados
5. **Usa --limit para tests** - Más rápido para probar
6. **Verifica credentials.json** si hay errores - Suele ser la causa

---

**Última actualización:** 2025-11-06
