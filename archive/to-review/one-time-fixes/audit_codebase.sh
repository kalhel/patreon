#!/bin/bash
# Script de auditoría completa del codebase
# Analiza scripts, archivos sueltos, dependencias Firebase, etc.

echo "=========================================="
echo "🔍 AUDITORÍA COMPLETA DEL CODEBASE"
echo "=========================================="
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📂 1. ARCHIVOS SUELTOS EN ROOT${NC}"
echo "=========================================="
echo ""

echo "Archivos Python en root:"
ls -lh *.py 2>/dev/null || echo "  ❌ Ninguno"
echo ""

echo "Archivos JSON en root:"
ls -lh *.json 2>/dev/null || echo "  ❌ Ninguno"
echo ""

echo "Imágenes en root:"
ls -lh *.{png,jpg,jpeg,webp,gif} 2>/dev/null || echo "  ❌ Ninguno"
echo ""

echo "Backups/comprimidos en root:"
ls -lh *.{tar.gz,zip,bak} 2>/dev/null || echo "  ❌ Ninguno"
echo ""

echo "Otros archivos relevantes en root:"
ls -lh *.{txt,md,log,csv} 2>/dev/null | grep -v README | grep -v PROGRESS || echo "  ❌ Ninguno"
echo ""

echo -e "${BLUE}📝 2. SCRIPTS PYTHON EN src/${NC}"
echo "=========================================="
echo ""

if [ -d "src/" ]; then
    for script in src/*.py; do
        if [ -f "$script" ]; then
            filename=$(basename "$script")
            lines=$(wc -l < "$script")

            # Check if uses Firebase
            uses_firebase=""
            if grep -q "firebase_tracker\|FirebaseTracker" "$script"; then
                uses_firebase="${RED}[USES FIREBASE]${NC}"
            fi

            # Get docstring if exists
            docstring=$(head -20 "$script" | grep -A 1 '"""' | head -2 | tail -1 | sed 's/^[[:space:]]*//' || echo "Sin descripción")

            echo -e "${GREEN}$filename${NC} ${uses_firebase}"
            echo "  Líneas: $lines"
            echo "  Desc: $docstring"
            echo ""
        fi
    done
else
    echo "❌ src/ no existe"
fi

echo -e "${BLUE}📝 3. SCRIPTS EN scripts/${NC}"
echo "=========================================="
echo ""

if [ -d "scripts/" ]; then
    for script in scripts/*.{py,sh}; do
        if [ -f "$script" ]; then
            filename=$(basename "$script")

            # Get description from first comment or docstring
            desc=$(head -10 "$script" | grep -E '^\#|^"""' | head -2 | sed 's/^[[:space:]]*#//' | sed 's/"""//g' | tr '\n' ' ' || echo "Sin descripción")

            echo -e "${GREEN}$filename${NC}"
            echo "  Desc: $desc"
            echo ""
        fi
    done
else
    echo "❌ scripts/ no existe"
fi

echo -e "${BLUE}🔥 4. DEPENDENCIAS DE FIREBASE${NC}"
echo "=========================================="
echo ""

echo "Scripts que importan firebase_tracker:"
grep -r "from.*firebase_tracker\|import.*firebase_tracker" src/ scripts/ 2>/dev/null || echo "  ❌ Ninguno encontrado"
echo ""

echo "Scripts que usan FirebaseTracker:"
grep -r "FirebaseTracker" src/ scripts/ 2>/dev/null | grep -v ".pyc" | head -20 || echo "  ❌ Ninguno encontrado"
echo ""

echo -e "${BLUE}📊 5. ESTADÍSTICAS GENERALES${NC}"
echo "=========================================="
echo ""

total_py=$(find src/ -name "*.py" 2>/dev/null | wc -l)
firebase_py=$(grep -rl "firebase_tracker\|FirebaseTracker" src/ 2>/dev/null | wc -l)
total_scripts=$(find scripts/ -name "*.py" -o -name "*.sh" 2>/dev/null | wc -l)

echo "Total scripts Python en src/: $total_py"
echo "Scripts que usan Firebase: $firebase_py"
echo "Scripts en scripts/: $total_scripts"
echo ""

echo -e "${BLUE}💾 6. ESTRUCTURA DE DATA/${NC}"
echo "=========================================="
echo ""

if [ -d "data/" ]; then
    echo "Subdirectorios en data/:"
    ls -ld data/*/ 2>/dev/null || echo "  ❌ Sin subdirectorios"
    echo ""

    echo "Archivos grandes en data/ (>10MB):"
    find data/ -type f -size +10M -exec ls -lh {} \; 2>/dev/null | head -10 || echo "  ❌ Ninguno"
    echo ""
else
    echo "❌ data/ no existe"
fi

echo -e "${BLUE}📸 7. ARCHIVOS MEDIA EN ROOT${NC}"
echo "=========================================="
echo ""

echo "Buscando avatares/imágenes sueltas en root:"
find . -maxdepth 1 -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.webp" \) -exec ls -lh {} \; 2>/dev/null || echo "  ❌ Ninguno"
echo ""

echo -e "${BLUE}🎯 8. RECOMENDACIONES${NC}"
echo "=========================================="
echo ""

# Count loose files in root
loose_images=$(find . -maxdepth 1 -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.webp" \) 2>/dev/null | wc -l)
loose_json=$(find . -maxdepth 1 -type f -name "*.json" 2>/dev/null | wc -l)
loose_tar=$(find . -maxdepth 1 -type f -name "*.tar.gz" 2>/dev/null | wc -l)

if [ $loose_images -gt 0 ]; then
    echo -e "${YELLOW}⚠️  $loose_images imágenes sueltas en root${NC}"
    echo "   Recomendación: Mover a data/avatars/ o config/avatars/"
    echo ""
fi

if [ $loose_json -gt 0 ]; then
    echo -e "${YELLOW}⚠️  $loose_json archivos JSON sueltos en root${NC}"
    echo "   Recomendación: Revisar y mover a data/processed/ o eliminar"
    echo ""
fi

if [ $loose_tar -gt 0 ]; then
    echo -e "${YELLOW}⚠️  $loose_tar backups .tar.gz en root${NC}"
    echo "   Recomendación: Mover a data/backups/ o eliminar si no son necesarios"
    echo ""
fi

if [ $firebase_py -gt 0 ]; then
    echo -e "${RED}🔥 $firebase_py scripts dependen de Firebase${NC}"
    echo "   Acción requerida: Migrar a PostgresTracker en Phase 2"
    echo ""
fi

echo "=========================================="
echo "✅ Auditoría completa"
echo "=========================================="
