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
PDF Export Module for Air-Scenting Logger
Exports training sessions to professionally formatted PDF documents
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
from datetime import datetime
import os
import json


def show_export_dialog(parent, db_type, current_dog, get_connection_func, backup_folder, trail_maps_folder, status_var=None):
    """
    Show export dialog for selecting sessions to export using list-based selection.
    
    Args:
        parent: Parent window
        db_type: Database type (sqlite/postgres/supabase)
        current_dog: Currently selected dog name
        get_connection_func: Function to get database connection
        backup_folder: Path to backup folder
        trail_maps_folder: Path to trail maps folder
        status_var: Optional StringVar for status bar messages
    """
    from sqlalchemy import text
    
    # Validate dog selection first
    if not current_dog:
        messagebox.showwarning("No Dog Selected", "Please select a dog first to export their sessions")
        return
    
    # Create dialog window
    dialog = tk.Toplevel(parent)
    dialog.title("Export Sessions to PDF")
    dialog.geometry("650x500")
    dialog.resizable(True, True)
    
    # Center dialog
    dialog.transient(parent)
    dialog.grab_set()
    dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (dialog.winfo_width() // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    
    # Dog display at top
    header_frame = tk.Frame(dialog, padx=10, pady=10)
    header_frame.pack(fill="x")
    tk.Label(header_frame, text="Dog:", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
    tk.Label(header_frame, text=current_dog, font=("Helvetica", 10)).pack(side=tk.LEFT, padx=(5, 0))
    
    # Instructions
    instructions = tk.Label(
        dialog, 
        text="Select sessions to export:\n"
             "\N{Bullet} Click to select one session\n"
             "\N{Bullet} Ctrl+Click to select multiple sessions\n"
             "\N{Bullet} Shift+Click to select a range",
        justify="left",
        padx=10,
        pady=5
    )
    instructions.pack()
    
    # Status filter radiobuttons
    filter_frame = tk.Frame(dialog)
    filter_frame.pack(pady=(5, 5))
    
    tk.Label(filter_frame, text="Show Sessions:").pack(side=tk.LEFT, padx=(0, 10))
    export_status_var = tk.StringVar(value="active")
    
    # Listbox with scrollbar
    list_frame = tk.Frame(dialog)
    list_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side="right", fill="y")
    
    listbox = tk.Listbox(
        list_frame, 
        selectmode="extended",  # Allow Ctrl+Click and Shift+Click
        yscrollcommand=scrollbar.set,
        font=("Courier", 10)
    )
    listbox.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=listbox.yview)
    
    # Store session numbers for reference
    session_numbers = []
    
    def get_sessions_for_dog(status_filter):
        """Get sessions for current dog with given status filter"""
        sessions = []
        try:
            # Build status filter clause
            if status_filter == "active":
                status_clause = " AND (status = 'active' OR status IS NULL)"
            elif status_filter == "deleted":
                status_clause = " AND status = 'deleted'"
            else:  # "both"
                status_clause = ""
            
            with get_connection_func() as conn:
                query = text(f"""
                    SELECT session_number, date, handler, dog_name, status
                    FROM training_sessions
                    WHERE dog_name = :dog_name{status_clause}
                    ORDER BY session_number ASC
                """)
                result = conn.execute(query, {"dog_name": current_dog})
                for row in result:
                    sessions.append(row)
        except Exception as e:
            # print(f"Error fetching sessions: {e}")
            pass
        return sessions
    
    def populate_listbox():
        """Populate listbox with sessions based on current filter"""
        listbox.delete(0, "end")
        session_numbers.clear()
        
        sessions = get_sessions_for_dog(export_status_var.get())
        
        for session in sessions:
            session_num, date, handler, dog, status = session
            handler = handler or ""
            status_marker = " [HIDDEN]" if status == 'deleted' else ""
            text = f"Session #{session_num:3d}  |  {date}  |  {handler:20s}{status_marker}"
            listbox.insert("end", text)
            session_numbers.append(session_num)
        
        # Select all by default
        if session_numbers:
            listbox.select_set(0, "end")
    
    def on_filter_changed():
        """Handle filter radiobutton change"""
        populate_listbox()
    
    # Add radiobuttons after defining the callback
    tk.Radiobutton(filter_frame, text="Active", variable=export_status_var,
                  value="active", command=on_filter_changed).pack(side=tk.LEFT, padx=5)
    tk.Radiobutton(filter_frame, text="Hidden", variable=export_status_var,
                  value="deleted", command=on_filter_changed).pack(side=tk.LEFT, padx=5)
    tk.Radiobutton(filter_frame, text="Both", variable=export_status_var,
                  value="both", command=on_filter_changed).pack(side=tk.LEFT, padx=5)
    
    # Initial population
    populate_listbox()
    
    # Buttons
    button_frame = tk.Frame(dialog)
    button_frame.pack(pady=10)
    
    def do_export():
        selected_indices = listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select at least one session to export")
            return
        
        # Get selected session numbers
        selected_sessions = [session_numbers[i] for i in selected_indices]
        
        # Import sv to get pdf_folder setting
        import sv as sv_module
        pdf_folder = sv_module.pdf_folder.get().strip() if sv_module.sv else ""
        
        # Build filepath using pdf_folder if set, otherwise ask user
        default_filename = f"AirScenting_Log_{current_dog}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        if pdf_folder and os.path.isdir(pdf_folder):
            # Use the configured PDF folder
            filepath = os.path.join(pdf_folder, default_filename)
            # Check if file exists and ask to overwrite
            if os.path.exists(filepath):
                if not messagebox.askyesno("File Exists", 
                    f"File already exists:\n{filepath}\n\nOverwrite?"):
                    return
        else:
            # No PDF folder configured, ask user for location
            filepath = filedialog.asksaveasfilename(
                parent=dialog,
                title="Save PDF As",
                defaultextension=".pdf",
                initialfile=default_filename,
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
            )
            
            if not filepath:
                return
        
        # Perform export with selected sessions (keep dialog open until complete)
        success = export_sessions_to_pdf(
            filepath=filepath,
            dog_name=current_dog,
            session_numbers=selected_sessions,
            get_connection_func=get_connection_func,
            trail_maps_folder=trail_maps_folder,
            status_msg_var=status_var
        )
        
        # Close dialog after export completes
        dialog.destroy()
    
    tk.Button(button_frame, text="Export", command=do_export, bg="#4CAF50", fg="white", width=15).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)


def export_sessions_to_pdf(filepath, dog_name, session_numbers, get_connection_func, trail_maps_folder, status_msg_var=None):
    """Export selected sessions to PDF
    
    Args:
        filepath: Path to save the PDF file
        dog_name: Name of the dog
        session_numbers: List of session numbers to export
        get_connection_func: Function to get database connection
        trail_maps_folder: Path to trail maps folder
        status_msg_var: Optional StringVar for status messages
        
    Returns:
        bool: True if export succeeded, False otherwise
    """
    # print(f"[PDF Export] Starting export to: {filepath}")
    # print(f"[PDF Export] Dog: {dog_name}, Sessions: {session_numbers}")
    
    
    try:
        # Fetch sessions from database
        # print("[PDF Export] Fetching sessions from database...")
        sessions = fetch_sessions_by_numbers(
            dog_name, session_numbers, get_connection_func
        )
        
        # print(f"[PDF Export] Found {len(sessions)} sessions")
        
        
        if not sessions:
            messagebox.showinfo("No Sessions", "No sessions found matching the specified criteria")
            return False
        
        # Generate PDF
        # print(f"[PDF Export] Generating PDF with trail_maps_folder: {trail_maps_folder}")
        generate_pdf(filepath, dog_name, sessions, trail_maps_folder)
        
        # Verify file was created
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            # print(f"[PDF Export] SUCCESS - File created: {filepath} ({file_size} bytes)")
            
            
            # Send success message to status bar instead of popup
            if status_msg_var:
                status_msg_var.set(f"Exported {len(sessions)} session(s) to: {filepath}")
            else:
                # print(f"Exported {len(sessions)} session(s) to: {filepath}")
            
                pass
            
            # Ask to open the PDF
            if messagebox.askyesno("Open File?", "Would you like to open the exported PDF?"):
                import subprocess
                import platform
                if platform.system() == 'Windows':
                    os.startfile(filepath)
                elif platform.system() == 'Darwin':
                    subprocess.run(['open', filepath])
                else:
                    subprocess.run(['xdg-open', filepath])
            
            return True
        else:
            # print(f"[PDF Export] ERROR - File was not created at: {filepath}")
            messagebox.showerror("Export Error", f"PDF file was not created.\nPath: {filepath}")
            return False
        
    except Exception as e:
        # print(f"[PDF Export] EXCEPTION: {type(e).__name__}: {e}")
        messagebox.showerror("Export Error", f"Failed to export PDF:\n{str(e)}")
        import traceback
        traceback.print_exc()
        return False


def fetch_sessions_by_numbers(dog_name, session_numbers, get_connection_func):
    """Fetch sessions from database by specific session numbers
    
    Args:
        dog_name: Name of the dog
        session_numbers: List of session numbers to fetch
        get_connection_func: Function to get database connection
        
    Returns:
        List of session dictionaries
    """
    from sqlalchemy import text
    
    sessions = []
    
    # Sort session numbers for consistent output
    sorted_numbers = sorted(session_numbers)
    
    with get_connection_func() as conn:
        for session_num in sorted_numbers:
            query = text("""
                SELECT id, date, session_number, handler, session_purpose, field_support,
                       location, search_area_size, num_subjects, handler_knowledge,
                       weather, temperature, wind_direction, wind_speed, search_type,
                       drive_level, subjects_found, a_percent_searched, start_time, finish_time, 
                       comments, image_files
                FROM training_sessions
                WHERE dog_name = :dog_name AND session_number = :session_num
            """)
            
            result = conn.execute(query, {
                "dog_name": dog_name,
                "session_num": session_num
            })
            
            row = result.fetchone()
            if row:
                session_id = row[0]
                
                # Get selected terrains for this session
                terrain_result = conn.execute(
                    text("SELECT terrain_name FROM selected_terrains WHERE session_id = :session_id ORDER BY terrain_name"),
                    {"session_id": session_id}
                )
                terrains = [t[0] for t in terrain_result.fetchall()]
                
                # Get subject responses for this session
                subject_result = conn.execute(
                    text("SELECT subject_number, tfr, refind FROM subject_responses WHERE session_id = :session_id ORDER BY subject_number"),
                    {"session_id": session_id}
                )
                subject_responses = [(s[0], s[1], s[2]) for s in subject_result.fetchall()]
                
                # Parse image files JSON
                image_files = []
                if row[21]:  # image_files column (now at index 21)
                    try:
                        image_files = json.loads(row[21])
                    except:
                        pass
                
                session_data = {
                    'id': session_id,
                    'date': row[1],
                    'session_number': row[2],
                    'handler': row[3],
                    'session_purpose': row[4],
                    'field_support': row[5],
                    'location': row[6],
                    'search_area_size': row[7],
                    'num_subjects': row[8],
                    'handler_knowledge': row[9],
                    'weather': row[10],
                    'temperature': row[11],
                    'wind_direction': row[12],
                    'wind_speed': row[13],
                    'search_type': row[14],
                    'drive_level': row[15],
                    'subjects_found': row[16],
                    'a_percent_searched': row[17],
                    'start_time': row[18],
                    'finish_time': row[19],
                    'comments': row[20],
                    'image_files': image_files,
                    'terrains': terrains,
                    'subject_responses': subject_responses
                }
                
                sessions.append(session_data)
    
    return sessions


def export_to_pdf(filepath, dog_name, range_type, start_value, end_value, sort_order, get_connection_func, trail_maps_folder, status_filter="active", status_msg_var=None):
    """Export sessions to PDF"""
    try:
        # Fetch sessions from database
        sessions = fetch_sessions_for_export(
            dog_name, range_type, start_value, end_value, sort_order, get_connection_func, status_filter
        )
        
        if not sessions:
            messagebox.showinfo("No Sessions", "No sessions found matching the specified criteria")
            return
        
        # Generate PDF
        generate_pdf(filepath, dog_name, sessions, trail_maps_folder)
        
        # Send success message to status bar instead of popup
        if status_msg_var:
            status_msg_var.set(f"Exported {len(sessions)} session(s) to: {filepath}")
        else:
            # print(f"Exported {len(sessions)} session(s) to: {filepath}")
        
            pass
        
        # Ask to open the PDF
        if messagebox.askyesno("Open File?", "Would you like to open the exported PDF?"):
            import subprocess
            import platform
            if platform.system() == 'Windows':
                os.startfile(filepath)
            elif platform.system() == 'Darwin':
                subprocess.run(['open', filepath])
            else:
                subprocess.run(['xdg-open', filepath])
        
    except Exception as e:
        messagebox.showerror("Export Error", f"Failed to export PDF:\n{str(e)}")
        import traceback
        traceback.print_exc()


def fetch_sessions_for_export(dog_name, range_type, start_value, end_value, sort_order, get_connection_func, status_filter="active"):
    """Fetch sessions from database based on criteria"""
    from sqlalchemy import text
    
    sessions = []
    
    # Build status filter clause
    if status_filter == "active":
        status_clause = " AND (status = 'active' OR status IS NULL)"
    elif status_filter == "deleted":
        status_clause = " AND status = 'deleted'"
    else:  # "both"
        status_clause = ""
    
    with get_connection_func() as conn:
        # Build query based on range type
        if range_type == "Date":
            query = text("""
                SELECT id, date, session_number, handler, session_purpose, field_support,
                       location, search_area_size, num_subjects, handler_knowledge,
                       weather, temperature, wind_direction, wind_speed, search_type,
                       drive_level, subjects_found, a_percent_searched, start_time, finish_time,
                       comments, image_files
                FROM training_sessions
                WHERE dog_name = :dog_name
                  AND date >= :start_value
                  AND date <= :end_value""" + status_clause + """
                ORDER BY """ + ("date ASC, session_number ASC" if sort_order == "Ascending" else "date DESC, session_number DESC"))
            
            result = conn.execute(query, {
                "dog_name": dog_name,
                "start_value": start_value,
                "end_value": end_value
            })
        else:  # Session
            query = text("""
                SELECT id, date, session_number, handler, session_purpose, field_support,
                       location, search_area_size, num_subjects, handler_knowledge,
                       weather, temperature, wind_direction, wind_speed, search_type,
                       drive_level, subjects_found, a_percent_searched, start_time, finish_time,
                       comments, image_files
                FROM training_sessions
                WHERE dog_name = :dog_name
                  AND session_number >= :start_value
                  AND session_number <= :end_value""" + status_clause + """
                ORDER BY """ + ("session_number ASC" if sort_order == "Ascending" else "session_number DESC"))
            
            result = conn.execute(query, {
                "dog_name": dog_name,
                "start_value": int(start_value),
                "end_value": int(end_value)
            })
        
        for row in result:
            session_id = row[0]
            
            # Get selected terrains for this session
            terrain_result = conn.execute(
                text("SELECT terrain_name FROM selected_terrains WHERE session_id = :session_id ORDER BY terrain_name"),
                {"session_id": session_id}
            )
            terrains = [t[0] for t in terrain_result.fetchall()]
            
            # Get subject responses for this session
            subject_result = conn.execute(
                text("SELECT subject_number, tfr, refind FROM subject_responses WHERE session_id = :session_id ORDER BY subject_number"),
                {"session_id": session_id}
            )
            subject_responses = [(s[0], s[1], s[2]) for s in subject_result.fetchall()]
            
            # Parse image files JSON
            image_files = []
            if row[21]:  # image_files column (now at index 21)
                try:
                    image_files = json.loads(row[21])
                except:
                    pass
            
            session_data = {
                'id': session_id,
                'date': row[1],
                'session_number': row[2],
                'handler': row[3],
                'session_purpose': row[4],
                'field_support': row[5],
                'location': row[6],
                'search_area_size': row[7],
                'num_subjects': row[8],
                'handler_knowledge': row[9],
                'weather': row[10],
                'temperature': row[11],
                'wind_direction': row[12],
                'wind_speed': row[13],
                'search_type': row[14],
                'drive_level': row[15],
                'subjects_found': row[16],
                'a_percent_searched': row[17],
                'start_time': row[18],
                'finish_time': row[19],
                'comments': row[20],
                'image_files': image_files,
                'terrains': terrains,
                'subject_responses': subject_responses
            }
            
            sessions.append(session_data)
    
    return sessions


def generate_pdf(filepath, dog_name, sessions, trail_maps_folder):
    """Generate the PDF document"""
    # print(f"[PDF Export] generate_pdf called with {len(sessions)} sessions")
    
    
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    
    # Create PDF
    # print(f"[PDF Export] Creating SimpleDocTemplate for: {filepath}")
    doc = SimpleDocTemplate(filepath, pagesize=letter,
                           topMargin=0.5*inch, bottomMargin=0.5*inch,
                           leftMargin=0.75*inch, rightMargin=0.75*inch)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2E4057'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#4CAF50'),
        spaceAfter=6,
        spaceBefore=6
    )
    
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#666666'),
        spaceAfter=2
    )
    
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8
    )
    
    # Title
    title = Paragraph(f"Air-Scenting Training Log for {dog_name}", title_style)
    story.append(title)
    story.append(Spacer(1, 0.2*inch))
    
    # Helper to create field row
    def make_field(label, value):
        if value and str(value).strip():
            return [
                Paragraph(f"<b>{label}:</b>", label_style),
                Paragraph(str(value), value_style)
            ]
        return None
    
    def format_time_for_pdf(time_value):
        """Format time value with ' hours' suffix for clarity in PDF"""
        if time_value and str(time_value).strip():
            return f"{time_value} hours"
        return None
    
    # Process each session
    for idx, session in enumerate(sessions):
        if idx > 0:
            # Add page break after every 2 sessions
            if idx % 2 == 0:
                story.append(PageBreak())
            else:
                # Add separator line between sessions on same page
                story.append(Spacer(1, 0.15*inch))
                story.append(Table([['']], colWidths=[7*inch], 
                                 style=[('LINEABOVE', (0,0), (-1,-1), 1, colors.grey)]))
                story.append(Spacer(1, 0.15*inch))
        
        # Session header
        date_str = str(session['date']) if session['date'] else ""
        session_header = Paragraph(f"<b>Session #{session['session_number']}</b> - {date_str}", heading_style)
        story.append(session_header)
        story.append(Spacer(1, 0.1*inch))
        
        # Session Information section
        session_info_data = []
        for label, key in [
            ("Handler", 'handler'),
            ("Session Purpose", 'session_purpose'),
            ("Field Support", 'field_support'),
        ]:
            row = make_field(label, session.get(key))
            if row:
                session_info_data.append(row)
        
        if session_info_data:
            info_table = Table(session_info_data, colWidths=[1.5*inch, 5.5*inch])
            info_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.1*inch))
        
        # Search Parameters section (including weather)
        story.append(Paragraph("<b>Search Parameters</b>", heading_style))
        search_data = []
        
        for label, key in [
            ("Location", 'location'),
            ("Search Area Size", 'search_area_size'),
            ("Number of Subjects", 'num_subjects'),
            ("Handler Knowledge", 'handler_knowledge'),
            ("Search Type", 'search_type'),
            ("Weather", 'weather'),
            ("Temperature", 'temperature'),
            ("Wind Direction", 'wind_direction'),
            ("Wind Speed", 'wind_speed'),
        ]:
            row = make_field(label, session.get(key))
            if row:
                search_data.append(row)
        
        # Add terrain types
        if session.get('terrains'):
            terrain_text = ", ".join(session['terrains'])
            row = make_field("Terrain Types", terrain_text)
            if row:
                search_data.append(row)
        
        if search_data:
            search_table = Table(search_data, colWidths=[1.5*inch, 5.5*inch])
            search_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ]))
            story.append(search_table)
            story.append(Spacer(1, 0.1*inch))
        
        # Search Results section (including subject responses and narrative)
        story.append(Paragraph("<b>Search Results</b>", heading_style))
        results_data = []
        
        for label, key in [
            ("Drive Level", 'drive_level'),
            ("Subjects Found", 'subjects_found'),
            ("Percent Searched Prior to Last Find", 'a_percent_searched'),
        ]:
            row = make_field(label, session.get(key))
            if row:
                results_data.append(row)
        
        # Add time fields with special formatting
        row = make_field("Start Time", format_time_for_pdf(session.get('start_time')))
        if row:
            results_data.append(row)
        row = make_field("Finish Time", format_time_for_pdf(session.get('finish_time')))
        if row:
            results_data.append(row)
        
        # Add subject responses inline
        if session.get('subject_responses'):
            response_lines = []
            for subj_num, tfr, refind in session['subject_responses']:
                parts = [f"Subject {subj_num}:"]
                if tfr:
                    parts.append(f"TFR={tfr}")
                if refind:
                    parts.append(f"Re-find={refind}")
                response_lines.append(" ".join(parts))
            if response_lines:
                responses_text = "; ".join(response_lines)
                row = make_field("Subject Responses", responses_text)
                if row:
                    results_data.append(row)
        
        # Add narrative (comments)
        if session.get('comments') and str(session['comments']).strip():
            narrative_text = str(session['comments']).replace('\n', '<br/>')
            row = [
                Paragraph(f"<b>Narrative:</b>", label_style),
                Paragraph(narrative_text, value_style)
            ]
            results_data.append(row)
        
        if results_data:
            results_table = Table(results_data, colWidths=[1.5*inch, 5.5*inch])
            results_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ]))
            story.append(results_table)
            story.append(Spacer(1, 0.1*inch))
        
        # Maps and images section
        if session.get('image_files') and trail_maps_folder:
            story.append(Paragraph("<b>Maps, Images, and Videos</b>", heading_style))
            
            # Video extensions to handle specially
            video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
            
            for image_file in session['image_files']:
                if image_file:
                    image_path = os.path.join(trail_maps_folder, image_file)
                    
                    if os.path.exists(image_path):
                        try:
                            # Check file extension
                            file_ext = os.path.splitext(image_file)[1].lower()
                            
                            if file_ext in ['.jpg', '.jpeg', '.png']:
                                # Regular image file - embed in PDF
                                img = Image(image_path, width=6.5*inch, height=6.5*inch, kind='proportional')
                                story.append(img)
                                story.append(Spacer(1, 0.05*inch))
                                caption = Paragraph(f"<i>{image_file}</i>", label_style)
                                story.append(caption)
                                story.append(Spacer(1, 0.1*inch))
                            elif file_ext == '.pdf':
                                # PDF file - show note
                                note_text = f"<i>{image_file}</i><br/><font color='blue'>PDF file (not embedded)</font>"
                                story.append(Paragraph(note_text, value_style))
                                story.append(Spacer(1, 0.1*inch))
                            elif file_ext in video_extensions:
                                # Video file - copy to PDF output folder and create link
                                pdf_folder = os.path.dirname(filepath)
                                video_filename = os.path.basename(image_file)
                                video_dest = os.path.join(pdf_folder, video_filename)
                                
                                # Copy video to same folder as PDF if not already there
                                if not os.path.exists(video_dest):
                                    try:
                                        import shutil
                                        shutil.copy2(image_path, video_dest)
                                        # print(f"[PDF Export] Copied video to: {video_dest}")
                                        pass
                                    except Exception as copy_err:
                                        # print(f"[PDF Export] Warning: Could not copy video: {copy_err}")
                                
                                        pass
                                
                                # Add link to video in PDF using file:/// URI for reliable opening
                                video_uri = 'file:///' + video_dest.replace('\\', '/').replace(' ', '%20')
                                video_link = f'<a href="{video_uri}" color="blue"><u>{video_filename}</u></a>'
                                note_text = f"<b>Video:</b> {video_link}<br/><font color='gray' size='8'>(Video file copied to PDF folder - click to open)</font>"
                                story.append(Paragraph(note_text, value_style))
                                story.append(Spacer(1, 0.1*inch))
                        except Exception as e:
                            error_text = f"<i>{image_file}</i><br/><font color='red'>Error loading file: {str(e)}</font>"
                            story.append(Paragraph(error_text, value_style))
                            story.append(Spacer(1, 0.1*inch))
                    else:
                        error_text = f"<i>{image_file}</i><br/><font color='red'>File not found</font>"
                        story.append(Paragraph(error_text, value_style))
                        story.append(Spacer(1, 0.1*inch))
    
    # Build PDF
    # print(f"[PDF Export] Building PDF with {len(story)} elements...")
    doc.build(story)
    # print(f"[PDF Export] doc.build() completed")
