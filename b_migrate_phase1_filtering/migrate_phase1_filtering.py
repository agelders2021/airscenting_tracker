#!/usr/bin/env python3
"""
Phase 1 Migration: Filtering Infrastructure

This script implements the foundation for computed session numbers:

Step 1: Add status filtering to session queries
  - Update get_sessions_for_dog() to accept status_filter parameter
  - Add WHERE clause logic to filter by status

Step 2: Create session number computation function
  - New function: compute_session_number(dog_name, session_date, status_filter)
  - Returns ordinal position of a session in filtered list
  - Counts sessions with same dog, matching status, with date <= given date

Usage:
    python migrate_phase1_filtering.py          # Show what will be done
    python migrate_phase1_filtering.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase1FilteringMigration:
    """Phase 1: Add filtering infrastructure and computation function"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_database.py": "Add status filtering and session number computation"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 1: FILTERING INFRASTRUCTURE")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        """Print what will be changed"""
        print("CHANGES TO BE MADE:")
        print()
        print("STEP 1 - Add Status Filtering:")
        print("  - Update get_sessions_for_dog() to accept status_filter parameter")
        print("    • status_filter='active' - WHERE status='active' OR status IS NULL")
        print("    • status_filter='deleted' - WHERE status='deleted'")
        print("    • status_filter='both' - no status filter")
        print()
        print("STEP 2 - Create Computation Function:")
        print("  - New function: compute_session_number(dog_name, session_date, status_filter)")
        print("  - Returns ordinal position in filtered session list")
        print("  - Logic: COUNT sessions with matching dog, status, date <= given date")
        print()
        print("FILES TO BE MODIFIED:")
        for filename, description in self.files_to_modify.items():
            filepath = os.path.join(self.project_dir, filename)
            exists = "✓" if os.path.exists(filepath) else "✗ NOT FOUND"
            print(f"  {exists} {filename}")
            print(f"      {description}")
        print()
        if self.execute:
            print(f"BACKUPS: Original files will be copied to {self.backup_folder}/")
            print()
    
    def create_backup_folder(self):
        """Create backup folder if it doesn't exist"""
        if not os.path.exists(self.backup_folder):
            os.makedirs(self.backup_folder)
            print(f"Created backup folder: {self.backup_folder}")
    
    def backup_file(self, filepath):
        """Copy file to backup folder"""
        self.create_backup_folder()
        filename = os.path.basename(filepath)
        backup_path = os.path.join(self.backup_folder, filename)
        shutil.copy2(filepath, backup_path)
        print(f"  ✓ Backed up: {filename} -> {self.backup_folder}/{filename}")
    
    def modify_ui_database(self):
        """Add status filtering and session number computation to ui_database.py"""
        print("\n[1/1] Modifying ui_database.py...")
        
        filepath = os.path.join(self.project_dir, "ui_database.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            success = True
            
            # STEP 1: Update get_sessions_for_dog to add status filtering
            old_get_sessions = '''    def get_sessions_for_dog(self, dog_name):
        """Get all sessions for a specific dog"""
        if not dog_name or not dog_name.strip():
            return []
        
        dog_name = dog_name.strip()
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                result = conn.execute(
                    text("""
                        SELECT session_number, date, handler, dog_name
                        FROM training_sessions 
                        WHERE dog_name = :dog_name
                        ORDER BY session_number
                    """),
                    {"dog_name": dog_name}
                )
                sessions = result.fetchall()
            
            self._restore_db_context(old_db_type)
            
            return sessions
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                return []
            else:
                print(f"Error getting sessions: {e}")
                return []'''
            
            new_get_sessions = '''    def get_sessions_for_dog(self, dog_name, status_filter='active'):
        """Get sessions for a specific dog filtered by status
        
        Args:
            dog_name: Name of the dog
            status_filter: 'active', 'deleted', or 'both'
        
        Returns:
            List of tuples: (session_number, date, handler, dog_name)
        """
        if not dog_name or not dog_name.strip():
            return []
        
        dog_name = dog_name.strip()
        
        try:
            old_db_type = self._switch_db_context()
            
            # Build WHERE clause based on status filter
            if status_filter == 'active':
                status_where = "AND (status = 'active' OR status IS NULL)"
            elif status_filter == 'deleted':
                status_where = "AND status = 'deleted'"
            else:  # 'both'
                status_where = ""
            
            with get_connection() as conn:
                result = conn.execute(
                    text(f"""
                        SELECT session_number, date, handler, dog_name
                        FROM training_sessions 
                        WHERE dog_name = :dog_name {status_where}
                        ORDER BY date, session_number
                    """),
                    {"dog_name": dog_name}
                )
                sessions = result.fetchall()
            
            self._restore_db_context(old_db_type)
            
            return sessions
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                return []
            else:
                print(f"Error getting sessions: {e}")
                return []'''
            
            if old_get_sessions in content:
                content = content.replace(old_get_sessions, new_get_sessions)
                print("  ✓ Updated get_sessions_for_dog() with status filtering")
            else:
                print("  ✗ Could not find get_sessions_for_dog() pattern")
                success = False
            
            # STEP 2: Add compute_session_number function
            # Insert it right after get_sessions_for_dog
            insertion_point = '''                print(f"Error getting sessions: {e}")
                return []
    
    # ===== SELECTED TERRAINS ====='''
            
            new_function = '''                print(f"Error getting sessions: {e}")
                return []
    
    def compute_session_number(self, dog_name, session_date, status_filter='active'):
        """Compute the ordinal session number for a session based on filtered list
        
        Args:
            dog_name: Name of the dog
            session_date: Date of the session (as string 'YYYY-MM-DD')
            status_filter: 'active', 'deleted', or 'both'
        
        Returns:
            int: Ordinal position (1-based) in the filtered list
        """
        if not dog_name or not dog_name.strip():
            return 1
        
        dog_name = dog_name.strip()
        
        try:
            old_db_type = self._switch_db_context()
            
            # Build WHERE clause based on status filter
            if status_filter == 'active':
                status_where = "AND (status = 'active' OR status IS NULL)"
            elif status_filter == 'deleted':
                status_where = "AND status = 'deleted'"
            else:  # 'both'
                status_where = ""
            
            with get_connection() as conn:
                # Count sessions with same dog, matching status, with date <= given date
                result = conn.execute(
                    text(f"""
                        SELECT COUNT(*) 
                        FROM training_sessions 
                        WHERE dog_name = :dog_name 
                        AND date <= :session_date
                        {status_where}
                    """),
                    {"dog_name": dog_name, "session_date": session_date}
                )
                count = result.scalar()
            
            self._restore_db_context(old_db_type)
            
            # Return count as ordinal position (minimum 1)
            return count if count > 0 else 1
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                return 1
            else:
                print(f"Error computing session number: {e}")
                return 1
    
    # ===== SELECTED TERRAINS ====='''
            
            if insertion_point in content:
                content = content.replace(insertion_point, new_function)
                print("  ✓ Added compute_session_number() function")
            else:
                print("  ✗ Could not find insertion point for compute_session_number()")
                success = False
            
            if success:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return success
        else:
            print("  - Would update get_sessions_for_dog() with status filtering")
            print("  - Would add compute_session_number() function")
            return True
    
    def run(self):
        """Execute the migration"""
        self.print_header()
        self.print_changes()
        
        if not self.execute:
            print("=" * 80)
            print("DRY RUN - No changes made")
            print("=" * 80)
            print()
            print("To execute this migration, run:")
            print(f"  python {os.path.basename(sys.argv[0])} --execute")
            print()
            return True
        
        print("=" * 80)
        print("EXECUTING MIGRATION")
        print("=" * 80)
        print()
        
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("\nMigration cancelled.")
            return False
        
        print("\nProceeding with migration...\n")
        
        results = []
        results.append(self.modify_ui_database())
        
        print("\n" + "=" * 80)
        if all(results):
            print("PHASE 1 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ get_sessions_for_dog() now accepts status_filter parameter")
            print("  ✓ compute_session_number() function added")
            print()
            print("NEXT STEPS:")
            print("  1. Test that get_sessions_for_dog() still works")
            print("  2. Test compute_session_number() manually if desired")
            print("  3. Ready for Phase 2: Update display to use computed numbers")
            print()
            print(f"RESTORE: If needed, copy files from {self.backup_folder}/")
            print()
            return True
        else:
            print("MIGRATION FAILED")
            print("=" * 80)
            print()
            print("Some patterns could not be found.")
            print(f"Original files preserved in: {self.backup_folder}/")
            print()
            return False


def main():
    """Main entry point"""
    execute = "--execute" in sys.argv
    
    migration = Phase1FilteringMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
