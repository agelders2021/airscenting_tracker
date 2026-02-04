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
Air Scenting UI Module
Contains only tkinter widget construction for the Air Scenting Training Session tab.
Helper methods are in air_helper.py
"""
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from datetime import datetime
from tips import ToolTip, ConditionalToolTip
import sv as sv_module


def setup_airscent_tab(ui):
    """
    Setup the Air Scenting Training Session Entry tab.
    
    Args:
        ui: The main TrainingLoggerUI instance
    
    Creates all widgets and stores references on the ui object with 'a_' prefix.
    """
    sv = sv_module.sv
    
    # Create scrollable frame
    canvas = tk.Canvas(ui.airscent_tab)
    scrollbar = ttk.Scrollbar(ui.airscent_tab, orient="vertical", command=canvas.yview)
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
    
    # =========================================================================
    # SESSION INFORMATION FRAME (Row 0)
    # =========================================================================
    session_frame = tk.LabelFrame(frame, text="Session Information", padx=10, pady=5)
    session_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    ui.a_session_frame = session_frame
    
    # Row 0: Date, Session #, New, View/Edit/Hide, Previous, Next, Export PDF
    tk.Label(session_frame, text="Date:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    ui.a_date_picker = DateEntry(session_frame, width=12, background='darkblue',
                                  foreground='white', borderwidth=2,
                                  date_pattern='yyyy-mm-dd')
    ui.a_date_picker.grid(row=0, column=1, sticky="w", padx=5, pady=2)
    ui.a_date_picker.bind("<<DateEntrySelected>>", lambda e: sv.date.set(ui.a_date_picker.get_date().strftime("%Y-%m-%d")))
    
    tk.Label(session_frame, text="Session #:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
    ui.a_session_entry = tk.Entry(session_frame, textvariable=sv.session_number, width=10)
    ui.a_session_entry.grid(row=0, column=3, sticky="w", padx=5, pady=2)
    
    tk.Button(session_frame, text="New", command=ui.form_mgmt.new_session).grid(row=0, column=4, padx=5)
    
    ui.a_edit_delete_btn = tk.Button(session_frame, text="View/Edit/Hide Prior Session(s)",
                                      command=ui.navigation.load_prior_session,
                                      bg="#4169E1", fg="white")
    ui.a_edit_delete_btn.grid(row=0, column=5, padx=5, pady=2)
    
    ui.a_prev_session_btn = tk.Button(session_frame, text="\N{BLACK LEFT-POINTING TRIANGLE} Previous", bg="#FF8C00", fg="white",
                                       width=10, command=ui.navigation.navigate_previous_session, state=tk.DISABLED)
    ui.a_prev_session_btn.grid(row=0, column=6, padx=2, pady=2)
    
    ui.a_next_session_btn = tk.Button(session_frame, text="Next \N{BLACK RIGHT-POINTING TRIANGLE}", bg="#FF8C00", fg="white",
                                       width=10, command=ui.navigation.navigate_next_session, state=tk.DISABLED)
    ui.a_next_session_btn.grid(row=0, column=7, padx=2, pady=2)
    
    ui.a_export_pdf_btn = tk.Button(session_frame, text="Export PDF", bg="#9370DB", fg="white",
                                     width=12, command=lambda: open_export_dialog(ui))
    ui.a_export_pdf_btn.grid(row=0, column=8, padx=2, pady=2)
    
    # Row 1: Handler, Add Session Purpose, Session Purposes listbox
    tk.Label(session_frame, text="Handler:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    ui.a_handler_entry = tk.Entry(session_frame, textvariable=sv.handler, width=15)
    ui.a_handler_entry.grid(row=1, column=1, sticky="w", padx=5, pady=2)
    
    tk.Label(session_frame, text="Add Session Purpose:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
    ui.a_purpose_combo = ttk.Combobox(session_frame, textvariable=sv.a_purpose, width=22, state="normal",
                                       values=['Area Search Training', 'Refind Training',
                                              'Motivational Training', 'Obedience',
                                              'Mock Certification Test', 'Mission'])
    ui.a_purpose_combo.grid(row=1, column=3, sticky="w", padx=5, pady=2)
    ui.a_purpose_combo.bind('<<ComboboxSelected>>', ui._add_to_purpose_accumulator)
    ui.a_purpose_combo.bind('<Return>', ui._add_to_purpose_accumulator)
    ToolTip(ui.a_purpose_combo, "Select purpose to add to list, or type custom and press Enter", delay=250)
    
    # Session Purposes listbox (accumulator) - spans rows 1-2
    purpose_list_frame = tk.Frame(session_frame)
    purpose_list_frame.grid(row=1, column=4, rowspan=2, columnspan=3, sticky="w", padx=5, pady=2)
    
    tk.Label(purpose_list_frame, text="Session Purposes:\n\n").pack(side=tk.LEFT, padx=(0, 5))
    
    ui.a_purpose_listbox = tk.Listbox(purpose_list_frame, height=3, width=25)
    ui.a_purpose_listbox.pack(side=tk.LEFT)
    ui.a_purpose_listbox.bind('<Double-Button-1>', ui._remove_purpose_from_list)
    ToolTip(ui.a_purpose_listbox, "Session Purposes\nDouble-click to remove", delay=750)
    
    ui.a_purpose_scrollbar = tk.Scrollbar(purpose_list_frame, orient="vertical", command=ui.a_purpose_listbox.yview)
    ui.a_purpose_listbox.config(yscrollcommand=ui.a_purpose_scrollbar.set)
    
    # Row 2: Field Support, Dog, Restore/Hide buttons
    tk.Label(session_frame, text="Field Support:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
    ui.a_field_support_entry = tk.Entry(session_frame, textvariable=sv.field_support, width=15)
    ui.a_field_support_entry.grid(row=2, column=1, sticky="w", padx=5, pady=2)
    
    tk.Label(session_frame, text="Dog:").grid(row=2, column=2, sticky="e", padx=5, pady=2)
    ui.a_dog_combo = ttk.Combobox(session_frame, textvariable=sv.dog, width=22, state="readonly")
    ui.a_dog_combo.grid(row=2, column=3, sticky="w", padx=5, pady=2)
    ui.a_dog_combo.bind('<<ComboboxSelected>>', ui.on_dog_changed)
    
    # Restore/Hide buttons frame
    ui.a_delete_undelete_frame = tk.Frame(session_frame)
    ui.a_delete_undelete_frame.grid(row=2, column=7, columnspan=2, sticky="w", padx=5, pady=5)
    
    ui.a_restore_btn = tk.Button(ui.a_delete_undelete_frame, text="Restore", bg="#28a745", fg="white",
                                  command=ui.navigation.undelete_current_session, width=10)
    ui.a_restore_btn.pack(side="left", padx=5)
    
    ui.a_hide_btn = tk.Button(ui.a_delete_undelete_frame, text="Hide", bg="#dc3545", fg="white",
                               command=ui.navigation.delete_current_session, width=10)
    ui.a_hide_btn.pack(side="left", padx=5)
    
    # Initially disable Restore/Hide buttons
    for child in ui.a_delete_undelete_frame.winfo_children():
        child.config(state="disabled")
    
    # =========================================================================
    # SEARCH PARAMETERS FRAME (Row 1) - includes Terrain
    # =========================================================================
    search_frame = tk.LabelFrame(frame, text="Search Parameters", padx=10, pady=5)
    search_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
    
    # Row 0: Location, Search Area, Number of Subjects, Handler Knowledge
    tk.Label(search_frame, text="Location:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    ui.a_location_combo = ttk.Combobox(search_frame, textvariable=sv.location, width=18, state="readonly")
    ui.a_location_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
    
    tk.Label(search_frame, text="Search Area (Acres):").grid(row=0, column=2, sticky="w", padx=5, pady=2)
    tk.Entry(search_frame, textvariable=sv.search_area_size, width=18).grid(row=0, column=3, sticky="w", padx=5, pady=2)
    
    tk.Label(search_frame, text="Number of Subjects:").grid(row=0, column=4, sticky="w", padx=5, pady=2)
    ui.a_num_subjects_combo = ttk.Combobox(search_frame, textvariable=sv.num_subjects, width=15, state="readonly",
                                            values=['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'])
    ui.a_num_subjects_combo.grid(row=0, column=5, sticky="w", padx=5, pady=2)
    ui.a_num_subjects_combo.bind('<<ComboboxSelected>>', ui.form_mgmt.update_subjects_found)
    
    tk.Label(search_frame, text="Handler Knowledge:").grid(row=0, column=6, sticky="w", padx=5, pady=2)
    handler_knowledge_combo = ttk.Combobox(search_frame, textvariable=sv.handler_knowledge, width=25, state="readonly",
                                           values=['Unknown number of subjects', 'Number of subjects known'])
    handler_knowledge_combo.grid(row=0, column=7, columnspan=2, sticky="w", padx=5, pady=2)
    
    # Row 1: Weather, Wind Direction, Wind Speed, Search Type
    tk.Label(search_frame, text="Weather:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    weather_combo = ttk.Combobox(search_frame, textvariable=sv.weather, width=18, state="readonly",
                                  values=['Clear', 'Cloudy', 'Light Rain', 'Heavy Rain',
                                         'Snow Cover', 'Snowing', 'Fog'])
    weather_combo.grid(row=1, column=1, sticky="w", padx=5, pady=2)
    
    tk.Label(search_frame, text="Wind Direction:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
    wind_dir_combo = ttk.Combobox(search_frame, textvariable=sv.wind_direction, width=15, state="readonly",
                                   values=['North', 'South', 'East', 'West',
                                          'NE', 'NW', 'SE', 'SW', 'Variable'])
    wind_dir_combo.grid(row=1, column=3, sticky="w", padx=5, pady=2)
    
    tk.Label(search_frame, text="Wind Speed:").grid(row=1, column=4, sticky="w", padx=5, pady=2)
    tk.Entry(search_frame, textvariable=sv.wind_speed, width=18).grid(row=1, column=5, sticky="w", padx=5, pady=2)
    
    tk.Label(search_frame, text="Search Type:").grid(row=1, column=6, sticky="w", padx=5, pady=2)
    search_type_combo = ttk.Combobox(search_frame, textvariable=sv.search_type, width=25, state="readonly",
                                     values=['Single blind', 'Double blind', 'Subject coordinates known'])
    search_type_combo.grid(row=1, column=7, sticky="w", padx=5, pady=2)
    
    # Row 2: Temperature, Add Terrain Type, Selected Terrains
    tk.Label(search_frame, text="Temperature:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    tk.Entry(search_frame, textvariable=sv.temperature, width=21).grid(row=2, column=1, sticky="w", padx=5, pady=2)
    
    tk.Label(search_frame, text="Add Terrain Type:").grid(row=2, column=2, sticky="w", padx=5, pady=2)
    ui.a_terrain_combo = ttk.Combobox(search_frame, textvariable=sv.terrain, width=15, state="readonly", values=[])
    ui.a_terrain_combo.grid(row=2, column=3, sticky="w", padx=5, pady=2)
    ui.a_terrain_combo.bind('<<ComboboxSelected>>', ui.add_to_terrain_accumulator)
    
    tk.Label(search_frame, text="Selected Terrains:").grid(row=2, column=4, sticky="w", padx=5, pady=2)
    ui.a_accumulated_terrain_combo = ttk.Combobox(search_frame, textvariable=sv.accumulated_terrain,
                                                   width=15, state="disabled", values=[])
    ui.a_accumulated_terrain_combo.grid(row=2, column=5, sticky="w", padx=5, pady=2)
    ui.a_accumulated_terrain_combo.bind('<<ComboboxSelected>>', ui.remove_terrain_from_list)
    ToolTip(ui.a_accumulated_terrain_combo, "Terrain List Accumulator\nClick an entry to remove from list", delay=750)
    
    ui.accumulated_terrains = []
    
    # =========================================================================
    # SEARCH RESULTS FRAME (Row 2)
    # =========================================================================
    results_frame = tk.LabelFrame(frame, text="Search Results", padx=10, pady=5)
    results_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
    
    # Row 0: Drive Level, Subjects Found, Subject Responses Tree (spans rows 0-1)
    tk.Label(results_frame, text="Drive Level:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    drive_level_combo = ttk.Combobox(results_frame, textvariable=sv.drive_level, width=39, state="readonly",
                                     values=['High - Needed no encouragement',
                                            'Medium - Needed occasional encouragement',
                                            'Low - Needed frequent encouragement',
                                            'Would not work'])
    drive_level_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
    
    tk.Label(results_frame, text="Subjects Found:").grid(row=0, column=2, sticky="w", padx=5, pady=2)
    ui.a_subjects_found_combo = ttk.Combobox(results_frame, textvariable=sv.subjects_found, width=15, state='disabled')
    ui.a_subjects_found_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)
    ui.a_subjects_found_combo.bind('<<ComboboxSelected>>', ui.update_subject_responses_grid)
    ConditionalToolTip(ui.a_subjects_found_combo, "Enter number of subjects found (set Number of Subjects first)", show_when_disabled=True)
    
    # Subject Responses Treeview (row 0-1, columns 4-7)
    tree_container = tk.Frame(results_frame)
    tree_container.grid(row=0, column=4, columnspan=4, rowspan=2, sticky="nsew", padx=5, pady=5)
    
    tree_scrollbar = ttk.Scrollbar(tree_container, orient="vertical")
    tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    ui.a_subject_responses_tree = ttk.Treeview(
        tree_container,
        columns=('subject', 'tfr', 'refind'),
        show='headings',
        height=4,
        yscrollcommand=tree_scrollbar.set,
        selectmode='browse'
    )
    ui.a_subject_responses_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    tree_scrollbar.config(command=ui.a_subject_responses_tree.yview)
    
    ui.a_subject_responses_tree.heading('subject', text='Subject #')
    ui.a_subject_responses_tree.heading('tfr', text='TFR')
    ui.a_subject_responses_tree.heading('refind', text='Re-find')
    
    ui.a_subject_responses_tree.column('subject', width=80, anchor='center')
    ui.a_subject_responses_tree.column('tfr', width=150, anchor='w')
    ui.a_subject_responses_tree.column('refind', width=150, anchor='w')
    
    # Pre-populate with 10 rows
    for i in range(1, 11):
        row_tag = 'odd' if i % 2 == 1 else 'even'
        ui.a_subject_responses_tree.insert('', tk.END, iid=f'subject_{i}',
                                           values=(f'Subject {i}', '', ''),
                                           tags=(row_tag, 'disabled'))
    
    ui.a_subject_responses_tree.tag_configure('odd', background='#f0f0f0')
    ui.a_subject_responses_tree.tag_configure('even', background='#ffffff')
    ui.a_subject_responses_tree.tag_configure('disabled', foreground='gray')
    ui.a_subject_responses_tree.tag_configure('enabled', foreground='black')
    
    ui.a_subject_responses_tree.bind('<Button-1>', ui.on_treeview_click)
    ToolTip(ui.a_subject_responses_tree, "Click cell under desired heading to edit value", delay=750)
    
    ui.tfr_options = ['Strong', 'Fair', 'Required cueing', 'None']
    ui.refind_options = ['Immediate', 'Required cue', 'None']
    ui.a_tree_edit_combo = None
    ui.tree_edit_item = None
    ui.tree_edit_column = None
    
    # Row 1: Overall Impression (inside results frame, cols 0-3)
    impression_frame = tk.LabelFrame(results_frame, text="Overall Impression", padx=5, pady=5)
    impression_frame.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=5, pady=(0, 5))
    
    ui.a_comments_text = tk.Text(impression_frame, width=56, height=4, wrap=tk.WORD)
    ui.a_comments_text.pack(fill=tk.BOTH, expand=True)
    ToolTip(ui.a_comments_text, "Enter overall impression of the search here")
    
    # Row 2: Start Time, Finish Time
    tk.Label(results_frame, text="Start Time:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    ui.a_start_time_entry = tk.Entry(results_frame, textvariable=sv.start_time, width=15)
    ui.a_start_time_entry.grid(row=2, column=1, sticky="w", padx=5, pady=2)
    ToolTip(ui.a_start_time_entry, "Enter search start time (e.g., 09:30 AM)")
    
    tk.Label(results_frame, text="Finish Time:").grid(row=2, column=2, sticky="w", padx=5, pady=2)
    ui.a_finish_time_entry = tk.Entry(results_frame, textvariable=sv.finish_time, width=15)
    ui.a_finish_time_entry.grid(row=2, column=3, sticky="w", padx=5, pady=2)
    ToolTip(ui.a_finish_time_entry, "Enter search finish time (e.g., 11:45 AM)")
    
    # =========================================================================
    # MAPS AND IMAGES FRAME (Row 3) - LabelFrame with drag-drop target
    # =========================================================================
    from tkinterdnd2 import DND_FILES
    
    # Main frame - Maps and Images (drag-drop target for entire frame)
    ui.a_map_frame = tk.LabelFrame(
        frame, 
        text="Drop Images/Videos Here (PDF/JPG/PNG/MP4/MOV)",
        padx=10, pady=5
    )
    ui.a_map_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
    
    # Container inside the map frame (for visual feedback on drag)
    ui.a_drop_container = tk.Frame(ui.a_map_frame)
    ui.a_drop_container.pack(fill=tk.BOTH, expand=True)
    
    list_button_container = tk.Frame(ui.a_drop_container)
    list_button_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    listbox_container = tk.Frame(list_button_container)
    listbox_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # Listbox with grey background (visual drop indicator)
    ui.a_map_listbox = tk.Listbox(listbox_container, height=4, font=('Arial', 9), bg="#e0e0e0")
    map_scroll = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL, command=ui.a_map_listbox.yview)
    ui.a_map_listbox.config(yscrollcommand=map_scroll.set)
    
    ui.a_map_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    map_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    ui.a_map_listbox.bind('<Double-Button-1>', lambda e: ui.file_ops.view_selected_map())
    
    map_button_frame = tk.Frame(list_button_container)
    map_button_frame.pack(side=tk.RIGHT, padx=(5, 0))
    
    ui.a_view_map_button = tk.Button(map_button_frame, text="View Selected",
                                      command=ui.file_ops.view_selected_map, state=tk.DISABLED, width=12)
    ui.a_view_map_button.pack(pady=(0, 2))
    
    ui.a_delete_map_button = tk.Button(map_button_frame, text="Delete Selected",
                                        command=ui.file_ops.delete_selected_map, state=tk.DISABLED, width=12)
    ui.a_delete_map_button.pack(pady=(2, 0))
    
    # Add Browse button (matching trailing session)
    ui.a_browse_map_button = tk.Button(map_button_frame, text="Browse...",
                                        command=ui.file_ops.browse_map_files, width=12)
    ui.a_browse_map_button.pack(pady=(2, 0))
    
    ui.map_files_list = []
    
    # Register drag-and-drop on the entire main LabelFrame
    try:
        ui.a_map_frame.drop_target_register(DND_FILES)
        ui.a_map_frame.dnd_bind('<<Drop>>', ui.file_ops.handle_drop)
        ui.a_map_frame.dnd_bind('<<DragEnter>>', ui.file_ops.drag_enter)
        ui.a_map_frame.dnd_bind('<<DragLeave>>', ui.file_ops.drag_leave)
    except Exception as e:
        # Drag-and-drop not available
        pass
    
    # =========================================================================
    # BUTTON FRAME (Row 4)
    # =========================================================================
    button_frame = tk.Frame(frame)
    button_frame.grid(row=4, column=0, columnspan=2, pady=20)
    
    ui.a_save_session_btn = tk.Button(button_frame, text="Save Session",
                                       command=ui.save_session,
                                       bg="#4CAF50", fg="white",
                                       font=("Helvetica", 12, "bold"),
                                       width=25, height=2)
    ui.a_save_session_btn.pack(side="left", padx=10)
    
    tk.Button(button_frame, text="Clear Form", command=ui.form_mgmt.clear_form,
              width=15).pack(side="left", padx=10)
    
    tk.Button(button_frame, text="Quit", command=ui.on_closing,
              width=10).pack(side="left", padx=10)
    
    # Initialize navigation button states
    ui.root.after(500, ui.navigation.update_navigation_buttons)


def open_export_dialog(ui):
    """Open the export PDF dialog"""
    import export_pdf
    from database import get_connection
    sv = sv_module.sv
    
    if not sv.dog.get():
        ui.show_status_message("No Dog Selected", "warning")
        from tkinter import messagebox
        messagebox.showwarning("No Dog Selected", "Please select a dog before exporting")
        return
    
    trail_maps_folder = sv.trail_maps_folder.get().strip()
    if not trail_maps_folder:
        ui.show_status_message("Trail Maps Folder Not Set", "warning")
        from tkinter import messagebox
        messagebox.showwarning("Configuration Required",
                              "Please configure the Images/Trail Maps folder in Setup tab first.")
        return
    
    backup_folder = sv.backup_folder.get().strip()
    
    export_pdf.show_export_dialog(
        parent=ui.root,
        db_type=sv.db_type.get(),
        current_dog=sv.dog.get(),
        get_connection_func=get_connection,
        backup_folder=backup_folder,
        trail_maps_folder=trail_maps_folder,
        status_var=sv.status
    )
