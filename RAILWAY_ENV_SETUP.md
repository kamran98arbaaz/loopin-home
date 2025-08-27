# Railway Environment Variables Setup

## Required Environment Variables

### 1. Database (Automatically provided by Railway PostgreSQL service)
```
DATABASE_URL=postgresql://username:password@hostname:port/database
```
**Note**: This is automatically set when you add a PostgreSQL service to your Railway project.

### 2. Flask Secret Key (MUST BE SET MANUALLY)
```
FLASK_SECRET_KEY=your-super-secret-key-here-make-it-long-and-random
```
**Important**: Generate a secure random key. You can use:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Port (Automatically provided by Railway)
```
PORT=8000
```
**Note**: Railway automatically sets this. Don't override unless necessary.

## Optional Environment Variables

### Flask Environment
```
FLASK_ENV=production
```

### Redis (if using Redis add-on)
```
REDIS_URL=redis://username:password@hostname:port
```

### Testing Mode (for development)
```
TESTING=false
```

## Railway Setup Steps

### 1. Create New Railway Project
1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Connect your GitHub repository

### 2. Add PostgreSQL Database
1. In your Railway project dashboard
2. Click "Add Service"
3. Select "PostgreSQL"
4. Railway will automatically set `DATABASE_URL`

### 3. Set Environment Variables
1. Go to your service settings
2. Click "Variables" tab
3. Add the required variables:
   - `FLASK_SECRET_KEY`: Your secure secret key

### 4. Deploy
1. Railway will automatically deploy when you push to master
2. Monitor deployment logs for any issues
3. Check health endpoints once deployed

## Health Check Endpoints

After deployment, verify these endpoints work:

- `https://your-app.railway.app/health` - Basic health (should always return 200)
- `https://your-app.railway.app/health/db` - Database connectivity
- `https://your-app.railway.app/ready` - Full readiness check

## Troubleshooting

### Health Check Fails
1. Check if `DATABASE_URL` is set correctly
2. Verify PostgreSQL service is running
3. Check deployment logs for database connection errors

### App Won't Start
1. Verify `FLASK_SECRET_KEY` is set
2. Check if all required environment variables are present
3. Review startup logs for specific error messages

### Database Issues
1. Ensure PostgreSQL service is attached to your project
2. Check if database migrations ran successfully
3. Verify `DATABASE_URL` format is correct

## Quick Verification Script

Run this in Railway shell to check environment:
```bash
python check_env.py
```

This will show you which environment variables are set and which are missing.
