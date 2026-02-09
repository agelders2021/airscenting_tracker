"""
SPDX-License-Identifier: GPL-3.0-or-later

Copyright (C) 2026 Al Gelders

This file is part of the SAR Dog Training Logger

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

"""
Help Window - User Manual Display
Displays the SAR K9 Training Record User Manual in a readonly text window.
Accessible via F1 key.
"""

import tkinter as tk
from tkinter import scrolledtext

USER_MANUAL_TEXT = """SAR K9 Training Record

Preface: This is a preliminary help file to get the user started. This window can always be viewed by pushing F1 on your keyboard.

Chapter 1 – Setup

1. Select the primary storage folder. The database and configuration files are saved here. Browse to the location you wish to save this data. On a modern Windows machine placing the folder either on a path included in Microsoft OneDrive or a Dropbox folder is recommended. Then, in the event of a hardware failure, the training log can be recovered as soon as the hardware is repaired.

2. Click on 'Initialize Data Structures' which creates an empty database.

3. Select a backup folder. While optional, it is STRONGLY recommended to configure this. Ideally, this folder should reside on an external hard drive or another service such as Google Drive. This additional redundancy helps ensure that data is never lost.

4. Configure a PDF export folder. This folder is used to export human readable logs suitable for certification or legal requirements.

5. Now enter training locations that will be used repeatedly. While not required, this shortcut will simplify data entry later. To enter a location, either type in the name followed by 'Enter' or click the 'Add Location' button.

6. Dog names are entered in an identical manner. Unlike location names, however, all dogs that are to be recorded must be entered here.

7. Terrain Types and Distraction types are entered in a similar manner. The user can adjust the order they appear in the table as desired. The most commonly used entries should usually appear at the top of each list.

8. Now click 'Save Configuration' then exit the program (using the \N{Negative Squared Cross Mark} at the upper right corner of the window).

Chapter 2 – Usage

1. Restart the application and select either the 'Area Search Session Tab' or 'Trailing Session Tab' as needed.

2. Notice that some fields have white backgrounds while others are light-grey. White fields can always have free text entered while light grey windows must use the dropdown by clicking the \N{Modifier Letter Down Arrowhead} on the right side of the entry. A few of the white entry fields also have a \N{Modifier Letter Down Arrowhead} which for common entries.

3. Start Time and Finish Time entries are unique – hover the mouse over the left half and rotate the mouse scroll wheel to change the hour. Hover over the right side to adjust the minutes. The time is recorded in 24-hour Military time to avoid confusion.
"""


class HelpWindow:
    """
    Display the user manual in a readonly text window.
    """
    
    def __init__(self, parent):
        """
        Initialize the help window.
        
        Args:
            parent: Parent tkinter window
        """
        self.parent = parent
        self.window = None
    
    def show(self):
        """Show the help window (or bring existing window to front)"""
        # If window already exists, just bring it to front
        if self.window and tk.Winfo.exists(self.window):
            self.window.lift()
            self.window.focus_force()
            return
        
        # Create new window
        self.window = tk.Toplevel(self.parent)
        self.window.title("SAR K9 Training Record - User Manual")
        
        # Set window size and position
        window_width = 800
        window_height = 600
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Create main frame
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create scrolled text widget
        text_widget = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            font=("Arial", 14),
            bg="white",
            fg="black",
            state=tk.NORMAL,
            relief=tk.SUNKEN,
            borderwidth=2
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Insert the user manual text
        text_widget.insert("1.0", USER_MANUAL_TEXT)
        
        # Make text readonly
        text_widget.config(state=tk.DISABLED)
        
        # Create close button frame
        button_frame = tk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Close button
        close_button = tk.Button(
            button_frame,
            text="Close",
            command=self.window.destroy,
            width=10
        )
        close_button.pack(side=tk.RIGHT)
        
        # Bind Escape key to close
        self.window.bind("<Escape>", lambda e: self.window.destroy())
        
        # Bind F1 to close (toggle behavior)
        self.window.bind("<F1>", lambda e: self.window.destroy())


def show_help_window(parent):
    """
    Show the help window.
    
    Args:
        parent: Parent tkinter window
    """
    help_win = HelpWindow(parent)
    help_win.show()
