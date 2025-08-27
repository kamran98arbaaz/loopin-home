# Railway Deployment Checklist

## Pre-Deployment Checklist

### ✅ Repository Setup
- [ ] Code is pushed to master branch
- [ ] All files are committed and up to date
- [ ] No sensitive data in repository (use environment variables)

### ✅ Railway Project Setup
- [ ] Railway project created and connected to GitHub repo
- [ ] PostgreSQL service added to project
- [ ] Environment variables configured (see RAILWAY_ENV_SETUP.md)

### ✅ Required Environment Variables
- [ ] `DATABASE_URL` (auto-set by PostgreSQL service)
- [ ] `FLASK_SECRET_KEY` (manually set - use secure random key)
- [ ] `PORT` (auto-set by Railway)

### ✅ Optional Environment Variables
- [ ] `FLASK_ENV=production` (recommended)
- [ ] `REDIS_URL` (if using Redis)

## Deployment Process

### 1. Automatic Deployment
Railway will automatically deploy when you push to master branch.

### 2. Monitor Deployment
1. Watch deployment logs in Railway dashboard
2. Look for these success indicators:
   - ✅ Build completed successfully
   - ✅ Database connectivity established
   - ✅ Flask migrations completed
   - ✅ Gunicorn started successfully
   - ✅ Health check passed

### 3. Verify Deployment
Test these endpoints after deployment:
- [ ] `https://your-app.railway.app/` - Main application
- [ ] `https://your-app.railway.app/health` - Basic health check
- [ ] `https://your-app.railway.app/health/db` - Database health
- [ ] `https://your-app.railway.app/ready` - Readiness probe

## Post-Deployment Verification

### ✅ Application Functionality
- [ ] Login system works
- [ ] Database operations work (create/read/update/delete)
- [ ] File uploads work (if applicable)
- [ ] All major features functional

### ✅ Performance Check
- [ ] Page load times acceptable
- [ ] Database queries performing well
- [ ] No memory leaks or excessive resource usage

### ✅ Security Check
- [ ] HTTPS enabled (automatic with Railway)
- [ ] Environment variables secure
- [ ] No sensitive data exposed in logs

## Troubleshooting Common Issues

### Build Fails
- Check Python version in `.python-version` file
- Verify `requirements.txt` is valid
- Review build logs for specific errors

### Health Check Fails
- Verify database service is running
- Check `DATABASE_URL` environment variable
- Test health endpoints manually

### App Won't Start
- Check `FLASK_SECRET_KEY` is set
- Verify all required environment variables
- Review application logs for errors

### Database Issues
- Ensure PostgreSQL service is attached
- Check database migrations completed
- Verify database connectivity

## Emergency Rollback

If deployment fails:
1. Check previous working commit
2. Revert to last known good state:
   ```bash
   git revert HEAD
   git push origin master
   ```
3. Railway will automatically redeploy the reverted version

## Success Indicators

Deployment is successful when:
- ✅ Railway shows "Deployed" status
- ✅ Health endpoints return 200 status
- ✅ Application is accessible via Railway URL
- ✅ Database operations work correctly
- ✅ No errors in application logs

## Support Resources

- Railway Documentation: https://docs.railway.app
- Flask Documentation: https://flask.palletsprojects.com
- PostgreSQL Documentation: https://www.postgresql.org/docs

## Contact

If deployment issues persist, check:
1. Railway deployment logs
2. Application error logs
3. Database connection status
4. Environment variable configuration
