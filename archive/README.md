# 📦 Archive - Deprecated Files

Este directorio contiene archivos obsoletos y código legacy que fueron reemplazados durante la migración a PostgreSQL.

## Estructura

```
archive/
├── docs/                    ← Documentación obsoleta (pre-migración)
├── phase1-firebase/         ← Código Firebase (será añadido en Phase 2)
└── scripts-old/             ← Scripts antiguos reemplazados
```

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
