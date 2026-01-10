#!/usr/bin/env python3
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
from datetime import datetime
import os


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
        
        # Status variable (can be linked to parent's status bar)
        self.t_status_var = tk.StringVar(value="Ready")
        
        # Initialize tracking variables
        self.selected_distraction_index = None
        self.selected_distraction_original = None
        self.editing_session = False
        self.editing_row = None
        self.dog_sessions_list = []
        self.current_session_index = -1
        self.form_snapshot = ""
        self.map_files_list = []
        
        # Build the UI
        self._create_widgets()
    
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
        canvas = tk.Canvas(self.parent)
        scrollbar = ttk.Scrollbar(self.parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        frame = tk.Frame(scrollable_frame, padx=20, pady=20)
        frame.pack(fill="both", expand=True)
        
        # Build sections
        self._create_session_info_section(frame)
        self._create_trail_details_section(frame)
        self._create_weather_section(frame)
        self._create_behavior_section(frame)
        self._create_distractions_section(frame)
        self._create_impression_section(frame)
        self._create_trail_map_section(frame)
        self._create_notes_section(frame)
        self._create_buttons_section(frame)
        
        # Configure grid weights
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)
    
    def _create_session_info_section(self, frame):
        """Create Session Information section (airscenting-style layout with purpose accumulator)"""
        session_frame = tk.LabelFrame(frame, text="Session Information", padx=10, pady=5)
        session_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
        
        # Row 0: Date, Session #, and action buttons
        tk.Label(session_frame, text="Date:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        # Use DateEntry for date picker
        self.t_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
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
        self.t_session_var = tk.StringVar(value="1")
        self.session_entry = tk.Entry(session_frame, textvariable=self.t_session_var, width=10)
        self.session_entry.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        tk.Button(session_frame, text="New", command=self._new_session).grid(row=0, column=4, padx=5)
        
        tk.Button(session_frame, text="View/Edit/Hide Prior Session(s)", 
                 command=self._load_prior_session, bg="#4169E1", fg="white").grid(row=0, column=5,sticky='e', padx=5, pady=2)
        
        # Navigation buttons
        self.prev_session_btn = tk.Button(session_frame, text="◀ Previous", bg="#FF8C00", fg="white", 
                                         width=10, command=self._navigate_previous_session, state=tk.DISABLED)
        self.prev_session_btn.grid(row=0, column=6, padx=2, pady=2)
        
        self.next_session_btn = tk.Button(session_frame, text="Next ▶", bg="#FF8C00", fg="white",
                                         width=10, command=self._navigate_next_session, state=tk.DISABLED)
        self.next_session_btn.grid(row=0, column=7, padx=2, pady=2)
        
        # Export PDF button
        tk.Button(session_frame, text="Export PDF", bg="#9370DB", fg="white", 
                 width=12, command=self._export_pdf).grid(row=0, column=8, padx=2, pady=2)
        
        # Row 1: Handler, Add Session Purpose + accumulator
        tk.Label(session_frame, text="Handler:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.t_handler_var = tk.StringVar(value=self._get_config_value('get_handler_name', ""))
        tk.Entry(session_frame, textvariable=self.t_handler_var, width=15).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(session_frame, text="Add Session Purpose:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self.t_purpose_var = tk.StringVar()
        self.purpose_combo = ttk.Combobox(session_frame, textvariable=self.t_purpose_var, width=16, state="enabled",
                                     values=['Flagged Trail', 'Unmarked Trail', 'Single Blind', 'Double Blind',
                                            'Motivational', 'Scent Discrimination', 
                                            'Obedience', 'Mock Cert Test', 'Mission'])
        self.purpose_combo.grid(row=1, column=3, sticky="w", padx=5, pady=2)
        self.purpose_combo.bind('<<ComboboxSelected>>', self._add_to_purpose_accumulator)
        
        # Session Purposes listbox (accumulator)
        purpose_list_frame = tk.Frame(session_frame)
        purpose_list_frame.grid(row=1, column=4, rowspan=2, columnspan=2, sticky="w", padx=5, pady=2)
        
        tk.Label(purpose_list_frame, text="Session Purposes:\n\n").pack(side=tk.LEFT, padx=(0, 5))
        
        self.purpose_listbox = tk.Listbox(purpose_list_frame, height=3, width=20)
        self.purpose_listbox.pack(side=tk.LEFT)
        self.purpose_listbox.bind('<Double-Button-1>', self._remove_purpose_from_list)
        ToolTip(self.purpose_listbox, "Session Purposes\nDouble-click an entry to remove from list", delay=750)
        
        # Scrollbar for purpose listbox (initially hidden)
        self.purpose_scrollbar = tk.Scrollbar(purpose_list_frame, orient="vertical", command=self.purpose_listbox.yview)
        self.purpose_listbox.config(yscrollcommand=self.purpose_scrollbar.set)
        
        # Row 2: Field Support, Dog, Resume/Hide buttons (aligned with Previous/Next)
        tk.Label(session_frame, text="Field Support:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.t_field_support_var = tk.StringVar()
        tk.Entry(session_frame, textvariable=self.t_field_support_var, width=15).grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(session_frame, text="Dog:").grid(row=2, column=2, sticky="e", padx=5, pady=2)
        self.t_dog_var = tk.StringVar(value=self._get_config_value('get_last_dog_name', ""))
        self.dog_combo = ttk.Combobox(session_frame, textvariable=self.t_dog_var, width=16, state="readonly")
        self.dog_combo['values'] = self._get_config_list('get_dog_names', [])
        self.dog_combo.grid(row=2, column=3, sticky="w", padx=5, pady=2)
        self.dog_combo.bind('<<ComboboxSelected>>', self._on_dog_changed)
        
        # Resume and Hide buttons (aligned with Previous/Next in columns 6-7)
        self.resume_btn = tk.Button(session_frame, text="Restore", bg="#28a745", fg="white",
                                   width=10, command=self._resume_session, state=tk.DISABLED)
        self.resume_btn.grid(row=2, column=6, padx=2, pady=2)
        
        self.hide_btn = tk.Button(session_frame, text="Hide", bg="#dc3545", fg="white",
                                 width=10, command=self._hide_session, state=tk.DISABLED)
        self.hide_btn.grid(row=2, column=7, padx=2, pady=2)
    
    def _create_trail_details_section(self, frame):
        """Create Trail Details section"""
        trail_frame = tk.LabelFrame(frame, text="Trail Details", padx=10, pady=5)
        trail_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        
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
        self.t_location_var = tk.StringVar()
        self.location_combo = ttk.Combobox(trail_frame, textvariable=self.t_location_var, width=location_width,
                                          values=sorted(locations))
        self.location_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        self.location_combo.bind('<FocusOut>', self._on_location_focus_out)
        
        tk.Label(trail_frame, text="Add Terrain Type:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
        self.t_terrain_var = tk.StringVar()
        self.terrain_combo = ttk.Combobox(trail_frame, textvariable=self.t_terrain_var, width=terrain_width, 
                                         state="readonly", values=terrain_types)
        self.terrain_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        self.terrain_combo.bind('<<ComboboxSelected>>', self._add_to_terrain_accumulator)
        
        # Terrain listbox
        tk.Label(trail_frame, text="Terrain types:").grid(row=0,column=4,sticky="e",padx=5,pady=2)
        self.terrain_listbox = tk.Listbox(trail_frame, height=3, width=entry_terrain_width)
        self.terrain_listbox.grid(row=0, column=5, sticky="wn", rowspan=3, padx=(5, 0), pady=2)
        self.terrain_listbox.bind('<Double-Button-1>', self._remove_terrain_from_list)
        ToolTip(self.terrain_listbox, "Terrain List Accumulator\nDouble-click an entry to remove from list", delay=750)
        
        # Scrollbar for terrain listbox
        self.terrain_scrollbar = tk.Scrollbar(trail_frame, orient="vertical", command=self.terrain_listbox.yview)
        self.terrain_listbox.config(yscrollcommand=self.terrain_scrollbar.set)
        
        # Start time
        time_location_width = 12
        tk.Label(trail_frame, text="Start Time:").grid(row=0, column=6, sticky="w", padx=5, pady=2)
        self.t_start_time_var = tk.StringVar()
        tk.Entry(trail_frame, textvariable=self.t_start_time_var, width=time_location_width).grid(row=0, column=7, sticky="w", padx=5, pady=2)
        
        # Finish time
        tk.Label(trail_frame, text="Finish Time:").grid(row=0, column=8, sticky="w", padx=5, pady=2)
        self.t_finish_time_var = tk.StringVar()
        tk.Entry(trail_frame, textvariable=self.t_finish_time_var, width=time_location_width).grid(row=0, column=9, sticky="w", padx=5, pady=2)
        
        # Row 1: Trail Age, Trail Length, Trail Difficulty
        tk.Label(trail_frame, text="Trail Age (hours):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.t_trail_age_var = tk.StringVar()
        tk.Entry(trail_frame, textvariable=self.t_trail_age_var, width=entry_location_width).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(trail_frame, text="Trail Length (miles):").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self.t_trail_length_var = tk.StringVar()
        tk.Entry(trail_frame, textvariable=self.t_trail_length_var, width=entry_terrain_width).grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(trail_frame, text="Trail Difficulty:").grid(row=1, column=6, sticky="w", padx=5, pady=2)
        self.t_difficulty_var = tk.StringVar()
        difficulty_combo = ttk.Combobox(trail_frame, textvariable=self.t_difficulty_var, width=9, state="readonly",
                                        values=['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'])
        difficulty_combo.grid(row=1, column=7, sticky="w", padx=5, pady=2)

        # Row 2 Trail Layer, Cross Track Layer, Cross Track Age
        tk.Label(trail_frame,text="Trail Layer").grid(row=2,column=0,sticky="w",padx=5,pady=2)
        self.t_trail_layer_var = tk.StringVar()
        tk.Entry(trail_frame,textvariable=self.t_trail_layer_var,width=entry_location_width).grid(row=2,column=1,padx=4,pady=2)

        tk.Label(trail_frame,text="Cross Track Layer:").grid(row=2,column=2,sticky="e",padx=5,pady=2)
        self.t_cross_track_layer_var = tk.StringVar(value="None")
        tk.Entry(trail_frame,textvariable=self.t_cross_track_layer_var,width=entry_terrain_width).grid(row=2,column=3,sticky="w",padx=4,pady=2)

        tk.Label(trail_frame,text="Cross Track Age:").grid(row=2,column=4,sticky="e",padx=5,pady=2)
        self.t_cross_track_age_var = tk.StringVar()
        tk.Entry(trail_frame,textvariable=self.t_cross_track_age_var,width=entry_terrain_width).grid(row=2,column=5,sticky="w",padx=5,pady=(5,2))



    def _create_weather_section(self, frame):
        """Create Weather subframes"""

        # Row 2 Weather frame container
        weather_frame_container = tk.Frame(frame)
        weather_frame_container.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        self._create_weather_laying_section(weather_frame_container)
        self._create_weather_running_section(weather_frame_container)
    
    def _create_weather_laying_section(self, frame):
        """Create Weather When Laying Trail section"""
        weather_frame = tk.LabelFrame(frame, text="Weather When Laying Trail and While Aging", padx=10, pady=5)
        weather_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        tk.Label(weather_frame, text="Weather:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.t_weather_laying_var = tk.StringVar()
        weather_combo = ttk.Combobox(weather_frame, textvariable=self.t_weather_laying_var, width=12,
                                     values=["Clear", "Cloudy", "Light Rain", "Heavy Rain", "Windy", "Snow", "Fog", "Hot/Sunny"])
        weather_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Wind Direction:").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.t_wind_direction_laying_var = tk.StringVar()
        wind_dir_combo = ttk.Combobox(weather_frame, textvariable=self.t_wind_direction_laying_var, width=12,
                                     values=["North", "South", "East", "West", "NE", "NW", "SE", "SW"])
        wind_dir_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Temperature (°F):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.t_temp_laying_var = tk.StringVar()
        tk.Entry(weather_frame, textvariable=self.t_temp_laying_var, width=15).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Humidity (%):").grid(row=1, column=2, sticky="e", padx=5, pady=2)
        self.t_humidity_laying_var = tk.StringVar()
        tk.Entry(weather_frame, textvariable=self.t_humidity_laying_var, width=15).grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Wind Speed:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.t_wind_laying_var = tk.StringVar()
        tk.Entry(weather_frame, textvariable=self.t_wind_laying_var, width=15).grid(row=2, column=1, sticky="w", padx=5, pady=2)
    
    def _create_weather_running_section(self, frame):
        """Create Weather at Time of Running Trail section"""
        weather_frame = tk.LabelFrame(frame, text="Weather at Time of Running Trail", padx=10, pady=5)
        weather_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        tk.Label(weather_frame, text="Weather:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.t_weather_running_var = tk.StringVar()
        weather_combo = ttk.Combobox(weather_frame, textvariable=self.t_weather_running_var, width=12,
                                     values=["Clear", "Cloudy", "Light Rain", "Heavy Rain", "Windy", "Snow", "Fog", "Hot/Sunny"])
        weather_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Wind Direction:").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.t_wind_direction_running_var = tk.StringVar()
        wind_dir_combo = ttk.Combobox(weather_frame, textvariable=self.t_wind_direction_running_var, width=12,
                                     values=["North", "South", "East", "West", "NE", "NW", "SE", "SW"])
        wind_dir_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Temperature (°F):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.t_temp_running_var = tk.StringVar()
        tk.Entry(weather_frame, textvariable=self.t_temp_running_var, width=15).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Humidity (%):").grid(row=1, column=2, sticky="e", padx=5, pady=2)
        self.t_humidity_running_var = tk.StringVar()
        tk.Entry(weather_frame, textvariable=self.t_humidity_running_var, width=15).grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Wind Speed:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.t_wind_running_var = tk.StringVar()
        tk.Entry(weather_frame, textvariable=self.t_wind_running_var, width=15).grid(row=2, column=1, sticky="w", padx=5, pady=2)
    
    def _create_behavior_section(self, frame):
        """Create Dog Behavior & Performance section"""
        behavior_frame = tk.LabelFrame(frame, text="Dog Behavior & Performance", padx=10, pady=5)
        behavior_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
        
        tk.Label(behavior_frame, text="Start Behavior:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.t_start_behavior_var = tk.StringVar()
        ttk.Combobox(behavior_frame, textvariable=self.t_start_behavior_var, width=54,
                    values=["Excellent—Direction of Travel immediately identified ",
                            "Very Good—Direction of travel not imediately identified",
                            "Good—Direction of travel identified with cueing",
                            "Fair—Direction of travel not identified",
                            "Poor—Direction of travel incorrectly identified",
                            "Needs Work—Could not identify trail"]).grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(behavior_frame, text="Pace:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
        self.t_pace_var = tk.StringVar()
        ttk.Combobox(behavior_frame, textvariable=self.t_pace_var, width=18,
                    values=["Fast", "Moderate", "Slow", "Variable"]).grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        # Start time and run time
        tk.Label(behavior_frame, text="Time to Complete (min):").grid(row=0, column=4, sticky="w", padx=5, pady=2)
        self.t_time_var = tk.StringVar()
        tk.Entry(behavior_frame, textvariable=self.t_time_var, width=15).grid(row=0, column=5, sticky="w", padx=5, pady=2)
        
        tk.Label(behavior_frame, text="Start Time:").grid(row=1, column=4, sticky="e", padx=5, pady=2)
        self.t_start_time_var = tk.StringVar()
        tk.Entry(behavior_frame, textvariable=self.t_start_time_var, width=15).grid(row=1, column=5, sticky="w", padx=5, pady=2)

        # Hidden head position var (kept for compatibility)
        self.t_head_pos_var = tk.StringVar()
        
        tk.Label(behavior_frame, text="Tracking Consistency:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self.t_consistency_var = tk.StringVar()
        ttk.Combobox(behavior_frame, textvariable=self.t_consistency_var, width=18,
                    values=["Excellent", "Good", "Fair", "Poor", "Needs Work"]).grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(behavior_frame, text="Indication at Find:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.t_indication_var = tk.StringVar()
        ttk.Combobox(behavior_frame, textvariable=self.t_indication_var, width=54,
                    values=["Immediate Trained Final Response",
                            "Strong Alert—Exhibited Trained Final Response after hesitation",
                            "Moderate Alert—Alert behavior but no TFR",
                            "Weak Alert—Hesitant, before clear response, needed cueing", 
                            "No Clear Indication"]).grid(row=1, column=1, sticky="w", padx=5, pady=2)
    
    def _create_distractions_section(self, frame):
        """Create Distractions section"""
        distraction_frame = tk.LabelFrame(frame, text="Distractions", padx=10, pady=5)
        distraction_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
        
        self.t_distractions_var = tk.StringVar()
        self.t_distraction_response_var = tk.StringVar()
        self.t_accumulated_distractions_var = tk.StringVar()
        
        # Input row
        tk.Label(distraction_frame, text="Distraction:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        distraction_types = self._get_config_list('get_distraction_types', self._get_default_distraction_types())
        self.distraction_combo = ttk.Combobox(distraction_frame, textvariable=self.t_distractions_var, width=20,
                                             values=distraction_types)
        self.distraction_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(distraction_frame, text="Response:").grid(row=0, column=1, sticky="e", padx=5, pady=2)
        self.response_combo = ttk.Combobox(distraction_frame, textvariable=self.t_distraction_response_var, width=20,
                    values=["Ignored", "Brief Check", "Prolonged Interest", "Lost Trail", "Recovered Quickly", "Scared", "Panicked", "Ate"],
                    state="disabled")
        self.response_combo.grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.response_combo.bind('<<ComboboxSelected>>', self._on_response_selected)
        self.response_combo.bind('<Return>', self._on_response_selected)
        
        # Trace for enabling/disabling response combo
        self.t_distractions_var.trace_add('write', self._on_distraction_change)
        
        # Table and buttons
        tk.Label(distraction_frame, text="Accumulated\nDistractions:").grid(row=1, column=0, sticky="nw", padx=5, pady=(10,2))
        
        table_container = tk.Frame(distraction_frame)
        table_container.grid(row=1, column=1, columnspan=3, sticky="ew", padx=5, pady=(10,2))
        
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
        self.t_distractions_var.trace_add('write', self._update_distraction_button_states)
    
    def _create_impression_section(self, frame):
        """Create Overall Impression section"""
        results_frame = tk.LabelFrame(frame, text="Overall Impression", padx=10, pady=5)
        results_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=5)
        
        # Hidden success var (kept for compatibility)
        self.t_success_var = tk.StringVar()
        
        self.t_impression_var = tk.StringVar()
        impression_container = tk.Frame(results_frame)
        impression_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.impression_text = tk.Text(impression_container, height=4, wrap=tk.WORD)
        impression_scrollbar = ttk.Scrollbar(impression_container, orient=tk.VERTICAL, command=self.impression_text.yview)
        self.impression_text.config(yscrollcommand=impression_scrollbar.set)
        
        self.impression_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        impression_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_trail_map_section(self, frame):
        """Create Trail Map section"""
        map_frame = tk.LabelFrame(frame, text="Trail Map", padx=10, pady=5)
        map_frame.grid(row=6, column=0, sticky="nsew", pady=5, padx=(0, 2.5))
        
        map_container = tk.Frame(map_frame)
        map_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Drag and drop area
        drop_frame = tk.Frame(map_container)
        drop_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.drop_label = tk.Label(
            drop_frame,
            text="Drag & Drop Trail Maps\n(PDF/JPG/PNG)",
            bg="#e0e0e0",
            relief="ridge",
            height=4
        )
        self.drop_label.pack(fill=tk.BOTH, expand=True)
        
        # Note: Drag-and-drop requires tkinterdnd2 which may not be available
        # If using with tkinterdnd2, enable with:
        # self.drop_label.drop_target_register(DND_FILES)
        # self.drop_label.dnd_bind('<<Drop>>', self._handle_drop)
        # self.drop_label.dnd_bind('<<DragEnter>>', self._drag_enter)
        # self.drop_label.dnd_bind('<<DragLeave>>', self._drag_leave)
        
        # Listbox with buttons
        list_frame = tk.Frame(map_container)
        list_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        list_button_container = tk.Frame(list_frame)
        list_button_container.pack(fill=tk.BOTH, expand=True)
        
        listbox_container = tk.Frame(list_button_container)
        listbox_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.map_listbox = tk.Listbox(listbox_container, height=3, font=('Arial', 9))
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
        
        # Browse button as fallback when dnd not available
        tk.Button(map_button_frame, text="Browse...", command=self._browse_trail_map, width=12).pack(pady=(2, 0))
    
    def _create_notes_section(self, frame):
        """Create Notes section"""
        notes_frame = tk.LabelFrame(frame, text="Notes", padx=10, pady=5)
        notes_frame.grid(row=6, column=1, sticky="nsew", pady=5, padx=(2.5, 0))
        
        notes_container = tk.Frame(notes_frame)
        notes_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.notes_text = tk.Text(notes_container, height=4, width=35, wrap=tk.WORD)
        notes_scrollbar = ttk.Scrollbar(notes_container, orient=tk.VERTICAL, command=self.notes_text.yview)
        self.notes_text.config(yscrollcommand=notes_scrollbar.set)
        
        self.notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        notes_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_buttons_section(self, frame):
        """Create action buttons section"""
        button_frame = tk.Frame(frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=10)
        
        tk.Button(button_frame, text="Save Session", command=self._save_session,
                 bg="#4CAF50", fg="white", font=("Helvetica", 12, "bold"),
                 width=25, height=2).pack(side="left", padx=10)
        
        tk.Button(button_frame, text="Clear Form", command=self._clear_form_with_check,
                 width=15).pack(side="left", padx=10)
        
        tk.Button(button_frame, text="Quit", command=self._quit,
                 width=10).pack(side="left", padx=10)
    
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
        selected_dog = self.t_dog_var.get()
        if selected_dog and 'on_dog_changed' in self.callbacks:
            self.callbacks['on_dog_changed'](selected_dog)
        
        # Update session number
        if 'get_next_session_number' in self.callbacks:
            next_session = self.callbacks['get_next_session_number'](selected_dog)
            self.t_session_var.set(str(next_session))
    
    def _auto_increment_session(self):
        """Auto-increment session number"""
        dog_name = self.t_dog_var.get()
        if 'get_next_session_number' in self.callbacks:
            next_session = self.callbacks['get_next_session_number'](dog_name)
            self.t_session_var.set(str(next_session))
    
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
        self.t_status_var.set("New session started")
    
    def _on_date_changed(self, event=None):
        """Handle date picker change - update the date_var StringVar"""
        selected_date = self.date_picker.get_date()
        self.t_date_var.set(selected_date.strftime("%Y-%m-%d"))
    
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
                self.t_status_var.set("Session saved successfully")
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
        if 'on_quit' in self.callbacks:
            self.callbacks['on_quit']()
        else:
            self.parent.master.quit()
    
    def _on_location_focus_out(self, event):
        """Handle location field losing focus - prompt to add new location"""
        location = self.t_location_var.get().strip()
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
        terrain_type = self.t_terrain_var.get()
        if terrain_type:
            current_items = self.terrain_listbox.get(0, tk.END)
            if terrain_type in current_items:
                messagebox.showinfo("Duplicate", f"'{terrain_type}' is already in the list")
                self.t_terrain_var.set("")
                return
            
            self.terrain_listbox.insert(tk.END, terrain_type)
            self.t_terrain_var.set("")
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
        """Show or hide terrain scrollbar based on number of items"""
        item_count = self.terrain_listbox.size()
        if item_count > 4:
            self.terrain_scrollbar.grid(row=0, column=5, sticky="ns", rowspan=3, pady=2)
        else:
            self.terrain_scrollbar.grid_remove()
    
    # =========================================================================
    # Session Purpose accumulator methods
    # =========================================================================
    
    def _add_to_purpose_accumulator(self, event):
        """Add selected session purpose to the listbox"""
        purpose = self.t_purpose_var.get()
        if purpose:
            current_items = self.purpose_listbox.get(0, tk.END)
            if purpose in current_items:
                messagebox.showinfo("Duplicate", f"'{purpose}' is already in the list")
                self.t_purpose_var.set("")
                return
            
            self.purpose_listbox.insert(tk.END, purpose)
            self.t_purpose_var.set("")
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
        """Show or hide purpose scrollbar based on number of items"""
        item_count = self.purpose_listbox.size()
        if item_count > 2:
            self.purpose_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        else:
            self.purpose_scrollbar.pack_forget()
    
    # =========================================================================
    # Distraction methods
    # =========================================================================
    
    def _on_distraction_change(self, *args):
        """Enable/disable response combobox based on distraction field content"""
        distraction = self.t_distractions_var.get().strip()
        if distraction:
            self.response_combo.config(state="normal")
        else:
            self.response_combo.config(state="disabled")
    
    def _on_response_selected(self, event):
        """Handle response combobox selection"""
        if self.selected_distraction_index:
            self._update_selected_distraction()
        elif self.t_distractions_var.get().strip():
            self._add_to_distraction_accumulator()
    
    def _add_to_distraction_accumulator(self, event=None):
        """Add distraction to table"""
        distraction = self.t_distractions_var.get().strip()
        response = self.t_distraction_response_var.get().strip()
        
        if not distraction:
            messagebox.showwarning("Empty Distraction", "Please enter a distraction")
            return
        
        if not response:
            messagebox.showwarning("Empty Response", "Please select a response")
            return
        
        self.distraction_tree.insert('', tk.END, values=(distraction, response))
        self._update_accumulated_distractions_string()
        
        self.distraction_tree.selection_remove(self.distraction_tree.selection())
        self.t_distractions_var.set("")
        self.t_distraction_response_var.set("")
        self.selected_distraction_index = None
        self.selected_distraction_original = None
        
        self.t_status_var.set("Distraction added")
    
    def _on_distraction_select(self, event):
        """Handle selection of a distraction in the table"""
        selection = self.distraction_tree.selection()
        if selection:
            item = selection[0]
            values = self.distraction_tree.item(item, 'values')
            if values:
                self.t_distractions_var.set(values[0])
                self.t_distraction_response_var.set(values[1])
                self.selected_distraction_index = item
                self.selected_distraction_original = values[0]
                self.t_status_var.set("Selected distraction - you can now Update or Delete it")
                self._update_distraction_button_states()
        else:
            self.selected_distraction_index = None
            self.selected_distraction_original = None
            self._update_distraction_button_states()
    
    def _update_distraction_button_states(self, *args):
        """Update the state of distraction management buttons"""
        distraction = self.t_distractions_var.get().strip()
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
        
        distraction = self.t_distractions_var.get().strip()
        response = self.t_distraction_response_var.get().strip()
        
        if not distraction or not response:
            messagebox.showwarning("Empty Fields", "Both distraction and response are required")
            return
        
        self.distraction_tree.item(self.selected_distraction_index, values=(distraction, response))
        self._update_accumulated_distractions_string()
        
        self.distraction_tree.selection_remove(self.distraction_tree.selection())
        self.t_distractions_var.set("")
        self.t_distraction_response_var.set("")
        self.selected_distraction_index = None
        self.selected_distraction_original = None
        
        self.t_status_var.set("Distraction updated")
    
    def _delete_selected_distraction(self):
        """Delete the selected distraction from the table"""
        selection = self.distraction_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a distraction from the table first")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this distraction?"):
            self.distraction_tree.delete(selection[0])
            self._update_accumulated_distractions_string()
            
            self.t_distractions_var.set("")
            self.t_distraction_response_var.set("")
            self.selected_distraction_index = None
            self.selected_distraction_original = None
            
            self.t_status_var.set("Distraction deleted")
    
    def _clear_distraction_fields(self):
        """Clear the distraction input fields"""
        self.distraction_tree.selection_remove(self.distraction_tree.selection())
        self.t_distractions_var.set("")
        self.t_distraction_response_var.set("")
        self.selected_distraction_index = None
        self.selected_distraction_original = None
        self.t_status_var.set("Distraction fields cleared")
    
    def _update_accumulated_distractions_string(self):
        """Update the accumulated distractions string from the treeview"""
        distractions_list = []
        for item in self.distraction_tree.get_children():
            values = self.distraction_tree.item(item, 'values')
            if values:
                distractions_list.append(f"{values[0]}:{values[1]}")
        
        self.t_accumulated_distractions_var.set(", ".join(distractions_list))
    
    # =========================================================================
    # Trail map methods
    # =========================================================================
    
    def _drag_enter(self, event):
        """Visual feedback when dragging over drop zone"""
        self.drop_label.configure(bg="#90EE90")
    
    def _drag_leave(self, event):
        """Reset visual feedback"""
        self.drop_label.configure(bg="#e0e0e0")
    
    def _handle_drop(self, event):
        """Handle dropped files"""
        self.drop_label.configure(bg="#e0e0e0")
        
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
                if ext in ['.pdf', '.jpg', '.jpeg', '.png']:
                    valid_files.append(filepath)
        
        if valid_files:
            self._add_map_files(valid_files)
        else:
            messagebox.showerror("Error", "Only PDF, JPG, and PNG files supported!")
    
    def _browse_trail_map(self):
        """Browse for trail map file"""
        filepaths = filedialog.askopenfilenames(
            title="Select Trail Map(s)",
            filetypes=[
                ("Image/PDF files", "*.pdf *.jpg *.jpeg *.png"),
                ("All files", "*.*")
            ]
        )
        if filepaths:
            self._add_map_files(list(filepaths))
    
    def _add_map_files(self, filepaths):
        """Add map files to the list"""
        self.map_files_list.extend(filepaths)
        # Remove duplicates while preserving order
        seen = set()
        self.map_files_list = [x for x in self.map_files_list if not (x in seen or seen.add(x))]
        
        self.map_listbox.delete(0, tk.END)
        for filepath in self.map_files_list:
            self.map_listbox.insert(tk.END, os.path.basename(filepath))
        
        self.view_trail_map_button.config(state=tk.NORMAL)
        self.delete_trail_map_button.config(state=tk.NORMAL)
        
        self.t_status_var.set(f"{len(filepaths)} trail map(s) added")
    
    def _view_selected_trail_map(self):
        """Open the selected trail map file"""
        selection = self.map_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a file from the list to view")
            return
        
        selected_index = selection[0]
        if selected_index < len(self.map_files_list):
            filepath = self.map_files_list[selected_index]
            self._open_external_file(filepath)
    
    def _delete_selected_trail_map(self):
        """Remove the selected trail map from the list"""
        selection = self.map_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a file from the list to remove")
            return
        
        selected_index = selection[0]
        if selected_index >= len(self.map_files_list):
            return
        
        filename = self.map_listbox.get(selected_index)
        
        result = messagebox.askokcancel(
            "Remove Trail Map",
            f"Remove '{filename}' from the list?",
            icon='warning'
        )
        
        if not result:
            return
        
        self.map_files_list.pop(selected_index)
        self.map_listbox.delete(selected_index)
        
        if not self.map_files_list:
            self.view_trail_map_button.config(state=tk.DISABLED)
            self.delete_trail_map_button.config(state=tk.DISABLED)
    
    def _open_external_file(self, file_path):
        """Open a file with the system's default application"""
        if not file_path or not os.path.exists(file_path):
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
        
        return {
            'date': self.t_date_var.get(),
            'session': self.t_session_var.get(),
            'purpose': ", ".join(self.purpose_listbox.get(0, tk.END)),
            'handler': self.t_handler_var.get(),
            'field_support': self.t_field_support_var.get(),
            'dog_name': self.t_dog_var.get(),
            'location': self.t_location_var.get(),
            'start_time': self.t_start_time_var.get(),
            'trail_age': self.t_trail_age_var.get(),
            'trail_length': self.t_trail_length_var.get(),
            'terrain': ", ".join(self.terrain_listbox.get(0, tk.END)),
            'difficulty': self.t_difficulty_var.get(),
            # Weather when laying trail
            'weather_laying': self.t_weather_laying_var.get(),
            'temperature_laying': self.t_temp_laying_var.get(),
            'wind_speed_laying': self.t_wind_laying_var.get(),
            'wind_direction_laying': self.t_wind_direction_laying_var.get(),
            'humidity_laying': self.t_humidity_laying_var.get(),
            # Weather at time of running trail
            'weather_running': self.t_weather_running_var.get(),
            'temperature_running': self.t_temp_running_var.get(),
            'wind_speed_running': self.t_wind_running_var.get(),
            'wind_direction_running': self.t_wind_direction_running_var.get(),
            'humidity_running': self.t_humidity_running_var.get(),
            'start_behavior': self.t_start_behavior_var.get(),
            'consistency': self.t_consistency_var.get(),
            'head_position': self.t_head_pos_var.get(),
            'pace': self.t_pace_var.get(),
            'indication': self.t_indication_var.get(),
            'time_to_complete': self.t_time_var.get(),
            'distractions': self.t_accumulated_distractions_var.get(),
            'success_rate': self.t_success_var.get(),
            'notes': self.notes_text.get("1.0", tk.END).strip(),
            'impression': self.impression_text.get("1.0", tk.END).strip(),
            'map_files': self.map_files_list.copy(),
        }
    
    def set_session_data(self, data):
        """Populate form from a dictionary of session data"""
        date_str = data.get('date', datetime.now().strftime("%Y-%m-%d"))
        self.t_date_var.set(date_str)
        # Also update the DateEntry picker
        try:
            self.date_picker.set_date(datetime.strptime(date_str, "%Y-%m-%d"))
        except (ValueError, AttributeError):
            pass
        self.t_session_var.set(data.get('session', ''))
        self.t_handler_var.set(data.get('handler', ''))
        self.t_field_support_var.set(data.get('field_support', ''))
        self.t_dog_var.set(data.get('dog_name', ''))
        self.t_location_var.set(data.get('location', ''))
        self.t_start_time_var.set(data.get('start_time', ''))
        self.t_trail_age_var.set(data.get('trail_age', ''))
        self.t_trail_length_var.set(data.get('trail_length', ''))
        self.t_difficulty_var.set(data.get('difficulty', ''))
        # Weather when laying trail
        self.t_weather_laying_var.set(data.get('weather_laying', ''))
        self.t_temp_laying_var.set(data.get('temperature_laying', ''))
        self.t_wind_laying_var.set(data.get('wind_speed_laying', ''))
        self.t_wind_direction_laying_var.set(data.get('wind_direction_laying', ''))
        self.t_humidity_laying_var.set(data.get('humidity_laying', ''))
        # Weather at time of running trail
        self.t_weather_running_var.set(data.get('weather_running', ''))
        self.t_temp_running_var.set(data.get('temperature_running', ''))
        self.t_wind_running_var.set(data.get('wind_speed_running', ''))
        self.t_wind_direction_running_var.set(data.get('wind_direction_running', ''))
        self.t_humidity_running_var.set(data.get('humidity_running', ''))
        self.t_start_behavior_var.set(data.get('start_behavior', ''))
        self.t_consistency_var.set(data.get('consistency', ''))
        self.t_head_pos_var.set(data.get('head_position', ''))
        self.t_pace_var.set(data.get('pace', ''))
        self.t_indication_var.set(data.get('indication', ''))
        self.t_time_var.set(data.get('time_to_complete', ''))
        self.t_success_var.set(data.get('success_rate', ''))
        
        # Session Purposes
        self.purpose_listbox.delete(0, tk.END)
        purpose = data.get('purpose', '')
        if purpose:
            for p in purpose.split(', '):
                if p.strip():
                    self.purpose_listbox.insert(tk.END, p.strip())
        self._update_purpose_scrollbar()
        
        # Terrain
        self.terrain_listbox.delete(0, tk.END)
        terrain = data.get('terrain', '')
        if terrain:
            for t in terrain.split(', '):
                if t.strip():
                    self.terrain_listbox.insert(tk.END, t.strip())
        self._update_terrain_scrollbar()
        
        # Distractions
        for item in self.distraction_tree.get_children():
            self.distraction_tree.delete(item)
        
        distractions = data.get('distractions', '')
        if distractions:
            for entry in distractions.split(', '):
                if ':' in entry:
                    parts = entry.split(':', 1)
                    self.distraction_tree.insert('', tk.END, values=(parts[0].strip(), parts[1].strip()))
        self._update_accumulated_distractions_string()
        
        # Text fields
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert("1.0", data.get('notes', ''))
        
        self.impression_text.delete("1.0", tk.END)
        self.impression_text.insert("1.0", data.get('impression', ''))
        
        # Map files
        self.map_files_list = data.get('map_files', [])
        self.map_listbox.delete(0, tk.END)
        for filepath in self.map_files_list:
            self.map_listbox.insert(tk.END, os.path.basename(filepath))
        
        if self.map_files_list:
            self.view_trail_map_button.config(state=tk.NORMAL)
            self.delete_trail_map_button.config(state=tk.NORMAL)
        else:
            self.view_trail_map_button.config(state=tk.DISABLED)
            self.delete_trail_map_button.config(state=tk.DISABLED)
        
        self.take_form_snapshot()
    
    def clear_form(self, keep_session=False):
        """Clear the entry form"""
        if not keep_session:
            self.t_date_var.set(datetime.now().strftime("%Y-%m-%d"))
            if 'get_next_session_number' in self.callbacks:
                next_session = self.callbacks['get_next_session_number'](self.t_dog_var.get())
                self.t_session_var.set(str(next_session))
            else:
                self.t_session_var.set("1")
        
        # Reset editing mode
        self.editing_session = False
        self.editing_row = None
        
        # Reset navigation state
        self.dog_sessions_list = []
        self.current_session_index = -1
        self.prev_session_btn.config(state=tk.DISABLED)
        self.next_session_btn.config(state=tk.DISABLED)
        
        # Keep handler from defaults
        self.t_handler_var.set(self._get_config_value('get_handler_name', ""))
        
        # Reset date picker to today
        try:
            self.date_picker.set_date(datetime.now())
        except AttributeError:
            pass
        
        # Clear all other fields
        self.t_field_support_var.set("")
        self.t_location_var.set("")
        self.t_purpose_var.set("")
        self.purpose_listbox.delete(0, tk.END)
        self._update_purpose_scrollbar()
        self.t_trail_age_var.set("")
        self.t_trail_length_var.set("")
        self.terrain_listbox.delete(0, tk.END)
        self._update_terrain_scrollbar()
        self.t_difficulty_var.set("")
        # Weather when laying trail
        self.t_weather_laying_var.set("")
        self.t_temp_laying_var.set("")
        self.t_wind_laying_var.set("")
        self.t_wind_direction_laying_var.set("")
        self.t_humidity_laying_var.set("")
        # Weather at time of running trail
        self.t_weather_running_var.set("")
        self.t_temp_running_var.set("")
        self.t_wind_running_var.set("")
        self.t_wind_direction_running_var.set("")
        self.t_humidity_running_var.set("")
        self.t_start_behavior_var.set("")
        self.t_consistency_var.set("")
        self.t_head_pos_var.set("")
        self.t_pace_var.set("")
        self.t_indication_var.set("")
        self.t_distractions_var.set("")
        self.t_distraction_response_var.set("")
        self.t_accumulated_distractions_var.set("")
        self.t_start_time_var.set("")
        
        # Clear distraction table
        for item in self.distraction_tree.get_children():
            self.distraction_tree.delete(item)
        self.selected_distraction_index = None
        
        self.t_success_var.set("")
        self.t_time_var.set("")
        self.notes_text.delete("1.0", tk.END)
        self.impression_text.delete("1.0", tk.END)
        self.map_files_list = []
        self.map_listbox.delete(0, tk.END)
        self.view_trail_map_button.config(state=tk.DISABLED)
        self.delete_trail_map_button.config(state=tk.DISABLED)
        
        self.t_status_var.set("Form cleared")
        self.take_form_snapshot()
    
    def get_form_state_string(self):
        """Get a string representation of all form fields for comparison"""
        parts = [
            self.t_date_var.get(),
            self.t_session_var.get(),
            self.t_dog_var.get(),
            self.t_handler_var.get(),
            self.t_field_support_var.get(),
            ", ".join(self.purpose_listbox.get(0, tk.END)),
            self.t_location_var.get(),
            self.t_start_time_var.get(),
            self.t_trail_age_var.get(),
            self.t_trail_length_var.get(),
            ", ".join(self.terrain_listbox.get(0, tk.END)),
            self.t_difficulty_var.get(),
            # Weather when laying trail
            self.t_weather_laying_var.get(),
            self.t_temp_laying_var.get(),
            self.t_wind_laying_var.get(),
            self.t_wind_direction_laying_var.get(),
            self.t_humidity_laying_var.get(),
            # Weather at time of running trail
            self.t_weather_running_var.get(),
            self.t_temp_running_var.get(),
            self.t_wind_running_var.get(),
            self.t_wind_direction_running_var.get(),
            self.t_humidity_running_var.get(),
            self.t_start_behavior_var.get(),
            self.t_consistency_var.get(),
            self.t_head_pos_var.get(),
            self.t_pace_var.get(),
            self.t_indication_var.get(),
            self.t_time_var.get(),
            self.t_success_var.get(),
            self.notes_text.get("1.0", tk.END).strip(),
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
        self.t_status_var.set(message)
    
    def enable_drag_drop(self, dnd_module):
        """
        Enable drag-and-drop support if tkinterdnd2 is available.
        
        Args:
            dnd_module: The tkinterdnd2 module or DND_FILES constant
        """
        try:
            self.drop_label.drop_target_register(dnd_module)
            self.drop_label.dnd_bind('<<Drop>>', self._handle_drop)
            self.drop_label.dnd_bind('<<DragEnter>>', self._drag_enter)
            self.drop_label.dnd_bind('<<DragLeave>>', self._drag_leave)
        except Exception as e:
            print(f"Could not enable drag-drop: {e}")


# Example usage / testing
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Trailing Entry Tab Test")
    root.geometry("1200x900")
    
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
        print("Save requested with data:")
        for k, v in data.items():
            print(f"  {k}: {v}")
        return True
    
    callbacks = {
        'on_save': on_save,
        'get_next_session_number': lambda dog: 1,
    }
    
    tab = TrailingEntryTab(entry_frame, TestConfig(), callbacks)
    
    # Status bar
    status_bar = tk.Label(root, textvariable=tab.t_status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
    status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    root.mainloop()
