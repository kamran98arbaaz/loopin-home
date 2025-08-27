#!/bin/bash
set -e

echo "🔧 Starting build process..."

# Upgrade pip first
python -m pip install --upgrade pip

# Install requirements
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "✅ Build completed successfully!"
