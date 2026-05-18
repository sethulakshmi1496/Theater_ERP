# AEC Cinemas ERP

## 🎬 Project Overview
Enterprise Theater ERP & Booking System for AEC Cinemas.  
Built with Django + PostgreSQL (backend) and React/Vite (frontend).

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL 14+ (install via `brew install postgresql@16`)
- Redis (optional, for Celery BMS sync)

### 1. Install PostgreSQL
```bash
brew install postgresql@16
brew services start postgresql@16
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
```
Add the export to your `~/.zshrc` to make it permanent.

### 2. Create Database & Run Migrations
```bash
cd /Users/sethubibin/Desktop/Theater_ERP
createdb aec_cinemas_db
python3 manage.py migrate
python3 manage.py seed_data
```

### 3. Start the Backend
```bash
python3 manage.py runserver
```
API available at: http://localhost:8000/api/

### 4. Start the Frontend
```bash
cd frontend
npm run dev
```
App available at: http://localhost:5173/

---

## 🔑 Login Credentials (Seeded)

| Role | Email | Password |
|------|-------|----------|
| MD (Managing Director) | md@aeccinemas.com | AEC@md2026 |
| Admin / Accountant | admin@aeccinemas.com | AEC@admin2026 |
| Staff | staff@aeccinemas.com | AEC@staff2026 |

---

## 🌐 Key URLs

| URL | Description |
|-----|-------------|
| http://localhost:5173/ | Admin Dashboard (login required) |
| http://localhost:5173/book | User Booking Portal (public) |
| http://localhost:8000/api/ | REST API root |
| http://localhost:8000/admin/ | Django Admin |

---

## 📦 Module Structure

```
aec_cinemas/          Django project config
apps/
  accounts/           Users & RBAC (Staff/Admin/MD)
  screens/            Screens, Movies, Shows, Seats
  bookings/           Booking engine (ACID-safe)
  revenue/            Canteen sales, Advertising slots
  operations/         Electricity, Generator, Lamp tracking
  finance/            Film advances, Distributor share
  payroll/            Staff management, Monthly payroll
  settings_app/       Global settings (editable rates)
  reports/            P&L engine, CSV export, Alerts
frontend/             React/Vite dashboard + booking app
```

---

## 💡 Key Business Logic

### Electricity Auto-Calculation
When staff enters meter readings:
```
Total Consumption = Final Reading − Initial Reading
Unit Conversion   = Total Consumption × 40
Elec. Charges     = Unit Conversion × ₹10.64
Units/Show        = Total Consumption ÷ Total Shows
```
Both `40` and `10.64` are stored in `GlobalSetting` and editable by the MD.

### Lamp Depreciation
Every `working_hours` entry automatically:
1. Subtracts from `screen.lamp_balance`
2. Triggers an alert if balance < 100 hours

### ACID-Safe Bookings
Uses `select_for_update()` + `@transaction.atomic` to prevent double-booking under concurrent load.

### P&L Engine
Daily and Monthly P&L aggregates:
- **Income**: Ticket Revenue + Canteen + Advertising
- **Expenses**: Electricity + Diesel + Distributor Share + Payroll
- **Net**: Income − Expenses

### MD Alerts
- 🚨 Lamp balance < 100 hours
- 🚨 Electricity costs > Ticket Revenue (Loss-Making Show)
- ⚠️ Units/Show > 20% above 3.84 average

---

## 🔌 Environment Variables (.env)
```
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=aec_cinemas_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
```
