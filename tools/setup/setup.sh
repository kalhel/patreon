#!/bin/bash
#
# Setup script for Patreon to Notion project
#

set -e

echo "════════════════════════════════════════════════════════════════"
echo "🚀 Patreon to Notion - Setup"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if venv exists
if [ -d "venv" ]; then
    echo "✅ Virtual environment already exists"
else
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

echo ""
echo "🔧 Activating virtual environment..."
source venv/bin/activate

echo ""
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Setup complete!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "🎯 Next steps:"
echo ""
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Run authentication:"
echo "   python3 src/patreon_auth_selenium.py"
echo ""
echo "3. Follow the guide:"
echo "   cat docs/QUICK_START.md"
echo ""
echo "════════════════════════════════════════════════════════════════"
