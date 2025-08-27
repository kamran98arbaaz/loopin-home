# LoopIn Database Backup System

This backup system provides comprehensive data protection for the LoopIn application to prevent data loss from accidental database wipes or other issues.

## Features

- **Automated Backups**: Create scheduled backups (daily, weekly, monthly)
- **Web Interface**: Manage backups through the admin panel
- **Backup Verification**: Automatic integrity checks
- **Retention Policy**: Automatic cleanup of old backups
- **Restore Functionality**: Easy database restoration from backups
- **Comprehensive Logging**: Detailed logs for all backup operations

## Components

### 1. backup_system.py
Core backup functionality with CLI interface.

**Usage:**
```bash
# Create manual backup
python backup_system.py backup manual

# Create scheduled backup
python backup_system.py backup daily

# List all backups
python backup_system.py list

# Restore from backup
python backup_system.py restore backups/loopin_backup_manual_20250824_143022.sql

# Verify backup integrity
python backup_system.py verify backups/loopin_backup_manual_20250824_143022.sql

# Cleanup old backups
python backup_system.py cleanup
```

### 2. scheduled_backup.py
Automated backup script for cron jobs.

**Usage:**
```bash
# Run daily backup
python scheduled_backup.py daily

# Run weekly backup
python scheduled_backup.py weekly

# Run monthly backup
python scheduled_backup.py monthly
```

### 3. Web Interface
Admin-only backup management through `/backup` route.

**Features:**
- Create new backups
- View backup history
- Restore from backups
- Cleanup old backups

## Setup Instructions

### 1. Install Dependencies
Ensure PostgreSQL client tools are installed:

```bash
# Ubuntu/Debian
sudo apt-get install postgresql-client

# CentOS/RHEL
sudo yum install postgresql

# macOS
brew install postgresql
```

### 2. Environment Variables
Ensure `DATABASE_URL` is set in your environment:

```bash
export DATABASE_URL="postgresql://username:password@host:port/database"
```

### 3. Create Backup Directory
```bash
mkdir -p backups logs
```

### 4. Set Permissions
Make scripts executable:

```bash
chmod +x backup_system.py
chmod +x scheduled_backup.py
```

### 5. Setup Scheduled Backups (Optional)
Add to crontab for automated backups:

```bash
# Edit crontab
crontab -e

# Add these lines for automated backups:
# Daily backup at 2 AM
0 2 * * * cd /path/to/loopin && /usr/bin/python3 scheduled_backup.py daily

# Weekly backup on Sunday at 3 AM
0 3 * * 0 cd /path/to/loopin && /usr/bin/python3 scheduled_backup.py weekly

# Monthly backup on 1st day at 4 AM
0 4 1 * * cd /path/to/loopin && /usr/bin/python3 scheduled_backup.py monthly
```

## Backup Retention Policy

- **Daily Backups**: Keep last 7 days
- **Weekly Backups**: Keep last 4 weeks
- **Monthly Backups**: Keep last 12 months

Old backups are automatically cleaned up when running the cleanup command.

## File Structure

```
backups/
├── loopin_backup_daily_20250824_020000.sql
├── loopin_backup_daily_20250824_020000.json
├── loopin_backup_weekly_20250818_030000.sql
├── loopin_backup_weekly_20250818_030000.json
└── ...

logs/
├── backup.log
├── scheduled_backup.log
└── ...
```

Each backup consists of:
- `.sql` file: PostgreSQL dump
- `.json` file: Backup metadata

## Security Considerations

1. **Access Control**: Only admin users can access backup functionality
2. **File Permissions**: Ensure backup files have appropriate permissions
3. **Storage Location**: Consider storing backups on separate storage
4. **Encryption**: Consider encrypting backup files for sensitive data

## Troubleshooting

### Common Issues

1. **pg_dump not found**
   - Install PostgreSQL client tools
   - Ensure pg_dump is in PATH

2. **Permission denied**
   - Check database connection permissions
   - Verify file system permissions

3. **Backup verification failed**
   - Check backup file integrity
   - Verify database connection

### Log Files

Check log files for detailed error information:
- `backup.log`: General backup operations
- `scheduled_backup.log`: Scheduled backup operations

### Manual Recovery

If the web interface is unavailable, use CLI tools:

```bash
# List available backups
ls -la backups/

# Restore manually
psql $DATABASE_URL < backups/loopin_backup_manual_20250824_143022.sql
```

## Best Practices

1. **Regular Testing**: Periodically test backup restoration
2. **Monitor Logs**: Check backup logs regularly
3. **Storage Management**: Monitor backup storage usage
4. **Documentation**: Keep backup procedures documented
5. **Multiple Locations**: Consider off-site backup storage

## Integration with LoopIn

The backup system is integrated into the main LoopIn application:

- **Admin Panel**: Access via `/backup` (admin only)
- **Role-based Access**: Only admin users can manage backups
- **Flash Messages**: User-friendly feedback for operations
- **Error Handling**: Graceful error handling and logging

## Support

For issues or questions about the backup system:

1. Check log files for error details
2. Verify environment configuration
3. Test database connectivity
4. Review backup file permissions

The backup system is designed to be robust and fail-safe, providing multiple layers of protection for your LoopIn data.
