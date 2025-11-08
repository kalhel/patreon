# 🔧 Phase 2: Core Backend Implementation

**Estado**: 🟡 PREPARADO - Pendiente de revisión antes de ejecución
**Fecha de creación**: 2025-11-07
**Última actualización**: 2025-11-07

---

## 📋 Índice

1. [Objetivo](#objetivo)
2. [Análisis del Código Actual](#análisis-del-código-actual)
3. [Plan de Implementación](#plan-de-implementación)
4. [Arquitectura PostgresTracker](#arquitectura-postgrestracker)
5. [Scripts a Migrar](#scripts-a-migrar)
6. [Testing y Verificación](#testing-y-verificación)
7. [Cronograma](#cronograma)

---

## 🎯 Objetivo

Migrar el sistema de tracking de **Firebase Realtime Database** a **PostgreSQL**, creando una clase `PostgresTracker` que reemplace completamente a `FirebaseTracker` y que aproveche el nuevo **Schema V2 multi-source**.

### ¿Por qué es importante?

1. **Eliminar dependencia de Firebase**: Centralizar todo en PostgreSQL
2. **Aprovechar Schema V2**: Usar el diseño multi-source (creators + creator_sources)
3. **Mejor performance**: Consultas SQL optimizadas vs REST API calls
4. **Integridad de datos**: Foreign keys, constraints, transacciones ACID
5. **Simplificar stack**: Una sola base de datos en vez de Firebase + PostgreSQL

---

## 🔍 Análisis del Código Actual

### FirebaseTracker - API Completa

El archivo `src/firebase_tracker.py` tiene **345 líneas** con los siguientes métodos:

#### **Métodos de Post Tracking**
```python
create_post_record(post_id, creator_id, post_url) -> bool
mark_url_collected(post_id) -> bool
mark_details_extracted(post_id, success, error) -> bool
mark_uploaded_to_notion(post_id, notion_page_id) -> bool
increment_attempt(post_id) -> bool
get_post(post_id) -> Optional[Dict]
post_exists(post_id) -> bool
get_all_posts() -> Dict[str, Dict]
get_posts_by_creator(creator_id) -> List[Dict]
get_posts_needing_details(creator_id=None) -> List[Dict]
get_posts_needing_notion_upload(creator_id=None) -> List[Dict]
```

#### **Métodos de Creator Stats**
```python
update_creator_stats(creator_id) -> bool
get_creator_stats(creator_id) -> Optional[Dict]
get_all_creator_stats() -> Dict[str, Dict]
```

#### **Métodos de Utilidad**
```python
get_summary() -> Dict
print_summary() -> None
```

### Scripts que usan FirebaseTracker

Encontrados **10 scripts** que dependen de FirebaseTracker:

| Script | Función | Prioridad |
|--------|---------|-----------|
| `src/phase1_url_collector.py` | Colecta URLs de posts | 🔴 Alta |
| `src/phase2_detail_extractor.py` | Extrae detalles de posts | 🔴 Alta |
| `src/orchestrator.py` | Orquesta phase 1 + 2 | 🔴 Alta |
| `src/daily_incremental_scrape.py` | Scraping incremental diario | 🟡 Media |
| `src/reset_creator.py` | Resetear estado de creator | 🟢 Baja |
| `tools/rescrape_youtube_posts.py` | Re-scrapear posts YouTube | 🟢 Baja |
| `tools/reset_processed_posts.py` | Resetear posts procesados | 🟢 Baja |
| `tools/fix_post_creator.py` | Arreglar creator de posts | 🟢 Baja |
| `tools/get_horoi_video_posts.py` | Obtener videos de Horoi | 🟢 Baja |
| `tools/inspect_horoi_posts.py` | Inspeccionar posts Horoi | 🟢 Baja |

**Estrategia**: Migrar primero los 3 scripts de alta prioridad, luego los demás.

### Estructura de Datos Firebase vs PostgreSQL

**Firebase estructura** (lo que tenemos ahora):
```json
{
  "posts": {
    "123456": {
      "post_id": "123456",
      "creator_id": "astrobymax",
      "post_url": "https://...",
      "status": {
        "url_collected": true,
        "url_collected_at": "2025-11-07T10:00:00",
        "details_extracted": false,
        "details_extracted_at": null,
        "uploaded_to_notion": false,
        "uploaded_to_notion_at": null,
        "last_attempt": "2025-11-07T10:00:00",
        "attempt_count": 1,
        "errors": []
      },
      "created_at": "2025-11-07T10:00:00",
      "updated_at": "2025-11-07T10:00:00"
    }
  },
  "creators": {
    "astrobymax": {
      "creator_id": "astrobymax",
      "last_scrape": "2025-11-07T10:00:00",
      "total_posts": 100,
      "processed_posts": 80,
      "pending_posts": 20,
      "updated_at": "2025-11-07T10:00:00"
    }
  }
}
```

**PostgreSQL Schema V2** (lo que vamos a usar):
```sql
-- Ya existe en database/schema_v2.sql
scraping_status (
  id SERIAL PRIMARY KEY,
  post_id VARCHAR(255) NOT NULL,
  source_id INTEGER REFERENCES creator_sources(id),  -- ⚠️ NOT creator_id!
  post_url TEXT NOT NULL,

  -- Status tracking
  url_collected BOOLEAN DEFAULT false,
  url_collected_at TIMESTAMP,
  details_extracted BOOLEAN DEFAULT false,
  details_extracted_at TIMESTAMP,
  uploaded_to_notion BOOLEAN DEFAULT false,
  uploaded_to_notion_at TIMESTAMP,

  -- Tracking
  last_attempt TIMESTAMP,
  attempt_count INTEGER DEFAULT 0,
  errors JSONB DEFAULT '[]',

  -- Metadata
  firebase_migrated BOOLEAN DEFAULT false,
  firebase_data JSONB,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(source_id, post_id)
)
```

**Diferencias clave:**
1. ✅ Firebase: `creator_id` → PostgreSQL: `source_id` (referencia a creator_sources)
2. ✅ Firebase: Nested dict `status` → PostgreSQL: Columnas planas (url_collected, details_extracted, etc.)
3. ✅ Firebase: Array de errors → PostgreSQL: JSONB `errors`
4. ✅ PostgreSQL tiene foreign keys y constraints (integridad referencial)

---

## 📝 Plan de Implementación

### Fase 2.1: Crear PostgresTracker ✅

**Archivo**: `src/postgres_tracker.py` (nuevo)

**Requerimientos**:
- ✅ Mantener **exactamente la misma API** que FirebaseTracker
- ✅ Usar SQLAlchemy ORM para queries
- ✅ Adaptarse a Schema V2 (source_id en lugar de creator_id)
- ✅ Incluir logging similar a Firebase
- ✅ Manejo de errores robusto
- ✅ Transacciones para operaciones críticas

**Estructura propuesta**:
```python
#!/usr/bin/env python3
"""
PostgreSQL Database Integration
Tracks post processing state in PostgreSQL
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


class PostgresTracker:
    """Track post processing state in PostgreSQL"""

    def __init__(self, db_url: str = None):
        """
        Initialize Postgres tracker

        Args:
            db_url: PostgreSQL connection URL (or read from env)
        """
        if db_url is None:
            # Build from env variables
            db_url = self._build_db_url_from_env()

        self.engine = create_engine(db_url, pool_pre_ping=True)
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"🐘 PostgreSQL Tracker initialized")

    def _build_db_url_from_env(self) -> str:
        """Build database URL from environment variables"""
        db_user = os.getenv('DB_USER', 'patreon_user')
        db_password = os.getenv('DB_PASSWORD')
        db_host = os.getenv('DB_HOST', '127.0.0.1')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'alejandria')

        # URL encode password
        encoded_password = quote_plus(db_password)
        return f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"

    # ========== POST TRACKING ==========

    def create_post_record(self, post_id: str, creator_id: str, post_url: str) -> bool:
        """
        Create initial post record in PostgreSQL

        ⚠️ IMPORTANTE: creator_id aquí se refiere al creator_id del SCHEMA V1
        En Schema V2, necesitamos encontrar el source_id correspondiente

        Args:
            post_id: Patreon post ID
            creator_id: Creator identifier (platform-agnostic name or platform_id)
            post_url: URL to the post

        Returns:
            True if successful
        """
        # Implementación detallada abajo...

    def mark_url_collected(self, post_id: str) -> bool:
        """Mark post URL as collected"""
        # ...

    def mark_details_extracted(self, post_id: str, success: bool = True, error: str = None) -> bool:
        """Mark post details as extracted"""
        # ...

    # ... resto de métodos con misma firma que FirebaseTracker
```

**Complejidad**: ~400-500 líneas (similar a FirebaseTracker)

---

### Fase 2.2: Adaptar a Schema V2 Multi-Source ⚠️

**Problema**: Los scripts actuales pasan `creator_id` (ej: "astrobymax"), pero Schema V2 usa `source_id`.

**Solución**: PostgresTracker necesita resolver `creator_id` → `source_id` internamente.

**Estrategia**:

1. **Opción A - Resolución automática** (Recomendada):
   ```python
   def _resolve_source_id(self, creator_identifier: str, platform: str = 'patreon') -> Optional[int]:
       """
       Resolve creator identifier to source_id

       Args:
           creator_identifier: Could be creator name OR platform_id
           platform: Platform name (default: 'patreon')

       Returns:
           source_id from creator_sources table
       """
       session = self.Session()
       try:
           # Try to find by platform_id first (exact match)
           result = session.execute(text("""
               SELECT cs.id
               FROM creator_sources cs
               WHERE cs.platform = :platform
                 AND cs.platform_id = :identifier
           """), {"platform": platform, "identifier": creator_identifier})

           row = result.fetchone()
           if row:
               return row[0]

           # Try to find by creator name (fallback)
           result = session.execute(text("""
               SELECT cs.id
               FROM creator_sources cs
               JOIN creators c ON c.id = cs.creator_id
               WHERE c.name = :name
                 AND cs.platform = :platform
           """), {"name": creator_identifier, "platform": platform})

           row = result.fetchone()
           return row[0] if row else None

       finally:
           session.close()
   ```

2. **Opción B - Requerir source_id explícito**:
   - Cambiar API para recibir `source_id` en lugar de `creator_id`
   - ❌ Problema: Requiere modificar TODOS los scripts que llaman a tracker

**Decisión**: Usar **Opción A** para minimizar cambios en scripts existentes.

---

### Fase 2.3: Migrar Scripts (Prioridad Alta) 🔴

#### Script 1: `src/phase1_url_collector.py`

**Cambios requeridos**:
```python
# ANTES:
from firebase_tracker import FirebaseTracker, load_firebase_config

database_url, database_secret = load_firebase_config()
tracker = FirebaseTracker(database_url, database_secret)

# DESPUÉS:
from postgres_tracker import PostgresTracker

tracker = PostgresTracker()  # Lee de .env automáticamente
```

**Testing**: Ejecutar con un creator de prueba, verificar que:
- ✅ URLs se guardan en `scraping_status`
- ✅ `source_id` se resuelve correctamente
- ✅ No hay errores de foreign keys

#### Script 2: `src/phase2_detail_extractor.py`

**Cambios requeridos**: Idénticos a Script 1

**Testing**: Ejecutar detail extraction sobre posts ya colectados, verificar:
- ✅ Campo `details_extracted` se actualiza
- ✅ Timestamps se guardan correctamente
- ✅ Errors se almacenan en JSONB

#### Script 3: `src/orchestrator.py`

**Cambios requeridos**: Idénticos a Script 1

**Testing**: Ejecutar workflow completo (phase1 + phase2), verificar:
- ✅ Todo el flujo funciona end-to-end
- ✅ Stats se actualizan correctamente

---

### Fase 2.4: Migrar Scripts Restantes 🟡

Mismos cambios para:
- `src/daily_incremental_scrape.py`
- `src/reset_creator.py`
- `tools/*_posts.py` (5 scripts)

**Estrategia**: Cambio mecánico de imports, testing individual de cada uno.

---

### Fase 2.5: Cleanup y Deprecación 🗑️

1. **Archivar FirebaseTracker**:
   ```bash
   mkdir -p archive/phase1-firebase/
   mv src/firebase_tracker.py archive/phase1-firebase/
   ```

2. **Actualizar .env**:
   - Comentar (NO eliminar) credenciales Firebase:
   ```bash
   # ===== FIREBASE (DEPRECATED - Phase 1 only) =====
   # FIREBASE_DATABASE_URL=https://patreon-...
   # FIREBASE_DATABASE_SECRET=...
   ```

3. **Actualizar requirements.txt**:
   - Revisar si `requests` se usa en otros lugares
   - Si no, marcarlo como opcional:
   ```
   # requests>=2.31.0  # Only needed for Firebase (deprecated)
   ```

4. **Documentar migración**:
   - Actualizar PROGRESS.md
   - Actualizar ARCHITECTURE.md
   - Crear MIGRATION_NOTES.md con detalles

---

## 🏗️ Arquitectura PostgresTracker

### Componentes Principales

```
PostgresTracker
├── __init__(db_url)                    # Constructor
├── _build_db_url_from_env()            # Helper: build URL from env vars
├── _resolve_source_id(creator_id)      # Helper: resolver creator → source_id
│
├── Post Tracking (11 métodos)
│   ├── create_post_record()
│   ├── mark_url_collected()
│   ├── mark_details_extracted()
│   ├── mark_uploaded_to_notion()
│   ├── increment_attempt()
│   ├── get_post()
│   ├── post_exists()
│   ├── get_all_posts()
│   ├── get_posts_by_creator()
│   ├── get_posts_needing_details()
│   └── get_posts_needing_notion_upload()
│
├── Creator Stats (3 métodos)
│   ├── update_creator_stats()
│   ├── get_creator_stats()
│   └── get_all_creator_stats()
│
└── Utilities (2 métodos)
    ├── get_summary()
    └── print_summary()
```

### Mapeo Firebase → PostgreSQL

| Firebase | PostgreSQL | Notas |
|----------|------------|-------|
| `posts/{post_id}` | `scraping_status` table | 1 row = 1 post |
| `creator_id` field | `source_id` (FK) | ⚠️ Resuelto via lookup |
| `status.url_collected` | `url_collected` column | Nested → flat |
| `status.errors` (array) | `errors` (JSONB) | Mantiene estructura |
| `creators/{creator_id}` | Calculado on-the-fly | No tabla separada (compute from scraping_status) |

### Queries Clave

#### Query 1: Get posts needing details
```sql
SELECT
    ss.post_id,
    ss.post_url,
    c.name as creator_name,
    cs.platform,
    ss.attempt_count,
    ss.last_attempt
FROM scraping_status ss
JOIN creator_sources cs ON cs.id = ss.source_id
JOIN creators c ON c.id = cs.creator_id
WHERE ss.url_collected = true
  AND ss.details_extracted = false
  AND (:creator_name IS NULL OR c.name = :creator_name)
ORDER BY ss.created_at DESC;
```

#### Query 2: Get creator stats
```sql
SELECT
    c.name as creator_name,
    cs.platform,
    COUNT(*) as total_posts,
    SUM(CASE WHEN ss.details_extracted = true THEN 1 ELSE 0 END) as processed_posts,
    SUM(CASE WHEN ss.details_extracted = false THEN 1 ELSE 0 END) as pending_posts,
    MAX(ss.updated_at) as last_scrape
FROM scraping_status ss
JOIN creator_sources cs ON cs.id = ss.source_id
JOIN creators c ON c.id = cs.creator_id
WHERE c.name = :creator_name
GROUP BY c.name, cs.platform;
```

---

## 📊 Scripts a Migrar

### Resumen

| # | Script | LOC | Complejidad | Tiempo Est. |
|---|--------|-----|-------------|-------------|
| 1 | `postgres_tracker.py` (nuevo) | 450 | Alta | 3-4 horas |
| 2 | `phase1_url_collector.py` | 2 | Baja | 15 min |
| 3 | `phase2_detail_extractor.py` | 2 | Baja | 15 min |
| 4 | `orchestrator.py` | 2 | Baja | 15 min |
| 5 | `daily_incremental_scrape.py` | 2 | Baja | 15 min |
| 6 | `reset_creator.py` | 2 | Baja | 10 min |
| 7-11 | `tools/*.py` (5 scripts) | 2 each | Baja | 10 min each |

**Total estimado**: 5-6 horas de trabajo

---

## ✅ Testing y Verificación

### Test 1: PostgresTracker Unit Tests

**Archivo**: `tests/test_postgres_tracker.py` (crear)

```python
import pytest
from src.postgres_tracker import PostgresTracker

def test_create_post_record():
    tracker = PostgresTracker()
    success = tracker.create_post_record(
        post_id="test123",
        creator_id="astrobymax",
        post_url="https://patreon.com/posts/test123"
    )
    assert success == True
    assert tracker.post_exists("test123") == True

def test_mark_details_extracted():
    tracker = PostgresTracker()
    tracker.create_post_record("test456", "astrobymax", "https://...")

    success = tracker.mark_details_extracted("test456", success=True)
    assert success == True

    post = tracker.get_post("test456")
    assert post['details_extracted'] == True
    assert post['details_extracted_at'] is not None

# ... más tests
```

### Test 2: Comparación Firebase vs PostgreSQL

**Objetivo**: Verificar que PostgresTracker produce los mismos resultados que FirebaseTracker

**Método**:
1. Ejecutar `phase1_url_collector.py` con FirebaseTracker (backup datos)
2. Ejecutar `phase1_url_collector.py` con PostgresTracker
3. Comparar resultados:
   - Misma cantidad de posts creados
   - Mismos fields poblados
   - Stats equivalentes

### Test 3: Integration Test - Full Workflow

**Script**: `scripts/test_phase2_migration.py`

```python
#!/usr/bin/env python3
"""
Integration test for Phase 2 migration
Tests full workflow with PostgresTracker
"""

from src.postgres_tracker import PostgresTracker
from src.phase1_url_collector import collect_urls_for_creator
from src.phase2_detail_extractor import extract_post_details

def test_full_workflow():
    """Test complete Phase 1 + 2 workflow"""
    tracker = PostgresTracker()

    # Phase 1: Collect URLs (limit to 5 for testing)
    print("Testing Phase 1: URL Collection...")
    # ... test code

    # Phase 2: Extract details
    print("Testing Phase 2: Detail Extraction...")
    # ... test code

    # Verify stats
    print("Verifying stats...")
    summary = tracker.get_summary()
    assert summary['total_posts'] > 0

    print("✅ Full workflow test PASSED")

if __name__ == "__main__":
    test_full_workflow()
```

### Test 4: Data Integrity Check

**Script**: `scripts/verify_phase2_integrity.sh`

```bash
#!/bin/bash
# Verify data integrity after Phase 2 migration

source .env

echo "============================================================"
echo "  Phase 2 Migration - Data Integrity Check"
echo "============================================================"

PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" << 'EOF'

-- Check 1: All scraping_status have valid source_id
SELECT
    CASE
        WHEN COUNT(*) = 0 THEN '✅ All scraping_status have valid source_id'
        ELSE '❌ ' || COUNT(*) || ' scraping_status with invalid source_id'
    END as check_1
FROM scraping_status ss
LEFT JOIN creator_sources cs ON cs.id = ss.source_id
WHERE cs.id IS NULL;

-- Check 2: All timestamps are valid
SELECT
    CASE
        WHEN COUNT(*) = COUNT(created_at) THEN '✅ All records have created_at'
        ELSE '❌ Missing created_at timestamps'
    END as check_2
FROM scraping_status;

-- Check 3: Stats accuracy
SELECT
    c.name,
    COUNT(*) as total_in_db,
    SUM(CASE WHEN ss.details_extracted THEN 1 ELSE 0 END) as processed
FROM scraping_status ss
JOIN creator_sources cs ON cs.id = ss.source_id
JOIN creators c ON c.id = cs.creator_id
GROUP BY c.name;

EOF

echo ""
echo "============================================================"
```

---

## 📅 Cronograma

### Semana 1: Desarrollo Core

| Día | Tarea | Duración | Entregable |
|-----|-------|----------|------------|
| 1 | Crear `postgres_tracker.py` (estructura básica) | 2h | Clase con __init__ y helpers |
| 1-2 | Implementar post tracking (11 métodos) | 4h | Métodos create, mark, get |
| 2 | Implementar creator stats (3 métodos) | 1h | update_stats, get_stats |
| 2 | Implementar utilities (2 métodos) | 1h | get_summary, print_summary |
| 3 | Unit tests | 2h | `tests/test_postgres_tracker.py` |
| 3 | Integration tests | 1h | `scripts/test_phase2_migration.py` |

**Total Semana 1**: ~11 horas

### Semana 2: Migración Scripts

| Día | Tarea | Duración | Entregable |
|-----|-------|----------|------------|
| 4 | Migrar phase1_url_collector.py | 30min | Script migrado + test |
| 4 | Migrar phase2_detail_extractor.py | 30min | Script migrado + test |
| 4 | Migrar orchestrator.py | 30min | Script migrado + test |
| 5 | Migrar daily_incremental_scrape.py | 30min | Script migrado + test |
| 5 | Migrar reset_creator.py | 15min | Script migrado |
| 5 | Migrar tools/*.py (5 scripts) | 1h | 5 scripts migrados |
| 6 | Testing completo end-to-end | 2h | Reporte de tests |
| 6 | Archivar firebase_tracker.py | 15min | Archivado + docs |
| 7 | Documentación final | 1h | PROGRESS.md actualizado |

**Total Semana 2**: ~6.5 horas

### Total Phase 2: ~17-18 horas

---

## 🚨 Riesgos y Mitigaciones

### Riesgo 1: Schema V2 no tiene todas las columnas necesarias

**Probabilidad**: Media
**Impacto**: Alto

**Mitigación**:
- Revisar schema_v2.sql ANTES de empezar
- Comparar columnas Firebase vs PostgreSQL
- Añadir columnas faltantes si es necesario

### Riesgo 2: Resolución creator_id → source_id falla

**Probabilidad**: Media
**Impacto**: Alto

**Mitigación**:
- Implementar logging detallado en `_resolve_source_id()`
- Tener fallback para errores (crear source si no existe?)
- Testing exhaustivo con diferentes creators

### Riesgo 3: Scripts tienen dependencias ocultas en Firebase

**Probabilidad**: Baja
**Impacto**: Medio

**Mitigación**:
- Revisar cada script ANTES de migrar
- Buscar usos de Firebase fuera de tracker (ej: REST API directo)
- Mantener Firebase disponible temporalmente como fallback

### Riesgo 4: Performance de PostgreSQL vs Firebase

**Probabilidad**: Baja
**Impacto**: Bajo

**Mitigación**:
- Usar índices apropiados (ya en schema_v2.sql)
- Connection pooling (SQLAlchemy default)
- Benchmark antes/después

---

## 📝 Checklist de Implementación

### Antes de Empezar
- [ ] Revisar schema_v2.sql y confirmar columnas
- [ ] Hacer backup de database actual
- [ ] Verificar que Phase 1.5 está 100% completo
- [ ] Confirmar que .env tiene todas las variables necesarias

### Durante Desarrollo
- [ ] Crear `src/postgres_tracker.py`
- [ ] Implementar todos los métodos (16 total)
- [ ] Crear tests unitarios
- [ ] Crear tests de integración
- [ ] Migrar 3 scripts prioritarios (phase1, phase2, orchestrator)
- [ ] Testing de scripts migrados
- [ ] Migrar scripts restantes (7 scripts)
- [ ] Testing completo end-to-end

### Al Finalizar
- [ ] Archivar `firebase_tracker.py` a `archive/phase1-firebase/`
- [ ] Comentar credenciales Firebase en .env
- [ ] Actualizar PROGRESS.md (marcar Phase 2 completa)
- [ ] Actualizar ARCHITECTURE.md
- [ ] Crear script de verificación (`verify_phase2.sh`)
- [ ] Commit + push con mensaje claro

---

## 🎯 Criterios de Éxito

Phase 2 se considera **COMPLETA** cuando:

1. ✅ `PostgresTracker` implementado con los 16 métodos
2. ✅ Todos los tests pasan (unit + integration)
3. ✅ Los 10 scripts migrados funcionan correctamente
4. ✅ Schema V2 maneja correctamente la resolución creator → source
5. ✅ No hay dependencias de Firebase en el código activo
6. ✅ Documentación actualizada (PROGRESS.md, ARCHITECTURE.md)
7. ✅ Script de verificación pasa todos los checks

---

## 📌 Notas Importantes

### Diferencias Schema V1 vs V2

**V1 (Firebase)**:
```
Post → creator_id (directo)
```

**V2 (PostgreSQL)**:
```
Post → source_id → creator_sources → creator_id → creators
```

Esta indirección es INTENCIONAL para soportar multi-source:
- Un creator puede tener múltiples sources (Patreon + YouTube + Substack)
- Cada source tiene su propio scraping_status

### Compatibilidad con Scripts Existentes

PostgresTracker mantiene API compatible con FirebaseTracker para minimizar cambios:
- Mismos nombres de métodos
- Mismas firmas (argumentos)
- Mismo comportamiento esperado
- Solo cambia el backend (Firebase → PostgreSQL)

### Performance Considerations

PostgreSQL debería ser **más rápido** que Firebase porque:
- ✅ Local (127.0.0.1) vs REST API calls
- ✅ Queries optimizadas con índices
- ✅ Connection pooling
- ✅ Transacciones ACID

---

**Documento preparado para revisión**
**Siguiente paso**: Recibir feedback del usuario antes de implementar
