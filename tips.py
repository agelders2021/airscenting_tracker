"""
Tooltip utility for tkinter widgets
"""
import tkinter as tk
from tkinter import ttk


class ToolTip:
    """Create a tooltip for a widget with configurable delay"""
    def __init__(self, widget, text, delay=750):
        self.widget = widget
        self.text = text
        self.delay = delay  # Delay in milliseconds
        self.tooltip = None
        self.timer = None
        
        widget.bind("<Enter>", self.schedule_show)
        widget.bind("<Leave>", self.hide)
        widget.bind("<Button>", self.hide)  # Hide on click
    
    def schedule_show(self, event=None):
        """Schedule tooltip to show after delay"""
        self.hide()  # Cancel any existing tooltip
        self.timer = self.widget.after(self.delay, self.show)
    
    def show(self):
        """Display the tooltip"""
        if self.tooltip:
            return
        
        # Get widget position
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        # Create tooltip window
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        # Create label with tooltip text
        label = tk.Label(self.tooltip, text=self.text, 
                        background="#ffffe0", 
                        foreground="black",
                        relief="solid", 
                        borderwidth=1, 
                        font=("Arial", 9),
                        padx=8, 
                        pady=5)
        label.pack()
    
    def hide(self, event=None):
        """Hide the tooltip"""
        # Cancel scheduled show
        if self.timer:
            self.widget.after_cancel(self.timer)
            self.timer = None
        
        # Destroy tooltip window
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class ConditionalToolTip(ToolTip):
    """Tooltip that only shows when widget is in a specific state"""
    def __init__(self, widget, text, show_when_disabled=False, delay=750):
        self.show_when_disabled = show_when_disabled
        super().__init__(widget, text, delay)
    
    def show(self):
        """Display tooltip only if condition is met"""
        # Check if widget is a ttk.Combobox and get its state
        if isinstance(self.widget, ttk.Combobox):
            widget_state = str(self.widget['state'])
            is_disabled = widget_state == 'disabled'
            
            # Only show if condition matches
            if self.show_when_disabled and not is_disabled:
                return  # Don't show if we want disabled but it's not
            elif not self.show_when_disabled and is_disabled:
                return  # Don't show if we don't want disabled but it is
        
        # Call parent show method
        super().show()

