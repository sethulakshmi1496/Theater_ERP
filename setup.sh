#!/bin/bash
# AEC Cinemas Setup Script
# Run this once to set up the full system

set -e
echo "🎬 AEC Cinemas Setup"
echo "============================================"

# 1. Install PostgreSQL if not present
if ! command -v psql &>/dev/null; then
  echo "📦 Installing PostgreSQL via Homebrew..."
  brew install postgresql@16
  brew services start postgresql@16
  export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
  sleep 3
fi

echo "✅ PostgreSQL found: $(psql --version)"

# 2. Create database
echo "🗄️  Creating database: aec_cinemas_db"
createdb aec_cinemas_db 2>/dev/null || echo "   (Database may already exist, continuing...)"

# 3. Django migrations
echo "🔄 Running Django migrations..."
cd /Users/sethubibin/Desktop/Theater_ERP
python3 manage.py migrate

# 4. Seed initial data
echo "🌱 Seeding initial data (screens, settings, users)..."
python3 manage.py seed_data

# 5. Done
echo ""
echo "✅ Backend setup complete!"
echo ""
echo "🚀 To start the system:"
echo "   Terminal 1: python3 manage.py runserver"
echo "   Terminal 2: cd frontend && npm run dev"
echo ""
echo "🔑 Login credentials:"
echo "   MD:    md@aeccinemas.com    / AEC@md2026"
echo "   Admin: admin@aeccinemas.com / AEC@admin2026"
echo "   Staff: staff@aeccinemas.com / AEC@staff2026"
echo ""
echo "🌐 URLs:"
echo "   Admin Dashboard: http://localhost:5173/"
echo "   User Booking:    http://localhost:5173/book"
echo "   Django API:      http://localhost:8000/api/"
