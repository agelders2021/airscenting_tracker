#!/usr/bin/env python3
"""
Phase 1.75 Migration: Make Previous/Next Buttons Respect Filter

This script updates the Previous/Next navigation buttons to respect the status filter
even when not using "View Selected" mode.

Changes:
1. Update navigate_previous_session() to navigate through filtered sessions
2. Update navigate_next_session() to navigate through filtered sessions  
3. Update update_navigation_buttons() to check filtered session list

Usage:
    python migrate_phase1_75_nav_filter.py          # Show what will be done
    python migrate_phase1_75_nav_filter.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase1_75_NavFilterMigration:
    """Phase 1.75: Make navigation buttons respect status filter"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_navigation.py": "Update Previous/Next navigation to use filtered sessions"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 1.75: NAVIGATION BUTTONS RESPECT FILTER")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        """Print what will be changed"""
        print("CHANGES TO BE MADE:")
        print()
        print("1. Update navigate_previous_session():")
        print("   - In normal mode, get filtered sessions for current dog")
        print("   - Navigate to previous session in filtered list")
        print()
        print("2. Update navigate_next_session():")
        print("   - In normal mode, get filtered sessions for current dog")
        print("   - Navigate to next session in filtered list")
        print()
        print("3. Update update_navigation_buttons():")
        print("   - Check if previous/next exist in filtered list")
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
    
    def modify_ui_navigation(self):
        """Update ui_navigation.py navigation methods"""
        print("\n[1/1] Modifying ui_navigation.py...")
        
        filepath = os.path.join(self.project_dir, "ui_navigation.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            success = True
            
            # 1. Update navigate_previous_session normal mode
            old_prev = '''        else:
            # Normal navigation - just decrement
            try:
                current = int(sv.session_number.get())
                if current > 1:
                    sv.session_number.set(str(current - 1))
                    self.load_session_by_number(current - 1)
                    self.update_navigation_buttons()
            except ValueError:
                pass'''
            
            new_prev = '''        else:
            # Normal navigation - navigate through filtered sessions
            try:
                current = int(sv.session_number.get())
                dog_name = sv.dog.get()
                
                if not dog_name:
                    return
                
                # Get filtered sessions for current dog
                db_ops = DatabaseOperations(self.ui)
                status_filter = sv.session_status_filter.get()
                sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter)
                
                if not sessions:
                    return
                
                # Extract session numbers from the list of tuples
                session_numbers = [s[0] for s in sessions]
                
                # Find current session in the list
                if current in session_numbers:
                    current_index = session_numbers.index(current)
                    if current_index > 0:  # Can go previous
                        prev_session = session_numbers[current_index - 1]
                        sv.session_number.set(str(prev_session))
                        self.load_session_by_number(prev_session)
                        self.update_navigation_buttons()
                
            except ValueError:
                pass'''
            
            if old_prev in content:
                content = content.replace(old_prev, new_prev)
                print("  ✓ Updated navigate_previous_session() to use filtered sessions")
            else:
                print("  ✗ Could not find navigate_previous_session() normal mode pattern")
                success = False
            
            # 2. Update navigate_next_session normal mode
            old_next = '''        else:
            # Normal navigation - just increment
            try:
                current = int(sv.session_number.get())
                db_ops = DatabaseOperations(self.ui)
                max_session = db_ops.get_next_session_number() - 1
                if current < max_session + 1:
                    sv.session_number.set(str(current + 1))
                    self.load_session_by_number(current + 1)
                    self.update_navigation_buttons()
            except ValueError:
                pass'''
            
            new_next = '''        else:
            # Normal navigation - navigate through filtered sessions
            try:
                current = int(sv.session_number.get())
                dog_name = sv.dog.get()
                
                if not dog_name:
                    return
                
                # Get filtered sessions for current dog
                db_ops = DatabaseOperations(self.ui)
                status_filter = sv.session_status_filter.get()
                sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter)
                
                if not sessions:
                    return
                
                # Extract session numbers from the list of tuples
                session_numbers = [s[0] for s in sessions]
                
                # Find current session in the list
                if current in session_numbers:
                    current_index = session_numbers.index(current)
                    if current_index < len(session_numbers) - 1:  # Can go next
                        next_session = session_numbers[current_index + 1]
                        sv.session_number.set(str(next_session))
                        self.load_session_by_number(next_session)
                        self.update_navigation_buttons()
                
            except ValueError:
                pass'''
            
            if old_next in content:
                content = content.replace(old_next, new_next)
                print("  ✓ Updated navigate_next_session() to use filtered sessions")
            else:
                print("  ✗ Could not find navigate_next_session() normal mode pattern")
                success = False
            
            # 3. Update update_navigation_buttons normal mode
            old_update = '''        else:
            # Normal mode - use session number
            try:
                current_session = int(sv.session_number.get())
                db_ops = DatabaseOperations(self.ui)
                max_session = db_ops.get_next_session_number() - 1
                
                # Enable Previous if session > 1
                if current_session > 1:
                    self.ui.a_prev_session_btn.config(state="normal")
                else:
                    self.ui.a_prev_session_btn.config(state="disabled")
                
                # Enable Next if session < max + 1
                if current_session < max_session + 1:
                    self.ui.a_next_session_btn.config(state="normal")
                else:
                    self.ui.a_next_session_btn.config(state="disabled")
                    
            except ValueError:
                self.ui.a_prev_session_btn.config(state="disabled")
                self.ui.a_next_session_btn.config(state="disabled")'''
            
            new_update = '''        else:
            # Normal mode - check filtered session list
            try:
                current_session = int(sv.session_number.get())
                dog_name = sv.dog.get()
                
                if not dog_name:
                    self.ui.a_prev_session_btn.config(state="disabled")
                    self.ui.a_next_session_btn.config(state="disabled")
                    return
                
                # Get filtered sessions for current dog
                db_ops = DatabaseOperations(self.ui)
                status_filter = sv.session_status_filter.get()
                sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter)
                
                if not sessions:
                    self.ui.a_prev_session_btn.config(state="disabled")
                    self.ui.a_next_session_btn.config(state="disabled")
                    return
                
                # Extract session numbers
                session_numbers = [s[0] for s in sessions]
                
                # Check if current session is in filtered list
                if current_session in session_numbers:
                    current_index = session_numbers.index(current_session)
                    
                    # Enable Previous if not at first filtered session
                    if current_index > 0:
                        self.ui.a_prev_session_btn.config(state="normal")
                    else:
                        self.ui.a_prev_session_btn.config(state="disabled")
                    
                    # Enable Next if not at last filtered session
                    if current_index < len(session_numbers) - 1:
                        self.ui.a_next_session_btn.config(state="normal")
                    else:
                        self.ui.a_next_session_btn.config(state="disabled")
                else:
                    # Current session not in filtered list - disable both
                    self.ui.a_prev_session_btn.config(state="disabled")
                    self.ui.a_next_session_btn.config(state="disabled")
                    
            except ValueError:
                self.ui.a_prev_session_btn.config(state="disabled")
                self.ui.a_next_session_btn.config(state="disabled")'''
            
            if old_update in content:
                content = content.replace(old_update, new_update)
                print("  ✓ Updated update_navigation_buttons() to use filtered sessions")
            else:
                print("  ✗ Could not find update_navigation_buttons() normal mode pattern")
                success = False
            
            if success:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return success
        else:
            print("  - Would update navigate_previous_session() to use filtered sessions")
            print("  - Would update navigate_next_session() to use filtered sessions")
            print("  - Would update update_navigation_buttons() to use filtered sessions")
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
        results.append(self.modify_ui_navigation())
        
        print("\n" + "=" * 80)
        if all(results):
            print("PHASE 1.75 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ Previous/Next buttons now navigate through filtered sessions")
            print("  ✓ Buttons disabled if no previous/next in filtered list")
            print()
            print("TEST IT:")
            print("  1. Load a session")
            print("  2. Select 'Active' filter - Previous/Next should only show active")
            print("  3. Select 'Deleted' filter - Previous/Next should only show deleted")
            print("  4. Select 'Both' - Previous/Next should show all sessions")
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
    
    migration = Phase1_75_NavFilterMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
