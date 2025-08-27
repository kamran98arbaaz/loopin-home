# Railway Deployment Guide

## Quick Setup

### 1. Environment Variables (Required)
Set these in Railway dashboard:

```bash
DATABASE_URL=postgresql://...  # Automatically provided by Railway PostgreSQL service
FLASK_SECRET_KEY=your-super-secret-key-here
PORT=8000  # Automatically set by Railway
```

### 2. Optional Environment Variables
```bash
FLASK_ENV=production
REDIS_URL=redis://...  # If using Redis add-on
```

## Deployment Commands

### Current Configuration
- **Start Command**: `flask db upgrade && gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1`
- **Health Check**: `/health`
- **Python Version**: 3.11.10

## Troubleshooting

### If pip install fails (exit code 127):
1. Check if `.python-version` file exists (should contain `3.11.10`)
2. Try using minimal requirements: `cp requirements_minimal.txt requirements.txt`
3. Check Railway build logs for specific error messages

### If health check fails:
1. Ensure DATABASE_URL is set correctly
2. Check if PostgreSQL service is attached
3. Verify `/health` endpoint returns 200 status

### If database migration fails:
1. Ensure PostgreSQL service is running
2. Check DATABASE_URL format: `postgresql://user:pass@host:port/dbname`
3. Try manual migration: `flask db upgrade`

## Files Overview

- `railway.json` - Railway deployment configuration
- `Procfile` - Backup deployment command
- `.python-version` - Python version specification
- `startup.py` - Database connectivity checker (optional)
- `check_env.py` - Environment variable debugger
- `requirements_minimal.txt` - Minimal dependencies for testing

## Manual Deployment Steps

If automatic deployment fails:

1. **Connect to Railway shell**:
   ```bash
   railway shell
   ```

2. **Check environment**:
   ```bash
   python check_env.py
   ```

3. **Test database connection**:
   ```bash
   python startup.py
   ```

4. **Run migrations**:
   ```bash
   flask db upgrade
   ```

5. **Start application**:
   ```bash
   gunicorn app:app --bind 0.0.0.0:$PORT
   ```
