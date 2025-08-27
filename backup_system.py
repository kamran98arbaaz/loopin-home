"""
Minimal backup system for LoopIn
"""
import os
import subprocess
import json
from pathlib import Path
from urllib.parse import urlparse
from timezone_utils import now_utc

class DatabaseBackupSystem:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        self.parsed_url = urlparse(self.database_url)
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(self, backup_type="manual"):
        """Create a database backup"""
        try:
            timestamp = now_utc().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"loopin_backup_{backup_type}_{timestamp}.sql"
            backup_path = self.backup_dir / backup_filename
            
            cmd = [
                "pg_dump",
                "--verbose",
                "--clean",
                "--no-acl",
                "--no-owner",
                "--format=plain",
                "--file", str(backup_path),
                self.database_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Create metadata
                metadata = {
                    "backup_type": backup_type,
                    "timestamp": timestamp,
                    "file_size": backup_path.stat().st_size,
                    "created_at": now_utc().isoformat()
                }
                
                metadata_path = backup_path.with_suffix('.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                return backup_path
            else:
                return None
        except Exception:
            return None
    
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
        """Restore database from backup"""
        try:
            cmd = [
                "psql",
                "-f", str(backup_path),
                "-v", "ON_ERROR_STOP=1",
                self.database_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return result.returncode == 0
        except:
            return False
    
    def cleanup_old_backups(self):
        """Clean up old backups"""
        # Keep last 10 backups
        backups = self.list_backups()
        if len(backups) > 10:
            for backup in backups[10:]:
                try:
                    backup['file'].unlink()
                    metadata_file = backup['file'].with_suffix('.json')
                    if metadata_file.exists():
                        metadata_file.unlink()
                except:
                    pass
