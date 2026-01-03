#!/usr/bin/env python3
"""
Phase 2.68 Migration: Fix Computed Number Calculation (Simpler Pattern)

Searches for just the essential line to replace.

Changes:
1. Replace compute_session_number() call with list position lookup

Usage:
    python migrate_phase2_68_fix_computed_simple.py          # Show what will be done
    python migrate_phase2_68_fix_computed_simple.py --execute  # Execute the migration
"""

import sys
import shutil
import os


class Phase2_68_FixComputedSimpleMigration:
    """Phase 2.68: Fix computed number with simpler pattern"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_navigation.py": "Fix computed number to use list position"
        }
    
    def print_header(self):
        print("=" * 80)
        print("PHASE 2.68: FIX COMPUTED NUMBER (SIMPLE PATTERN)")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def create_backup_folder(self):
        if not os.path.exists(self.backup_folder):
            os.makedirs(self.backup_folder)
    
    def backup_file(self, filepath):
        self.create_backup_folder()
        filename = os.path.basename(filepath)
        backup_path = os.path.join(self.backup_folder, filename)
        shutil.copy2(filepath, backup_path)
        print(f"  ✓ Backed up: {filename}")
    
    def backup_script(self):
        self.create_backup_folder()
        script_path = os.path.abspath(sys.argv[0])
        script_name = os.path.basename(script_path)
        backup_path = os.path.join(self.backup_folder, script_name)
        shutil.copy2(script_path, backup_path)
        print(f"  ✓ Backed up script")
    
    def modify_ui_navigation(self):
        print("\n[1/1] Modifying ui_navigation.py...")
        
        filepath = os.path.join(self.project_dir, "ui_navigation.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'rb') as f:
                content = f.read().decode('utf-8')
            
            # Search for just the essential line
            old_line = 'computed_number = db_ops.compute_session_number(dog_name, session_dict["date"], status_filter)'
            
            new_code = '''# Get filtered list and find position of current session
            filtered_sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter)
            session_numbers = [s[0] for s in filtered_sessions]
            
            # Find position (1-indexed)
            if session_number in session_numbers:
                computed_number = session_numbers.index(session_number) + 1
            else:
                # Session not in filtered list (shouldn't happen), use DB number
                computed_number = session_number'''
            
            if old_line in content:
                content = content.replace(old_line, new_code)
                
                with open(filepath, 'wb') as f:
                    f.write(content.encode('utf-8'))
                
                print("  ✓ Replaced compute_session_number with list position lookup")
                return True
            else:
                print("  ✗ Could not find the line to replace")
                print(f"  Searched for: {old_line[:60]}...")
                return False
        else:
            print("  - Would replace compute_session_number call")
            return True
    
    def run(self):
        self.print_header()
        
        if not self.execute:
            print("DRY RUN")
            print()
            print("To execute: python", os.path.basename(sys.argv[0]), "--execute")
            return True
        
        print("EXECUTING")
        print()
        
        response = input("Proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("\nCancelled.")
            return False
        
        print()
        self.backup_script()
        print()
        
        if self.modify_ui_navigation():
            print("\n" + "=" * 80)
            print("PHASE 2.68 COMPLETED")
            print("=" * 80)
            print("\n✓ Computed numbers now use position in filtered list")
            print("✓ No more duplicate numbers for same-date sessions")
            print(f"\nRestore from: {self.backup_folder}/")
            return True
        else:
            print("\n" + "=" * 80)
            print("FAILED")
            print("=" * 80)
            return False


def main():
    execute = "--execute" in sys.argv
    migration = Phase2_68_FixComputedSimpleMigration(execute=execute)
    success = migration.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
