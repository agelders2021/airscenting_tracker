#!/usr/bin/env python3
"""
SPDX-License-Identifier: GPL-3.0-or-later

Copyright (C) 2026 Al Gelders

This file is part of the airscenting an trailing logging programs

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
Mantrailing Training Logger - UI Module
Extracted UI components for integration into main application.

This module contains the user interface elements without data storage logic.
Data operations should be implemented by the parent application using the
existing database schema.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkcalendar import DateEntry
from tktimepicker import SpinTimePickerModern, constants
from datetime import datetime
from pathlib import Path
import os
import shutil
import sv  # Import sv module for centralized StringVars
from ui_utils import enable_mousewheel_scroll


class ToolTip:
    """Create a tooltip for a widget with configurable delay"""
    def __init__(self, widget, text, delay=750):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip = None
        self.timer = None
        
        widget.bind("<Enter>", self.schedule_show)
        widget.bind("<Leave>", self.hide)
        widget.bind("<Button>", self.hide)
    
    def schedule_show(self, event=None):
        """Schedule tooltip to show after delay"""
        self.hide()
        self.timer = self.widget.after(self.delay, self.show)
    
    def show(self):
        """Display the tooltip"""
        if self.tooltip:
            return
        
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
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
        if self.timer:
            self.widget.after_cancel(self.timer)
            self.timer = None
        
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class TrailingEntryTab:
    """
    Mantrailing training session entry tab UI.
    
    This class creates the UI for entering training session data.
    It does not handle data persistence - that should be implemented
    by the parent application.
    
    Usage:
        tab = TrailingEntryTab(parent_frame, config_provider, callbacks)
        
    Where:
        - parent_frame: tk.Frame to contain the tab content
        - config_provider: object with methods to get configuration data
        - callbacks: dict of callback functions for data operations
    """
    
    def __init__(self, parent_frame, config_provider=None, callbacks=None):
        """
        Initialize the trailing entry tab.
        
        Args:
            parent_frame: Parent tk.Frame for the tab content
            config_provider: Object providing configuration data with methods:
                - get_handler_name() -> str
                - get_dog_names() -> list[str]
                - get_last_dog_name() -> str
                - get_terrain_types() -> list[str]
                - get_distraction_types() -> list[str]
                - get_training_locations() -> list[str]
            callbacks: Dict of callback functions:
                - on_save(session_data) -> bool
                - on_dog_changed(dog_name)
                - get_next_session_number(dog_name) -> int
                - on_load_prior_session()
                - on_export_pdf()
                - on_navigate_previous()
                - on_navigate_next()
                - on_resume_session()
                - on_hide_session()
        """
        self.parent = parent_frame
        self.config = config_provider
        self.callbacks = callbacks or {}
        
        # Initialize tracking variables
        self.selected_distraction_index = None
        self.selected_distraction_original = None
        self.editing_session = False
        self.editing_row = None
        self.dog_sessions_list = []
        self.current_session_index = -1
        self.form_snapshot = ""
        
        # Build the UI
        self._create_widgets()
        
        # Note: form_snapshot is taken by the parent (t_ui.py) after initial data is loaded
        # to prevent false "unsaved changes" detection on startup
    
    def _get_config_value(self, method_name, default=None):
        """Safely get a config value"""
        if self.config and hasattr(self.config, method_name):
            return getattr(self.config, method_name)()
        return default if default is not None else ""
    
    def _get_config_list(self, method_name, default=None):
        """Safely get a config list value"""
        if self.config and hasattr(self.config, method_name):
            return getattr(self.config, method_name)()
        return default if default is not None else []
    
    def _create_widgets(self):
        """Create all UI widgets for the entry tab"""
        # Create scrollable frame
        self.canvas = tk.Canvas(self.parent)
        scrollbar = ttk.Scrollbar(self.parent, orient="vertical", command=self.canvas.yview)
        scrollable_frame = ttk.Frame(self.canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Enable mouse wheel scrolling anywhere on the tab
        enable_mousewheel_scroll(self.canvas, self.parent)
        
        frame = tk.Frame(scrollable_frame, padx=20, pady=20)
        frame.pack(fill="both", expand=True)
        
        # F1 Help text at top
        help_label = tk.Label(frame, text="Push F1 to view the Help window.",
                             font=('Arial', 9),
                             fg='red')
        help_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        
        # Build sections
        self._create_session_info_section(frame)
        self._create_trail_details_section(frame)
        self._create_weather_section(frame)
        self._create_behavior_section(frame)
        self._create_distractions_section(frame)
        self._create_impression_section(frame)
        self._create_trail_map_section(frame)
        self._create_buttons_section(frame)
        
        # Configure grid weights
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)
    
    def _create_session_info_section(self, frame):
        """Create Session Information section (airscenting-style layout with purpose accumulator)"""
        self.session_frame = tk.LabelFrame(frame, text="Session Information", padx=10, pady=5)
        self.session_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        session_frame = self.session_frame  # Keep local reference for existing code
        
        # Row 0: Date, Session #, and action buttons
        tk.Label(session_frame, text="Date:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        # Use DateEntry for date picker
        self.date_picker = DateEntry(
            session_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd',
            year=datetime.now().year,
            month=datetime.now().month,
            day=datetime.now().day
        )
        self.date_picker.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        # Bind date picker changes to update the StringVar
        self.date_picker.bind("<<DateEntrySelected>>", self._on_date_changed)
        
        tk.Label(session_frame, text="Session #:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
        self.session_entry = tk.Entry(session_frame, textvariable=sv.t_session, width=10)
        self.session_entry.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        tk.Button(session_frame, text="New", command=self._new_session).grid(row=0, column=4, padx=5)
        
        self.view_edit_hide_btn = tk.Button(session_frame, text="View/Edit/Hide Prior Session(s)", 
                 command=self._load_prior_session, bg="#4169E1", fg="white")
        self.view_edit_hide_btn.grid(row=0, column=5, sticky='e', padx=5, pady=2)
        
        # Navigation buttons
        self.prev_session_btn = tk.Button(session_frame, text="\N{BLACK LEFT-POINTING TRIANGLE} Previous", bg="#FF8C00", fg="white", 
                                         width=10, command=self._navigate_previous_session, state=tk.DISABLED)
        self.prev_session_btn.grid(row=0, column=6, padx=2, pady=2)
        
        self.next_session_btn = tk.Button(session_frame, text="Next \N{BLACK RIGHT-POINTING TRIANGLE}", bg="#FF8C00", fg="white",
                                         width=10, command=self._navigate_next_session, state=tk.DISABLED)
        self.next_session_btn.grid(row=0, column=7, padx=2, pady=2)
        
        # Export PDF button
        self.export_pdf_btn = tk.Button(session_frame, text="Export PDF", bg="#9370DB", fg="white", 
                 width=12, command=self._export_pdf)
        self.export_pdf_btn.grid(row=0, column=8, padx=2, pady=2)
        
        # Row 1: Handler, Add Session Purpose + accumulator
        tk.Label(session_frame, text="Handler:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        # Initialize handler from config
        sv.t_handler.set(self._get_config_value('get_handler_name', ""))
        tk.Entry(session_frame, textvariable=sv.t_handler, width=15).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(session_frame, text="Add Session Purpose:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self.purpose_combo = ttk.Combobox(session_frame, textvariable=sv.t_purpose, width=16, state="enabled",
                                     values=['Flagged Trail', 'Unmarked Trail', 'Single Blind', 'Double Blind',
                                            'Motivational', 'Scent Discrimination', 
                                            'Obedience', 'Mock Cert Test', 'Mission'])
        self.purpose_combo.grid(row=1, column=3, sticky="w", padx=5, pady=2)
        self.purpose_combo.bind('<<ComboboxSelected>>', self._add_to_purpose_accumulator)
        self.purpose_combo.bind('<Return>', self._add_to_purpose_accumulator)
        ToolTip(self.purpose_combo,"Select purpose to be added to 'Session Purposes' list to right \N{BLACK RIGHT-POINTING TRIANGLE}\nOr type custom purpose and press 'Enter'\n(Selections are not shown in this entry box)",delay=250)
        
        # Session Purposes listbox (accumulator)
        purpose_list_frame = tk.Frame(session_frame)
        purpose_list_frame.grid(row=1, column=4, rowspan=2, columnspan=3, sticky="w", padx=5, pady=2)
        
        tk.Label(purpose_list_frame, text="Session Purposes:\n\n").pack(side=tk.LEFT, padx=(0, 5))
        
        self.purpose_listbox = tk.Listbox(purpose_list_frame, height=3, width=25)
        self.purpose_listbox.pack(side=tk.LEFT)
        self.purpose_listbox.bind('<Double-Button-1>', self._remove_purpose_from_list)
        ToolTip(self.purpose_listbox, "Session Purposes\nDouble-click an entry to remove from list", delay=750)
        
        # Scrollbar for purpose listbox (permanent)
        self.purpose_scrollbar = ttk.Scrollbar(purpose_list_frame, orient="vertical", command=self.purpose_listbox.yview)
        self.purpose_listbox.config(yscrollcommand=self.purpose_scrollbar.set)
        self.purpose_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        
        # Setup mouse wheel handling for the purpose listbox
        self._setup_listbox_wheel(self.purpose_listbox)
        
        # Row 2: Field Support, Dog, Resume/Hide buttons (aligned with Previous/Next)
        tk.Label(session_frame, text="Field Support:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        tk.Entry(session_frame, textvariable=sv.t_field_support, width=15).grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(session_frame, text="Dog:").grid(row=2, column=2, sticky="e", padx=5, pady=2)
        # Initialize dog from config
        sv.t_dog.set(self._get_config_value('get_last_dog_name', ""))
        self.dog_combo = ttk.Combobox(session_frame, textvariable=sv.t_dog, width=16, state="readonly")
        self.dog_combo['values'] = self._get_config_list('get_dog_names', [])
        self.dog_combo.grid(row=2, column=3, sticky="w", padx=5, pady=2)
        self.dog_combo.bind('<<ComboboxSelected>>', self._on_dog_changed)
        
        # Resume and Hide buttons (aligned with Previous/Next in columns 6-7)
        self.resume_btn = tk.Button(session_frame, text="Restore", bg="#28a745", fg="white",
                                   width=10, command=self._resume_session, state=tk.DISABLED)
        self.resume_btn.grid(row=2, column=7, padx=2, pady=2)
        
        self.hide_btn = tk.Button(session_frame, text="Hide", bg="#dc3545", fg="white",
                                 width=10, command=self._hide_session, state=tk.DISABLED)
        self.hide_btn.grid(row=2, column=8, padx=2, pady=2)
    
    def _create_trail_details_section(self, frame):
        """Create Trail Details section"""
        trail_frame = tk.LabelFrame(frame, text="Trail Details", padx=10, pady=5)
        trail_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        
        # Get dynamic widths
        locations = self._get_config_list('get_training_locations', [])
        terrain_types = self._get_config_list('get_terrain_types', self._get_default_terrain_types())
        location_width = max([len(loc) for loc in locations], default=10)
        location_width = max(location_width, 15)
        terrain_width = max([len(t) for t in terrain_types], default=8)
        terrain_width = max(terrain_width, 15)
        
        entry_location_width = location_width + 3
        entry_terrain_width = terrain_width + 3
        
        # Row 0: Location, Terrain Type, Start Time
        tk.Label(trail_frame, text="Location:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.location_combo = ttk.Combobox(trail_frame, textvariable=sv.t_location, width=location_width,
                                          values=sorted(locations))
        self.location_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        self.location_combo.bind('<FocusOut>', self._on_location_focus_out)
        
        tk.Label(trail_frame, text="Add Terrain Type:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
        self.terrain_combo = ttk.Combobox(trail_frame, textvariable=sv.t_terrain, width=terrain_width, 
                                         state="readonly", values=terrain_types)
        self.terrain_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        self.terrain_combo.bind('<<ComboboxSelected>>', self._add_to_terrain_accumulator)
        ToolTip(self.terrain_combo,"Select terrain type to be added to 'Terrain Types' to right \N{BLACK RIGHT-POINTING TRIANGLE}\n(Selections are not shown in this entry box)",delay=250)
        
        # Terrain listbox
        tk.Label(trail_frame, text="Terrain Types:").grid(row=0,column=4,sticky="e",padx=5,pady=2)
        self.terrain_listbox = tk.Listbox(trail_frame, height=2, width=entry_terrain_width)
        self.terrain_listbox.grid(row=0, column=5, sticky="wn", rowspan=2, padx=(5, 0), pady=2)
        self.terrain_listbox.bind('<Double-Button-1>', self._remove_terrain_from_list)
        ToolTip(self.terrain_listbox, "Terrain List Accumulator\nDouble-click an entry to remove from list", delay=750)
        
        # Scrollbar for terrain listbox (permanent)
        self.terrain_scrollbar = ttk.Scrollbar(trail_frame, orient="vertical", command=self.terrain_listbox.yview)
        self.terrain_listbox.config(yscrollcommand=self.terrain_scrollbar.set)
        self.terrain_scrollbar.grid(row=0, column=6, sticky="nsw", rowspan=2, pady=2, padx=(0, 5))
        
        # Setup mouse wheel handling for the terrain listbox
        self._setup_listbox_wheel(self.terrain_listbox)
        
        # Start time with manual colon separator
        time_location_width = 12
        tk.Label(trail_frame, text="Start Time:").grid(row=0, column=8, sticky="w", padx=5, pady=2)
        
        # Create a frame with border to wrap the time picker components
        time_picker_frame = tk.Frame(trail_frame, relief="sunken", borderwidth=1, bg="#ffffff", pady=0)
        time_picker_frame.grid(row=0, column=9, sticky="w", padx=5, pady=2)
        ToolTip(time_picker_frame,"Use Mouse Wheel to change time.\nHover over 'hour' to adjust hour,\nhover over 'minute' to adjust minutes",delay=200)
        
        # Create hours picker
        self.start_time_hours = SpinTimePickerModern(time_picker_frame)
        self.start_time_hours.addHours24()
        self.start_time_hours.configureAll(bg="#ffffff", fg="#000000", width=3)
        self.start_time_hours.pack(padx=1, pady=0, ipady=0, side=tk.LEFT)
        self.start_time_hours.set24Hrs(0)  # Initialize to 00
        
        # Add manual colon separator
        self.start_time_separator = tk.Label(time_picker_frame, text=":", bg="#ffffff", fg="#000000")
        self.start_time_separator.pack(pady=0, side=tk.LEFT)
        
        # Create minutes picker
        self.start_time_minutes = SpinTimePickerModern(time_picker_frame)
        self.start_time_minutes.addMinutes()
        self.start_time_minutes.configureAll(bg="#ffffff", fg="#000000", width=3)
        self.start_time_minutes.pack(padx=1, pady=0, ipady=0, side=tk.LEFT)
        self.start_time_minutes.setMins(0)  # Initialize to 00
        
        # Store references for easy access (for compatibility with existing code)
        # Create a simple proxy object to maintain API compatibility
        class TimePickerProxy:
            def __init__(proxy_self, hours_picker, minutes_picker):
                proxy_self._hours = hours_picker
                proxy_self._minutes = minutes_picker
            
            def hours24(proxy_self):
                return proxy_self._hours.hours24()
            
            def minutes(proxy_self):
                return proxy_self._minutes.minutes()
            
            def set24Hrs(proxy_self, h):
                proxy_self._hours.set24Hrs(h)
            
            def setMins(proxy_self, m):
                proxy_self._minutes.setMins(m)
        
        self.start_time_picker = TimePickerProxy(self.start_time_hours, self.start_time_minutes)
        
        # Bind time picker changes to update the StringVar
        self.start_time_hours.bind("<<HoursChanged>>", lambda e: self._on_start_time_changed())
        self.start_time_minutes.bind("<<MinChanged>>", lambda e: self._on_start_time_changed())
        
        # Setup mouse wheel handling for time picker components
        self._setup_timepicker_wheel(self.start_time_hours, time_picker_frame, 'hours')
        self._setup_timepicker_wheel(self.start_time_minutes, time_picker_frame, 'minutes')
        
        # Row 1: Trail Age, Trail Length, Trail Difficulty
        tk.Label(trail_frame, text="Trail Age (hours):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        # tk.Entry(trail_frame, textvariable=sv.t_trail_age, width=entry_location_width).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        ttk.Combobox(trail_frame, textvariable=sv.t_trail_age, width=location_width,
                    values=[
                        "Hot Trail",
                        "15 Minutes",
                        "\N{Vulgar Fraction One Half} Hour",
                        "\N{Vulgar Fraction Three Quarters} Hour",
                        "1 Hour",
                        "1 \N{Vulgar Fraction One Quarter} Hours",
                        "1 \N{Vulgar Fraction One Half} Hours",
                        "2 Hours","3 Hours","4 Hours","6 Hours","8 Hours", "12 Hours", "18 Hours", "24 Hours","36 Hours", "48 Hours"]).grid(row=1,column=1,sticky="w",padx=5,pady=2)
        
        tk.Label(trail_frame, text="Trail Length:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        #tk.Entry(trail_frame, textvariable=sv.t_trail_length, width=entry_terrain_width).grid(row=1, column=3, sticky="w", padx=5, pady=2)
        ttk.Combobox(trail_frame, textvariable=sv.t_trail_length,
                    values=[
                        "\N{Vulgar Fraction One Quarter} Mile",
                        "\N{Vulgar Fraction One Half} Mile",
                        "\N{Vulgar Fraction Three Quarters} Mile",
                        "1 Mile",
                        "1 \N{Vulgar Fraction One Quarter} Miles",
                        "1 \N{Vulgar Fraction One Half} Miles",
                        "1 \N{Vulgar Fraction Three Quarters} Miles",
                        "2 Miles.",
                        "2 \N{Vulgar Fraction One Half} Miles",
                        "3 Miles","4 Miles","5 Miles","6 Miles",],
                     width=entry_terrain_width-3).grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(trail_frame, text="Trail Difficulty:").grid(row=1, column=8, sticky="w", padx=5, pady=2)
        difficulty_combo = ttk.Combobox(trail_frame, textvariable=sv.t_difficulty, width=8, state="readonly",
                                        values=['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'])
        difficulty_combo.grid(row=1, column=9, sticky="w", padx=5, pady=2)

        # Row 2 Trail Layer, Cross Track Layer, Cross Track Age
        tk.Label(trail_frame,text="Trail Layer").grid(row=2,column=0,sticky="w",padx=5,pady=2)
        tk.Entry(trail_frame,textvariable=sv.t_trail_layer,width=entry_location_width).grid(row=2,column=1,padx=4,pady=2)

        tk.Label(trail_frame,text="Cross Track Layer:").grid(row=2,column=2,sticky="e",padx=5,pady=2)
        tk.Entry(trail_frame,textvariable=sv.t_cross_track_layer,width=entry_terrain_width).grid(row=2,column=3,sticky="w",padx=4,pady=2)

        tk.Label(trail_frame,text="Cross Track Age:").grid(row=2,column=4,sticky="e",padx=5,pady=2)
        # tk.Entry(trail_frame,textvariable=sv.t_cross_track_age,width=entry_terrain_width).grid(row=2,column=5,sticky="w",padx=5,pady=(5,2))
        ttk.Combobox(trail_frame, textvariable=sv.t_cross_track_age, width=location_width,
                    values=[
                        "15 Minutes or Less",
                        "\N{Vulgar Fraction One Half} Hour",
                        "\N{Vulgar Fraction Three Quarters} Hour",
                        "1 Hour",
                        "1 \N{Vulgar Fraction One Quarter} Hours",
                        "1 \N{Vulgar Fraction One Half} Hours",
                        "2 Hours","3 Hours","4 Hours","6 Hours","8 Hours"]).grid(row=2,column=5,sticky="w",padx=5,pady=2)



    def _create_weather_section(self, frame):
        """Create Weather subframes"""

        # Row 3 Weather frame container
        weather_frame_container = tk.Frame(frame)
        weather_frame_container.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
        self._create_weather_laying_section(weather_frame_container)
        self._create_weather_running_section(weather_frame_container)
    
    def _create_weather_laying_section(self, frame):
        """Create Weather When Laying Trail section"""
        weather_frame = tk.LabelFrame(frame, text="Weather When Laying Trail and While Aging", padx=10, pady=5)
        weather_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        tk.Label(weather_frame, text="Weather:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        weather_combo = ttk.Combobox(weather_frame, textvariable=sv.t_weather_laying, width=12,
                                     values=["Clear", "Cloudy", "Light Rain", "Heavy Rain", "Windy", "Snow", "Fog", "Hot/Sunny"])
        weather_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Wind Direction:").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        wind_dir_combo = ttk.Combobox(weather_frame, textvariable=sv.t_wind_direction_laying, width=12,
                                     values=["North", "South", "East", "West", "NE", "NW", "SE", "SW"])
        wind_dir_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Temperature (\N{Degree Sign}F):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        tk.Entry(weather_frame, textvariable=sv.t_temp_laying, width=15).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Humidity (%):").grid(row=1, column=2, sticky="e", padx=5, pady=2)
        tk.Entry(weather_frame, textvariable=sv.t_humidity_laying, width=15).grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Wind Speed:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        tk.Entry(weather_frame, textvariable=sv.t_wind_laying, width=15).grid(row=2, column=1, sticky="w", padx=5, pady=2)
    
    def _create_weather_running_section(self, frame):
        """Create Weather at Time of Running Trail section"""
        weather_frame = tk.LabelFrame(frame, text="Weather at Time of Running Trail", padx=10, pady=5)
        weather_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        tk.Label(weather_frame, text="Weather:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        weather_combo = ttk.Combobox(weather_frame, textvariable=sv.t_weather_running, width=12,
                                     values=["Clear", "Cloudy", "Light Rain", "Heavy Rain", "Windy", "Snow", "Fog", "Hot/Sunny"])
        weather_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Wind Direction:").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        wind_dir_combo = ttk.Combobox(weather_frame, textvariable=sv.t_wind_direction_running, width=12,
                                     values=["North", "South", "East", "West", "NE", "NW", "SE", "SW"])
        wind_dir_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Temperature (\N{Degree Sign}F):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        tk.Entry(weather_frame, textvariable=sv.t_temp_running, width=15).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Humidity (%):").grid(row=1, column=2, sticky="e", padx=5, pady=2)
        tk.Entry(weather_frame, textvariable=sv.t_humidity_running, width=15).grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Wind Speed:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        tk.Entry(weather_frame, textvariable=sv.t_wind_running, width=15).grid(row=2, column=1, sticky="w", padx=5, pady=2)
    
    def _create_behavior_section(self, frame):
        """Create Dog Behavior & Performance section"""
        behavior_frame = tk.LabelFrame(frame, text="Dog Behavior & Performance", padx=10, pady=5)
        behavior_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
        
        tk.Label(behavior_frame, text="Start Behavior:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Combobox(behavior_frame, textvariable=sv.t_start_behavior, width=54,
                    values=["Excellent\N{EM DASH}Direction of Travel immediately identified ",
                            "Very Good\N{EM DASH}Direction of travel not imediately identified",
                            "Good\N{EM DASH}Direction of travel identified with cueing",
                            "Fair\N{EM DASH}Direction of travel not identified",
                            "Poor\N{EM DASH}Direction of travel incorrectly identified",
                            "Needs Work\N{EM DASH}Could not identify trail"]).grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        
        tk.Label(behavior_frame, text="Pace:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
        ttk.Combobox(behavior_frame, textvariable=sv.t_pace, width=18,
                    values=["Fast", "Moderate", "Slow", "Variable"]).grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        # Start time and run time
        tk.Label(behavior_frame, text="Time to Complete (min):").grid(row=0, column=4, sticky="w", padx=5, pady=2)
        tk.Entry(behavior_frame, textvariable=sv.t_time, width=15).grid(row=0, column=5, sticky="w", padx=5, pady=2)
        
        tk.Label(behavior_frame, text="Tracking Consistency:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        ttk.Combobox(behavior_frame, textvariable=sv.t_consistency, width=18,
                    values=["Excellent", "Good", "Fair", "Poor", "Needs Work"]).grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(behavior_frame, text="Indication at Find:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Combobox(behavior_frame, textvariable=sv.t_indication, width=54,
                    values=["Immediate Trained Final Response",
                            "Strong Alert\N{EM DASH}Exhibited Trained Final Response after hesitation",
                            "Moderate Alert\N{EM DASH}Alert behavior but no TFR",
                            "Weak Alert\N{EM DASH}Hesitant, before clear response, needed cueing", 
                            "No Clear Indication"]).grid(row=1, column=1, sticky="w", padx=5, pady=2)
    
    def _create_distractions_section(self, frame):
        """Create Distractions section"""
        distraction_frame = tk.LabelFrame(frame, text="Distractions", padx=10, pady=5)
        distraction_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=5)
        
        # Input row
        tk.Label(distraction_frame, text="Distraction:").grid(row=0, column=0, sticky="nw", padx=5, pady=2)
        distraction_types = self._get_config_list('get_distraction_types', self._get_default_distraction_types())
        self.distraction_combo = ttk.Combobox(distraction_frame, textvariable=sv.t_distractions, width=20,
                                             values=distraction_types)
        self.distraction_combo.grid(row=0, column=1, sticky="nw", padx=5, pady=2)
        ToolTip(self.distraction_combo,"Select Distraction via dropdown list or type custom distraction\nThen select 'Response' to the right \N{BLACK RIGHT-POINTING TRIANGLE}",delay=250) 
        
        tk.Label(distraction_frame, text="Response:").grid(row=0, column=2, sticky="ne", padx=5, pady=2)
        self.response_combo = ttk.Combobox(distraction_frame, textvariable=sv.t_distraction_response, width=20,
                    values=["Ignored", "Brief Check", "Prolonged Interest", "Lost Trail", "Recovered Quickly", "Scared", "Panicked", "Ate"],
                    state="disabled")
        self.response_combo.grid(row=0, column=3, sticky="nw", padx=5, pady=2)
        self.response_combo.bind('<<ComboboxSelected>>', self._on_response_selected)
        self.response_combo.bind('<Return>', self._on_response_selected)
        ToolTip(self.response_combo,"Select response using dropdown list or type custom response followed by 'Enter' key",delay=500)
        
        # Trace for enabling/disabling response combo
        sv.t_distractions.trace_add('write', self._on_distraction_change)
        
        # Table and buttons
        tk.Label(distraction_frame, text="Accumulated\nDistractions:").grid(row=1, column=3,rowspan=3, sticky="ne", padx=5, pady=(2,2))
        
        table_container = tk.Frame(distraction_frame)
        table_container.grid(row=0, column=4, rowspan=3, sticky="new", padx=5, pady=(0,2))
        
        tree_frame = tk.Frame(table_container)
        tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.distraction_tree = ttk.Treeview(tree_frame, columns=('Type', 'Response'),
                                            show='headings', height=2)
        self.distraction_tree.heading('Type', text='Distraction')
        self.distraction_tree.heading('Response', text='Response')
        self.distraction_tree.column('Type', width=200)
        self.distraction_tree.column('Response', width=150)
        
        dist_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.distraction_tree.yview)
        self.distraction_tree.config(yscrollcommand=dist_scrollbar.set)
        
        self.distraction_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dist_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Button frame
        button_frame = tk.Frame(table_container)
        button_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        update_clear_frame = tk.Frame(button_frame)
        update_clear_frame.pack(pady=2)
        
        self.update_distraction_btn = tk.Button(update_clear_frame, text="Update", 
                                                command=self._update_selected_distraction, 
                                                width=10, state="disabled")
        self.update_distraction_btn.pack(side=tk.LEFT, padx=1)
        
        self.clear_distraction_btn = tk.Button(update_clear_frame, text="Clear", 
                                               command=self._clear_distraction_fields, 
                                               width=10, state="disabled")
        self.clear_distraction_btn.pack(side=tk.LEFT, padx=1)
        
        self.delete_distraction_btn = tk.Button(button_frame, text="Delete", 
                                                command=self._delete_selected_distraction, 
                                                width=21, state="disabled")
        self.delete_distraction_btn.pack(pady=2)
        
        # Bind selection event and trace
        self.distraction_tree.bind('<<TreeviewSelect>>', self._on_distraction_select)
        sv.t_distractions.trace_add('write', self._update_distraction_button_states)
        
        # Setup mouse wheel handling for the distraction tree
        self._setup_treeview_wheel(self.distraction_tree)
    
    def _create_impression_section(self, frame):
        """Create combined Overall Impression and Trail Map section with drop zone"""
        # Main frame - Overall Impression (drop target for entire frame)
        self.impression_map_frame = tk.LabelFrame(
            frame, 
            text="Overall Impression", 
            padx=10, pady=5
        )
        self.impression_map_frame.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=5)
        
        # Container for two-column layout (not grey)
        container = tk.Frame(self.impression_map_frame)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure grid for 50/50 split
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)
        
        # LEFT HALF: Overall Impression text
        left_frame = tk.Frame(container)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        impression_container = tk.Frame(left_frame)
        impression_container.pack(fill=tk.BOTH, expand=True)
        
        self.impression_text = tk.Text(impression_container, height=8, wrap=tk.WORD)
        impression_scrollbar = ttk.Scrollbar(impression_container, orient=tk.VERTICAL, command=self.impression_text.yview)
        self.impression_text.config(yscrollcommand=impression_scrollbar.set)
        
        self.impression_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        impression_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Setup mouse wheel handling for the overall impression text
        self._setup_text_wheel(self.impression_text)
        
        # RIGHT HALF: Nested LabelFrame for trail maps (with grey background)
        trail_map_labelframe = tk.LabelFrame(
            container, 
            text="Drop Images/Videos Here\n(PDF/JPG/PNG/MP4/MOV)",
            padx=5, pady=5
        )
        trail_map_labelframe.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Container inside the trail map labelframe (for visual feedback on drag)
        self._drop_container = tk.Frame(trail_map_labelframe)
        self._drop_container.pack(fill=tk.BOTH, expand=True)
        
        list_button_container = tk.Frame(self._drop_container)
        list_button_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        listbox_container = tk.Frame(list_button_container)
        listbox_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Only the listbox is grey
        self.map_listbox = tk.Listbox(listbox_container, height=6, font=('Arial', 9), bg="#e0e0e0")
        map_scroll = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL, command=self.map_listbox.yview)
        self.map_listbox.config(yscrollcommand=map_scroll.set)
        
        self.map_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        map_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.map_listbox.bind('<Double-Button-1>', lambda e: self._view_selected_trail_map())
        
        map_button_frame = tk.Frame(list_button_container)
        map_button_frame.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.view_trail_map_button = tk.Button(map_button_frame, text="View Selected", 
                                         command=self._view_selected_trail_map, state=tk.DISABLED, width=12)
        self.view_trail_map_button.pack(pady=(0, 2))
        
        self.delete_trail_map_button = tk.Button(map_button_frame, text="Delete Selected", 
                                         command=self._delete_selected_trail_map, state=tk.DISABLED, width=12)
        self.delete_trail_map_button.pack(pady=(2, 0))
        
        tk.Button(map_button_frame, text="Browse...", command=self._browse_trail_map, width=12).pack(pady=(2, 0))
        
        # Register drag-and-drop on the entire main label frame
        try:
            from tkinterdnd2 import DND_FILES
            self.impression_map_frame.drop_target_register(DND_FILES)
            self.impression_map_frame.dnd_bind('<<Drop>>', self._handle_drop)
            self.impression_map_frame.dnd_bind('<<DragEnter>>', self._drag_enter)
            self.impression_map_frame.dnd_bind('<<DragLeave>>', self._drag_leave)
        except Exception as e:
            # print(f"Drag-and-drop not available: {e}")
            pass
    
    def _create_trail_map_section(self, frame):
        """Trail map section is now combined with impression section - this is a no-op"""
        pass
    
    def _create_buttons_section(self, frame):
        """Create action buttons section"""
        button_frame = tk.Frame(frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=10)
        
        self.save_btn = tk.Button(button_frame, text="Save Session", command=self._save_session,
                 bg="#4CAF50", fg="white", font=("Helvetica", 12, "bold"),
                 width=25, height=2)
        self.save_btn.pack(side="left", padx=10)
        
        tk.Button(button_frame, text="Clear Form", command=self._clear_form_with_check,
                 width=15).pack(side="left", padx=10)
        
        tk.Button(button_frame, text="Quit", command=self._quit,
                 width=10).pack(side="left", padx=10)
    
    def update_save_button_text(self):
        """Update save button text based on editing mode"""
        if self.editing_session:
            self.save_btn.config(text="Update Session")
        else:
            self.save_btn.config(text="Save Session")
    
    # =========================================================================
    # Default data providers
    # =========================================================================
    
    def _get_default_terrain_types(self):
        """Get default terrain types list"""
        return [
            "Urban", "Rural", "Forest", "Scrub", "Desert", "Sandy", "Rocky", 
            "City park", "Meadow", "Dense brush", "Many cacti", "Stream", 
            "Roadway", "Marsh", "Mixed", "Industrial", "Residential"
        ]
    
    def _get_default_distraction_types(self):
        """Get default distraction types list"""
        return [
            "Critter", "Horse", "Loud noise", "Motorcycle", "Hikers", 
            "Cow", "Vehicle"
        ]
    
    # =========================================================================
    # Event handlers
    # =========================================================================
    
    def _on_dog_changed(self, event=None):
        """Handle dog selection change"""
        selected_dog = sv.t_dog.get()
        if selected_dog and 'on_dog_changed' in self.callbacks:
            self.callbacks['on_dog_changed'](selected_dog)
        
        # Update session number
        if 'get_next_session_number' in self.callbacks:
            next_session = self.callbacks['get_next_session_number'](selected_dog)
            sv.t_session.set(str(next_session))
    
    def _auto_increment_session(self):
        """Auto-increment session number"""
        dog_name = sv.t_dog.get()
        if 'get_next_session_number' in self.callbacks:
            next_session = self.callbacks['get_next_session_number'](dog_name)
            sv.t_session.set(str(next_session))
    
    def _new_session(self):
        """Start a new session - clear form and get next session number"""
        # Check for unsaved changes first
        if self.has_unsaved_changes():
            result = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes.\n\nDo you want to save before starting a new session?",
                icon='warning'
            )
            if result is None:  # Cancel
                return
            elif result:  # Yes - save first
                self._save_session()
        
        # Clear the form
        self.clear_form()
        sv.t_status.set("New session started")
    
    def _on_date_changed(self, event=None):
        """Handle date picker change - update the date_var StringVar"""
        selected_date = self.date_picker.get_date()
        sv.t_date.set(selected_date.strftime("%Y-%m-%d"))
    
    def _on_start_time_changed(self):
        """Handle start time picker change - update the start_time StringVar in HHMM format"""
        # Get time from picker as tuple (hours, minutes, period)
        hours = self.start_time_picker.hours24()
        minutes = self.start_time_picker.minutes()
        # Format as HHMM (e.g., 1436 for 2:36 PM) - no colon
        time_str = f"{hours:02d}{minutes:02d}"
        sv.t_start_time.set(time_str)
    
    def _setup_timepicker_wheel(self, time_picker, frame, component_type):
        """
        Setup mouse wheel handling for the time picker component.
        
        When hovering over the widget, wheel adjusts its value.
        When not over the picker widget, wheel scrolls the window.
        
        Args:
            time_picker: The SpinTimePickerModern instance (hours or minutes component)
            frame: The frame containing the time picker
            component_type: 'hours' or 'minutes' to identify which component
        """
        import platform
        
        # Get reference to the appropriate widget
        if component_type == 'hours':
            widget = time_picker._24HrsTime
        else:  # minutes
            widget = time_picker._minutes
        
        def adjust_spinlabel(widget, delta):
            """Adjust a SpinLabel value by delta (positive = increment, negative = decrement)"""
            # Access the internal attributes of SpinLabel
            number_lst = widget.number_lst
            current_index = widget._current_index
            
            if delta > 0:
                # Scroll up - increment
                if current_index < len(number_lst) - 1:
                    widget._current_index += 1
                else:
                    widget._current_index = 0
            else:
                # Scroll down - decrement
                if current_index > 0:
                    widget._current_index -= 1
                else:
                    widget._current_index = len(number_lst) - 1
            
            widget.current_val = number_lst[widget._current_index]
            widget.updateLabel()
        
        def on_wheel(event):
            """Handle wheel events on widget"""
            if platform.system() == 'Linux':
                delta = 1 if event.num == 4 else -1
            else:
                delta = 1 if event.delta > 0 else -1
            adjust_spinlabel(widget, delta)
            self._on_start_time_changed()
            return "break"
        
        def on_frame_wheel(event):
            """Handle wheel events on the frame (not on hours/minutes) - block propagation"""
            # Just block propagation, don't do anything
            return "break"
        
        # Bind wheel events
        if platform.system() == 'Linux':
            widget.bind("<Button-4>", on_wheel)
            widget.bind("<Button-5>", on_wheel)
            # Block wheel on the frame to prevent window scroll
            frame.bind("<Button-4>", on_frame_wheel)
            frame.bind("<Button-5>", on_frame_wheel)
            time_picker.bind("<Button-4>", on_frame_wheel)
            time_picker.bind("<Button-5>", on_frame_wheel)
        else:
            widget.bind("<MouseWheel>", on_wheel)
            # Block wheel on the frame to prevent window scroll
            frame.bind("<MouseWheel>", on_frame_wheel)
            time_picker.bind("<MouseWheel>", on_frame_wheel)
    
    def _setup_treeview_wheel(self, treeview):
        """
        Setup mouse wheel handling for treeview widgets.
        
        When hovering over the treeview, wheel scrolls the treeview.
        This prevents the wheel from scrolling the entire window when over the treeview.
        
        Args:
            treeview: The ttk.Treeview widget
        """
        import platform
        
        def on_wheel(event):
            """Handle wheel events on treeview"""
            if platform.system() == 'Linux':
                # Linux uses Button-4 for scroll up, Button-5 for scroll down
                delta = -1 if event.num == 4 else 1
            else:
                # Windows/Mac use MouseWheel with delta
                delta = -int(event.delta / 120)
            
            treeview.yview_scroll(delta, "units")
            return "break"  # Prevent event from propagating to parent
        
        # Bind wheel events
        if platform.system() == 'Linux':
            treeview.bind("<Button-4>", on_wheel)
            treeview.bind("<Button-5>", on_wheel)
        else:
            treeview.bind("<MouseWheel>", on_wheel)
    
    def _setup_listbox_wheel(self, listbox):
        """
        Setup mouse wheel handling for listbox widgets.
        
        When hovering over the listbox, wheel scrolls the listbox.
        This prevents the wheel from scrolling the entire window when over the listbox.
        
        Args:
            listbox: The tk.Listbox widget
        """
        import platform
        
        def on_wheel(event):
            """Handle wheel events on listbox"""
            if platform.system() == 'Linux':
                # Linux uses Button-4 for scroll up, Button-5 for scroll down
                delta = -1 if event.num == 4 else 1
            else:
                # Windows/Mac use MouseWheel with delta
                delta = -int(event.delta / 120)
            
            listbox.yview_scroll(delta, "units")
            return "break"  # Prevent event from propagating to parent
        
        # Bind wheel events
        if platform.system() == 'Linux':
            listbox.bind("<Button-4>", on_wheel)
            listbox.bind("<Button-5>", on_wheel)
        else:
            listbox.bind("<MouseWheel>", on_wheel)
    
    def _setup_text_wheel(self, text_widget):
        """
        Setup mouse wheel handling for Text widgets.
        
        When hovering over the text widget, wheel scrolls the text.
        This prevents the wheel from scrolling the entire window when over the text widget.
        
        Args:
            text_widget: The tk.Text widget
        """
        import platform
        
        def on_wheel(event):
            """Handle wheel events on text widget"""
            if platform.system() == 'Linux':
                # Linux uses Button-4 for scroll up, Button-5 for scroll down
                delta = -1 if event.num == 4 else 1
            else:
                # Windows/Mac use MouseWheel with delta
                delta = -int(event.delta / 120)
            
            text_widget.yview_scroll(delta, "units")
            return "break"  # Prevent event from propagating to parent
        
        # Bind wheel events
        if platform.system() == 'Linux':
            text_widget.bind("<Button-4>", on_wheel)
            text_widget.bind("<Button-5>", on_wheel)
        else:
            text_widget.bind("<MouseWheel>", on_wheel)
    
    def _load_prior_session(self):
        """Load a prior session for editing"""
        if 'on_load_prior_session' in self.callbacks:
            self.callbacks['on_load_prior_session']()
    
    def _navigate_previous_session(self):
        """Navigate to previous session"""
        if 'on_navigate_previous' in self.callbacks:
            self.callbacks['on_navigate_previous']()
    
    def _navigate_next_session(self):
        """Navigate to next session"""
        if 'on_navigate_next' in self.callbacks:
            self.callbacks['on_navigate_next']()
    
    def _resume_session(self):
        """Resume a hidden/paused session"""
        if 'on_resume_session' in self.callbacks:
            self.callbacks['on_resume_session']()
    
    def _hide_session(self):
        """Hide/pause the current session"""
        if 'on_hide_session' in self.callbacks:
            self.callbacks['on_hide_session']()
    
    def _export_pdf(self):
        """Export session to PDF"""
        if 'on_export_pdf' in self.callbacks:
            self.callbacks['on_export_pdf']()
    
    def _save_session(self):
        """Save the current session"""
        session_data = self.get_session_data()
        
        if 'on_save' in self.callbacks:
            success = self.callbacks['on_save'](session_data)
            if success:
                sv.t_status.set("Session saved successfully")
                self.take_form_snapshot()
        else:
            messagebox.showinfo("Save", "Save callback not configured")
    
    def _clear_form_with_check(self):
        """Clear form with unsaved changes check"""
        if self.has_unsaved_changes():
            result = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes.\n\nDo you want to save before clearing?",
                icon='warning'
            )
            if result is None:  # Cancel
                return
            elif result:  # Yes - save first
                self._save_session()
        
        self.clear_form()
    
    def _quit(self):
        """Handle quit button"""
        # Check for unsaved changes before quitting
        if self.has_unsaved_changes():
            result = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes to the current session.\n\n"
                "Do you want to save before exiting?",
                icon='warning'
            )
            
            if result is None:  # Cancel - don't quit
                return
            elif result:  # Yes - save first
                self._save_session()
        
        if 'on_quit' in self.callbacks:
            self.callbacks['on_quit']()
        else:
            self.parent.master.quit()
    
    def _on_location_focus_out(self, event):
        """Handle location field losing focus - prompt to add new location"""
        location = sv.t_location.get().strip()
        if not location:
            return
        
        locations = self._get_config_list('get_training_locations', [])
        if location in locations:
            return
        
        if 'on_new_location' in self.callbacks:
            response = messagebox.askyesno("Add Location?", 
                                           f"'{location}' is not in your saved locations list.\n\n"
                                           f"Would you like to add it to the list?")
            if response:
                self.callbacks['on_new_location'](location)
    
    # =========================================================================
    # Terrain methods
    # =========================================================================
    
    def _add_to_terrain_accumulator(self, event):
        """Add selected terrain type to the listbox"""
        terrain_type = sv.t_terrain.get()
        if terrain_type:
            current_items = self.terrain_listbox.get(0, tk.END)
            if terrain_type in current_items:
                messagebox.showinfo("Duplicate", f"'{terrain_type}' is already in the list")
                sv.t_terrain.set("")
                return
            
            self.terrain_listbox.insert(tk.END, terrain_type)
            sv.t_terrain.set("")
            self._update_terrain_scrollbar()
    
    def _remove_terrain_from_list(self, event):
        """Remove terrain type from listbox when double-clicked"""
        selection = self.terrain_listbox.curselection()
        if not selection:
            return
        
        terrain_type = self.terrain_listbox.get(selection[0])
        
        if messagebox.askyesno("Remove Terrain Type", f"Remove '{terrain_type}' from the list?"):
            self.terrain_listbox.delete(selection[0])
            self._update_terrain_scrollbar()
    
    def _update_terrain_scrollbar(self):
        """Terrain scrollbar is now permanent - this method is kept for compatibility"""
        pass
    
    # =========================================================================
    # Session Purpose accumulator methods
    # =========================================================================
    
    def _add_to_purpose_accumulator(self, event):
        """Add selected session purpose to the listbox"""
        purpose = sv.t_purpose.get()
        if purpose:
            current_items = self.purpose_listbox.get(0, tk.END)
            if purpose in current_items:
                messagebox.showinfo("Duplicate", f"'{purpose}' is already in the list")
                sv.t_purpose.set("")
                return
            
            self.purpose_listbox.insert(tk.END, purpose)
            sv.t_purpose.set("")
            self._update_purpose_scrollbar()
    
    def _remove_purpose_from_list(self, event):
        """Remove session purpose from listbox when double-clicked"""
        selection = self.purpose_listbox.curselection()
        if not selection:
            return
        
        purpose = self.purpose_listbox.get(selection[0])
        
        if messagebox.askyesno("Remove Session Purpose", f"Remove '{purpose}' from the list?"):
            self.purpose_listbox.delete(selection[0])
            self._update_purpose_scrollbar()
    
    def _update_purpose_scrollbar(self):
        """Purpose scrollbar is now permanent - this method is kept for compatibility"""
        pass
    
    # =========================================================================
    # Distraction methods
    # =========================================================================
    
    def _on_distraction_change(self, *args):
        """Enable/disable response combobox based on distraction field content"""
        distraction = sv.t_distractions.get().strip()
        if distraction:
            self.response_combo.config(state="normal")
        else:
            self.response_combo.config(state="disabled")
    
    def _on_response_selected(self, event):
        """Handle response combobox selection"""
        if self.selected_distraction_index:
            self._update_selected_distraction()
        elif sv.t_distractions.get().strip():
            self._add_to_distraction_accumulator()
    
    def _add_to_distraction_accumulator(self, event=None):
        """Add distraction to table"""
        distraction = sv.t_distractions.get().strip()
        response = sv.t_distraction_response.get().strip()
        
        if not distraction:
            messagebox.showwarning("Empty Distraction", "Please enter a distraction")
            return
        
        if not response:
            messagebox.showwarning("Empty Response", "Please select a response")
            return
        
        self.distraction_tree.insert('', tk.END, values=(distraction, response))
        self._update_accumulated_distractions_string()
        
        self.distraction_tree.selection_remove(self.distraction_tree.selection())
        sv.t_distractions.set("")
        sv.t_distraction_response.set("")
        self.selected_distraction_index = None
        self.selected_distraction_original = None
        
        sv.t_status.set("Distraction added")
    
    def _on_distraction_select(self, event):
        """Handle selection of a distraction in the table"""
        selection = self.distraction_tree.selection()
        if selection:
            item = selection[0]
            values = self.distraction_tree.item(item, 'values')
            if values:
                sv.t_distractions.set(values[0])
                sv.t_distraction_response.set(values[1])
                self.selected_distraction_index = item
                self.selected_distraction_original = values[0]
                sv.t_status.set("Selected distraction - you can now Update or Delete it")
                self._update_distraction_button_states()
        else:
            self.selected_distraction_index = None
            self.selected_distraction_original = None
            self._update_distraction_button_states()
    
    def _update_distraction_button_states(self, *args):
        """Update the state of distraction management buttons"""
        distraction = sv.t_distractions.get().strip()
        has_content = bool(distraction)
        has_selection = self.selected_distraction_index is not None
        
        if has_selection and self.selected_distraction_original is not None:
            is_modified = (distraction != self.selected_distraction_original)
        else:
            is_modified = False
        
        self.clear_distraction_btn.config(state="normal" if has_content else "disabled")
        self.delete_distraction_btn.config(state="normal" if (has_selection and not is_modified) else "disabled")
        self.update_distraction_btn.config(state="normal" if (has_selection and is_modified) else "disabled")
    
    def _update_selected_distraction(self):
        """Update the selected distraction in the table"""
        if not self.selected_distraction_index:
            messagebox.showwarning("No Selection", "Please select a distraction from the table first")
            return
        
        distraction = sv.t_distractions.get().strip()
        response = sv.t_distraction_response.get().strip()
        
        if not distraction or not response:
            messagebox.showwarning("Empty Fields", "Both distraction and response are required")
            return
        
        self.distraction_tree.item(self.selected_distraction_index, values=(distraction, response))
        self._update_accumulated_distractions_string()
        
        self.distraction_tree.selection_remove(self.distraction_tree.selection())
        sv.t_distractions.set("")
        sv.t_distraction_response.set("")
        self.selected_distraction_index = None
        self.selected_distraction_original = None
        
        sv.t_status.set("Distraction updated")
    
    def _delete_selected_distraction(self):
        """Delete the selected distraction from the table"""
        selection = self.distraction_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a distraction from the table first")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this distraction?"):
            self.distraction_tree.delete(selection[0])
            self._update_accumulated_distractions_string()
            
            sv.t_distractions.set("")
            sv.t_distraction_response.set("")
            self.selected_distraction_index = None
            self.selected_distraction_original = None
            
            sv.t_status.set("Distraction deleted")
    
    def _clear_distraction_fields(self):
        """Clear the distraction input fields"""
        self.distraction_tree.selection_remove(self.distraction_tree.selection())
        sv.t_distractions.set("")
        sv.t_distraction_response.set("")
        self.selected_distraction_index = None
        self.selected_distraction_original = None
        sv.t_status.set("Distraction fields cleared")
    
    def _update_accumulated_distractions_string(self):
        """Update the accumulated distractions string from the treeview"""
        distractions_list = []
        for item in self.distraction_tree.get_children():
            values = self.distraction_tree.item(item, 'values')
            if values:
                distractions_list.append(f"{values[0]}:{values[1]}")
        
        sv.t_accumulated_distractions.set(", ".join(distractions_list))
    
    # =========================================================================
    # Trail map methods
    # =========================================================================
    
    def _drag_enter(self, event):
        """Visual feedback when dragging over drop zone"""
        if hasattr(self, '_drop_container'):
            self._drop_container.configure(bg="#90EE90")
    
    def _drag_leave(self, event):
        """Reset visual feedback"""
        if hasattr(self, '_drop_container'):
            self._drop_container.configure(bg="SystemButtonFace")
    
    def _handle_drop(self, event):
        """Handle dropped files"""
        if hasattr(self, '_drop_container'):
            self._drop_container.configure(bg="SystemButtonFace")
        
        data = event.data.strip()
        
        filepaths = []
        if data.startswith("{"):
            parts = data.split("} {")
            for part in parts:
                part = part.strip("{}")
                if part:
                    filepaths.append(part)
        else:
            filepaths = [data]
        
        valid_files = []
        for filepath in filepaths:
            filepath = filepath.strip()
            if os.path.exists(filepath):
                ext = os.path.splitext(filepath)[1].lower()
                if ext in ['.pdf', '.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi', '.mkv', '.webm']:
                    valid_files.append(filepath)
        
        if valid_files:
            self._add_map_files(valid_files)
        else:
            messagebox.showerror("Error", "Only PDF, JPG, PNG, and video files (MP4, MOV, AVI, MKV, WebM) supported!")
    
    def _browse_trail_map(self):
        """Browse for trail map file"""
        filepaths = filedialog.askopenfilenames(
            title="Select Trail Map(s)",
            filetypes=[
                ("Image/PDF/Video files", "*.pdf *.jpg *.jpeg *.png *.mp4 *.mov *.avi *.mkv *.webm"),
                ("All files", "*.*")
            ]
        )
        if filepaths:
            self._add_map_files(list(filepaths))
    
    def _add_map_files(self, filepaths):
        """Add map files to the list and copy to Images folders.
        
        Copies files to both primary and secondary Images folders with
        unique naming: t_{dog}_session{session}_{timestamp}_{original}.ext
        """
        import re
        from ui_utils import get_primary_images_folder, get_secondary_images_folder
        
        dog_name = sv.t_dog.get()
        session_number = sv.t_session.get() or '0'
        
        if not dog_name:
            messagebox.showwarning(
                "No Dog Selected",
                "Please select a dog before adding trail maps.\n\n"
                "The dog name is used to organize files."
            )
            return
        
        # Get primary and secondary Images folders
        primary_folder = get_primary_images_folder()
        secondary_folder = get_secondary_images_folder(create_if_missing=True)
        
        if not primary_folder:
            messagebox.showerror(
                "Images Folder Not Set",
                "Primary storage folder not properly initialized.\n\n"
                "Please use 'Initialize Data Structures' in the Setup tab first."
            )
            return
        
        copied_files = []
        safe_dog_name = re.sub(r'[^\w\-]', '_', dog_name)
        
        for filepath in filepaths:
            filepath = Path(filepath)
            if filepath.exists():
                ext = filepath.suffix.lower()
                if ext in ['.pdf', '.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi', '.mkv', '.webm']:
                    # Create unique filename: t_{dog}_session{session}_{timestamp}_{original}
                    original_name = filepath.name
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    unique_name = f"t_{safe_dog_name}_session{session_number}_{timestamp}_{original_name}"
                    
                    # Copy to primary Images folder
                    try:
                        primary_dest = primary_folder / unique_name
                        shutil.copy2(str(filepath), str(primary_dest))
                        copied_files.append(unique_name)  # Store just filename, not full path
                        # print(f"Copied to primary: {primary_dest}")
                        pass
                        
                        # Mirror to secondary Images folder
                        if secondary_folder:
                            try:
                                secondary_dest = secondary_folder / unique_name
                                shutil.copy2(str(filepath), str(secondary_dest))
                                # print(f"Mirrored to secondary: {secondary_dest}")
                                pass
                            except Exception as e:
                                # print(f"Warning: Failed to mirror to secondary: {e}")
                                pass
                                
                    except Exception as e:
                        # print(f"Error copying {filepath}: {e}")
                        messagebox.showerror("Copy Error", f"Failed to copy {filepath.name}:\n{e}")
        
        if copied_files:
            sv.t_map_files_list.extend(copied_files)
            # Remove duplicates while preserving order
            seen = set()
            sv.t_map_files_list = [x for x in sv.t_map_files_list if not (x in seen or seen.add(x))]
            
            self.map_listbox.delete(0, tk.END)
            for fname in sv.t_map_files_list:
                self.map_listbox.insert(tk.END, fname)
            
            self.view_trail_map_button.config(state=tk.NORMAL)
            self.delete_trail_map_button.config(state=tk.NORMAL)
            
            sv.t_status.set(f"{len(copied_files)} trail map(s) added and copied to backup")
    
    def _view_selected_trail_map(self):
        """Open the selected trail map file"""
        selection = self.map_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a file from the list to view")
            return
        
        selected_index = selection[0]
        if selected_index < len(sv.t_map_files_list):
            filename = sv.t_map_files_list[selected_index]
            
            # Build full path from trail maps folder
            trail_maps_folder = sv.trail_maps_folder.get().strip()
            if trail_maps_folder and not os.path.isabs(filename):
                filepath = os.path.join(trail_maps_folder, filename)
            else:
                filepath = filename
            
            self._open_external_file(filepath)
    
    def _delete_selected_trail_map(self):
        """Remove the selected trail map from the list and delete from both primary and secondary folders"""
        from ui_utils import get_secondary_images_folder
        
        selection = self.map_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a file from the list to remove")
            return
        
        selected_index = selection[0]
        if selected_index >= len(sv.t_map_files_list):
            return
        
        filename = sv.t_map_files_list[selected_index]
        
        result = messagebox.askokcancel(
            "Delete Trail Map",
            f"Are you sure you want to delete '{filename}'?\n\nThis will delete from both primary and secondary storage.\nThis operation cannot be reversed.",
            icon='warning'
        )
        
        if not result:
            return
        
        # Delete the actual file from primary Images folder
        try:
            trail_maps_folder = sv.trail_maps_folder.get().strip()
            if trail_maps_folder:
                full_path = os.path.join(trail_maps_folder, filename)
            else:
                full_path = filename
            
            if os.path.exists(full_path):
                os.remove(full_path)
                # print(f"Deleted from primary: {full_path}")
                sv.t_status.set(f"Deleted file: {filename}")
            else:
                sv.t_status.set(f"Removed from list (file not found): {filename}")
            
            # Also delete from secondary Images folder if it exists there
            secondary_folder = get_secondary_images_folder()
            if secondary_folder:
                secondary_path = secondary_folder / filename
                if secondary_path.exists():
                    try:
                        secondary_path.unlink()
                        # print(f"Deleted from secondary: {secondary_path}")
                        pass
                    except Exception as e:
                        # print(f"Warning: Failed to delete from secondary: {e}")
                        pass
                        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete file:\n{str(e)}")
            return
        
        # Remove from list and listbox
        sv.t_map_files_list.pop(selected_index)
        self.map_listbox.delete(selected_index)
        
        if not sv.t_map_files_list:
            self.view_trail_map_button.config(state=tk.DISABLED)
            self.delete_trail_map_button.config(state=tk.DISABLED)
    
    def _open_external_file(self, file_path):
        """Open a file with the system's default application"""
        if not file_path:
            messagebox.showwarning("No File", "No file path specified")
            return
        
        # If not an absolute path, try trail maps folder
        if not os.path.isabs(file_path) and not os.path.exists(file_path):
            trail_maps_folder = sv.trail_maps_folder.get().strip()
            if trail_maps_folder:
                potential_path = os.path.join(trail_maps_folder, file_path)
                if os.path.exists(potential_path):
                    file_path = potential_path
        
        if not os.path.exists(file_path):
            messagebox.showerror("File Not Found", f"Could not find file:\n{file_path}")
            return
        
        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # macOS or Linux
                import subprocess
                import platform
                if platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', file_path])
                else:  # Linux
                    subprocess.run(['xdg-open', file_path])
        except Exception as e:
            messagebox.showerror("Error Opening File", f"Could not open file:\n{file_path}\n\nError: {str(e)}")
    
    # =========================================================================
    # Form state methods
    # =========================================================================
    
    def get_session_data(self):
        """Get all form data as a dictionary"""
        self._update_accumulated_distractions_string()
        
        # Convert map_files list to JSON string for database storage
        import json
        map_files_json = json.dumps(sv.t_map_files_list) if sv.t_map_files_list else ""
        
        return {
            't_date': sv.t_date.get(),
            't_session_number': sv.t_session.get(),
            't_handler': sv.t_handler.get(),
            't_field_support': sv.t_field_support.get(),
            't_dog_name': sv.t_dog.get(),
            't_location': sv.t_location.get(),
            't_start_time': sv.t_start_time.get(),
            't_finish_time': sv.t_finish_time.get(),
            't_trail_age': sv.t_trail_age.get(),
            't_trail_length': sv.t_trail_length.get(),
            't_difficulty': sv.t_difficulty.get(),
            't_trail_layer': sv.t_trail_layer.get(),
            't_cross_track_layer': sv.t_cross_track_layer.get(),
            't_cross_track_age': sv.t_cross_track_age.get(),
            # Weather when laying trail - use column names from schema
            't_weather_laying': sv.t_weather_laying.get(),
            't_temperature_laying': sv.t_temp_laying.get(),
            't_wind_speed_laying': sv.t_wind_laying.get(),
            't_wind_direction_laying': sv.t_wind_direction_laying.get(),
            't_humidity_laying': sv.t_humidity_laying.get(),
            # Weather at time of running trail
            't_weather_running': sv.t_weather_running.get(),
            't_temperature_running': sv.t_temp_running.get(),
            't_wind_speed_running': sv.t_wind_running.get(),
            't_wind_direction_running': sv.t_wind_direction_running.get(),
            't_humidity_running': sv.t_humidity_running.get(),
            # Behavior - use column names from schema
            't_start_behavior': sv.t_start_behavior.get(),
            't_consistency': sv.t_consistency.get(),
            't_head_position': sv.t_head_pos.get(),
            't_pace': sv.t_pace.get(),
            't_indication': sv.t_indication.get(),
            't_time_to_complete': sv.t_time.get(),
            't_success_rate': sv.t_success.get(),
            't_impression': self.impression_text.get("1.0", tk.END).strip(),
            't_map_files': map_files_json,
        }
    
    def set_session_data(self, data):
        """Populate form from a dictionary of session data"""
        import json as json_module
        
        date_str = data.get('t_date', datetime.now().strftime("%Y-%m-%d"))
        sv.t_date.set(date_str)
        # Also update the DateEntry picker
        try:
            self.date_picker.set_date(datetime.strptime(date_str, "%Y-%m-%d"))
        except (ValueError, AttributeError):
            pass
        sv.t_session.set(str(data.get('t_session_number', '')))
        sv.t_handler.set(data.get('t_handler', ''))
        sv.t_field_support.set(data.get('t_field_support', ''))
        sv.t_dog.set(data.get('t_dog_name', ''))
        sv.t_location.set(data.get('t_location', ''))
        sv.t_start_time.set(data.get('t_start_time', ''))
        
        # Also update the time picker widget
        start_time_str = data.get('t_start_time', '')
        if start_time_str:
            try:
                # Parse time - support both military format (HHMM) and HH:MM format
                if ':' in start_time_str:
                    # Legacy HH:MM format
                    hours, minutes = start_time_str.split(':')
                    self.start_time_picker.set24Hrs(int(hours))
                    self.start_time_picker.setMins(int(minutes))
                elif len(start_time_str) == 4 and start_time_str.isdigit():
                    # Military format HHMM (e.g., "1436")
                    hours = int(start_time_str[:2])
                    minutes = int(start_time_str[2:])
                    self.start_time_picker.set24Hrs(hours)
                    self.start_time_picker.setMins(minutes)
                elif len(start_time_str) == 3 and start_time_str.isdigit():
                    # Military format HMM (e.g., "936" for 9:36)
                    hours = int(start_time_str[0])
                    minutes = int(start_time_str[1:])
                    self.start_time_picker.set24Hrs(hours)
                    self.start_time_picker.setMins(minutes)
            except (ValueError, AttributeError):
                pass
        
        sv.t_finish_time.set(data.get('t_finish_time', ''))
        sv.t_trail_age.set(data.get('t_trail_age', ''))
        sv.t_trail_length.set(data.get('t_trail_length', ''))
        sv.t_difficulty.set(data.get('t_difficulty', ''))
        sv.t_trail_layer.set(data.get('t_trail_layer', ''))
        sv.t_cross_track_layer.set(data.get('t_cross_track_layer', 'None'))
        sv.t_cross_track_age.set(data.get('t_cross_track_age', ''))
        # Weather when laying trail - use column names from schema
        sv.t_weather_laying.set(data.get('t_weather_laying', ''))
        sv.t_temp_laying.set(data.get('t_temperature_laying', ''))
        sv.t_wind_laying.set(data.get('t_wind_speed_laying', ''))
        sv.t_wind_direction_laying.set(data.get('t_wind_direction_laying', ''))
        sv.t_humidity_laying.set(data.get('t_humidity_laying', ''))
        # Weather at time of running trail
        sv.t_weather_running.set(data.get('t_weather_running', ''))
        sv.t_temp_running.set(data.get('t_temperature_running', ''))
        sv.t_wind_running.set(data.get('t_wind_speed_running', ''))
        sv.t_wind_direction_running.set(data.get('t_wind_direction_running', ''))
        sv.t_humidity_running.set(data.get('t_humidity_running', ''))
        # Behavior - use column names from schema
        sv.t_start_behavior.set(data.get('t_start_behavior', ''))
        sv.t_consistency.set(data.get('t_consistency', ''))
        sv.t_head_pos.set(data.get('t_head_position', ''))
        sv.t_pace.set(data.get('t_pace', ''))
        sv.t_indication.set(data.get('t_indication', ''))
        sv.t_time.set(data.get('t_time_to_complete', ''))
        sv.t_success.set(data.get('t_success_rate', ''))
        
        # Impression text field
        self.impression_text.delete("1.0", tk.END)
        self.impression_text.insert("1.0", data.get('t_impression', ''))
        
        # Map files - parse JSON string from database
        map_files_data = data.get('t_map_files', '')
        if isinstance(map_files_data, str) and map_files_data:
            try:
                sv.t_map_files_list = json_module.loads(map_files_data)
            except:
                sv.t_map_files_list = []
        elif isinstance(map_files_data, list):
            sv.t_map_files_list = map_files_data
        else:
            sv.t_map_files_list = []
        
        self.map_listbox.delete(0, tk.END)
        for filepath in sv.t_map_files_list:
            self.map_listbox.insert(tk.END, os.path.basename(filepath))
        
        if sv.t_map_files_list:
            self.view_trail_map_button.config(state=tk.NORMAL)
            self.delete_trail_map_button.config(state=tk.NORMAL)
        else:
            self.view_trail_map_button.config(state=tk.DISABLED)
            self.delete_trail_map_button.config(state=tk.DISABLED)
        
        # Update session frame title based on status
        status = data.get('status', 'active')
        self.update_session_frame_title(status)
        
        self.take_form_snapshot()
    
    def update_session_frame_title(self, status):
        """Update the Session Information LabelFrame title based on status
        
        Args:
            status: 'active', 'deleted', or None
        """
        if hasattr(self, 'session_frame'):
            if status == 'deleted':
                self.session_frame.config(
                    text="Session Information *** MARKED HIDDEN ***",
                    foreground="red",
                    font=("TkDefaultFont", 9, "bold")
                )
            else:
                # Active or None (treat NULL as active)
                self.session_frame.config(
                    text="Session Information",
                    foreground="black",
                    font=("TkDefaultFont", 9)
                )
    
    def set_selected_purposes(self, purposes_list):
        """Populate purpose listbox from a list of purpose names"""
        self.purpose_listbox.delete(0, tk.END)
        for purpose in purposes_list:
            if purpose and purpose.strip():
                self.purpose_listbox.insert(tk.END, purpose.strip())
        self._update_purpose_scrollbar()
    
    def set_selected_terrains(self, terrains_list):
        """Populate terrain listbox from a list of terrain names"""
        self.terrain_listbox.delete(0, tk.END)
        for terrain in terrains_list:
            if terrain and terrain.strip():
                self.terrain_listbox.insert(tk.END, terrain.strip())
        self._update_terrain_scrollbar()
    
    def set_distractions(self, distractions_list):
        """Populate distraction treeview from a list of distraction dicts
        
        Args:
            distractions_list: List of dicts with 'type' and 'response' keys
        """
        for item in self.distraction_tree.get_children():
            self.distraction_tree.delete(item)
        
        for distraction in distractions_list:
            d_type = distraction.get('type', '')
            d_response = distraction.get('response', '')
            if d_type:
                self.distraction_tree.insert('', tk.END, values=(d_type, d_response))
        
        self._update_accumulated_distractions_string()
    
    def clear_form(self, keep_session=False):
        """Clear the entry form"""
        if not keep_session:
            sv.t_date.set(datetime.now().strftime("%Y-%m-%d"))
            if 'get_next_session_number' in self.callbacks:
                next_session = self.callbacks['get_next_session_number'](sv.t_dog.get())
                sv.t_session.set(str(next_session))
            else:
                sv.t_session.set("1")
        
        # Reset editing mode
        self.editing_session = False
        self.editing_row = None
        self.update_save_button_text()  # Change button back to "Save Session"
        
        # Reset navigation state
        self.dog_sessions_list = []
        self.current_session_index = -1
        self.prev_session_btn.config(state=tk.DISABLED)
        self.next_session_btn.config(state=tk.DISABLED)
        
        # Disable Hide/Restore buttons when not viewing a session
        if hasattr(self, 'hide_btn'):
            self.hide_btn.config(state=tk.DISABLED)
        if hasattr(self, 'resume_btn'):
            self.resume_btn.config(state=tk.DISABLED)
        
        # Keep handler: preserve current value, or get from config if empty
        current_handler = sv.t_handler.get()
        if not current_handler:
            current_handler = self._get_config_value('get_handler_name', "")
        sv.t_handler.set(current_handler)
        
        # Reset date picker to today
        try:
            self.date_picker.set_date(datetime.now())
        except AttributeError:
            pass
        
        # Clear all other fields
        sv.t_field_support.set("")
        sv.t_location.set("")
        sv.t_purpose.set("")
        self.purpose_listbox.delete(0, tk.END)
        self._update_purpose_scrollbar()
        sv.t_trail_age.set("")
        sv.t_trail_length.set("")
        self.terrain_listbox.delete(0, tk.END)
        self._update_terrain_scrollbar()
        sv.t_difficulty.set("")
        sv.t_trail_layer.set("")
        # sv.t_cross_track_layer.set("None") ahg
        sv.t_cross_track_age.set("")
        # Weather when laying trail
        sv.t_weather_laying.set("")
        sv.t_temp_laying.set("")
        sv.t_wind_laying.set("")
        sv.t_wind_direction_laying.set("")
        sv.t_humidity_laying.set("")
        # Weather at time of running trail
        sv.t_weather_running.set("")
        sv.t_temp_running.set("")
        sv.t_wind_running.set("")
        sv.t_wind_direction_running.set("")
        sv.t_humidity_running.set("")
        sv.t_start_behavior.set("")
        sv.t_consistency.set("")
        sv.t_head_pos.set("")
        sv.t_pace.set("")
        sv.t_indication.set("")
        sv.t_distractions.set("")
        sv.t_distraction_response.set("")
        sv.t_accumulated_distractions.set("")
        sv.t_start_time.set("")
        sv.t_finish_time.set("")
        
        # Reset time picker to midnight (00:00)
        try:
            self.start_time_picker.set24Hrs(0)
            self.start_time_picker.setMins(0)
        except AttributeError:
            pass
        
        # Clear distraction table
        for item in self.distraction_tree.get_children():
            self.distraction_tree.delete(item)
        self.selected_distraction_index = None
        
        sv.t_success.set("")
        sv.t_time.set("")
        self.impression_text.delete("1.0", tk.END)
        sv.t_map_files_list = []
        self.map_listbox.delete(0, tk.END)
        self.view_trail_map_button.config(state=tk.DISABLED)
        self.delete_trail_map_button.config(state=tk.DISABLED)
        
        sv.t_status.set("Form cleared")
        
        # Reset session frame title
        self.update_session_frame_title('active')
        
        self.take_form_snapshot()
    
    def get_form_state_string(self):
        """Get a string representation of all form fields for comparison"""
        parts = [
            sv.t_date.get(),
            sv.t_session.get(),
            sv.t_dog.get(),
            sv.t_handler.get(),
            sv.t_field_support.get(),
            ", ".join(self.purpose_listbox.get(0, tk.END)),
            sv.t_location.get(),
            sv.t_start_time.get(),
            sv.t_finish_time.get(),
            sv.t_trail_age.get(),
            sv.t_trail_length.get(),
            ", ".join(self.terrain_listbox.get(0, tk.END)),
            sv.t_difficulty.get(),
            sv.t_trail_layer.get(),
            sv.t_cross_track_layer.get(),
            sv.t_cross_track_age.get(),
            # Weather when laying trail
            sv.t_weather_laying.get(),
            sv.t_temp_laying.get(),
            sv.t_wind_laying.get(),
            sv.t_wind_direction_laying.get(),
            sv.t_humidity_laying.get(),
            # Weather at time of running trail
            sv.t_weather_running.get(),
            sv.t_temp_running.get(),
            sv.t_wind_running.get(),
            sv.t_wind_direction_running.get(),
            sv.t_humidity_running.get(),
            sv.t_start_behavior.get(),
            sv.t_consistency.get(),
            sv.t_head_pos.get(),
            sv.t_pace.get(),
            sv.t_indication.get(),
            sv.t_time.get(),
            sv.t_success.get(),
            self.impression_text.get("1.0", tk.END).strip(),
        ]
        
        # Add distractions from the table
        for item in self.distraction_tree.get_children():
            values = self.distraction_tree.item(item, 'values')
            if len(values) >= 2:
                parts.append(f"{values[0]}:{values[1]}")
        
        return "|".join(parts)
    
    def take_form_snapshot(self):
        """Take a snapshot of the current form state"""
        self.form_snapshot = self.get_form_state_string()
    
    def has_unsaved_changes(self):
        """Check if the form has unsaved changes"""
        current_state = self.get_form_state_string()
        return current_state != self.form_snapshot
    
    # =========================================================================
    # Methods for updating config-driven UI elements
    # =========================================================================
    
    def update_dog_list(self, dog_names):
        """Update the dog combobox values"""
        self.dog_combo['values'] = dog_names
    
    def update_location_list(self, locations):
        """Update the location combobox values"""
        self.location_combo['values'] = sorted(locations)
    
    def update_terrain_types(self, terrain_types):
        """Update the terrain combobox values"""
        self.terrain_combo['values'] = terrain_types
    
    def update_distraction_types(self, distraction_types):
        """Update the distraction combobox values"""
        self.distraction_combo['values'] = distraction_types
    
    def set_status(self, message):
        """Set the status message"""
        sv.t_status.set(message)
    
    def enable_drag_drop(self, dnd_module):
        """
        Enable drag-and-drop support if tkinterdnd2 is available.
        
        Args:
            dnd_module: The tkinterdnd2 module or DND_FILES constant
        """
        try:
            if hasattr(self, 'impression_map_frame'):
                self.impression_map_frame.drop_target_register(dnd_module)
                self.impression_map_frame.dnd_bind('<<Drop>>', self._handle_drop)
                self.impression_map_frame.dnd_bind('<<DragEnter>>', self._drag_enter)
                self.impression_map_frame.dnd_bind('<<DragLeave>>', self._drag_leave)
        except Exception as e:
            # print(f"Could not enable drag-drop: {e}")
            pass


# Example usage / testing
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Trailing Entry Tab Test")
    root.geometry("1200x900")
    
    # Initialize sv module with the root window
    sv.initialize(root)
    
    # Create a notebook for testing
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Create the entry tab
    entry_frame = ttk.Frame(notebook)
    notebook.add(entry_frame, text="Training Session Entry")
    
    # Simple config provider for testing
    class TestConfig:
        def get_handler_name(self):
            return "Test Handler"
        
        def get_dog_names(self):
            return ["Buddy", "Max", "Luna"]
        
        def get_last_dog_name(self):
            return "Buddy"
        
        def get_terrain_types(self):
            return ["Urban", "Rural", "Forest", "Desert", "Mixed"]
        
        def get_distraction_types(self):
            return ["Critter", "Vehicle", "Hikers", "Other animals"]
        
        def get_training_locations(self):
            return ["Park A", "Trail B", "Open Space C"]
    
    # Test callbacks
    def on_save(data):
        # print("Save requested with data:")
        for k, v in data.items():
            # print(f"  {k}: {v}")
            pass
        return True
    
    callbacks = {
        'on_save': on_save,
        'get_next_session_number': lambda dog: 1,
    }
    
    tab = TrailingEntryTab(entry_frame, TestConfig(), callbacks)
    
    # Status bar
    status_bar = tk.Label(root, textvariable=sv.t_status, bd=1, relief=tk.SUNKEN, anchor=tk.W)
    status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    root.mainloop()
