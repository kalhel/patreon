# 🔧 Creator Population Fix

## 🐛 Problema Detectado

Durante la migración a Schema V2, solo se creó **1 creator ("Unknown")** en lugar de los **4 creators** que tenemos en `config/creators.json`:

1. ❌ astrobymax
2. ❌ horoiproject
3. ❌ headonhistory
4. ❌ skyscript

### ¿Por qué pasó esto?

El script `migrate_to_schema_v2.py` carga los creators de la tabla `creators` (Schema V1) **antes** de dropear la base de datos. Pero en Schema V1 solo había 1 creator o los datos estaban mal poblados.

### Estado actual de la DB:

```
creators:        1 ("Unknown")
creator_sources: 1 (platform: patreon, platform_id: "unknown")
scraping_status: 982 posts (TODOS apuntando a source_id=1 incorrecto)
```

---

## 🛠️ Solución

He creado un script que arregla esto automáticamente:

### Script: `fix_creators_population.py`

**Qué hace:**

1. ✅ **Elimina** el creator "Unknown" (cascade a creator_sources)
2. ✅ **Lee** `config/creators.json` (4 creators)
3. ✅ **Crea** 4 creators en tabla `creators` (platform-agnostic)
4. ✅ **Crea** 4 creator_sources (todos Patreon)
5. ✅ **Actualiza** scraping_status para apuntar al `source_id` correcto basándose en `firebase_data->>'creator_id'`

**Mapeo que hará:**

```
firebase_data->>'creator_id' → source_id
-----------------------------------------
"astrobymax"      → source_id para AstroByMax (Patreon)
"horoiproject"    → source_id para HOROI Project (Patreon)
"headonhistory"   → source_id para Ali A Olomi (Patreon)
"skyscript"       → source_id para Skyscript (Patreon)
```

---

## 📋 Pasos para Ejecutar

### Paso 1: Diagnosticar (opcional)

```bash
# Ver qué creator_ids hay en firebase_data
bash diagnose_migration_issue.sh
```

Esto te mostrará la distribución de creators en los datos de Firebase.

### Paso 2: Ejecutar el Fix

```bash
# Arreglar la población de creators
python3 fix_creators_population.py
```

El script te pedirá confirmación antes de hacer cambios.

### Paso 3: Verificar

```bash
# Verificar que todo está correcto
bash check_creators.sh
```

**Resultado esperado:**
```
CREATORS:
  id |      name       | avatar_filename
 ----+-----------------+-----------------
   2 | AstroByMax      | astrobymax.jpg
   3 | HOROI Project   | horoiproject.jpg
   4 | Ali A Olomi     | headonhistory.jpg
   5 | Skyscript       | skyscript.png

CREATOR_SOURCES:
  id |      name       | platform | platform_id
 ----+-----------------+----------+--------------
   2 | AstroByMax      | patreon  | astrobymax
   3 | HOROI Project   | patreon  | horoiproject
   4 | Ali A Olomi     | patreon  | headonhistory
   5 | Skyscript       | patreon  | skyscript

COUNTS:
  total_creators: 4
  total_sources:  4
  total_posts:    982 (distribuidos entre los 4 creators)
```

---

## 🔍 Cómo Funciona

### 1. Lee config/creators.json

```json
{
  "creators": [
    {
      "creator_id": "astrobymax",
      "name": "AstroByMax",
      "url": "https://www.patreon.com/astrobymax",
      "avatar": "astrobymax.jpg"
    },
    // ... 3 más
  ]
}
```

### 2. Crea Creators (Platform-Agnostic)

```sql
INSERT INTO creators (name, avatar_filename, active)
VALUES ('AstroByMax', 'astrobymax.jpg', true);
-- Repite para los 4 creators
```

### 3. Crea Creator Sources (Patreon)

```sql
INSERT INTO creator_sources (
  creator_id, platform, platform_id, platform_url, is_active
) VALUES (
  2, 'patreon', 'astrobymax', 'https://www.patreon.com/astrobymax', true
);
-- Repite para los 4 creators
```

### 4. Actualiza scraping_status

```sql
-- Para cada post en scraping_status:
UPDATE scraping_status
SET source_id = (SELECT id FROM creator_sources WHERE platform_id = firebase_data->>'creator_id')
WHERE id = ...;
```

---

## ⚠️ Notas Importantes

### Backup Automático

El script NO crea backup porque ya tenemos backups de la migración anterior en:
```
database/backups/schema_v1_backup_*.sql
```

Si quieres un backup adicional antes del fix:
```bash
bash scripts/backup_database.sh
```

### Datos de Firebase Preservados

Los 982 posts tienen `firebase_data` (JSONB) con el `creator_id` original. El script usa esto para mapear correctamente.

### ¿Qué pasa si hay posts sin firebase_data?

El script los reportará como "unknown" pero no los eliminará. Puedes revisarlos manualmente después.

---

## 🎯 Después del Fix

Una vez ejecutado exitosamente:

1. ✅ Los 4 creators estarán en la tabla `creators`
2. ✅ Los 4 creator_sources estarán en `creator_sources`
3. ✅ Los 982 posts en `scraping_status` apuntarán a los `source_id` correctos
4. ✅ El Schema V2 multi-source funcionará correctamente
5. ✅ Podemos continuar con **Phase 2** (PostgresTracker)

---

## 🐞 Si Algo Sale Mal

### Opción 1: Restaurar desde backup

```bash
bash restore_oldest_backup.sh
# Luego volver a ejecutar migrate_to_schema_v2.py
```

### Opción 2: Re-ejecutar el fix

El script es **idempotente** - puedes ejecutarlo múltiples veces. Eliminará y recreará los creators cada vez.

---

**Creado**: 2025-11-07
**Razón**: Fix de migración Schema V2 incompleta
