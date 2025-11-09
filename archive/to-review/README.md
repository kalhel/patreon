# 📦 Archive - Scripts para Revisar

**Fecha de archivo**: 2025-11-09
**Razón**: Reorganización del proyecto

---

## 📋 ¿Qué hay aquí?

Esta carpeta contiene scripts que **probablemente ya no son necesarios** pero se archivaron en lugar de eliminarse para poder revisarlos con calma.

---

## 📁 Estructura

### `debug-scripts/`
Scripts de debugging one-time para posts específicos o problemas puntuales.

**Contenido típico:**
- `debug_*.py` - Debug de posts específicos
- `check_*.py` - Verificaciones puntuales
- `analyze_*.py` - Análisis específicos

**Recomendación**: Estos fueron útiles una vez pero probablemente ya no sirven. Revisar y eliminar después de confirmar que el problema está resuelto.

### `one-time-fixes/`
Scripts que se ejecutaron una sola vez para arreglar un problema específico.

**Contenido típico:**
- `fix_*.py` - Correcciones aplicadas
- `cleanup_*.py` - Limpiezas ejecutadas
- `diagnose_*.py` - Diagnósticos completados
- `validate_*.py` - Validaciones ya hechas

**Recomendación**: Si el fix ya se aplicó exitosamente, estos scripts se pueden eliminar. Solo mantener si el problema puede reaparecer.

---

## ⚠️ Antes de Eliminar

Pregúntate:

1. **¿El problema que resolvía este script está 100% solucionado?**
   - Si SÍ → Puedes eliminarlo
   - Si NO → Mantenerlo en archive

2. **¿Este script contiene lógica que podría ser útil en el futuro?**
   - Si SÍ → Extraer la lógica útil a `tools/` antes de eliminar
   - Si NO → Puedes eliminarlo

3. **¿Hay documentación de qué hacía este script?**
   - Si NO → Leer el código y documentar antes de eliminar

---

## 🗑️ Cómo Eliminar de Forma Segura

```bash
# 1. Verificar que el script está en git
git log --follow archive/to-review/debug-scripts/debug_post.py

# 2. Si necesitas recuperarlo después, anota el commit hash
git log -1 archive/to-review/debug-scripts/debug_post.py

# 3. Eliminar con git
git rm archive/to-review/debug-scripts/debug_post.py

# 4. Commit
git commit -m "Remove debug_post.py - issue resolved"
```

---

## 📊 Inventario Actual

### Debug Scripts (15 archivos)
- `debug_*.py` - Scripts de debugging temporal
- `check_*.py` - Verificaciones puntuales
- `analyze_*.py` - Análisis específicos

### One-Time Fixes (31 archivos)
- `fix_*.py` - Correcciones ya aplicadas
- `cleanup_*.py` - Limpiezas ejecutadas
- `diagnose_*.py` - Diagnósticos completados
- `validate_*.py` - Validaciones ya hechas
- `*.sql` - Queries de debugging/diagnóstico específicas
- `docker-compose.yml` - Docker Compose (no usado aún)
- `*.sh` - Scripts bash temporales
- `*.sql` - Scripts SQL one-time

**Total**: ~46 archivos para revisar (15 debug + 31 one-time-fixes)

---

## ✅ Recomendación Final

**Revisar en 3-6 meses**:
- Si el proyecto ha estado funcionando sin problemas
- Y no has necesitado ninguno de estos scripts
- Entonces es seguro eliminarlos todos

**Mantener si**:
- El proyecto está en desarrollo activo
- Los problemas que resolvían pueden reaparecer
- Contienen lógica útil para debugging futuro

---

**Última revisión**: Pendiente
**Próxima revisión sugerida**: 2025-05-09 (6 meses)
