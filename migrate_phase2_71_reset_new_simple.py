#!/usr/bin/env python3
"""
Phase 2.71 Migration: Reset UI When Clicking New (Single Line Match)

Searches for just one unique line to avoid formatting issues.

Changes:
1. Update new_session() in ui_form_management.py to reset UI state

Usage:
    python migrate_phase2_71_reset_new_simple.py          # Show what will be done
    python migrate_phase2_71_reset_new_simple.py --execute  # Execute the migration
"""

import sys
import shutil
import os


class Phase2_71_ResetNewMigration:
    """Phase 2.71: Reset UI state when clicking New (simple match)"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_form_management.py": "Reset LabelFrame title and filter when clicking New"
        }
    
    def print_header(self):
        print("=" * 80)
        print("PHASE 2.71: RESET UI WHEN CLICKING NEW")
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
    
    def modify_ui_form_management(self):
        print("\n[1/1] Modifying ui_form_management.py...")
        
        filepath = os.path.join(self.project_dir, "ui_form_management.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'rb') as f:
                content = f.read().decode('utf-8')
            
            # Search for just the update navigation line in new_session context
            # We need to find it specifically in new_session, not elsewhere
            old_line = '        nav.update_navigation_buttons()'
            
            # Check if we're in the new_session method by looking for the preceding status.set
            if 'sv.status.set(f"New session #{next_session}")' in content:
                # Find the position of the new_session status line
                status_pos = content.find('sv.status.set(f"New session #{next_session}")')
                # Find the next occurrence of nav.update_navigation_buttons after it
                nav_pos = content.find(old_line, status_pos)
                
                if nav_pos > status_pos:
                    # Insert our new code before nav.update_navigation_buttons
                    new_code = '''        # Reset UI to active state
        sv.session_status_filter.set('active')  # Reset filter to active
        
        # Reset LabelFrame title to normal (not deleted)
        if hasattr(self.ui, 'a_session_frame'):
            self.ui.a_session_frame.config(
                text="Session Information",
                foreground="black",
                font=("TkDefaultFont", 9)
            )
        
        '''
                    
                    # Insert before the nav.update_navigation_buttons line
                    content = content[:nav_pos] + new_code + content[nav_pos:]
                    
                    with open(filepath, 'wb') as f:
                        f.write(content.encode('utf-8'))
                    
                    print("  ✓ Added UI reset code to new_session()")
                    return True
                else:
                    print("  ✗ Could not find nav.update_navigation_buttons after status.set")
                    return False
            else:
                print("  ✗ Could not find new_session method")
                return False
        else:
            print("  - Would add UI reset code to new_session()")
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
        
        if self.modify_ui_form_management():
            print("\n" + "=" * 80)
            print("PHASE 2.71 COMPLETED")
            print("=" * 80)
            print("\n✓ Clicking 'New' now resets filter to 'active'")
            print("✓ LabelFrame title resets to normal (black)")
            print(f"\nRestore from: {self.backup_folder}/")
            return True
        else:
            print("\n" + "=" * 80)
            print("FAILED")
            print("=" * 80)
            return False


def main():
    execute = "--execute" in sys.argv
    migration = Phase2_71_ResetNewMigration(execute=execute)
    success = migration.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
