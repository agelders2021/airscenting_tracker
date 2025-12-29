"""
Working Dialog for Air-Scenting Logger
Modal dialog that displays "Working, please wait" during long operations
"""
import tkinter as tk
from tkinter import ttk


class WorkingDialog:
    """
    Modal dialog that displays while a long operation is running.
    Prevents user interaction with main window until operation completes.
    """
    
    def __init__(self, parent, title="Working", message="Please wait..."):
        """
        Create a working dialog
        
        Args:
            parent: Parent window
            title: Dialog title
            message: Message to display
        """
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        
        # Make it modal (blocks parent window)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Remove window decorations (minimize, maximize, close buttons)
        # User must wait for operation to complete
        self.dialog.overrideredirect(False)  # Keep title bar but disable close
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: None)  # Disable close button
        
        # Set size
        width = 400
        height = 150
        
        # Center on parent window
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        self.dialog.resizable(False, False)
        
        # Create frame
        frame = tk.Frame(self.dialog, bg='white', padx=20, pady=20)
        frame.pack(fill='both', expand=True)
        
        # Message label
        self.message_label = tk.Label(
            frame,
            text=message,
            font=('Arial', 12),
            bg='white',
            fg='#2c3e50'
        )
        self.message_label.pack(pady=(10, 20))
        
        # Progress bar (indeterminate mode - animated)
        self.progress = ttk.Progressbar(
            frame,
            mode='indeterminate',
            length=300
        )
        self.progress.pack(pady=10)
        self.progress.start(10)  # Animate the progress bar
        
        # Status label (optional, for detailed status)
        self.status_label = tk.Label(
            frame,
            text="",
            font=('Arial', 9, 'italic'),
            bg='white',
            fg='#7f8c8d'
        )
        self.status_label.pack(pady=(5, 0))
        
        # Flag to track if dialog is still open
        self.is_open = True
        
        # Start aggressive update loop to keep progress bar animating
        # Uses update_idletasks() which is lighter than full update()
        self.schedule_fast_update()
        
        # Update the display
        self.dialog.update()
    
    def schedule_fast_update(self):
        """Schedule very frequent updates to keep progress bar animating during blocking operations"""
        if self.is_open:
            try:
                # Use update_idletasks() - processes widget updates without processing events
                # This is lighter and can run even during blocking operations
                self.dialog.update_idletasks()
            except:
                pass  # Dialog might be closing
            # Schedule next update in 20ms (50 fps) for smooth animation
            self.dialog.after(20, self.schedule_fast_update)
    
    def update_message(self, message):
        """Update the message displayed in the dialog"""
        self.message_label.config(text=message)
        self.dialog.update()
    
    def update_status(self, status):
        """Update the status text (smaller text below progress bar)"""
        self.status_label.config(text=status)
        self.dialog.update()
    
    def close(self, delay_ms=200):
        """
        Close the working dialog
        
        Args:
            delay_ms: Delay in milliseconds before closing (default 200ms)
                     This ensures UI has time to fully update before dialog closes
        """
        # Stop the update loop
        self.is_open = False
        
        def _do_close():
            try:
                self.progress.stop()
                self.dialog.grab_release()
                self.dialog.destroy()
            except:
                pass
        
        if delay_ms > 0:
            # Schedule close after delay to ensure UI is responsive
            self.dialog.after(delay_ms, _do_close)
        else:
            # Close immediately
            _do_close()


class WorkingOperation:
    """
    Context manager for running long operations with a working dialog.
    
    Usage:
        with WorkingOperation(self.root, "Connecting to database..."):
            # Your long operation here
            result = connect_to_database()
    """
    
    def __init__(self, parent, message="Please wait...", title="Working"):
        self.parent = parent
        self.message = message
        self.title = title
        self.dialog = None
    
    def __enter__(self):
        self.dialog = WorkingDialog(self.parent, self.title, self.message)
        return self.dialog
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.dialog:
            self.dialog.close()
        return False  # Don't suppress exceptions


def run_with_working_dialog(parent, operation_func, message="Please wait...", 
                            title="Working", on_complete=None, on_error=None):
    """
    Run a long operation with a working dialog.
    Uses threading to keep UI responsive.
    
    Args:
        parent: Parent window
        operation_func: Function to run (should return a result or None)
        message: Message to display
        title: Dialog title
        on_complete: Callback when operation completes successfully (receives result)
        on_error: Callback when operation fails (receives exception)
    
    Example:
        def save_to_db():
            # Long operation
            return result
        
        def on_done(result):
            messagebox.showinfo("Success", f"Saved: {result}")
        
        run_with_working_dialog(
            self.root,
            save_to_db,
            "Saving to database...",
            on_complete=on_done
        )
    """
    import threading
    
    dialog = WorkingDialog(parent, title, message)
    result = None
    error = None
    
    def run_operation():
        nonlocal result, error
        try:
            result = operation_func()
        except Exception as e:
            error = e
        finally:
            # Close dialog on UI thread
            parent.after(100, finish_operation)
    
    def finish_operation():
        dialog.close()
        
        if error:
            if on_error:
                on_error(error)
        else:
            if on_complete:
                on_complete(result)
    
    # Start operation in background thread
    thread = threading.Thread(target=run_operation, daemon=True)
    thread.start()
