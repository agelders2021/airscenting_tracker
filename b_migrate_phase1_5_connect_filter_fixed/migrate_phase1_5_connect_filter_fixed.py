#!/usr/bin/env python3
"""
Phase 1.5 Migration: Connect Status Filter to Session Loading (CORRECTED)

This script connects the radio buttons to actual filtering:

1. Update get_all_sessions_for_dog() wrapper in ui_database.py to accept status_filter
2. Update load_prior_session() in ui_navigation.py to pass status_filter
3. Add command to radio buttons to refresh when filter changes

This makes the filter actually work!

Usage:
    python migrate_phase1_5_connect_filter_fixed.py          # Show what will be done
    python migrate_phase1_5_connect_filter_fixed.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase1_5_ConnectFilterMigration:
    """Phase 1.5: Connect filter to session loading"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_database.py": "Update get_all_sessions_for_dog wrapper to accept status_filter",
            "ui_navigation.py": "Pass status_filter when loading sessions",
            "ui.py": "Add command to radio buttons to trigger refresh"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 1.5: CONNECT STATUS FILTER (CORRECTED)")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        """Print what will be changed"""
        print("CHANGES TO BE MADE:")
        print()
        print("1. Update get_all_sessions_for_dog() wrapper in ui_database.py:")
        print("   - Add status_filter parameter")
        print("   - Pass it through to self.db_manager.get_sessions_for_dog()")
        print()
        print("2. Update load_prior_session() in ui_navigation.py:")
        print("   - Pass sv.session_status_filter.get() to get_all_sessions_for_dog()")
        print()
        print("3. Add filter change handler in ui_navigation.py:")
        print("   - Add on_status_filter_changed() method")
        print()
        print("4. Connect radio buttons in ui.py:")
        print("   - Add command=self.navigation.on_status_filter_changed")
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
        """Update ui_database.py wrapper method"""
        print("\n[1/3] Modifying ui_database.py...")
        
        filepath = os.path.join(self.project_dir, "ui_database.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update get_all_sessions_for_dog wrapper to accept and pass status_filter
            old_wrapper = '''    def get_all_sessions_for_dog(self, dog_name):
        """Get all sessions for a dog (returns list of tuples)"""
        return self.db_manager.get_sessions_for_dog(dog_name)'''
            
            new_wrapper = '''    def get_all_sessions_for_dog(self, dog_name, status_filter='active'):
        """Get all sessions for a dog filtered by status (returns list of tuples)"""
        return self.db_manager.get_sessions_for_dog(dog_name, status_filter)'''
            
            if old_wrapper in content:
                content = content.replace(old_wrapper, new_wrapper)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Updated get_all_sessions_for_dog() wrapper")
                return True
            else:
                print("  ✗ Could not find get_all_sessions_for_dog() wrapper pattern")
                return False
        else:
            print("  - Would update get_all_sessions_for_dog() wrapper to accept status_filter")
            return True
    
    def modify_ui_navigation(self):
        """Update ui_navigation.py to pass status filter"""
        print("\n[2/3] Modifying ui_navigation.py...")
        
        filepath = os.path.join(self.project_dir, "ui_navigation.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            success = True
            
            # Update load_prior_session to pass status filter
            old_load_prior = '''        db_ops = DatabaseOperations(self.ui)
        sessions = db_ops.get_all_sessions_for_dog(dog_name)'''
            
            new_load_prior = '''        db_ops = DatabaseOperations(self.ui)
        status_filter = sv.session_status_filter.get()
        sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter)'''
            
            if old_load_prior in content:
                content = content.replace(old_load_prior, new_load_prior)
                print("  ✓ Updated load_prior_session() to pass status_filter")
            else:
                print("  ✗ Could not find load_prior_session() pattern")
                success = False
            
            # Add on_status_filter_changed method
            insertion_point = "    def delete_sessions(self, session_numbers):"
            
            new_method = '''    def on_status_filter_changed(self):
        """Handle status filter radio button change - update status bar"""
        from sv import sv
        
        # Get current filter
        status_filter = sv.session_status_filter.get()
        
        # Update status bar
        filter_label = {"active": "Active", "deleted": "Deleted", "both": "All"}[status_filter]
        dog_name = sv.dog.get()
        if dog_name:
            sv.status.set(f"Filter: {filter_label} sessions for {dog_name}")
        else:
            sv.status.set(f"Filter: {filter_label}")
    
    '''
            
            if insertion_point in content:
                content = content.replace(insertion_point, new_method + insertion_point)
                print("  ✓ Added on_status_filter_changed() method")
            else:
                print("  ✗ Could not find insertion point for on_status_filter_changed()")
                success = False
            
            if success:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return success
        else:
            print("  - Would update load_prior_session() to pass status_filter")
            print("  - Would add on_status_filter_changed() method")
            return True
    
    def modify_ui(self):
        """Update ui.py to connect radio buttons"""
        print("\n[3/3] Modifying ui.py...")
        
        filepath = os.path.join(self.project_dir, "ui.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update radio buttons to add command
            old_radio_buttons = '''        tk.Label(status_filter_frame, text="Show Sessions:").pack(side="left", padx=(0, 10))
        tk.Radiobutton(status_filter_frame, text="Active", variable=sv.session_status_filter, 
                      value="active").pack(side="left", padx=5)
        tk.Radiobutton(status_filter_frame, text="Deleted", variable=sv.session_status_filter, 
                      value="deleted").pack(side="left", padx=5)
        tk.Radiobutton(status_filter_frame, text="Both", variable=sv.session_status_filter, 
                      value="both").pack(side="left", padx=5)'''
            
            new_radio_buttons = '''        tk.Label(status_filter_frame, text="Show Sessions:").pack(side="left", padx=(0, 10))
        tk.Radiobutton(status_filter_frame, text="Active", variable=sv.session_status_filter, 
                      value="active", command=self.navigation.on_status_filter_changed).pack(side="left", padx=5)
        tk.Radiobutton(status_filter_frame, text="Deleted", variable=sv.session_status_filter, 
                      value="deleted", command=self.navigation.on_status_filter_changed).pack(side="left", padx=5)
        tk.Radiobutton(status_filter_frame, text="Both", variable=sv.session_status_filter, 
                      value="both", command=self.navigation.on_status_filter_changed).pack(side="left", padx=5)'''
            
            if old_radio_buttons in content:
                content = content.replace(old_radio_buttons, new_radio_buttons)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Connected radio buttons to on_status_filter_changed()")
                return True
            else:
                print("  ✗ Could not find radio buttons pattern")
                return False
        else:
            print("  - Would add command to radio buttons")
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
        results.append(self.modify_ui_navigation())
        results.append(self.modify_ui())
        
        print("\n" + "=" * 80)
        if all(results):
            print("PHASE 1.5 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ get_all_sessions_for_dog() wrapper accepts status_filter")
            print("  ✓ load_prior_session() passes status_filter")
            print("  ✓ Radio buttons connected to on_status_filter_changed()")
            print()
            print("TEST IT:")
            print("  1. Start the application")
            print("  2. Click 'Edit/Delete Prior Session'")
            print("  3. Select 'Active' - only active sessions should show")
            print("  4. Select 'Deleted' - only deleted sessions should show")
            print("  5. Select 'Both' - all sessions should show")
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
    
    migration = Phase1_5_ConnectFilterMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
