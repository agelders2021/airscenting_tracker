#!/usr/bin/env python3
"""
Phase 2.65 Migration: Display Computed Session Numbers (Handle Line Endings)

This ensures the session number displayed on screen is the computed ordinal
position, not the database session_number value. Handles Windows line endings.

Changes:
1. After loading session, compute ordinal position and display it
2. Update session frame title based on status
3. Set button states based on status

Usage:
    python migrate_phase2_65_display_computed_fixed.py          # Show what will be done
    python migrate_phase2_65_display_computed_fixed.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase2_65_DisplayComputedMigration:
    """Phase 2.65: Display computed session numbers (handle line endings)"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_navigation.py": "Display computed session numbers instead of database numbers"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 2.65: DISPLAY COMPUTED SESSION NUMBERS")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        """Print what will be changed"""
        print("CHANGES TO BE MADE:")
        print()
        print("1. Update load_session_by_number() to display computed numbers:")
        print("   - Get session status from database")
        print("   - Compute ordinal position based on current filter")
        print("   - Display computed number (not database session_number)")
        print("   - Update frame title based on status")
        print("   - Enable/disable buttons based on status")
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
            print(f"         Migration script will also be copied to {self.backup_folder}/")
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
    
    def backup_script(self):
        """Copy this migration script to backup folder"""
        self.create_backup_folder()
        script_path = os.path.abspath(sys.argv[0])
        script_name = os.path.basename(script_path)
        backup_path = os.path.join(self.backup_folder, script_name)
        shutil.copy2(script_path, backup_path)
        print(f"  ✓ Backed up migration script: {script_name} -> {self.backup_folder}/{script_name}")
    
    def modify_ui_navigation(self):
        """Update load_session_by_number to display computed numbers"""
        print("\n[1/1] Modifying ui_navigation.py...")
        
        filepath = os.path.join(self.project_dir, "ui_navigation.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            # Read with universal newlines to handle both \n and \r\n
            with open(filepath, 'r', encoding='utf-8', newline=None) as f:
                content = f.read()
            
            # Search for the pattern - strip to ignore whitespace differences
            old_line = 'sv.status.set(f"Loaded session #{session_number}")'
            
            if old_line in content:
                # Find the line with proper indentation
                lines = content.split('\n')
                found_index = -1
                
                for i, line in enumerate(lines):
                    if old_line in line:
                        found_index = i
                        # Get the indentation
                        indent = line[:len(line) - len(line.lstrip())]
                        break
                
                if found_index >= 0:
                    # Build the replacement
                    new_lines = [
                        f'{indent}# Get session status and compute ordinal position',
                        f'{indent}session_status = db_ops.get_session_status(session_number, dog_name)',
                        f'{indent}status_filter = sv.session_status_filter.get()',
                        f'{indent}',
                        f'{indent}# Compute ordinal session number based on current filter',
                        f'{indent}computed_number = db_ops.compute_session_number(dog_name, session_dict["date"], status_filter)',
                        f'{indent}',
                        f'{indent}# Display computed number (not database session_number)',
                        f'{indent}sv.session_number.set(str(computed_number))',
                        f'{indent}',
                        f'{indent}# Update session frame title based on status',
                        f'{indent}self.update_session_frame_title(session_status)',
                        f'{indent}',
                        f'{indent}# Enable/disable delete/undelete buttons based on status',
                        f'{indent}if session_status == \'deleted\':',
                        f'{indent}    # Deleted session - disable Delete, enable Undelete',
                        f'{indent}    if hasattr(self.ui, \'a_delete_undelete_frame\'):',
                        f'{indent}        for child in self.ui.a_delete_undelete_frame.winfo_children():',
                        f'{indent}            button_text = child.cget(\'text\')',
                        f'{indent}            if button_text == \'Delete\':',
                        f'{indent}                child.config(state="disabled")',
                        f'{indent}            elif button_text == \'Undelete\':',
                        f'{indent}                child.config(state="normal")',
                        f'{indent}else:',
                        f'{indent}    # Active session - enable Delete, disable Undelete',
                        f'{indent}    if hasattr(self.ui, \'a_delete_undelete_frame\'):',
                        f'{indent}        for child in self.ui.a_delete_undelete_frame.winfo_children():',
                        f'{indent}            button_text = child.cget(\'text\')',
                        f'{indent}            if button_text == \'Delete\':',
                        f'{indent}                child.config(state="normal")',
                        f'{indent}            elif button_text == \'Undelete\':',
                        f'{indent}                child.config(state="disabled")',
                        f'{indent}',
                        f'{indent}sv.status.set(f"Loaded session (computed #{computed_number})")'
                    ]
                    
                    # Replace the line
                    lines[found_index] = '\n'.join(new_lines)
                    
                    # Write back with Windows line endings
                    with open(filepath, 'w', encoding='utf-8', newline='\r\n') as f:
                        f.write('\n'.join(lines))
                    
                    print("  ✓ Updated load_session_by_number() to display computed numbers")
                    return True
                else:
                    print("  ✗ Found pattern but couldn't locate line index")
                    return False
            else:
                print("  ✗ Could not find the status.set line to replace")
                print(f"  Searched for: {old_line}")
                return False
        else:
            print("  - Would update load_session_by_number() to display computed numbers")
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
        
        # Backup the migration script itself first
        self.backup_script()
        print()
        
        results = []
        results.append(self.modify_ui_navigation())
        
        print("\n" + "=" * 80)
        if all(results):
            print("PHASE 2.65 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ Sessions now display computed ordinal numbers")
            print("  ✓ Numbers update based on current filter")
            print("  ✓ Frame title updates based on status")
            print("  ✓ Buttons enable/disable based on status")
            print("  ✓ Migration script backed up")
            print()
            print("PHASE 2 IS NOW COMPLETE!")
            print()
            print("TEST IT:")
            print("  1. Load a session - see computed number (not DB number)")
            print("  2. Change filter - number recomputes")
            print("  3. Click Previous/Next - navigates filtered list with computed numbers")
            print()
            print(f"RESTORE: If needed, copy files from {self.backup_folder}/")
            print()
            return True
        else:
            print("MIGRATION FAILED")
            print("=" * 80)
            print()
            print("Pattern not found.")
            print(f"Original files preserved in: {self.backup_folder}/")
            print()
            return False


def main():
    """Main entry point"""
    execute = "--execute" in sys.argv
    
    migration = Phase2_65_DisplayComputedMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
