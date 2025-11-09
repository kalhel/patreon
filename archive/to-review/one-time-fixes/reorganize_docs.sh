#!/bin/bash
# Script para reorganizar documentación y archivos obsoletos
# Mueve todo lo antiguo a archive/ manteniendo solo lo esencial

set -e  # Exit on error

echo "=================================="
echo "🗂️  REORGANIZACIÓN DE DOCUMENTACIÓN"
echo "=================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para preguntar confirmación
confirm() {
    read -p "$1 (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

echo -e "${YELLOW}Este script va a:${NC}"
echo "  1. Crear directorio archive/ con subdirectorios"
echo "  2. Mover documentación obsoleta a archive/docs/"
echo "  3. Mantener solo: README.md, PROGRESS.md, docs/ARCHITECTURE.md"
echo "  4. Crear .gitignore para archive/ si no existe"
echo ""

if ! confirm "¿Continuar?"; then
    echo "❌ Cancelado por el usuario"
    exit 0
fi

echo ""
echo "📁 Paso 1: Crear estructura de archive/"
echo "--------------------------------------"

mkdir -p archive/docs
mkdir -p archive/phase1-firebase
mkdir -p archive/scripts-old

echo -e "${GREEN}✅ Directorios creados${NC}"
echo ""

echo "📄 Paso 2: Mover documentación obsoleta del root"
echo "--------------------------------------"

# Lista de archivos MD a mover (excepto README.md y PROGRESS.md)
DOCS_TO_MOVE=(
    "STATUS.md"
    "ROADMAP.md"
    "WORKFLOW.md"
    "CHANGELOG.md"
    "READY_TO_USE.md"
    "README_UPDATES.md"
    "PROJECT_COMPLETE.md"
    "COLLECTIONS_PLAN.md"
)

for doc in "${DOCS_TO_MOVE[@]}"; do
    if [ -f "$doc" ]; then
        mv "$doc" "archive/docs/"
        echo -e "${GREEN}✅ Movido: $doc → archive/docs/${NC}"
    else
        echo -e "${YELLOW}⚠️  No encontrado: $doc${NC}"
    fi
done

echo ""
echo "📄 Paso 3: Mover docs obsoletos de docs/"
echo "--------------------------------------"

# Lista de docs obsoletos en docs/ (excepto ARCHITECTURE.md y PHASE0_INSTALLATION.md)
DOCS_DIR_TO_MOVE=(
    "docs/DAILY_AUTOMATION.md"
    "docs/ADVANCED_SEARCH.md"
    "docs/TWO_PHASE_WORKFLOW.md"
    "docs/QUICK_START.md"
    "docs/NOTION_DATABASE_DESIGN.md"
    "docs/WEB_VIEWER.md"
    "docs/RESUMEN.md"
)

for doc in "${DOCS_DIR_TO_MOVE[@]}"; do
    if [ -f "$doc" ]; then
        mv "$doc" "archive/docs/"
        echo -e "${GREEN}✅ Movido: $doc → archive/docs/${NC}"
    else
        echo -e "${YELLOW}⚠️  No encontrado: $doc${NC}"
    fi
done

echo ""
echo "📄 Paso 4: Crear README en archive/"
echo "--------------------------------------"

cat > archive/README.md << 'EOF'
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
EOF

echo -e "${GREEN}✅ README creado en archive/${NC}"
echo ""

echo "📄 Paso 5: Actualizar .gitignore"
echo "--------------------------------------"

# Añadir archive/ a .gitignore si no está
if [ -f ".gitignore" ]; then
    if ! grep -q "^archive/" .gitignore; then
        echo "" >> .gitignore
        echo "# Archive directory (deprecated files)" >> .gitignore
        echo "# archive/" >> .gitignore
        echo -e "${GREEN}✅ Añadido archive/ a .gitignore (comentado por defecto)${NC}"
        echo -e "${YELLOW}⚠️  Si quieres ignorar archive/, descomenta la línea en .gitignore${NC}"
    else
        echo -e "${YELLOW}⚠️  archive/ ya está en .gitignore${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  .gitignore no existe, creándolo${NC}"
    cat > .gitignore << 'EOF'
# Archive directory (deprecated files)
# Descomenta la siguiente línea si no quieres versionar archive/
# archive/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual environments
venv/
.venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment variables
.env
.env.local

# Logs
logs/*.log

# Data (descomenta si no quieres versionar data/)
# data/

# OS
.DS_Store
Thumbs.db
EOF
    echo -e "${GREEN}✅ .gitignore creado${NC}"
fi

echo ""
echo "📊 Paso 6: Resumen de cambios"
echo "--------------------------------------"

echo ""
echo -e "${GREEN}✅ REORGANIZACIÓN COMPLETA${NC}"
echo ""
echo "📂 Estructura resultante:"
echo ""
echo "patreon/"
echo "├── README.md                    ← Entrada principal"
echo "├── PROGRESS.md                  ← Tracking oficial"
echo "├── docs/"
echo "│   ├── ARCHITECTURE.md          ← Diseño técnico"
echo "│   └── PHASE0_INSTALLATION.md   ← Instrucciones Phase 0"
echo "└── archive/"
echo "    ├── README.md                ← Explicación del archive"
echo "    ├── docs/                    ← Docs obsoletos (${#DOCS_TO_MOVE[@]} + ${#DOCS_DIR_TO_MOVE[@]} archivos)"
echo "    ├── phase1-firebase/         ← Código Firebase (vacío por ahora)"
echo "    └── scripts-old/             ← Scripts antiguos (vacío por ahora)"
echo ""
echo -e "${YELLOW}💡 PRÓXIMOS PASOS:${NC}"
echo "  1. Revisa los archivos movidos a archive/"
echo "  2. Ejecuta 'git status' para ver cambios"
echo "  3. Si todo está bien, haz commit de la reorganización"
echo "  4. En Phase 2, moveremos código Firebase a archive/phase1-firebase/"
echo ""
