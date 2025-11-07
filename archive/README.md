# 📦 Archive - Deprecated Files

Este directorio contiene archivos obsoletos y código legacy que fueron reemplazados durante la migración a PostgreSQL.

## Estructura

```
archive/
├── docs/                    ← Documentación obsoleta (pre-migración)
├── phase1-firebase/         ← Código Firebase (será añadido en Phase 2)
├── scripts-old/             ← Scripts antiguos reemplazados
├── avatars-old/             ← Avatares antiguos del root (NO usados por web viewer)
├── backups/                 ← Backups y JSONs duplicados
└── temp-scripts/            ← Scripts temporales/test
```

### 📂 Detalles de Carpetas

**avatars-old/** (7 archivos, 523 KB)
- Avatares antiguos que estaban en root directory
- El web viewer usa `web/static/{creator_id}.jpg` en su lugar
- Incluye: astrobymax.jpg, horoi.jpg, olomihead on history.jpg, prueba*.jpeg
- **Puede borrarse**: No afecta funcionalidad actual

**backups/** (3 archivos, 34 MB)
- backup_jsons_20251107.tar.gz (15 MB)
- web_backup_20251103_065805.tar.gz (4 MB)
- headonhistory_posts_detailed.json (15 MB - duplicado de data/processed/)
- **Revisar antes de borrar**: Verificar que no contienen datos únicos

**temp-scripts/** (1 archivo)
- test_json_adapter.py (632 bytes)
- Scripts temporales de prueba
- **Puede borrarse**: Scripts de desarrollo temporal

## ⚠️ IMPORTANTE

**NO usar estos archivos** para desarrollo actual. Son mantenidos únicamente como referencia histórica.

## Documentación Actual (Oficial)

- **README.md** (root) - Entrada principal del proyecto
- **PROGRESS.md** (root) - Tracking oficial de migración
- **docs/ARCHITECTURE.md** - Diseño técnico actualizado

## Cuándo borrar este directorio

Este directorio puede ser eliminado completamente después de que:
1. Phase 2 esté completa y verificada
2. Se haya validado que no se necesita código Firebase
3. Pasen al menos 2-4 semanas sin referencias a estos archivos

---

**Fecha de creación**: 2025-11-07
**Razón**: Migración Firebase → PostgreSQL
