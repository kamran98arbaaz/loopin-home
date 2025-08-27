#!/usr/bin/env python3
"""
Scheduled Backup Script for LoopIn
This script can be run via cron to create automated backups.

Usage:
  python scheduled_backup.py daily    # Create daily backup
  python scheduled_backup.py weekly   # Create weekly backup  
  python scheduled_backup.py monthly  # Create monthly backup

Example cron entries:
  # Daily backup at 2 AM
  0 2 * * * /usr/bin/python3 /path/to/scheduled_backup.py daily
  
  # Weekly backup on Sunday at 3 AM
  0 3 * * 0 /usr/bin/python3 /path/to/scheduled_backup.py weekly
  
  # Monthly backup on 1st day at 4 AM
  0 4 1 * * /usr/bin/python3 /path/to/scheduled_backup.py monthly
"""

import sys
import os
import logging
from pathlib import Path

# Add the current directory to Python path so we can import backup_system
sys.path.insert(0, str(Path(__file__).parent))

from backup_system import DatabaseBackupSystem

def setup_logging():
    """Setup logging for scheduled backups"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'scheduled_backup.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def main():
    """Main function for scheduled backup"""
    logger = setup_logging()
    
    if len(sys.argv) != 2:
        logger.error("Usage: python scheduled_backup.py <backup_type>")
        logger.error("Backup types: daily, weekly, monthly")
        sys.exit(1)
    
    backup_type = sys.argv[1].lower()
    
    if backup_type not in ['daily', 'weekly', 'monthly']:
        logger.error(f"Invalid backup type: {backup_type}")
        logger.error("Valid types: daily, weekly, monthly")
        sys.exit(1)
    
    try:
        logger.info(f"Starting scheduled {backup_type} backup")
        
        # Create backup system instance
        backup_system = DatabaseBackupSystem()
        
        # Create backup
        backup_path = backup_system.create_backup(backup_type)
        
        if backup_path:
            logger.info(f"Scheduled {backup_type} backup completed successfully: {backup_path}")
            
            # Verify the backup
            if backup_system.verify_backup(backup_path):
                logger.info("Backup verification passed")
            else:
                logger.error("Backup verification failed")
                sys.exit(1)
            
            # Cleanup old backups
            logger.info("Running backup cleanup")
            backup_system.cleanup_old_backups()
            logger.info("Backup cleanup completed")
            
        else:
            logger.error(f"Scheduled {backup_type} backup failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error during scheduled backup: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
