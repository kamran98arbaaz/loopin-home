#!/usr/bin/env python3
"""
Database Backup System for LoopIn
Provides automated backup functionality to prevent data loss from accidental wipes.
"""

import os
import sys
import subprocess
import datetime
import json
import logging
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
from timezone_utils import now_utc

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DatabaseBackupSystem:
    def __init__(self):
        # ✅ RESPECT TEST ENVIRONMENT - Use appropriate database URL
        flask_env = os.getenv("FLASK_ENV", "production").lower()
        testing_mode = os.getenv("TESTING", "false").lower() == "true"

        if testing_mode or flask_env == "testing":
            # Use test database URL if in testing mode
            self.database_url = os.getenv("TEST_DATABASE_URL")
            if not self.database_url:
                self.database_url = "sqlite:///test_loopin.db"
            backup_suffix = "_test"
            print("🧪 Backup system using TEST database")
        else:
            # Use production database URL
            self.database_url = os.getenv("DATABASE_URL")
            backup_suffix = ""
            print("🚀 Backup system using PRODUCTION database")

        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")

        self.parsed_url = urlparse(self.database_url)

        # Use separate backup directories for test and production
        self.backup_dir = Path(f"backups{backup_suffix}")
        self.backup_dir.mkdir(exist_ok=True)

        # Backup retention settings
        self.max_daily_backups = 7
        self.max_weekly_backups = 4
        self.max_monthly_backups = 12
        
    def create_backup(self, backup_type="manual"):
        """Create a database backup"""
        try:
            timestamp = now_utc().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"loopin_backup_{backup_type}_{timestamp}.sql"
            backup_path = self.backup_dir / backup_filename
            
            logger.info(f"Starting {backup_type} backup to {backup_path}")
            
            # Create pg_dump command with better compatibility
            cmd = [
                "pg_dump",
                "--verbose",
                "--clean",
                "--no-acl",
                "--no-owner",
                "--format=plain",
                "--no-comments",  # Reduce version-specific comments
                "--file", str(backup_path),
                self.database_url
            ]
            
            # Execute backup
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Backup completed successfully: {backup_path}")
                
                # Create metadata file
                metadata = {
                    "backup_type": backup_type,
                    "timestamp": timestamp,
                    "database_url": self.parsed_url.hostname,
                    "database_name": self.parsed_url.path.lstrip('/'),
                    "file_size": backup_path.stat().st_size,
                    "created_at": now_utc().isoformat()
                }
                
                metadata_path = backup_path.with_suffix('.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                return backup_path
            else:
                logger.error(f"Backup failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Backup error: {str(e)}")
            return None
    
    def clean_backup_for_compatibility(self, backup_path):
        """Clean backup file to remove incompatible SQL statements"""
        try:
            temp_path = backup_path.with_suffix('.tmp')

            with open(backup_path, 'r') as infile, open(temp_path, 'w') as outfile:
                for line in infile:
                    # Skip problematic SET statements that cause compatibility issues
                    if any(skip_pattern in line for skip_pattern in [
                        'SET transaction_timeout',
                        'SET idle_in_transaction_session_timeout',
                        'SET lock_timeout'
                    ]):
                        outfile.write(f'-- SKIPPED: {line}')
                        continue
                    outfile.write(line)

            # Replace original with cleaned version
            temp_path.replace(backup_path)
            logger.info(f"Cleaned backup file for compatibility: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Error cleaning backup file: {e}")
            return False

    def restore_backup(self, backup_path):
        """Restore database from backup file with improved error handling"""
        try:
            backup_path = Path(backup_path)
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False

            logger.info(f"Starting restore from {backup_path}")

            # Verify backup one more time before restore
            if not self.verify_backup(backup_path):
                logger.error(f"Backup verification failed during restore: {backup_path}")
                return False

            # Clean backup for compatibility
            if not self.clean_backup_for_compatibility(backup_path):
                logger.warning("Failed to clean backup file, proceeding anyway")

            # Terminate existing connections to speed up restore
            self.terminate_database_connections()


            # Create optimized psql command for faster restore
            cmd = [
                "psql",
                "-f", str(backup_path),
                "-v", "ON_ERROR_STOP=1",  # Stop on first error
                "--quiet",                # Reduce output for speed
                "-X",                     # Don't read startup file
                "--set", "autocommit=on", # Enable autocommit for faster execution
                self.database_url
            ]

            logger.info(f"Executing optimized restore command: {' '.join(cmd[:-1])} [DATABASE_URL]")

            # Execute restore with shorter timeout for faster operations
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)  # 90 second timeout

            if result.returncode == 0:
                logger.info("Database restore completed successfully")
                logger.info(f"Restore output: {result.stdout[:500]}...")  # Log first 500 chars

                # After successful restore, move archived items back to original tables
                self.restore_archived_items_to_original_tables()

                return True
            else:
                logger.error(f"Restore failed with return code {result.returncode}")
                logger.error(f"Restore stderr: {result.stderr}")
                logger.error(f"Restore stdout: {result.stdout}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Restore operation timed out after 90 seconds")
            return False
        except Exception as e:
            logger.error(f"Restore error: {str(e)}")
            import traceback
            logger.error(f"Restore traceback: {traceback.format_exc()}")
            return False

    def restore_archived_items_to_original_tables(self):
        """Move archived items back to their original tables after backup restore"""
        try:
            # Import here to avoid circular imports
            from extensions import db
            from models import (Update, SOPSummary, LessonLearned,
                              ArchivedUpdate, ArchivedSOPSummary, ArchivedLessonLearned)

            logger.info("Starting restoration of archived items to original tables...")

            restored_count = 0

            # Restore archived updates
            archived_updates = ArchivedUpdate.query.all()
            for archived in archived_updates:
                # Check if update already exists in main table
                existing = Update.query.get(archived.id)
                if not existing:
                    # Create new update from archived data
                    restored_update = Update(
                        id=archived.id,
                        name=archived.name,
                        message=archived.message,
                        process=archived.process,
                        timestamp=archived.timestamp
                    )
                    db.session.add(restored_update)
                    restored_count += 1

                # Remove from archive
                db.session.delete(archived)

            # Restore archived SOPs
            archived_sops = ArchivedSOPSummary.query.all()
            for archived in archived_sops:
                # Check if SOP already exists in main table
                existing = SOPSummary.query.get(archived.id)
                if not existing:
                    # Create new SOP from archived data
                    restored_sop = SOPSummary(
                        id=archived.id,
                        title=archived.title,
                        content=archived.content,
                        tags=archived.tags,
                        timestamp=archived.timestamp
                    )
                    db.session.add(restored_sop)
                    restored_count += 1

                # Remove from archive
                db.session.delete(archived)

            # Restore archived lessons learned
            archived_lessons = ArchivedLessonLearned.query.all()
            for archived in archived_lessons:
                # Check if lesson already exists in main table
                existing = LessonLearned.query.get(archived.id)
                if not existing:
                    # Create new lesson from archived data
                    restored_lesson = LessonLearned(
                        id=archived.id,
                        title=archived.title,
                        content=archived.content,
                        tags=archived.tags,
                        timestamp=archived.timestamp
                    )
                    db.session.add(restored_lesson)
                    restored_count += 1

                # Remove from archive
                db.session.delete(archived)

            # Commit all changes
            db.session.commit()
            logger.info(f"Successfully restored {restored_count} archived items to original tables")

        except Exception as e:
            logger.error(f"Error restoring archived items: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass

    def terminate_database_connections(self):
        """Terminate existing database connections to speed up restore"""
        try:
            if self.parsed_url.scheme == 'postgresql':
                # Get database name from URL
                db_name = self.parsed_url.path.lstrip('/')

                # Create command to terminate connections
                terminate_cmd = [
                    "psql",
                    "-c", f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}' AND pid <> pg_backend_pid();",
                    "--quiet",
                    self.database_url
                ]

                logger.info("Terminating existing database connections for faster restore...")
                result = subprocess.run(terminate_cmd, capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    logger.info("Successfully terminated existing database connections")
                else:
                    logger.warning(f"Could not terminate all connections: {result.stderr}")

        except Exception as e:
            logger.warning(f"Could not terminate database connections: {str(e)}")

    def list_backups(self):
        """List all available backups"""
        backups = []
        for backup_file in self.backup_dir.glob("*.sql"):
            metadata_file = backup_file.with_suffix('.json')
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                backups.append({
                    'file': backup_file,
                    'metadata': metadata
                })
            else:
                # Create basic metadata for files without it
                stat = backup_file.stat()
                backups.append({
                    'file': backup_file,
                    'metadata': {
                        'backup_type': 'unknown',
                        'file_size': stat.st_size,
                        'created_at': datetime.datetime.fromtimestamp(stat.st_mtime, tz=datetime.timezone.utc).isoformat()
                    }
                })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['metadata']['created_at'], reverse=True)
        return backups
    
    def cleanup_old_backups(self):
        """Remove old backups based on retention policy"""
        try:
            backups = self.list_backups()
            
            # Group backups by type and age
            daily_backups = []
            weekly_backups = []
            monthly_backups = []
            
            now = now_utc()
            
            for backup in backups:
                created_at = datetime.datetime.fromisoformat(backup['metadata']['created_at'])
                age_days = (now - created_at).days
                
                if age_days <= 7:
                    daily_backups.append(backup)
                elif age_days <= 30:
                    weekly_backups.append(backup)
                else:
                    monthly_backups.append(backup)
            
            # Remove excess backups
            to_remove = []
            
            if len(daily_backups) > self.max_daily_backups:
                to_remove.extend(daily_backups[self.max_daily_backups:])
            
            if len(weekly_backups) > self.max_weekly_backups:
                to_remove.extend(weekly_backups[self.max_weekly_backups:])
            
            if len(monthly_backups) > self.max_monthly_backups:
                to_remove.extend(monthly_backups[self.max_monthly_backups:])
            
            # Delete old backups
            for backup in to_remove:
                backup_file = backup['file']
                metadata_file = backup_file.with_suffix('.json')
                
                backup_file.unlink()
                if metadata_file.exists():
                    metadata_file.unlink()
                
                logger.info(f"Removed old backup: {backup_file}")
            
            logger.info(f"Cleanup completed. Removed {len(to_remove)} old backups")
            
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
    
    def verify_backup(self, backup_path):
        """Verify backup file integrity"""
        try:
            backup_path = Path(backup_path)
            if not backup_path.exists():
                return False
            
            # Basic file size check
            if backup_path.stat().st_size == 0:
                logger.error(f"Backup file is empty: {backup_path}")
                return False
            
            # Check if file contains SQL content
            with open(backup_path, 'r') as f:
                # Read first part for header check
                header_content = f.read(500)

                # Check for PostgreSQL dump header first
                if 'PostgreSQL database dump' not in header_content:
                    logger.error(f"Backup file doesn't appear to be a valid PostgreSQL dump: {backup_path}")
                    return False

                # Read more content to check for SQL statements
                f.seek(0)  # Reset to beginning
                full_content = f.read()  # Read entire file for proper validation

                # A valid backup should have CREATE TABLE statements (schema) and either INSERT INTO or COPY (data)
                has_create_table = 'CREATE TABLE' in full_content
                has_insert_data = 'INSERT INTO' in full_content
                has_copy_data = 'COPY public.' in full_content and 'FROM stdin' in full_content

                if not has_create_table:
                    logger.error(f"Backup file doesn't contain CREATE TABLE statements: {backup_path}")
                    return False

                if not (has_insert_data or has_copy_data):
                    # This might be a schema-only backup, which is still valid
                    logger.warning(f"Backup file appears to be schema-only (no data): {backup_path}")

                logger.info(f"Backup validation: CREATE TABLE={has_create_table}, INSERT={has_insert_data}, COPY={has_copy_data}")
            
            logger.info(f"Backup verification passed: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Backup verification error: {str(e)}")
            return False

def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print("Usage: python backup_system.py <command> [options]")
        print("Commands:")
        print("  backup [type]     - Create backup (type: manual, daily, weekly, monthly)")
        print("  restore <file>    - Restore from backup file")
        print("  list             - List all backups")
        print("  cleanup          - Remove old backups")
        print("  verify <file>    - Verify backup file")
        return
    
    backup_system = DatabaseBackupSystem()
    command = sys.argv[1]
    
    if command == "backup":
        backup_type = sys.argv[2] if len(sys.argv) > 2 else "manual"
        result = backup_system.create_backup(backup_type)
        if result:
            print(f"Backup created: {result}")
        else:
            print("Backup failed")
            sys.exit(1)
    
    elif command == "restore":
        if len(sys.argv) < 3:
            print("Error: Please specify backup file to restore")
            sys.exit(1)
        
        backup_file = sys.argv[2]
        if backup_system.restore_backup(backup_file):
            print("Restore completed successfully")
        else:
            print("Restore failed")
            sys.exit(1)
    
    elif command == "list":
        backups = backup_system.list_backups()
        if backups:
            print(f"Found {len(backups)} backups:")
            for backup in backups:
                metadata = backup['metadata']
                size_mb = metadata['file_size'] / (1024 * 1024)

                # Convert UTC timestamp to IST for display
                try:
                    from timezone_utils import format_ist
                    import datetime
                    dt = datetime.datetime.fromisoformat(metadata['created_at'].replace('Z', '+00:00'))
                    formatted_time = format_ist(dt, '%Y-%m-%d %H:%M:%S IST')
                except:
                    formatted_time = metadata['created_at']

                print(f"  {backup['file'].name} - {metadata['backup_type']} - {size_mb:.1f}MB - {formatted_time}")
        else:
            print("No backups found")
    
    elif command == "cleanup":
        backup_system.cleanup_old_backups()
        print("Cleanup completed")
    
    elif command == "verify":
        if len(sys.argv) < 3:
            print("Error: Please specify backup file to verify")
            sys.exit(1)
        
        backup_file = sys.argv[2]
        if backup_system.verify_backup(backup_file):
            print("Backup verification passed")
        else:
            print("Backup verification failed")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
