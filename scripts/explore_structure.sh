#!/bin/bash
# Script para explorar la estructura completa del proyecto
# Incluye archivos que pueden estar en .gitignore

echo "=================================="
echo "📂 ESTRUCTURA COMPLETA DEL PROYECTO"
echo "=================================="
echo ""

echo "📊 Tamaño de directorios principales:"
echo "--------------------------------------"
du -sh data/ config/ src/ scripts/ docs/ logs/ 2>/dev/null || echo "Algunos directorios no existen"
echo ""

echo "📁 Estructura de data/:"
echo "--------------------------------------"
if [ -d "data/" ]; then
    tree -L 3 -h data/ 2>/dev/null || find data/ -type f -o -type d | head -50
    echo ""
    echo "Conteo de archivos en data/:"
    find data/ -type f | wc -l
    echo "Tamaño total de data/:"
    du -sh data/
else
    echo "❌ data/ no existe"
fi
echo ""

echo "📁 Estructura de src/:"
echo "--------------------------------------"
if [ -d "src/" ]; then
    ls -lh src/*.py 2>/dev/null || echo "No hay archivos Python en src/"
else
    echo "❌ src/ no existe"
fi
echo ""

echo "📁 Estructura de scripts/:"
echo "--------------------------------------"
if [ -d "scripts/" ]; then
    ls -lh scripts/*.py scripts/*.sh 2>/dev/null || echo "No hay scripts"
else
    echo "❌ scripts/ no existe"
fi
echo ""

echo "📁 Archivos MD en root:"
echo "--------------------------------------"
ls -lh *.md 2>/dev/null || echo "No hay archivos MD"
echo ""

echo "📁 Archivos de configuración:"
echo "--------------------------------------"
ls -lh config/ 2>/dev/null || echo "❌ config/ no existe"
echo ""

echo "📁 Logs:"
echo "--------------------------------------"
if [ -d "logs/" ]; then
    ls -lh logs/ 2>/dev/null | head -10
    echo "Total archivos de logs:"
    find logs/ -type f | wc -l
else
    echo "❌ logs/ no existe"
fi
echo ""

echo "📊 RESUMEN GENERAL:"
echo "--------------------------------------"
echo "Total archivos Python (.py):"
find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" | wc -l

echo "Total archivos Markdown (.md):"
find . -name "*.md" -not -path "./venv/*" -not -path "./.venv/*" | wc -l

echo "Total archivos JSON (.json):"
find . -name "*.json" -not -path "./venv/*" -not -path "./.venv/*" | wc -l

echo ""
echo "✅ Exploración completa"
