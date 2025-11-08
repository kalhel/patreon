# 🔄 Schema V2 Migration - Instructions

## Estado Actual

Tu base de datos tiene una **mezcla** de schema v1 y v2:
- ✅ **Schema V2**: `scraping_status`, `creator_sources`, `creators`
- ❌ **Schema V1**: `posts` (usa `creator_id` VARCHAR), `collections` (usa `creator_id` VARCHAR)

## Objetivo

Migrar **posts** y **collections** a schema v2 (usar `source_id` INTEGER en lugar de `creator_id` VARCHAR).

## ⚠️ IMPORTANTE - Antes de empezar

1. **NO ejecutes nada hasta que hagas pull de los scripts**
2. **Asegúrate de tener espacio en disco** (mínimo 1GB libre)
3. **Cierra el web viewer** si está corriendo
4. **Ten tiempo** (el proceso toma ~5-10 minutos)

---

## 📋 Procedimiento - Ejecuta EN ORDEN

### PASO 0: Pull de los scripts

```bash
cd ~/proyectos/astrologia/patreon
git pull origin claude/phase0-infrastructure-011CUv1ZBJQonSVuZF4tYcaY
```

---

### PASO 1: Backup de la base de datos

**¿Qué hace?** Crea un backup completo de la BD antes de cualquier cambio.

```bash
cd ~/proyectos/astrologia/patreon
bash scripts/step1_backup_database.sh
```

**Resultado esperado:**
```
✅ Backup created successfully!
File: backups/schema_v2_migration/alejandria_before_v2_migration_YYYYMMDD_HHMMSS.sql
```

**Si falla:** Verifica que tienes la contraseña correcta en `.env` y que PostgreSQL está corriendo.

---

### PASO 2: Migración quirúrgica

**¿Qué hace?**
- Añade columna `source_id` a `posts` y `collections`
- Mapea `creator_id` (VARCHAR) → `source_id` (INTEGER)
- Añade foreign keys
- **NO elimina nada**, solo añade y mapea

```bash
python3 scripts/step2_migrate_posts_collections_to_v2.py
```

**Resultado esperado:**
```
✅ MIGRATION COMPLETE

Summary:
  - XXX posts migrated to schema v2
  - XXX collections migrated to schema v2
```

**Si falla:**
- Automáticamente hace **ROLLBACK** (la BD queda sin cambios)
- Revisa el error mostrado
- Pide ayuda si no entiendes el error

**⚠️ CRITICAL:** Si ves errores como "unmapped posts" o "unmapped collections", **detente y pide ayuda**.

---

### PASO 3: Verificación completa

**¿Qué hace?** Verifica que todo migró correctamente.

```bash
python3 scripts/step3_verify_migration.py
```

**Resultado esperado:**
```
✅ ALL CHECKS PASSED - Migration successful!
```

**Si algún check falla:**
- **NO sigas adelante**
- Revisa qué check falló
- Puedes restaurar el backup si es necesario

---

### PASO 4: Prueba el web viewer

```bash
cd ~/proyectos/astrologia/patreon/web
python3 viewer.py
```

Abre `http://localhost:5555` y verifica:
- ✅ Se muestran los posts
- ✅ Se muestran las collections
- ✅ El settings page muestra datos correctos

---

### PASO 5: Ejecutar diagnóstico nuevamente

```bash
cd ~/proyectos/astrologia/patreon
python3 scripts/diagnose_phase2_phase3_data.py
```

Verifica que todo sigue funcionando correctamente.

---

## 🔧 Si algo sale mal - Rollback

### Opción 1: Rollback automático (si step2 falló)

El script hace rollback automático si hay error. La BD queda intacta.

### Opción 2: Restaurar desde backup

Si step2 terminó pero los resultados están mal:

```bash
# Encuentra tu backup
ls -lh backups/schema_v2_migration/

# Restaura (REEMPLAZA TIMESTAMP con el de tu backup)
PGPASSWORD=$DB_PASSWORD psql -h 127.0.0.1 -U patreon_user -d alejandria < backups/schema_v2_migration/alejandria_before_v2_migration_TIMESTAMP.sql
```

---

## ❓ Preguntas Frecuentes

### ¿Se va a borrar algo?

**NO.** El script solo **añade** columnas y **mapea** datos. No elimina nada.

### ¿Puedo ejecutar los scripts múltiples veces?

**SÍ.** El step2 detecta si ya se ejecutó y pregunta si quieres continuar.

### ¿Cuánto tarda?

- Step1 (backup): 10-30 segundos
- Step2 (migración): 5-15 segundos
- Step3 (verificación): 5 segundos

Total: ~1 minuto

### ¿Qué pasa con creator_id después?

Las columnas `creator_id` (VARCHAR) **permanecen** pero **ya no se usan**.
Se pueden eliminar después si todo funciona, pero no es urgente.

---

## 📞 Si necesitas ayuda

Detén todo y pregunta. Es mejor perder 5 minutos preguntando que 5 horas arreglando una BD rota.

**Información útil para debug:**
```bash
# Ver estructura de posts
psql -U patreon_user -h localhost -d alejandria -c "\d posts"

# Ver estructura de collections
psql -U patreon_user -h localhost -d alejandria -c "\d collections"

# Contar registros
psql -U patreon_user -h localhost -d alejandria -c "SELECT COUNT(*) FROM posts"
psql -U patreon_user -h localhost -d alejandria -c "SELECT COUNT(*) FROM collections"
```

---

**Creado:** 2025-11-08
**Versión:** 1.0
**Seguro para ejecutar:** ✅ SÍ (tiene rollback automático)
