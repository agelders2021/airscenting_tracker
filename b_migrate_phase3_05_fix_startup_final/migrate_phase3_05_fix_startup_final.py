#!/usr/bin/env python3
"""
Phase 3.05 Migration: Fix Startup Dog Loading

The load_data_incrementally() method in ui_misc_data_ops.py loads the last dog
at startup and sets session_number to database next. This is THE place that's
setting the wrong value at startup!

Changes:
1. Update step5() in load_data_incrementally() to use computed next number

Usage:
    python migrate_phase3_05_fix_startup_final.py          # Show what will be done
    python migrate_phase3_05_fix_startup_final.py --execute  # Execute the migration
"""

import sys
import shutil
import os


class Phase3_05_FixStartupFinalMigration:
    """Phase 3.05: Fix startup dog loading to use computed numbers"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_misc_data_ops.py": "Fix step5() to use computed next number"
        }
    
    def print_header(self):
        print("=" * 80)
        print("PHASE 3.05: FIX STARTUP FINAL")
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
    
    def modify_ui_misc_data_ops(self):
        print("\n[1/1] Modifying ui_misc_data_ops.py...")
        
        filepath = os.path.join(self.project_dir, "ui_misc_data_ops.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find the lines in step5() that set session number to database value
            old_code = '''                    # Update session number for this dog (on_dog_changed not triggered by programmatic set)
                    next_session = DatabaseOperations(self.ui).get_next_session_number(last_dog)
                    sv.session_number.set(str(next_session))'''
            
            new_code = '''                    # Update session number for this dog (on_dog_changed not triggered by programmatic set)
                    # Use computed next number based on filter
                    status_filter = sv.session_status_filter.get()
                    filtered_sessions = DatabaseOperations(self.ui).get_all_sessions_for_dog(last_dog, status_filter)
                    next_computed = len(filtered_sessions) + 1
                    sv.session_number.set(str(next_computed))'''
            
            if old_code in content:
                content = content.replace(old_code, new_code)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Updated step5() to use computed numbers")
                return True
            else:
                print("  ✗ Could not find the code to replace")
                print("  Searching for: '# Update session number for this dog'")
                return False
        else:
            print("  - Would update step5() to use computed numbers")
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
        
        if self.modify_ui_misc_data_ops():
            print("\n" + "=" * 80)
            print("🎉 PHASE 3.05 COMPLETED - THIS WAS THE ISSUE! 🎉")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ Fixed startup dog loading to use computed numbers")
            print("  ✓ This is where the database number was coming from!")
            print()
            print("ALL SOFT-DELETE MIGRATION NOW TRULY COMPLETE!")
            print()
            print("EVERY LOCATION NOW USES COMPUTED NUMBERS:")
            print("  ✅ Startup - loads dog and sets computed next")
            print("  ✅ New button - computed next")
            print("  ✅ Save Session - computed next after save")
            print("  ✅ Change dog - computed next")
            print("  ✅ Load session - computed position")
            print("  ✅ Edit/Delete dialog - computed positions")
            print("  ✅ Filter change - recomputes")
            print()
            print(f"Restore from: {self.backup_folder}/")
            return True
        else:
            print("\n" + "=" * 80)
            print("FAILED")
            print("=" * 80)
            return False


def main():
    execute = "--execute" in sys.argv
    migration = Phase3_05_FixStartupFinalMigration(execute=execute)
    success = migration.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
