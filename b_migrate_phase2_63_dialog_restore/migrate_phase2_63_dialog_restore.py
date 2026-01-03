#!/usr/bin/env python3
"""
Phase 2.63 Migration: Context-Aware Delete/Restore Button in Dialog

When viewing the Edit/Delete Prior Session dialog:
- If filter is "Active" or "Both" → "Delete Selected" button (marks as deleted)
- If filter is "Deleted" → "Restore Selected" button (marks as active)

Changes:
1. Update load_prior_session() to check filter and set button text/action accordingly

Usage:
    python migrate_phase2_63_dialog_restore.py          # Show what will be done
    python migrate_phase2_63_dialog_restore.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase2_63_DialogRestoreMigration:
    """Phase 2.63: Context-aware Delete/Restore button"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_navigation.py": "Update dialog button based on filter"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 2.63: CONTEXT-AWARE DELETE/RESTORE BUTTON")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        """Print what will be changed"""
        print("CHANGES TO BE MADE:")
        print()
        print("1. Update load_prior_session() dialog in ui_navigation.py:")
        print("   - Check current filter status")
        print("   - If 'Deleted': button says 'Restore Selected', undeletes sessions")
        print("   - If 'Active' or 'Both': button says 'Delete Selected', deletes sessions")
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
        """Update dialog button based on filter"""
        print("\n[1/1] Modifying ui_navigation.py...")
        
        filepath = os.path.join(self.project_dir, "ui_navigation.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find the on_delete_selected function definition
            old_delete_handler = '''        def on_delete_selected():
            selected_indices = listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one session to delete")
                return
            
            selected_nums = [session_numbers[i] for i in selected_indices]
            result = messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete {len(selected_nums)} session(s)?\\n\\n"
                f"Sessions: {', '.join(map(str, selected_nums))}\\n\\n"
                "This action cannot be undone!",
                icon='warning'
            )
            
            if result:
                self.delete_sessions(selected_nums)
                dialog.destroy()'''
            
            new_delete_handler = '''        def on_delete_selected():
            """Handle delete/restore based on current filter"""
            selected_indices = listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one session")
                return
            
            selected_nums = [session_numbers[i] for i in selected_indices]
            status_filter = sv.session_status_filter.get()
            
            if status_filter == 'deleted':
                # Restore sessions (undelete)
                result = messagebox.askyesno(
                    "Confirm Restore",
                    f"Restore {len(selected_nums)} session(s) to active?\\n\\n"
                    f"Sessions: {', '.join(map(str, selected_nums))}",
                    icon='question'
                )
                
                if result:
                    self.restore_sessions(selected_nums)
                    dialog.destroy()
            else:
                # Delete sessions (mark as deleted)
                result = messagebox.askyesno(
                    "Confirm Delete",
                    f"Mark {len(selected_nums)} session(s) as deleted?\\n\\n"
                    f"Sessions: {', '.join(map(str, selected_nums))}\\n\\n"
                    "This can be undone by restoring the sessions.",
                    icon='warning'
                )
                
                if result:
                    self.mark_sessions_deleted(selected_nums)
                    dialog.destroy()'''
            
            if old_delete_handler in content:
                content = content.replace(old_delete_handler, new_delete_handler)
                print("  ✓ Updated on_delete_selected handler")
            else:
                print("  ✗ Could not find on_delete_selected handler")
                return False
            
            # Update the button creation
            old_button = '''        tk.Button(button_frame, text="View Selected", command=on_view_selected,
                 bg="#4169E1", fg="white", width=15).pack(side="left", padx=5)
        tk.Button(button_frame, text="Delete Selected", command=on_delete_selected,
                 bg="#DC143C", fg="white", width=15).pack(side="left", padx=5)'''
            
            new_button = '''        tk.Button(button_frame, text="View Selected", command=on_view_selected,
                 bg="#4169E1", fg="white", width=15).pack(side="left", padx=5)
        
        # Context-aware button text based on filter
        status_filter = sv.session_status_filter.get()
        if status_filter == 'deleted':
            button_text = "Restore Selected"
            button_color = "#28a745"  # Green
        else:
            button_text = "Delete Selected"
            button_color = "#DC143C"  # Red
        
        tk.Button(button_frame, text=button_text, command=on_delete_selected,
                 bg=button_color, fg="white", width=15).pack(side="left", padx=5)'''
            
            if old_button in content:
                content = content.replace(old_button, new_button)
                print("  ✓ Updated button creation to be context-aware")
            else:
                print("  ✗ Could not find button creation code")
                return False
            
            # Add restore_sessions and mark_sessions_deleted methods at end of class
            old_end = '''    def on_status_filter_changed(self):
        """Called when status filter radio button changes"""
        from sv import sv
        status_filter = sv.session_status_filter.get()
        
        # If a session is currently loaded, reload it to recompute number
        if hasattr(self, 'current_db_session_number') and self.current_db_session_number:
            self.load_session_by_number(self.current_db_session_number)
        else:
            sv.status.set(f"Filter: {status_filter}")
            self.update_navigation_buttons()'''
            
            new_end = '''    def restore_sessions(self, session_numbers):
        """Restore (undelete) multiple sessions"""
        from sv import sv
        from ui_database import DatabaseOperations
        from ui_form_management import FormManagement
        
        dog_name = sv.dog.get()
        db_ops = DatabaseOperations(self.ui)
        
        success_count = 0
        for session_num in session_numbers:
            if db_ops.update_session_status(session_num, dog_name, 'active'):
                success_count += 1
        
        if success_count > 0:
            messagebox.showinfo("Success", f"Restored {success_count} session(s) to active")
            
            # Reset to new session
            self.ui.selected_sessions = []
            self.ui.selected_sessions_index = -1
            form_mgmt = FormManagement(self.ui)
            form_mgmt.new_session()
    
    def mark_sessions_deleted(self, session_numbers):
        """Mark multiple sessions as deleted (soft delete)"""
        from sv import sv
        from ui_database import DatabaseOperations
        from ui_form_management import FormManagement
        
        dog_name = sv.dog.get()
        db_ops = DatabaseOperations(self.ui)
        
        success_count = 0
        for session_num in session_numbers:
            if db_ops.update_session_status(session_num, dog_name, 'deleted'):
                success_count += 1
        
        if success_count > 0:
            messagebox.showinfo("Success", f"Marked {success_count} session(s) as deleted")
            
            # Reset to new session
            self.ui.selected_sessions = []
            self.ui.selected_sessions_index = -1
            form_mgmt = FormManagement(self.ui)
            form_mgmt.new_session()
    
    def on_status_filter_changed(self):
        """Called when status filter radio button changes"""
        from sv import sv
        status_filter = sv.session_status_filter.get()
        
        # If a session is currently loaded, reload it to recompute number
        if hasattr(self, 'current_db_session_number') and self.current_db_session_number:
            self.load_session_by_number(self.current_db_session_number)
        else:
            sv.status.set(f"Filter: {status_filter}")
            self.update_navigation_buttons()'''
            
            if old_end in content:
                content = content.replace(old_end, new_end)
                print("  ✓ Added restore_sessions() method")
                print("  ✓ Added mark_sessions_deleted() method")
            else:
                print("  ✗ Could not find insertion point for new methods")
                return False
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        else:
            print("  - Would update on_delete_selected handler")
            print("  - Would make button context-aware")
            print("  - Would add restore_sessions() method")
            print("  - Would add mark_sessions_deleted() method")
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
            print("PHASE 2.63 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ Delete button is now context-aware")
            print("  ✓ When filter = 'Deleted': button says 'Restore Selected' (green)")
            print("  ✓ When filter = 'Active/Both': button says 'Delete Selected' (red)")
            print("  ✓ Added restore_sessions() method")
            print("  ✓ Added mark_sessions_deleted() method")
            print("  ✓ Migration script backed up")
            print()
            print("TEST IT:")
            print("  1. Set filter to 'Active', click Edit/Delete → 'Delete Selected' (red)")
            print("  2. Set filter to 'Deleted', click Edit/Delete → 'Restore Selected' (green)")
            print("  3. Select and restore/delete sessions")
            print()
            print(f"RESTORE: If needed, copy files from {self.backup_folder}/")
            print()
            return True
        else:
            print("MIGRATION FAILED")
            print("=" * 80)
            print()
            print("Some patterns not found.")
            print(f"Original files preserved in: {self.backup_folder}/")
            print()
            return False


def main():
    """Main entry point"""
    execute = "--execute" in sys.argv
    
    migration = Phase2_63_DialogRestoreMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
