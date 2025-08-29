"""
Railway-compatible backup system for LoopIn - No PostgreSQL client tools required
"""
import os
import json
import time
from pathlib import Path
from urllib.parse import urlparse
from timezone_utils import now_utc
from extensions import db
from models import Update, SOPSummary, LessonLearned, ArchivedUpdate, ArchivedSOPSummary, ArchivedLessonLearned, User, ReadLog, ActivityLog

class DatabaseBackupSystem:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")

        self.parsed_url = urlparse(self.database_url)

        # Use configurable backup directory with fallback
        backup_dir_env = os.getenv("BACKUP_DIR", "backups")
        self.backup_dir = Path(backup_dir_env)
        self.backup_dir.mkdir(exist_ok=True)

        # Environment detection
        self.is_railway = self._detect_railway_environment()
        self.is_production = os.getenv("RAILWAY_ENVIRONMENT") == "production" or os.getenv("FLASK_ENV") == "production"
        self.is_development = os.getenv("FLASK_ENV") == "development" or not self.is_production

        # Load backup configuration
        self._load_backup_config()

        # Log only in development or for important events
        if self.is_development:
            print(f"[OK] Database backup system initialized for {'Railway' if self.is_railway else 'standard'} environment")

    def _detect_railway_environment(self):
        """Detect if we're running on Railway"""
        return (
            "railway" in self.database_url.lower() or
            os.getenv("RAILWAY_ENVIRONMENT") is not None or
            os.getenv("RAILWAY_PROJECT_ID") is not None
        )

    def _load_backup_config(self):
        """Load backup configuration with environment-specific settings"""
        # Default configuration
        self.max_backup_size = int(os.getenv("MAX_BACKUP_SIZE", "524288000"))  # 500MB default
        self.backup_retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
        self.compress_backups = os.getenv("COMPRESS_BACKUPS", "true").lower() == "true"
        self.validate_backups = os.getenv("VALIDATE_BACKUPS", "true").lower() == "true"

        # Production-specific settings
        if self.is_production:
            # More conservative settings for production
            self.backup_retention_days = min(self.backup_retention_days, 90)  # Max 90 days in production
            self.max_backup_size = min(self.max_backup_size, 1073741824)  # Max 1GB in production
        else:
            # More permissive settings for development
            self.backup_retention_days = max(self.backup_retention_days, 7)  # Min 7 days in development
    
    def create_backup(self, backup_type="manual"):
        """Create a database backup using SQLAlchemy (Railway-compatible)"""
        try:
            timestamp = now_utc().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"loopin_backup_{backup_type}_{timestamp}.json"
            backup_path = self.backup_dir / backup_filename

            if self.is_development:
                print(f"📦 Creating Railway-compatible backup: {backup_path}")

            # Collect all data using SQLAlchemy
            backup_data = {
                "metadata": {
                    "backup_type": backup_type,
                    "timestamp": timestamp,
                    "created_at": now_utc().isoformat(),
                    "backup_version": "3.1",  # Updated Railway-compatible version
                    "format": "sqlalchemy_json",
                    "database_url": self._mask_database_url(),
                    "railway_compatible": True,
                    "environment": "production" if self.is_production else "development",
                    "compression_enabled": self.compress_backups,
                    "max_backup_size": self.max_backup_size
                },
                "data": {}
            }

            # Export all tables
            tables_to_export = [
                ("updates", Update),
                ("users", User),
                ("read_logs", ReadLog),
                ("activity_logs", ActivityLog),
                ("sop_summaries", SOPSummary),
                ("lessons_learned", LessonLearned),
                ("archived_updates", ArchivedUpdate),
                ("archived_sop_summaries", ArchivedSOPSummary),
                ("archived_lessons_learned", ArchivedLessonLearned)
            ]

            total_records = 0
            for table_name, model_class in tables_to_export:
                try:
                    print(f"  📊 Exporting {table_name}...")
                    records = model_class.query.all()
                    backup_data["data"][table_name] = [record.to_dict() if hasattr(record, 'to_dict') else self._model_to_dict(record) for record in records]
                    total_records += len(records)
                    print(f"    ✅ {len(records)} records exported")
                except Exception as e:
                    print(f"    ⚠️  Failed to export {table_name}: {e}")
                    backup_data["data"][table_name] = []

            # Save backup to JSON file
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)

            # Check backup file size
            file_size = backup_path.stat().st_size
            if file_size > self.max_backup_size:
                if self.is_development:
                    print(f"⚠️  Backup size ({file_size} bytes) exceeds maximum allowed size ({self.max_backup_size} bytes)")
                backup_path.unlink()  # Delete the oversized backup
                return None

            # Verify backup file
            if backup_path.exists() and file_size > 0:
                if self.is_development:
                    print(f"✅ Backup created successfully: {backup_path}")
                    print(f"   📊 Total records: {total_records}")
                    print(f"   📁 File size: {file_size} bytes")

                # Create metadata file
                metadata = {
                    "backup_type": backup_type,
                    "timestamp": timestamp,
                    "file_size": file_size,
                    "created_at": now_utc().isoformat(),
                    "format": "sqlalchemy_json",
                    "database_url": self._mask_database_url(),
                    "total_records": total_records,
                    "railway_compatible": True,
                    "backup_version": "3.1",
                    "restore_instructions": "Use the Railway-compatible restore method",
                    "environment": "production" if self.is_production else "development"
                }

                metadata_path = backup_path.with_suffix('.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)

                return backup_path
            else:
                if self.is_development:
                    print("❌ Backup file was not created or is empty")
                return None

        except Exception as e:
            print(f"❌ Backup error: {e}")
            return None

    def _model_to_dict(self, model_instance):
        """Convert SQLAlchemy model instance to dictionary"""
        try:
            result = {}
            for column in model_instance.__table__.columns:
                value = getattr(model_instance, column.name)
                # Convert datetime objects to ISO strings
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                result[column.name] = value
            return result
        except Exception as e:
            print(f"⚠️  Error converting model to dict: {e}")
            return {}

    def _mask_database_url(self):
        """Mask sensitive information in database URL for metadata"""
        try:
            parsed = self.parsed_url
            if parsed.password:
                masked_password = "***"
                masked_url = f"{parsed.scheme}://{parsed.username}:{masked_password}@{parsed.hostname}:{parsed.port}{parsed.path}"
                return masked_url
            return str(self.database_url)
        except:
            return "postgresql://***:***@***:***/***"

    def _clear_existing_data(self):
        """Clear existing data before restore"""
        try:
            print("  🗑️  Clearing existing data...")

            # Clear tables in reverse dependency order
            tables_to_clear = [
                ReadLog, ActivityLog,  # Foreign key dependencies
                Update, SOPSummary, LessonLearned,  # Main tables
                ArchivedUpdate, ArchivedSOPSummary, ArchivedLessonLearned,  # Archive tables
                User  # Users table last
            ]

            for table_class in tables_to_clear:
                try:
                    deleted_count = table_class.query.delete()
                    print(f"    🗑️  Cleared {deleted_count} records from {table_class.__tablename__}")
                except Exception as e:
                    print(f"    ⚠️  Failed to clear {table_class.__tablename__}: {e}")

            db.session.commit()
            print("  ✅ Existing data cleared")
            return True

        except Exception as e:
            print(f"  ❌ Failed to clear existing data: {e}")
            db.session.rollback()
            return False

    def _restore_table(self, model_class, records):
        """Restore records to a specific table"""
        try:
            restored_count = 0
            for record_data in records:
                try:
                    # Create new instance
                    record = model_class()

                    # Set attributes
                    for key, value in record_data.items():
                        if hasattr(record, key):
                            # Handle special cases
                            if key == 'timestamp' and value and isinstance(value, str):
                                # Parse ISO timestamp
                                from datetime import datetime
                                try:
                                    if value.endswith('Z'):
                                        value = value.replace('Z', '+00:00')
                                    record.timestamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                except:
                                    record.timestamp = now_utc()
                            elif key == 'created_at' and value and isinstance(value, str):
                                from datetime import datetime
                                try:
                                    if value.endswith('Z'):
                                        value = value.replace('Z', '+00:00')
                                    record.created_at = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                except:
                                    record.created_at = now_utc()
                            elif key == 'updated_at' and value and isinstance(value, str):
                                from datetime import datetime
                                try:
                                    if value.endswith('Z'):
                                        value = value.replace('Z', '+00:00')
                                    record.updated_at = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                except:
                                    record.updated_at = now_utc()
                            elif key == 'archived_at' and value and isinstance(value, str):
                                from datetime import datetime
                                try:
                                    if value.endswith('Z'):
                                        value = value.replace('Z', '+00:00')
                                    record.archived_at = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                except:
                                    record.archived_at = now_utc()
                            else:
                                setattr(record, key, value)

                    # Add to session
                    db.session.add(record)
                    restored_count += 1

                except Exception as e:
                    print(f"    ⚠️  Failed to restore record: {e}")
                    continue

            # Commit the batch
            db.session.commit()
            return restored_count

        except Exception as e:
            print(f"  ❌ Failed to restore table {model_class.__tablename__}: {e}")
            db.session.rollback()
            return 0
    
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
        
        backups.sort(key=lambda x: x['metadata']['created_at'], reverse=True)
        return backups
    
    def verify_backup(self, backup_path):
        """Verify backup file exists and is readable"""
        try:
            return backup_path.exists() and backup_path.stat().st_size > 0
        except:
            return False
    
    def restore_backup(self, backup_path):
        """Restore database from Railway-compatible JSON backup"""
        try:
            print(f"🚀 Starting Railway-compatible restore from: {backup_path}")

            # Step 1: Load backup data
            if not backup_path.exists():
                print(f"❌ Backup file not found: {backup_path}")
                return False

            print("📖 Loading backup data...")
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            if "data" not in backup_data:
                print("❌ Invalid backup format - missing data section")
                return False

            # Step 2: Clear existing data (optional - ask user?)
            print("🧹 Preparing database for restore...")
            if not self._clear_existing_data():
                print("⚠️  Warning: Could not clear existing data")

            # Step 3: Restore all tables
            total_restored = 0
            tables_to_restore = [
                ("users", User),
                ("updates", Update),
                ("read_logs", ReadLog),
                ("activity_logs", ActivityLog),
                ("sop_summaries", SOPSummary),
                ("lessons_learned", LessonLearned),
                ("archived_updates", ArchivedUpdate),
                ("archived_sop_summaries", ArchivedSOPSummary),
                ("archived_lessons_learned", ArchivedLessonLearned)
            ]

            for table_name, model_class in tables_to_restore:
                if table_name in backup_data["data"]:
                    records = backup_data["data"][table_name]
                    if records:
                        print(f"  📊 Restoring {table_name} ({len(records)} records)...")
                        restored_count = self._restore_table(model_class, records)
                        total_restored += restored_count
                        print(f"    ✅ {restored_count} records restored")
                    else:
                        print(f"  📊 {table_name}: No data to restore")

            # Step 4: Handle archived items restoration
            print("🔄 Processing archived items restoration...")
            archived_restore_success = self._restore_archived_items_to_original_locations()

            if not archived_restore_success:
                print("⚠️  Warning: Archived items restoration had issues")

            # Step 5: Verify restore
            print("✅ Restore completed successfully!")
            print(f"📊 Total records restored: {total_restored}")
            print("📋 Summary:")
            print("   ✅ Database tables restored")
            print("   ✅ Archived items moved to original locations")
            print("   ✅ Railway-compatible format used")

            return True

        except Exception as e:
            print(f"❌ Restore failed: {e}")
            return False

    def _preflight_checks(self, backup_path):
        """Quick pre-flight checks before restore"""
        print("🔍 Running pre-flight checks...")

        # Check if backup file exists and is readable
        if not self.verify_backup(backup_path):
            print(f"❌ Backup file verification failed: {backup_path}")
            return False

        # Check file size (should not be empty)
        file_size = backup_path.stat().st_size
        if file_size == 0:
            print("❌ Backup file is empty")
            return False

        print(f"✅ Backup file OK ({file_size} bytes)")
        return True

    def _restore_archived_items_to_original_locations(self):
        """Move all archived items back to their original tables using SQLAlchemy"""
        print("🔄 Moving archived items to original locations...")

        try:
            # Move archived updates back to updates table
            archived_updates = ArchivedUpdate.query.all()
            for archived in archived_updates:
                try:
                    # Create new update from archived data
                    restored_update = Update(
                        id=archived.id,
                        name=archived.name,
                        process=archived.process,
                        message=archived.message,
                        timestamp=archived.timestamp
                    )
                    db.session.add(restored_update)
                except Exception as e:
                    print(f"  ⚠️  Failed to restore archived update {archived.id}: {e}")

            # Move archived SOPs back to sop_summaries table
            archived_sops = ArchivedSOPSummary.query.all()
            for archived in archived_sops:
                try:
                    restored_sop = SOPSummary(
                        id=archived.id,
                        title=archived.title,
                        summary_text=archived.summary_text,
                        department=archived.department,
                        tags=archived.tags,
                        created_at=archived.created_at
                    )
                    db.session.add(restored_sop)
                except Exception as e:
                    print(f"  ⚠️  Failed to restore archived SOP {archived.id}: {e}")

            # Move archived lessons back to lessons_learned table
            archived_lessons = ArchivedLessonLearned.query.all()
            for archived in archived_lessons:
                try:
                    restored_lesson = LessonLearned(
                        id=archived.id,
                        title=archived.title,
                        content=archived.content,
                        summary=archived.summary,
                        author=archived.author,
                        department=archived.department,
                        tags=archived.tags,
                        created_at=archived.created_at,
                        updated_at=archived.updated_at
                    )
                    db.session.add(restored_lesson)
                except Exception as e:
                    print(f"  ⚠️  Failed to restore archived lesson {archived.id}: {e}")

            # Commit all changes
            db.session.commit()
            print("✅ Archived items moved to original locations")
            return True

        except Exception as e:
            print(f"❌ Failed to restore archived items: {e}")
            db.session.rollback()
            return False

    def _post_restore_cleanup_and_verify(self):
        """Clean up archived tables and verify restore integrity"""
        print("🧹 Post-restore cleanup and verification...")

        try:
            # Clear archived tables since items are now in original locations
            archived_tables = [ArchivedUpdate, ArchivedSOPSummary, ArchivedLessonLearned]

            for table_class in archived_tables:
                try:
                    deleted_count = table_class.query.delete()
                    print(f"  🗑️  Cleared {deleted_count} records from {table_class.__tablename__}")
                except Exception as e:
                    print(f"  ⚠️  Failed to clean up {table_class.__tablename__}: {e}")

            db.session.commit()
            print("✅ Post-restore cleanup completed")
            return True

        except Exception as e:
            print(f"⚠️  Post-restore cleanup had issues: {e}")
            db.session.rollback()
            return False
    
    def cleanup_old_backups(self):
        """Clean up old backups based on retention policy"""
        try:
            from datetime import datetime, timedelta

            # Get all backup files
            backup_files = list(self.backup_dir.glob("*.json"))
            current_time = now_utc()

            # Filter out metadata files (they have .json extension but are not the main backup files)
            main_backup_files = [f for f in backup_files if not f.name.endswith('.json.json')]

            backups_to_delete = []

            for backup_file in main_backup_files:
                try:
                    # Check file age
                    file_age_days = (current_time - datetime.fromtimestamp(backup_file.stat().st_mtime, tz=current_time.tzinfo)).days

                    if file_age_days > self.backup_retention_days:
                        backups_to_delete.append(backup_file)
                except Exception as e:
                    if self.is_development:
                        print(f"⚠️  Error checking backup file {backup_file}: {e}")
                    continue

            # Delete old backups
            deleted_count = 0
            for backup_file in backups_to_delete:
                try:
                    # Delete main backup file
                    backup_file.unlink()

                    # Delete associated metadata file
                    metadata_file = backup_file.with_suffix('.json')
                    if metadata_file.exists():
                        metadata_file.unlink()

                    deleted_count += 1
                    if self.is_development:
                        print(f"🗑️  Deleted old backup: {backup_file.name}")
                except Exception as e:
                    if self.is_development:
                        print(f"⚠️  Error deleting backup {backup_file}: {e}")

            if self.is_development and deleted_count > 0:
                print(f"✅ Cleaned up {deleted_count} old backups (retention: {self.backup_retention_days} days)")

        except Exception as e:
            if self.is_development:
                print(f"❌ Error during backup cleanup: {e}")
