"""
Air Scenting UI Module
Contains only tkinter widget construction for the Air Scenting Training Session tab.
Helper methods are in air_helper.py
"""
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from datetime import datetime
from tips import ToolTip
import sv


def setup_airscent_tab(ui):
    """
    Setup the Air Scenting Training Session Entry tab.
    
    Args:
        ui: The main TrainingLoggerUI instance
    
    Creates all widgets and stores references on the ui object with 'a_' prefix.
    """
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
    # SESSION INFORMATION FRAME
    # =========================================================================
    ui.a_session_frame = tk.LabelFrame(frame, text="Session Information", padx=10, pady=5)
    ui.a_session_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    session_frame = ui.a_session_frame
    
    # Row 0: Date, Session #, and action buttons
    tk.Label(session_frame, text="Date:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    ui.a_date_picker = DateEntry(
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
    ui.a_date_picker.grid(row=0, column=1, sticky="w", padx=5, pady=2)
    ui.a_date_picker.bind("<<DateEntrySelected>>", ui.on_date_changed)
    
    tk.Label(session_frame, text="Session #:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
    ui.a_session_entry = tk.Entry(session_frame, textvariable=sv.session_number, width=10)
    ui.a_session_entry.grid(row=0, column=3, sticky="w", padx=5, pady=2)
    ui.a_session_entry.bind("<FocusOut>", ui.navigation.on_session_number_changed)
    ui.a_session_entry.bind("<Return>", ui.navigation.on_session_number_changed)
    
    tk.Button(session_frame, text="New", command=ui.form_mgmt.new_session).grid(row=0, column=4, padx=5)
    
    ui.a_edit_delete_btn = tk.Button(session_frame, text="View/Edit/Hide Prior Session(s)",
                                     command=ui.navigation.load_prior_session,
                                     bg="#4169E1", fg="white")
    ui.a_edit_delete_btn.grid(row=0, column=5, padx=5, pady=2)
    
    # Navigation buttons
    ui.a_prev_session_btn = tk.Button(session_frame, text="\u25C0 Previous", bg="#FF8C00", fg="white",
                                      width=10, command=ui.navigation.navigate_previous_session, state=tk.DISABLED)
    ui.a_prev_session_btn.grid(row=0, column=6, padx=2, pady=2)
    
    ui.a_next_session_btn = tk.Button(session_frame, text="Next \u25B6", bg="#FF8C00", fg="white",
                                      width=10, command=ui.navigation.navigate_next_session, state=tk.DISABLED)
    ui.a_next_session_btn.grid(row=0, column=7, padx=2, pady=2)
    
    # Export PDF button
    ui.a_export_pdf_btn = tk.Button(session_frame, text="Export PDF", bg="#9370DB", fg="white",
                                    width=12, command=lambda: open_export_dialog(ui))
    ui.a_export_pdf_btn.grid(row=0, column=8, padx=2, pady=2)
    
    # Track selected sessions for navigation
    ui.selected_sessions = []
    ui.selected_sessions_index = -1
    
    # Delete/Undelete buttons frame
    ui.a_delete_undelete_frame = tk.Frame(session_frame)
    ui.a_delete_undelete_frame.grid(row=2, column=7, columnspan=3, sticky="w", padx=5, pady=5)
    
    tk.Button(ui.a_delete_undelete_frame, text="Restore", bg="#28a745", fg="white",
              command=ui.navigation.undelete_current_session, width=10).pack(side="left", padx=5)
    tk.Button(ui.a_delete_undelete_frame, text="Hide", bg="#dc3545", fg="white",
              command=ui.navigation.delete_current_session, width=10).pack(side="left", padx=5)
    
    # Initially disable delete/undelete buttons
    for child in ui.a_delete_undelete_frame.winfo_children():
        child.config(state="disabled")
    
    # Row 1: Handler, Add Session Purpose + accumulator
    tk.Label(session_frame, text="Handler:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    airscenting_config = ui.config.get("airscenting", {})
    default_handler = airscenting_config.get("default_handler", "") or airscenting_config.get("last_handler", "")
    sv.handler.set(default_handler)
    tk.Entry(session_frame, textvariable=sv.handler, width=15).grid(row=1, column=1, sticky="w", padx=5, pady=2)
    
    tk.Label(session_frame, text="Add Session Purpose:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
    ui.a_purpose_combo = ttk.Combobox(session_frame, textvariable=sv.a_purpose, width=22, state="enabled",
                                      values=['Area Search Training', 'Refind Training',
                                             'Motivational Training',
                                             'Obedience', 'Mock Certification Test', 'Mission'])
    ui.a_purpose_combo.grid(row=1, column=3, sticky="w", padx=5, pady=2)
    ui.a_purpose_combo.bind('<<ComboboxSelected>>', ui._add_to_purpose_accumulator)
    ui.a_purpose_combo.bind('<Return>', ui._add_to_purpose_accumulator)
    ToolTip(ui.a_purpose_combo, "Select purpose to be added to 'Session Purposes' list to right \u25B6\nOr type custom purpose and press Enter\n(Selections are not shown in this entry box)", delay=250)
    
    # Session Purposes listbox (accumulator)
    purpose_list_frame = tk.Frame(session_frame)
    purpose_list_frame.grid(row=1, column=4, rowspan=2, columnspan=3, sticky="w", padx=5, pady=2)
    
    tk.Label(purpose_list_frame, text="Session Purposes:\n\n").pack(side=tk.LEFT, padx=(0, 5))
    
    ui.a_purpose_listbox = tk.Listbox(purpose_list_frame, height=3, width=25)
    ui.a_purpose_listbox.pack(side=tk.LEFT)
    ui.a_purpose_listbox.bind('<Double-Button-1>', ui._remove_purpose_from_list)
    ToolTip(ui.a_purpose_listbox, "Session Purposes\nDouble-click an entry to remove from list", delay=750)
    
    ui.a_purpose_scrollbar = tk.Scrollbar(purpose_list_frame, orient="vertical", command=ui.a_purpose_listbox.yview)
    ui.a_purpose_listbox.config(yscrollcommand=ui.a_purpose_scrollbar.set)
    
    # Row 2: Field Support, Dog
    tk.Label(session_frame, text="Field Support:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
    tk.Entry(session_frame, textvariable=sv.field_support, width=15).grid(row=2, column=1, sticky="w", padx=5, pady=2)
    
    tk.Label(session_frame, text="Dog:").grid(row=2, column=2, sticky="e", padx=5, pady=2)
    ui.a_dog_combo = ttk.Combobox(session_frame, textvariable=sv.dog, width=22, state="readonly")
    ui.a_dog_combo.grid(row=2, column=3, sticky="w", padx=5, pady=2)
    ui.a_dog_combo.bind('<<ComboboxSelected>>', ui.on_dog_changed)
    
    # =========================================================================
    # SEARCH PARAMETERS FRAME
    # =========================================================================
    search_frame = tk.LabelFrame(frame, text="Search Parameters", padx=10, pady=5)
    search_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
    
    tk.Label(search_frame, text="Location:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    ui.a_location_combo = ttk.Combobox(search_frame, textvariable=sv.location, width=18, state="readonly")
    ui.a_location_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
    ui.root.after(150, ui.refresh_location_list)
    
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
    
    # Row 1: Weather, Wind Direction, Wind Speed
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
    wind_speed_combo = ttk.Combobox(search_frame, textvariable=sv.wind_speed, width=15, state="readonly",
                                    values=['Calm (0-3 mph)', 'Light (4-7 mph)', 'Moderate (8-12 mph)',
                                           'Fresh (13-18 mph)', 'Strong (19-24 mph)', 'High (25+ mph)'])
    wind_speed_combo.grid(row=1, column=5, sticky="w", padx=5, pady=2)
    
    tk.Label(search_frame, text="Temperature (°F):").grid(row=1, column=6, sticky="w", padx=5, pady=2)
    tk.Entry(search_frame, textvariable=sv.temperature, width=10).grid(row=1, column=7, sticky="w", padx=5, pady=2)
    
    # =========================================================================
    # TERRAIN FRAME
    # =========================================================================
    terrain_frame = tk.LabelFrame(frame, text="Terrain", padx=10, pady=5)
    terrain_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
    
    tk.Label(terrain_frame, text="Add Terrain Type:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    ui.a_terrain_combo = ttk.Combobox(terrain_frame, textvariable=sv.terrain, width=18, state="readonly")
    ui.a_terrain_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
    ui.a_terrain_combo.bind('<<ComboboxSelected>>', ui.add_to_terrain_accumulator)
    ToolTip(ui.a_terrain_combo, "Select terrain type to be added to list to right \u25B6\n(Selections are not shown in this entry box)", delay=250)
    
    tk.Label(terrain_frame, text="Terrain Types:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
    
    # Accumulated terrain combobox (shows selected terrains, click to remove)
    ui.a_accumulated_terrain_combo = ttk.Combobox(terrain_frame, textvariable=sv.accumulated_terrain,
                                                   width=25, state='disabled')
    ui.a_accumulated_terrain_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)
    ui.a_accumulated_terrain_combo.bind('<<ComboboxSelected>>', ui.remove_terrain_from_list)
    ToolTip(ui.a_accumulated_terrain_combo, "Terrain List Accumulator\nClick an entry to remove from list", delay=750)
    
    # Initialize accumulated terrains list
    ui.accumulated_terrains = []
    
    # =========================================================================
    # SEARCH RESULTS FRAME
    # =========================================================================
    results_frame = tk.LabelFrame(frame, text="Search Results", padx=10, pady=5)
    results_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
    
    tk.Label(results_frame, text="Search Type:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    search_type_combo = ttk.Combobox(results_frame, textvariable=sv.search_type, width=15, state="readonly",
                                     values=['Hasty', 'Grid', 'Contour', 'Attraction', 'Other'])
    search_type_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
    
    tk.Label(results_frame, text="Drive Level:").grid(row=0, column=2, sticky="w", padx=5, pady=2)
    drive_combo = ttk.Combobox(results_frame, textvariable=sv.drive_level, width=15, state="readonly",
                               values=['1 - Very Low', '2 - Low', '3 - Medium', '4 - High', '5 - Very High'])
    drive_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)
    
    tk.Label(results_frame, text="Subjects Found:").grid(row=0, column=4, sticky="w", padx=5, pady=2)
    ui.a_subjects_found_combo = ttk.Combobox(results_frame, textvariable=sv.subjects_found, width=5, state='disabled')
    ui.a_subjects_found_combo.grid(row=0, column=5, sticky="w", padx=5, pady=2)
    
    tk.Label(results_frame, text="Start Time:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    tk.Entry(results_frame, textvariable=sv.start_time, width=18).grid(row=1, column=1, sticky="w", padx=5, pady=2)
    
    tk.Label(results_frame, text="Finish Time:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
    tk.Entry(results_frame, textvariable=sv.finish_time, width=18).grid(row=1, column=3, sticky="w", padx=5, pady=2)
    
    # =========================================================================
    # SUBJECT RESPONSES FRAME
    # =========================================================================
    responses_frame = tk.LabelFrame(frame, text="Subject Responses", padx=10, pady=5)
    responses_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=5)
    
    # Treeview for subject responses - matches original ui.py
    columns = ('subject', 'tfr', 'refind')
    ui.a_subject_responses_tree = ttk.Treeview(responses_frame, columns=columns, show='headings', height=5)
    
    ui.a_subject_responses_tree.heading('subject', text='Subject')
    ui.a_subject_responses_tree.heading('tfr', text='Trained Final Response')
    ui.a_subject_responses_tree.heading('refind', text='Re-find')
    
    ui.a_subject_responses_tree.column('subject', width=80, anchor='center')
    ui.a_subject_responses_tree.column('tfr', width=150, anchor='w')
    ui.a_subject_responses_tree.column('refind', width=150, anchor='w')
    
    # Pre-populate with 10 empty/disabled rows to support up to 10 subjects
    for i in range(1, 11):
        row_tag = 'odd' if i % 2 == 1 else 'even'
        ui.a_subject_responses_tree.insert('', tk.END, iid=f'subject_{i}',
                                          values=(f'Subject {i}', '', ''),
                                          tags=(row_tag, 'disabled'))
    
    # Style for alternating rows
    ui.a_subject_responses_tree.tag_configure('odd', background='#f0f0f0')
    ui.a_subject_responses_tree.tag_configure('even', background='#ffffff')
    ui.a_subject_responses_tree.tag_configure('disabled', foreground='gray')
    ui.a_subject_responses_tree.tag_configure('enabled', foreground='black')
    
    # Bind single-click to edit with inline combobox
    ui.a_subject_responses_tree.bind('<Button-1>', ui.on_treeview_click)
    
    ui.a_subject_responses_tree.grid(row=0, column=0, columnspan=4, sticky="ew", padx=5, pady=2)
    
    ToolTip(ui.a_subject_responses_tree, 
            "Click cell under desired heading on desired row to edit value", 
            delay=750)
    
    # TFR and Re-find options for editing
    ui.tfr_options = ['Strong', 'Fair', 'Required cueing', 'None']
    ui.refind_options = ['Immediate', 'Required cue', 'None']
    
    # Track current editing combobox
    ui.a_tree_edit_combo = None
    ui.tree_edit_item = None
    ui.tree_edit_column = None
    
    # =========================================================================
    # OVERALL IMPRESSION (COMMENTS) FRAME
    # =========================================================================
    impression_frame = tk.LabelFrame(frame, text="Overall Impression", padx=10, pady=5)
    impression_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)
    
    ui.a_comments_text = tk.Text(impression_frame, height=4, width=80, wrap=tk.WORD)
    ui.a_comments_text.pack(fill="x", expand=True, padx=5, pady=5)
    ToolTip(ui.a_comments_text, "Enter overall impression of the search here")
    
    # =========================================================================
    # MAPS AND IMAGES FRAME
    # =========================================================================
    from tkinterdnd2 import DND_FILES
    
    map_frame = tk.LabelFrame(frame, text="Maps and Images", padx=10, pady=5)
    map_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=5)
    
    # Create container for drag-drop and listbox side by side
    map_container = tk.Frame(map_frame)
    map_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Left side - Drag and drop area
    drop_frame = tk.Frame(map_container)
    drop_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
    
    ui.a_drop_label = tk.Label(
        drop_frame,
        text="Drag & Drop Maps/Images/Videos\n(PDF/JPG/PNG/MP4/MOV)",
        bg="#e0e0e0",
        relief="ridge",
        height=4
    )
    ui.a_drop_label.pack(fill=tk.BOTH, expand=True)
    
    # Enable drag and drop
    ui.a_drop_label.drop_target_register(DND_FILES)
    ui.a_drop_label.dnd_bind('<<Drop>>', ui.file_ops.handle_drop)
    ui.a_drop_label.dnd_bind('<<DragEnter>>', ui.file_ops.drag_enter)
    ui.a_drop_label.dnd_bind('<<DragLeave>>', ui.file_ops.drag_leave)
    
    # Right side - Listbox with scrollbar and view button
    list_frame = tk.Frame(map_container)
    list_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
    
    # Container for listbox and buttons on same row
    list_button_container = tk.Frame(list_frame)
    list_button_container.pack(fill=tk.BOTH, expand=True)
    
    listbox_container = tk.Frame(list_button_container)
    listbox_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    ui.a_map_listbox = tk.Listbox(listbox_container, height=3, font=('Arial', 9))
    map_scroll = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL,
                               command=ui.a_map_listbox.yview)
    ui.a_map_listbox.config(yscrollcommand=map_scroll.set)
    
    ui.a_map_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    map_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Bind double-click to open file
    ui.a_map_listbox.bind('<Double-Button-1>', lambda e: ui.file_ops.view_selected_map())
    
    # Button frame to the right of listbox
    map_button_frame = tk.Frame(list_button_container)
    map_button_frame.pack(side=tk.RIGHT, padx=(5, 0))
    
    # View button
    ui.a_view_map_button = tk.Button(map_button_frame, text="View Selected",
                                     command=ui.file_ops.view_selected_map, state=tk.DISABLED, width=12)
    ui.a_view_map_button.pack(pady=(0, 2))
    
    # Delete button
    ui.a_delete_map_button = tk.Button(map_button_frame, text="Hide Selected",
                                       command=ui.file_ops.delete_selected_map, state=tk.DISABLED, width=12)
    ui.a_delete_map_button.pack(pady=(2, 0))
    
    ui.map_files_list = []  # Store list of files
    
    # =========================================================================
    # BUTTON FRAME
    # =========================================================================
    button_frame = tk.Frame(frame)
    button_frame.grid(row=10, column=0, columnspan=2, pady=20)
    
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
    
    # Initialize subjects_found as disabled
    ui.a_subjects_found_combo['state'] = 'disabled'


def open_export_dialog(ui):
    """Open export PDF dialog for Air Scenting sessions"""
    from tkinter import messagebox, filedialog
    
    # Check if dog is selected
    if not sv.dog.get():
        ui.show_status_message("No Dog Selected", "warning")
        messagebox.showwarning("No Dog Selected", "Please select a dog before exporting")
        return
    
    # Check if trail maps folder is configured
    trail_maps_folder = sv.trail_maps_folder.get().strip()
    if not trail_maps_folder:
        ui.show_status_message("Trail Maps Folder Not Set", "warning")
        messagebox.showwarning("Trail Maps Folder Not Set",
                             "Trail maps folder not configured.\n\n"
                             "Images will not be included in the PDF.\n\n"
                             "Configure in Setup tab to include images.")
    
    # Import the export module
    import export_pdf
    
    # Get database connection function
    def get_connection():
        import config
        from database import engine
        return engine.connect()
    
    # Show export dialog
    export_pdf.show_export_dialog(
        parent=ui.root,
        db_type=sv.db_type.get(),
        current_dog=sv.dog.get(),
        get_connection_func=get_connection,
        backup_folder=sv.backup_folder.get().strip(),
        trail_maps_folder=trail_maps_folder
    )
