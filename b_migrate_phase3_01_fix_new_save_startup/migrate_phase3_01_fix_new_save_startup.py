#!/usr/bin/env python3
"""
Phase 3.01 Migration: Fix New, Save, and Startup Computed Numbers

Fix the remaining cases where database numbers are shown instead of computed:
1. "New" button - show next computed number for current filter
2. "Save Session" - show computed number after saving
3. Startup - show computed number for initial session

Changes:
1. Update new_session() to show computed next number
2. Update save_session handling to reload and show computed
3. Update initial session number at startup

Usage:
    python migrate_phase3_01_fix_new_save_startup.py          # Show what will be done
    python migrate_phase3_01_fix_new_save_startup.py --execute  # Execute the migration
"""

import sys
import shutil
import os


class Phase3_01_FixNewSaveStartupMigration:
    """Phase 3.01: Fix New, Save, and Startup to show computed numbers"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_form_management.py": "Fix new_session() to show computed number",
            "ui.py": "Fix startup to show computed number"
        }
    
    def print_header(self):
        print("=" * 80)
        print("PHASE 3.01: FIX NEW, SAVE, AND STARTUP")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        print("CHANGES TO BE MADE:")
        print()
        print("1. Fix new_session() in ui_form_management.py:")
        print("   - Count active sessions and show next computed number")
        print("   - If 3 active sessions exist, show #4")
        print()
        print("2. Fix startup in ui.py:")
        print("   - Show computed next number at startup")
        print()
        print("Note: Save Session already reloads, so it will show computed number")
        print()
        print("FILES TO BE MODIFIED:")
        for filename, description in self.files_to_modify.items():
            filepath = os.path.join(self.project_dir, filename)
            exists = "✓" if os.path.exists(filepath) else "✗ NOT FOUND"
            print(f"  {exists} {filename}")
            print(f"      {description}")
        print()
        if self.execute:
            print(f"BACKUPS: Will be copied to {self.backup_folder}/")
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
    
    def modify_ui_form_management(self):
        print("\n[1/2] Modifying ui_form_management.py...")
        
        filepath = os.path.join(self.project_dir, "ui_form_management.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'rb') as f:
                content = f.read().decode('utf-8')
            
            # Find where we get next_session and set it
            old_code = '''        db_ops = DatabaseOperations(self.ui)
        next_session = db_ops.get_next_session_number()
        sv.session_number.set(str(next_session))'''
            
            new_code = '''        db_ops = DatabaseOperations(self.ui)
        
        # Get the next COMPUTED number based on current filter
        dog_name = sv.dog.get()
        status_filter = sv.session_status_filter.get()
        
        if dog_name:
            # Count sessions in current filter and add 1
            filtered_sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter)
            next_computed = len(filtered_sessions) + 1
        else:
            # No dog selected, use 1
            next_computed = 1
        
        sv.session_number.set(str(next_computed))
        
        # Also get database next number for actual saving later
        next_session = db_ops.get_next_session_number()'''
            
            if old_code in content:
                content = content.replace(old_code, new_code)
                print("  ✓ Updated new_session() to show computed number")
                
                with open(filepath, 'wb') as f:
                    f.write(content.encode('utf-8'))
                
                return True
            else:
                print("  ✗ Could not find code to replace")
                return False
        else:
            print("  - Would update new_session() to show computed number")
            return True
    
    def modify_ui(self):
        print("\n[2/2] Modifying ui.py...")
        
        filepath = os.path.join(self.project_dir, "ui.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'rb') as f:
                content = f.read().decode('utf-8')
            
            # Find the update_initial_session function
            old_startup = '''        def update_initial_session():
            loaded_dog = sv.dog.get()
            if loaded_dog:
                next_session = DatabaseOperations(self).get_next_session_number(loaded_dog)
                sv.session_number.set(str(next_session))
                sv.status.set(f"Ready - {loaded_dog} - Next session: #{next_session}")
                # Update navigation button states
                self.navigation.update_navigation_buttons()'''
            
            new_startup = '''        def update_initial_session():
            loaded_dog = sv.dog.get()
            if loaded_dog:
                # Get computed next number based on active filter
                db_ops = DatabaseOperations(self)
                status_filter = sv.session_status_filter.get()
                filtered_sessions = db_ops.get_all_sessions_for_dog(loaded_dog, status_filter)
                next_computed = len(filtered_sessions) + 1
                
                sv.session_number.set(str(next_computed))
                sv.status.set(f"Ready - {loaded_dog} - Next session: #{next_computed}")
                # Update navigation button states
                self.navigation.update_navigation_buttons()'''
            
            if old_startup in content:
                content = content.replace(old_startup, new_startup)
                print("  ✓ Updated startup to show computed number")
                
                with open(filepath, 'wb') as f:
                    f.write(content.encode('utf-8'))
                
                return True
            else:
                print("  ✗ Could not find startup code to replace")
                return False
        else:
            print("  - Would update startup to show computed number")
            return True
    
    def run(self):
        self.print_header()
        self.print_changes()
        
        if not self.execute:
            print("=" * 80)
            print("DRY RUN")
            print("=" * 80)
            print()
            print("To execute: python", os.path.basename(sys.argv[0]), "--execute")
            return True
        
        print("=" * 80)
        print("EXECUTING")
        print("=" * 80)
        print()
        
        response = input("Proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("\nCancelled.")
            return False
        
        print()
        self.backup_script()
        print()
        
        results = []
        results.append(self.modify_ui_form_management())
        results.append(self.modify_ui())
        
        if all(results):
            print("\n" + "=" * 80)
            print("PHASE 3.01 COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ 'New' button now shows next computed number")
            print("  ✓ Startup shows computed number")
            print("  ✓ Numbers based on current filter setting")
            print()
            print("ALL SOFT-DELETE MIGRATION COMPLETE! 🎉")
            print()
            print("TEST IT:")
            print("  1. Start app - should show computed next number")
            print("  2. Click 'New' - shows next in filtered list")
            print("  3. Change filter - 'New' updates to show next in that filter")
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
    migration = Phase3_01_FixNewSaveStartupMigration(execute=execute)
    success = migration.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
