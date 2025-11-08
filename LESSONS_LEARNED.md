# 🎓 Lecciones Aprendidas - Phase 1.5

**Fecha**: 2025-11-07
**Contexto**: Errores cometidos durante Schema V2 migration que costaron tiempo y dinero al usuario

---

## ❌ Errores Cometidos

### Error 1: No cargar `.env` en scripts Python
**Qué pasó**:
```python
# fix_creators_population.py (versión inicial)
import os
# ... no había load_dotenv()

db_password = os.getenv('DB_PASSWORD')  # ← None
```

**Consecuencia**: Script falló inmediatamente con "DB_PASSWORD not found"

**Por qué pasó**: Asumí que las variables de entorno estarían disponibles automáticamente

**Costo**: 1 iteración fallida

---

### Error 2: Eliminar datos sin considerar CASCADE 🚨 **CRÍTICO**
**Qué pasó**:
```python
# fix_creators_population.py
conn.execute(text("DELETE FROM creators WHERE name = 'Unknown'"))
```

**Consecuencia**:
- Foreign key con `ON DELETE CASCADE` en `scraping_status`
- Eliminó el creator "Unknown" → **eliminó 982 posts automáticamente**
- Pérdida total de datos

**Por qué pasó**:
1. No revisé el schema para ver qué foreign keys existían
2. No consideré las consecuencias del CASCADE
3. Diseñé el script para eliminar en lugar de actualizar

**Costo**: Tuvimos que restaurar desde backup. Si no hubiera backup, pérdida permanente de 982 posts.

---

### Error 3: SQL syntax incorrecto (RAISE NOTICE fuera de bloques DO)
**Qué pasó**:
```sql
ALTER TABLE scraping_status RENAME COLUMN creator_id TO source_id;
RAISE NOTICE '✅ Done';  -- ← Error de sintaxis
```

**Consecuencia**: Script SQL falló, transacción rollback

**Por qué pasó**: No conocía bien la sintaxis de PostgreSQL para mensajes informativos

**Costo**: 1 iteración fallida

---

### Error 4: No actualizar valores ANTES de añadir foreign key
**Qué pasó**:
```sql
-- fix_scraping_status_schema.sql (versión inicial)
ALTER TABLE scraping_status RENAME COLUMN creator_id TO source_id;
-- ← Los valores siguen siendo 1, pero creator_sources tiene IDs 2,3,4,5

ALTER TABLE scraping_status
    ADD CONSTRAINT scraping_status_source_id_fkey
    FOREIGN KEY (source_id) REFERENCES creator_sources(id);
-- ← Error: Key (source_id)=(1) is not present in table "creator_sources"
```

**Consecuencia**: Constraint violation, transacción rollback

**Por qué pasó**: No pensé en el orden correcto de operaciones

**Costo**: 1 iteración fallida

---

## ✅ Soluciones Aplicadas

### Solución al Error 1:
```python
from dotenv import load_dotenv

# Load .env file FIRST
load_dotenv()

db_password = os.getenv('DB_PASSWORD')  # ✅ Funciona
```

### Solución al Error 2:
```bash
# Restore desde backup
bash restore_last_backup.sh
```

**Aprendizaje**:
- ✅ Restaurar datos primero
- ✅ Nuevo enfoque: UPDATE en lugar de DELETE
- ✅ NUNCA eliminar datos que tienen foreign keys CASCADE

### Solución al Error 3:
```sql
-- Usar \echo para mensajes en psql
\echo '✅ Done'

-- O usar DO blocks para RAISE NOTICE
DO $$
BEGIN
    RAISE NOTICE '✅ Done';
END $$;
```

### Solución al Error 4:
```sql
-- Orden correcto:
-- 1. Renombrar columna
ALTER TABLE scraping_status RENAME COLUMN creator_id TO source_id;

-- 2. Actualizar valores PRIMERO
UPDATE scraping_status ss
SET source_id = cm.source_id
FROM creator_mapping cm
WHERE ss.firebase_data->>'creator_id' = cm.firebase_creator_id;

-- 3. DESPUÉS añadir foreign key
ALTER TABLE scraping_status
    ADD CONSTRAINT scraping_status_source_id_fkey
    FOREIGN KEY (source_id) REFERENCES creator_sources(id);
```

---

## 📋 Checklist para Phase 2 (y futuras fases)

### Antes de crear CUALQUIER script:

- [ ] **1. Revisar el schema actual**
  - ¿Qué foreign keys existen?
  - ¿Tienen ON DELETE CASCADE?
  - ¿Qué tablas se verán afectadas?

- [ ] **2. Diseñar el enfoque**
  - Preferir UPDATE sobre DELETE
  - Si necesito DELETE, ¿puedo desactivar CASCADE temporalmente?
  - ¿Necesito backup antes de ejecutar?

- [ ] **3. Verificar dependencias**
  - ¿El script necesita .env? → Añadir `load_dotenv()`
  - ¿El script necesita librerías? → Verificar imports
  - ¿El script funciona sin conexión a DB? → Añadir error handling

- [ ] **4. Pensar en el orden de operaciones**
  - Para SQL: ¿Qué debe ejecutarse primero?
  - Para Python: ¿Qué validaciones necesito antes de modificar datos?

- [ ] **5. Testear mentalmente**
  - ¿Qué pasa si esto falla a la mitad?
  - ¿Puedo hacer rollback?
  - ¿Tengo backup?

- [ ] **6. Validar sintaxis**
  - SQL: Probar comandos simples primero
  - Python: Verificar que imports y funciones existen

### Durante la ejecución:

- [ ] **7. Crear backup ANTES de operaciones destructivas**
  ```bash
  bash scripts/backup_database.sh
  ```

- [ ] **8. Ejecutar en transacciones (SQL)**
  ```sql
  BEGIN;
  -- operaciones
  -- Si algo falla → ROLLBACK automático
  COMMIT;
  ```

- [ ] **9. Verificar resultados DESPUÉS**
  - ¿Los counts son correctos?
  - ¿Los foreign keys son válidos?
  - ¿Los datos se migraron completamente?

### Después de completar:

- [ ] **10. Documentar QUÉ se hizo y POR QUÉ**
  - Actualizar PROGRESS.md
  - Archivar scripts temporales
  - Explicar decisiones tomadas

---

## 🎯 Principios para Phase 2

### 1. **Safety First** 🛡️
- Backup antes de CUALQUIER operación que modifique datos
- Transacciones para operaciones SQL
- Error handling en Python

### 2. **Think Before Execute** 🧠
- Revisar schema ANTES de escribir código
- Pensar en consecuencias de CASCADE
- Validar sintaxis antes de ejecutar

### 3. **Prefer Updates Over Deletes** 🔄
- UPDATE valores existentes en lugar de DELETE + INSERT
- Si necesito DELETE, revisar foreign keys primero

### 4. **Test Incrementally** 📊
- No hacer múltiples cambios a la vez
- Verificar después de cada paso
- Si algo falla, saber exactamente qué fue

### 5. **Dependencies Matter** 📦
- Cargar .env en scripts Python
- Verificar que librerías estén instaladas
- Orden correcto de operaciones (especialmente en SQL)

---

## 💰 Impacto de los Errores

**Iteraciones fallidas**: 4
**Tiempo perdido**: ~30-40 minutos
**Costo en tokens**: Estimado 15,000-20,000 tokens en fixes

**Lección más importante**:
> Un error de diseño (eliminar con CASCADE) casi causa pérdida permanente de 982 posts. Solo el backup nos salvó.

---

## ✅ Compromiso para Phase 2

**YO (Claude) me comprometo a**:

1. ✅ Revisar el schema COMPLETO antes de crear scripts
2. ✅ NUNCA usar DELETE sin revisar CASCADE primero
3. ✅ Preferir UPDATE sobre DELETE
4. ✅ Incluir `load_dotenv()` en TODOS los scripts Python
5. ✅ Usar transacciones en SQL para poder hacer rollback
6. ✅ Testear mentalmente antes de ejecutar
7. ✅ Crear backups antes de operaciones destructivas
8. ✅ Documentar decisiones claramente

**El usuario merece**:
- Scripts que funcionen a la primera
- Código bien pensado y testeado
- Minimizar iteraciones fallidas
- Respetar que cada error cuesta dinero

---

## 📚 Referencias para Consultar

**Antes de Phase 2, revisar**:
- `database/schema_v2.sql` - Schema completo con foreign keys
- `scripts/verify_schema_v2.sh` - Script de verificación existente
- `docs/PHASE2_CORE_BACKEND.md` - Plan de Phase 2

**Durante Phase 2, recordar**:
- Este documento (LESSONS_LEARNED.md)
- archive/phase1.5-fixes/README.md - Errores específicos

---

**Creado**: 2025-11-07
**Propósito**: Aprender de errores para NO repetirlos en Phase 2 y futuras fases
**Revisión obligatoria**: Antes de escribir CUALQUIER script en Phase 2
