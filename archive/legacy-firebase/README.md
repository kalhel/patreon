# 🗄️ Archive - Scripts Legacy (Firebase/JSON)

**Fecha de archivo**: 2025-11-09
**Razón**: Migración completa a PostgreSQL completada

---

## 📋 ¿Qué hay aquí?

Scripts del sistema **anterior** que usaban:
- Firebase Realtime Database (deprecado)
- JSONs en filesystem (deprecado)
- Scrapers v1 (reemplazados por v2 con PostgreSQL)

---

## 🔄 Estado del Proyecto

**Sistema anterior** (deprecado):
- ❌ Firebase Realtime Database para tracking
- ❌ JSONs en `data/processed/` para posts
- ❌ Scrapers legacy

**Sistema actual** (producción):
- ✅ PostgreSQL para todo (tracking + posts + media)
- ✅ Scrapers v2 con `patreon_scraper_v2.py`
- ✅ `postgres_tracker.py` para tracking

---

## 📁 Contenido

### Scrapers Legacy
- `incremental_scraper.py` - Scraper incremental v1 (pre-Phase2)
- `daily_incremental_scrape.py` - Daily scrape legacy
- `incremental_collections_scraper.py` - Collections scraper legacy
- `patreon_scraper.py` - Scraper base v1

**Reemplazados por:**
- `src/phase1_url_collector.py`
- `src/phase2_detail_extractor.py`
- `src/phase3_collections_scraper.py`
- `src/patreon_scraper_v2.py`

### Auth Legacy
- `patreon_auth.py` - Auth con credenciales guardadas

**Reemplazado por:**
- `src/patreon_auth_selenium.py`

### Utilidades Legacy
- `clean_ui_labels.py` - Limpia labels de UI en JSONs
- `diagnose_posts.py` - Debug de creator_id en JSONs
- `find_youtube_posts.py` - Busca posts con YouTube en JSON
- `get_horoi_videos_from_json.py` - Obtiene videos de JSON
- `inspect_horoi_posts.py` - Inspecciona estructura JSON
- `migrate_media_structure.py` - Migra estructura de media antigua

---

## ⚠️ ¿Cuándo Usar Estos Scripts?

### ✅ Mantener como Referencia
- Si necesitas entender cómo funcionaba el sistema anterior
- Si necesitas extraer datos de backups antiguos
- Si tienes JSONs antiguos que necesitas procesar

### ❌ NO Usar para Producción
- El sistema actual usa PostgreSQL exclusivamente
- Los scrapers v2 son más robustos y completos
- Firebase ya no está en uso

---

## 🔄 Recuperar Datos Antiguos

Si necesitas recuperar datos de Firebase o JSONs antiguos:

```bash
# Ver backups disponibles
ls -lh backups/pre-migration/

# Usar script de migración archivado
python archive/migrations-done/migrate_firebase_to_postgres.py
python archive/migrations-done/migrate_json_to_postgres.py
```

---

## 🗑️ Cuándo Eliminar

**Eliminar cuando**:
- Han pasado 12+ meses desde la migración
- No existen backups en Firebase/JSON que necesites
- El sistema PostgreSQL ha demostrado ser estable

**Mantener si**:
- Aún tienes datos en Firebase que no migraste
- Necesitas referencia del código legacy
- Quieres estudiar cómo evolucionó el sistema

---

## 📝 Historial de Migración

| Fecha | Evento |
|-------|--------|
| 2025-11-07 | Phase 1: Migración Firebase → PostgreSQL (982 posts) |
| 2025-11-07 | Phase 1.5: Schema V2 multi-source |
| 2025-11-09 | Archivado de scripts legacy |

---

**Migración completada**: ✅ 100%
**Sistema actual**: PostgreSQL
**Última revisión**: 2025-11-09
**Próxima revisión sugerida**: 2026-11-09 (12 meses)
