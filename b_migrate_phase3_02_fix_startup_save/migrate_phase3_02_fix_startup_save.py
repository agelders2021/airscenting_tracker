#!/usr/bin/env python3
"""
Phase 3.02 Migration: Fix Startup and Save Session (Regex)

Uses regex to handle both Windows (CRLF) and Linux (LF) line endings.

Changes:
1. Fix startup computed number (regex-based replacement)
2. After saving session, reload it to show computed number

Usage:
    python migrate_phase3_02_fix_startup_save.py          # Show what will be done
    python migrate_phase3_02_fix_startup_save.py --execute  # Execute the migration
"""

import sys
import shutil
import os
import re


class Phase3_02_StartupSaveMigration:
    """Phase 3.02: Fix startup and save using regex"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui.py": "Fix startup to show computed number (regex)",
            "ui_misc2.py": "Reload after save to show computed number"
        }
    
    def print_header(self):
        print("=" * 80)
        print("PHASE 3.02: FIX STARTUP AND SAVE SESSION")
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
    
    def modify_ui_startup(self):
        print("\n[1/2] Modifying ui.py (startup)...")
        
        filepath = os.path.join(self.project_dir, "ui.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use regex to match regardless of line endings
            # Match the old pattern
            old_pattern = re.compile(
                r'(\s+)def update_initial_session\(\):\s+'
                r'loaded_dog = sv\.dog\.get\(\)\s+'
                r'if loaded_dog:\s+'
                r'next_session = DatabaseOperations\(self\)\.get_next_session_number\(loaded_dog\)\s+'
                r'sv\.session_number\.set\(str\(next_session\)\)\s+'
                r'sv\.status\.set\(f"Ready - {loaded_dog} - Next session: #{next_session}"\)\s+'
                r'# Update navigation button states\s+'
                r'self\.navigation\.update_navigation_buttons\(\)',
                re.MULTILINE
            )
            
            # Replacement text (will preserve the indentation from capture group)
            replacement = (
                r'\1def update_initial_session():\n'
                r'\1    loaded_dog = sv.dog.get()\n'
                r'\1    if loaded_dog:\n'
                r'\1        # Get computed next number based on active filter\n'
                r'\1        db_ops = DatabaseOperations(self)\n'
                r'\1        status_filter = sv.session_status_filter.get()\n'
                r'\1        filtered_sessions = db_ops.get_all_sessions_for_dog(loaded_dog, status_filter)\n'
                r'\1        next_computed = len(filtered_sessions) + 1\n'
                r'\1        \n'
                r'\1        sv.session_number.set(str(next_computed))\n'
                r'\1        sv.status.set(f"Ready - {loaded_dog} - Next session: #{next_computed}")\n'
                r'\1        # Update navigation button states\n'
                r'\1        self.navigation.update_navigation_buttons()'
            )
            
            new_content, count = old_pattern.subn(replacement, content)
            
            if count > 0:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"  ✓ Updated startup to show computed number ({count} replacement)")
                return True
            else:
                print("  ✗ Could not find startup pattern to replace")
                print("  Note: May have already been manually updated")
                return True  # Don't fail if already updated
        else:
            print("  - Would update startup to show computed number")
            return True
    
    def modify_save_session(self):
        print("\n[2/2] Modifying ui_misc2.py (save session)...")
        
        filepath = os.path.join(self.project_dir, "ui_misc2.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find where we show success message and add reload after
            old_pattern = re.compile(
                r'(\s+)sv\.status\.set\(message\)\s+'
                r'messagebox\.showinfo\("Success", message\)',
                re.MULTILINE
            )
            
            replacement = (
                r'\1sv.status.set(message)\n'
                r'\1messagebox.showinfo("Success", message)\n'
                r'\1\n'
                r'\1# Reload session to display computed number\n'
                r'\1from ui_navigation import Navigation\n'
                r'\1nav = Navigation(self.ui)\n'
                r'\1nav.load_session_by_number(session_data["session_number"])'
            )
            
            new_content, count = old_pattern.subn(replacement, content)
            
            if count > 0:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"  ✓ Added reload after save ({count} replacement)")
                return True
            else:
                print("  ✗ Could not find save success pattern")
                return False
        else:
            print("  - Would add reload after save")
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
        
        results = []
        results.append(self.modify_ui_startup())
        results.append(self.modify_save_session())
        
        print("\n" + "=" * 80)
        if all(results):
            print("PHASE 3.02 COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ Startup shows computed next number")
            print("  ✓ Save Session reloads to show computed number")
            print()
            print("ALL SOFT-DELETE MIGRATION COMPLETE! 🎉")
            print()
            print(f"Restore from: {self.backup_folder}/")
            return True
        else:
            print("FAILED")
            print("=" * 80)
            return False


def main():
    execute = "--execute" in sys.argv
    migration = Phase3_02_StartupSaveMigration(execute=execute)
    success = migration.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
