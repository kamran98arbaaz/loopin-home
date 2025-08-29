#!/usr/bin/env python3
"""
Test script for backup restoration fixes
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_backup_system():
    """Test backup system initialization and basic functionality"""
    print("Testing backup system...")

    try:
        from backup_system import DatabaseBackupSystem
        from app import create_app

        # Create Flask app
        app = create_app()
        print("OK: Flask app created")

        # Test backup system initialization
        with app.app_context():
            backup_system = DatabaseBackupSystem()
            print("OK: Backup system initialized")

            # Test basic functionality
            print(f"INFO: Backup directory: {backup_system.backup_dir}")
            print(f"INFO: Is Railway: {backup_system.is_railway}")
            print(f"INFO: Environment: {'production' if backup_system.is_production else 'development'}")

            # Test listing backups (should work even if empty)
            backups = backup_system.list_backups()
            print(f"OK: Found {len(backups)} existing backups")

            return True

    except Exception as e:
        print(f"ERROR: Backup system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backup_creation():
    """Test backup creation functionality"""
    print("\nTesting backup creation...")

    try:
        from backup_system import DatabaseBackupSystem
        from app import create_app

        app = create_app()

        with app.app_context():
            backup_system = DatabaseBackupSystem()

            # Create a test backup
            print("Creating test backup...")
            backup_path = backup_system.create_backup("test")

            if backup_path:
                print(f"OK: Backup created successfully: {backup_path}")

                # Verify backup file exists
                if backup_path.exists():
                    print(f"OK: Backup file exists, size: {backup_path.stat().st_size} bytes")
                    return backup_path
                else:
                    print("ERROR: Backup file was not created")
                    return None
            else:
                print("ERROR: Backup creation failed")
                return None

    except Exception as e:
        print(f"ERROR: Backup creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_backup_restoration(backup_path):
    """Test backup restoration functionality"""
    print(f"\nTesting backup restoration with: {backup_path}")

    try:
        from backup_system import DatabaseBackupSystem
        from app import create_app

        app = create_app()

        with app.app_context():
            backup_system = DatabaseBackupSystem()

            # Test restoration
            print("Starting restoration...")
            result = backup_system.restore_backup(backup_path)

            if result:
                print("OK: Backup restoration completed successfully")
                return True
            else:
                print("ERROR: Backup restoration failed")
                return False

    except Exception as e:
        print(f"ERROR: Backup restoration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("Starting backup system tests...\n")

    # Test 1: Backup system initialization
    system_ok = test_backup_system()

    if not system_ok:
        print("ERROR: Backup system initialization failed")
        return 1

    # Test 2: Backup creation
    backup_path = test_backup_creation()

    if not backup_path:
        print("ERROR: Backup creation failed")
        return 1

    # Test 3: Backup restoration
    restore_ok = test_backup_restoration(backup_path)

    # Summary
    print("\n" + "="*50)
    print("BACKUP SYSTEM TEST SUMMARY")
    print("="*50)

    if system_ok and backup_path and restore_ok:
        print("SUCCESS: ALL TESTS PASSED!")
        print("OK: Backup system initialization")
        print("OK: Backup creation")
        print("OK: Backup restoration")
        print("\nBackup system is working correctly!")
        return 0
    else:
        print("ERROR: SOME TESTS FAILED!")
        print(f"System init: {'PASSED' if system_ok else 'FAILED'}")
        print(f"Backup creation: {'PASSED' if backup_path else 'FAILED'}")
        print(f"Backup restoration: {'PASSED' if restore_ok else 'FAILED'}")
        print("\nPlease check the error messages above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())