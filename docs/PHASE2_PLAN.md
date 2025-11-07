# 📋 Phase 2 Plan: Firebase → PostgreSQL Migration

**Fecha de creación**: 2025-11-07
**Estado**: Planificación completada
**Objetivo**: Migrar todos los scripts Python de Firebase a PostgreSQL

---

## 🔍 Auditoría Completada

### Scripts que dependen de Firebase (6 scripts)

1. **src/daily_incremental_scrape.py** (311 líneas)
   - Scraper incremental diario
   - Usa: `FirebaseTracker`
   - Prioridad: **ALTA** (script de uso diario)

2. **src/phase1_url_collector.py** (311 líneas)
   - Recolector de URLs (Fase 1)
   - Usa: `FirebaseTracker`
   - Prioridad: **ALTA** (script crítico)

3. **src/phase2_detail_extractor.py** (389 líneas)
   - Extractor de detalles (Fase 2)
   - Usa: `FirebaseTracker`
   - Prioridad: **ALTA** (script crítico)

4. **src/orchestrator.py** (262 líneas)
   - Orquestador de procesos
   - Usa: `FirebaseTracker`
   - Prioridad: **MEDIA**

5. **src/reset_creator.py** (208 líneas)
   - Reset de datos de creador
   - Usa: `FirebaseTracker`
   - Prioridad: **BAJA** (utility script)

6. **src/firebase_tracker.py** (344 líneas)
   - **Tracker de Firebase (A REEMPLAZAR)**
   - Prioridad: **CRÍTICA**

---

## 🎯 Plan de Migración

### Paso 1: Crear PostgresTracker ✅ (PRÓXIMO)

**Archivo**: `src/postgres_tracker.py`

**Requisitos**:
- Misma API que `FirebaseTracker`
- Usar SQLAlchemy ORM
- Conectar a tabla `scraping_status` de PostgreSQL
- Implementar todos los métodos:

**Métodos de Post Tracking** (11 métodos):
- `create_post_record(post_id, creator_id, post_url)`
- `mark_url_collected(post_id)`
- `mark_details_extracted(post_id, success, error)`
- `mark_uploaded_to_notion(post_id, notion_page_id)`
- `increment_attempt(post_id)`
- `get_post(post_id)`
- `post_exists(post_id)`
- `get_all_posts()`
- `get_posts_by_creator(creator_id)`
- `get_posts_needing_details(creator_id)`
- `get_posts_needing_notion_upload(creator_id)`

**Métodos de Creator Stats** (3 métodos):
- `update_creator_stats(creator_id)`
- `get_creator_stats(creator_id)`
- `get_all_creator_stats()`

**Métodos de Utilidades** (2 métodos):
- `get_summary()`
- `print_summary()`

### Paso 2: Migrar Scripts (Orden de prioridad)

#### 2.1 Scripts Críticos (migrar primero)

**a) phase1_url_collector.py**
```python
# ANTES:
from firebase_tracker import FirebaseTracker, load_firebase_config

# DESPUÉS:
from postgres_tracker import PostgresTracker, load_postgres_config
```

**b) phase2_detail_extractor.py**
```python
# ANTES:
from firebase_tracker import FirebaseTracker, load_firebase_config

# DESPUÉS:
from postgres_tracker import PostgresTracker, load_postgres_config
```

**c) daily_incremental_scrape.py**
```python
# ANTES:
from firebase_tracker import FirebaseTracker, load_firebase_config

# DESPUÉS:
from postgres_tracker import PostgresTracker, load_postgres_config
```

#### 2.2 Scripts Secundarios

**d) orchestrator.py**
**e) reset_creator.py**

### Paso 3: Testing

Para cada script migrado:
```bash
# Test básico de import
python -c "from src.postgres_tracker import PostgresTracker; print('✓ Import OK')"

# Test de funcionalidad (según script)
python src/phase1_url_collector.py --help
```

### Paso 4: Mover a Archive

Una vez todos los scripts migren exitosamente:
```bash
# Mover firebase_tracker.py a archive
mv src/firebase_tracker.py archive/phase1-firebase/

# Eliminar credenciales Firebase de .env (opcional)
# FIREBASE_DATABASE_URL y FIREBASE_DATABASE_SECRET
```

---

## 📦 Limpieza de Archivos (Phase 3 - FUTURO)

**NO hacer ahora, documentado para después**

### Archivos a mover/limpiar:

#### Avatares (7 archivos)
**Acción**: Mover a `data/avatars/` o `config/avatars/`
- `astrobymax.jpg`
- `horoi.jpg`
- `olomihead on history.jpg`
- `prueba.jpeg`, `prueba2.jpeg`, `prueba3.jpeg`, `prueba4.jpeg`

#### JSON sueltos (1 archivo)
**Acción**: Mover a `data/processed/` o eliminar si es backup viejo
- `headonhistory_posts_detailed.json` (15MB)

#### Backups (2 archivos)
**Acción**: Mover a `data/backups/`
- `backup_jsons_20251107.tar.gz` (15MB)
- `web_backup_20251103_065805.tar.gz` (4MB)

#### Scripts de test (1 archivo)
**Acción**: Mover a `scripts/` o eliminar
- `test_json_adapter.py`

#### Otros archivos
**Acción**: Revisar si es necesario
- `scraper.txt` (451KB)

**Script de limpieza** (crear en Phase 3):
```bash
# Crear directorios
mkdir -p data/avatars config/avatars

# Mover avatares
mv *.jpg *.jpeg data/avatars/

# Mover backups
mv *.tar.gz data/backups/

# Mover JSON grandes
mv *_posts_detailed.json data/processed/

# Limpiar tests
mv test_*.py scripts/
```

---

## 📊 Métricas

**Scripts Python total**: 22
**Scripts que usan Firebase**: 6
**Scripts a migrar**: 6
**Métodos a implementar**: 16
**Archivos a limpiar**: 11 (Phase 3)

---

## ⏭️ Próximo Paso Inmediato

1. **Crear `src/postgres_tracker.py`** con SQLAlchemy
2. **Implementar los 16 métodos** con API compatible
3. **Hacer commit y push**
4. **Migrar `phase1_url_collector.py`** como prueba piloto
5. **Verificar funcionamiento**
6. **Continuar con resto de scripts**

---

## 📝 Notas Importantes

- **NO tocar limpieza de archivos** hasta que Phase 2 esté completa
- Los avatares probablemente se usan en algún script, **verificar primero**
- Los backups pueden ser importantes, **NO borrar sin revisar**
- `firebase_tracker.py` NO eliminar, solo mover a `archive/` cuando todo funcione

---

**Última actualización**: 2025-11-07
**Por**: Claude
**Siguiente revisión**: Después de completar PostgresTracker
