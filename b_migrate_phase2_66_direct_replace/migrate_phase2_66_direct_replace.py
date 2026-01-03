#!/usr/bin/env python3
"""
Phase 2.66 Migration: Display Computed Session Numbers (Direct Replacement)

Uses direct string replacement to ensure it works.

Changes:
1. After loading session, compute ordinal position and display it

Usage:
    python migrate_phase2_66_direct_replace.py          # Show what will be done
    python migrate_phase2_66_direct_replace.py --execute  # Execute the migration
"""

import sys
import shutil
import os


class Phase2_66_DirectReplaceMigration:
    """Phase 2.66: Display computed session numbers (direct replacement)"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_navigation.py": "Display computed session numbers"
        }
    
    def print_header(self):
        print("=" * 80)
        print("PHASE 2.66: DISPLAY COMPUTED SESSION NUMBERS (DIRECT REPLACE)")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def create_backup_folder(self):
        if not os.path.exists(self.backup_folder):
            os.makedirs(self.backup_folder)
            print(f"Created backup folder: {self.backup_folder}")
    
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
        print(f"  ✓ Backed up migration script")
    
    def modify_ui_navigation(self):
        print("\n[1/1] Modifying ui_navigation.py...")
        
        filepath = os.path.join(self.project_dir, "ui_navigation.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            # Read binary to preserve exact line endings
            with open(filepath, 'rb') as f:
                content = f.read()
            
            # Decode
            text = content.decode('utf-8')
            
            # The exact string to find (with proper indentation)
            old = '            sv.status.set(f"Loaded session #{session_number}")'
            
            new = '''            # Get session status and compute ordinal position
            session_status = db_ops.get_session_status(session_number, dog_name)
            status_filter = sv.session_status_filter.get()
            
            # Compute ordinal session number based on current filter
            computed_number = db_ops.compute_session_number(dog_name, session_dict["date"], status_filter)
            
            # Display computed number (not database session_number)
            sv.session_number.set(str(computed_number))
            
            # Update session frame title based on status
            self.update_session_frame_title(session_status)
            
            # Enable/disable delete/undelete buttons based on status
            if session_status == 'deleted':
                # Deleted session - disable Delete, enable Undelete
                if hasattr(self.ui, 'a_delete_undelete_frame'):
                    for child in self.ui.a_delete_undelete_frame.winfo_children():
                        button_text = child.cget('text')
                        if button_text == 'Delete':
                            child.config(state="disabled")
                        elif button_text == 'Undelete':
                            child.config(state="normal")
            else:
                # Active session - enable Delete, disable Undelete
                if hasattr(self.ui, 'a_delete_undelete_frame'):
                    for child in self.ui.a_delete_undelete_frame.winfo_children():
                        button_text = child.cget('text')
                        if button_text == 'Delete':
                            child.config(state="normal")
                        elif button_text == 'Undelete':
                            child.config(state="disabled")
            
            sv.status.set(f"Loaded session (computed #{computed_number})")'''
            
            if old in text:
                text = text.replace(old, new)
                
                # Write back as binary to preserve line endings
                with open(filepath, 'wb') as f:
                    f.write(text.encode('utf-8'))
                
                print("  ✓ Replaced status.set line with computed number logic")
                return True
            else:
                print("  ✗ Could not find the exact line to replace")
                # Show what we're searching for
                print(f"  Searching for: '{old}'")
                # Show what's near line 275
                lines = text.split('\n')
                if len(lines) > 275:
                    print(f"  Line 275 contains: '{lines[274].strip()}'")
                return False
        else:
            print("  - Would replace status.set line with computed number logic")
            return True
    
    def run(self):
        self.print_header()
        
        if not self.execute:
            print("DRY RUN - No changes made")
            print()
            print("To execute: python", os.path.basename(sys.argv[0]), "--execute")
            return True
        
        print("EXECUTING MIGRATION")
        print()
        
        response = input("Proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("\nCancelled.")
            return False
        
        print("\nProceeding...\n")
        
        self.backup_script()
        print()
        
        if self.modify_ui_navigation():
            print("\n" + "=" * 80)
            print("PHASE 2.66 COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print("\nSession numbers now display computed values!")
            print(f"\nRestore from: {self.backup_folder}/")
            return True
        else:
            print("\n" + "=" * 80)
            print("MIGRATION FAILED")
            print("=" * 80)
            return False


def main():
    execute = "--execute" in sys.argv
    migration = Phase2_66_DirectReplaceMigration(execute=execute)
    success = migration.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
