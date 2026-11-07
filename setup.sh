#!/bin/bash
# ============================================
# IDS Project - One-Click Setup Script
# ============================================

set -e

echo "🛡️  Setting up Intrusion Detection System Project..."
echo "=================================================="

# Create directory structure
echo "📁 Creating project directories..."
mkdir -p data/raw data/processed
mkdir -p notebooks
mkdir -p src/models
mkdir -p models
mkdir -p dashboard/pages dashboard/assets
mkdir -p reports/figures

# Create __init__.py files
touch src/__init__.py
touch src/models/__init__.py

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo "=================================================="
echo "To activate the environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To start the dashboard later:"
echo "  streamlit run dashboard/app.py"
