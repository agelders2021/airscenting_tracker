#!/usr/bin/env python3
"""
About Dialog for Airscent Training Tracker
Copyright (C) 2024 Al Gelders

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import tkinter as tk
from tkinter import ttk
import webbrowser

class AboutDialog:
    """Display an About dialog with program information"""
    
    def __init__(self, parent, version="1.0"):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("About Airscent Training Tracker")
        self.dialog.resizable(False, False)
        
        # Set size
        width = 450
        height = 350
        
        # Center on parent window
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Create main frame
        frame = tk.Frame(self.dialog, bg='white', padx=20, pady=20)
        frame.pack(fill='both', expand=True)
        
        # Title
        title_label = tk.Label(
            frame,
            text="Airscent Training Tracker",
            font=('Arial', 16, 'bold'),
            bg='white',
            fg='#2c3e50'
        )
        title_label.pack(pady=(10, 5))
        
        # Version
        version_label = tk.Label(
            frame,
            text=f"Version {version}",
            font=('Arial', 10),
            bg='white',
            fg='#7f8c8d'
        )
        version_label.pack(pady=5)
        
        # Copyright
        copyright_label = tk.Label(
            frame,
            text="Copyright © 2024 Al Gelders",
            font=('Arial', 10),
            bg='white',
            fg='#34495e'
        )
        copyright_label.pack(pady=(20, 5))
        
        # License info
        license_text = (
            "This program is free software licensed under the\n"
            "GNU General Public License v3.0\n\n"
            "You are free to use, modify, and distribute this software\n"
            "under the terms of the GPL v3 license."
        )
        license_label = tk.Label(
            frame,
            text=license_text,
            font=('Arial', 9),
            bg='white',
            fg='#34495e',
            justify='center'
        )
        license_label.pack(pady=10)
        
        # GitHub link
        github_frame = tk.Frame(frame, bg='white')
        github_frame.pack(pady=15)
        
        github_label = tk.Label(
            github_frame,
            text="Project Repository:",
            font=('Arial', 9),
            bg='white',
            fg='#34495e'
        )
        github_label.pack()
        
        # Clickable GitHub URL
        github_url = "https://github.com/agelders2021/mantrailing_tracker"
        github_link = tk.Label(
            github_frame,
            text=github_url,
            font=('Arial', 9, 'underline'),
            bg='white',
            fg='#3498db',
            cursor='hand2'
        )
        github_link.pack()
        github_link.bind('<Button-1>', lambda e: webbrowser.open(github_url))
        
        # Close button
        close_button = ttk.Button(
            frame,
            text="Close",
            command=self.dialog.destroy,
            width=15
        )
        close_button.pack(pady=(20, 10))
        
        # Focus the close button
        close_button.focus_set()
        
        # Bind Escape key to close
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())

def show_about(parent, version="1.0"):
    """Convenience function to show the About dialog"""
    AboutDialog(parent, version)
