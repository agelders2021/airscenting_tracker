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


def show_export_dialog(parent, db_type, current_dog, get_connection_func, backup_folder, trail_maps_folder):
    """
    Show export dialog for selecting sessions to export
    
    Args:
        parent: Parent window
        db_type: Database type (sqlite/postgres/supabase)
        current_dog: Currently selected dog name
        get_connection_func: Function to get database connection
        backup_folder: Path to backup folder
        trail_maps_folder: Path to trail maps folder
    """
    # Create dialog window
    dialog = tk.Toplevel(parent)
    dialog.title("Export Sessions to PDF")
    dialog.geometry("500x400")
    dialog.resizable(False, False)
    
    # Center dialog
    dialog.transient(parent)
    dialog.grab_set()
    dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (dialog.winfo_width() // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    
    frame = tk.Frame(dialog, padx=20, pady=20)
    frame.pack(fill="both", expand=True)
    
    # Dog selection (read-only, shows current dog)
    tk.Label(frame, text="Dog:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
    dog_var = tk.StringVar(value=current_dog if current_dog else "")
    tk.Label(frame, text=current_dog if current_dog else "(No dog selected)", 
             font=("Helvetica", 10)).grid(row=0, column=1, sticky="w", pady=(0, 10))
    
    # Range type selection
    tk.Label(frame, text="Export Range:", font=("Helvetica", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(10, 5))
    
    range_type_var = tk.StringVar(value="Date")
    tk.Radiobutton(frame, text="Date Range", variable=range_type_var, value="Date").grid(row=2, column=0, sticky="w", padx=(20, 0))
    tk.Radiobutton(frame, text="Session Number Range", variable=range_type_var, value="Session").grid(row=3, column=0, sticky="w", padx=(20, 0))
    
    # Range inputs frame
    input_frame = tk.Frame(frame)
    input_frame.grid(row=2, column=1, rowspan=2, sticky="w", padx=(20, 0))
    
    # Function to get min/max dates and sessions for the selected dog
    def get_dog_ranges():
        """Get min/max dates and session numbers for selected dog"""
        if not current_dog:
            return None, None, None, None
        
        try:
            from sqlalchemy import text
            
            with get_connection_func() as conn:
                # Get min/max dates
                date_result = conn.execute(
                    text("""
                        SELECT MIN(date), MAX(date)
                        FROM training_sessions
                        WHERE dog_name = :dog_name
                    """),
                    {"dog_name": current_dog}
                )
                date_row = date_result.fetchone()
                min_date = date_row[0] if date_row else None
                max_date = date_row[1] if date_row else None
                
                # Get min/max session numbers
                session_result = conn.execute(
                    text("""
                        SELECT MIN(session_number), MAX(session_number)
                        FROM training_sessions
                        WHERE dog_name = :dog_name
                    """),
                    {"dog_name": current_dog}
                )
                session_row = session_result.fetchone()
                min_session = session_row[0] if session_row else None
                max_session = session_row[1] if session_row else None
                
                return min_date, max_date, min_session, max_session
        except Exception as e:
            print(f"Error getting dog ranges: {e}")
            return None, None, None, None
    
    # Labels
    tk.Label(input_frame, text="Start:").grid(row=0, column=0, sticky="e", padx=5)
    tk.Label(input_frame, text="End:").grid(row=1, column=0, sticky="e", padx=5)
    
    # Date Entry widgets (for date range)
    start_date = DateEntry(input_frame, width=14, date_pattern='yyyy-mm-dd')
    start_date.grid(row=0, column=1, padx=5, pady=2)
    
    end_date = DateEntry(input_frame, width=14, date_pattern='yyyy-mm-dd')
    end_date.grid(row=1, column=1, padx=5, pady=2)
    
    # Text Entry widgets (for session number range)
    start_var = tk.StringVar()
    start_entry = tk.Entry(input_frame, textvariable=start_var, width=15)
    
    end_var = tk.StringVar()
    end_entry = tk.Entry(input_frame, textvariable=end_var, width=15)
    
    # Helper labels for format
    format_label = tk.Label(input_frame, text="(Click to select)", font=("Helvetica", 8), fg="gray")
    format_label.grid(row=0, column=2, sticky="w")
    
    def update_input_widgets(*args):
        """Show appropriate input widgets based on range type and auto-fill with data"""
        if range_type_var.get() == "Date":
            # Show date pickers
            start_date.grid(row=0, column=1, padx=5, pady=2)
            end_date.grid(row=1, column=1, padx=5, pady=2)
            # Hide text entries
            start_entry.grid_remove()
            end_entry.grid_remove()
            format_label.config(text="(Click to select)")
            
            # Auto-fill with min/max dates
            min_date, max_date, _, _ = get_dog_ranges()
            if min_date and max_date:
                # Convert to date objects if needed
                if isinstance(min_date, str):
                    min_date = datetime.strptime(min_date, "%Y-%m-%d").date()
                if isinstance(max_date, str):
                    max_date = datetime.strptime(max_date, "%Y-%m-%d").date()
                start_date.set_date(min_date)
                end_date.set_date(max_date)
        else:
            # Show text entries
            start_entry.grid(row=0, column=1, padx=5, pady=2)
            end_entry.grid(row=1, column=1, padx=5, pady=2)
            # Hide date pickers
            start_date.grid_remove()
            end_date.grid_remove()
            format_label.config(text="(Session #)")
            
            # Auto-fill with min/max session numbers
            _, _, min_session, max_session = get_dog_ranges()
            if min_session is not None and max_session is not None:
                start_var.set(str(min_session))
                end_var.set(str(max_session))
    
    range_type_var.trace("w", update_input_widgets)
    
    # Initial fill
    update_input_widgets()
    
    # Function to get the appropriate start/end values
    def get_range_values():
        if range_type_var.get() == "Date":
            return start_date.get_date().strftime("%Y-%m-%d"), end_date.get_date().strftime("%Y-%m-%d")
        else:
            return start_var.get(), end_var.get()
    
    # Sort order
    tk.Label(frame, text="Sort Order:", font=("Helvetica", 10, "bold")).grid(row=4, column=0, sticky="w", pady=(15, 5))
    sort_var = tk.StringVar(value="Ascending")
    sort_combo = ttk.Combobox(frame, textvariable=sort_var, width=25, state="readonly", values=["Ascending", "Descending"])
    sort_combo.grid(row=4, column=1, sticky="w", pady=(15, 5))
    
    # Buttons
    button_frame = tk.Frame(frame)
    button_frame.grid(row=5, column=0, columnspan=2, pady=(20, 0))
    
    def do_export():
        # Validate dog selection
        if not current_dog:
            messagebox.showwarning("No Dog Selected", "Please select a dog first")
            return
        
        # Get range values
        start_value, end_value = get_range_values()
        
        # Validate range inputs
        if not start_value or not end_value:
            messagebox.showwarning("Invalid Range", "Please enter both start and end values")
            return
        
        # Validate that start is not greater than end
        try:
            if range_type_var.get() == "Date":
                # Compare dates
                start_date_obj = datetime.strptime(start_value, "%Y-%m-%d").date()
                end_date_obj = datetime.strptime(end_value, "%Y-%m-%d").date()
                
                if start_date_obj > end_date_obj:
                    messagebox.showerror("Invalid Date Range", 
                                       f"Start date ({start_value}) is after end date ({end_value}).\n\n"
                                       "Please correct the date range.")
                    return
            else:  # Session
                # Compare session numbers
                start_session = int(start_value)
                end_session = int(end_value)
                
                if start_session > end_session:
                    messagebox.showerror("Invalid Session Range",
                                       f"Start session ({start_session}) is greater than end session ({end_session}).\n\n"
                                       "Please correct the session range.")
                    return
        except (ValueError, TypeError) as e:
            messagebox.showerror("Invalid Range", f"Error validating range: {str(e)}")
            return
        
        # Get file save location
        default_filename = f"AirScenting_Log_{current_dog}_{datetime.now().strftime('%Y%m%d')}.pdf"
        filepath = filedialog.asksaveasfilename(
            title="Save PDF As",
            defaultextension=".pdf",
            initialfile=default_filename,
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        # Close dialog
        dialog.destroy()
        
        # Perform export
        export_to_pdf(
            filepath=filepath,
            dog_name=current_dog,
            range_type=range_type_var.get(),
            start_value=start_value,
            end_value=end_value,
            sort_order=sort_var.get(),
            get_connection_func=get_connection_func,
            trail_maps_folder=trail_maps_folder
        )
    
    tk.Button(button_frame, text="Export to PDF", command=do_export, bg="#4CAF50", fg="white", width=15).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)


def export_to_pdf(filepath, dog_name, range_type, start_value, end_value, sort_order, get_connection_func, trail_maps_folder):
    """Export sessions to PDF"""
    try:
        # Fetch sessions from database
        sessions = fetch_sessions_for_export(
            dog_name, range_type, start_value, end_value, sort_order, get_connection_func
        )
        
        if not sessions:
            messagebox.showinfo("No Sessions", "No sessions found matching the specified criteria")
            return
        
        # Generate PDF
        generate_pdf(filepath, dog_name, sessions, trail_maps_folder)
        
        messagebox.showinfo("Success", f"Exported {len(sessions)} session(s) to:\n{filepath}")
        
    except Exception as e:
        messagebox.showerror("Export Error", f"Failed to export PDF:\n{str(e)}")
        import traceback
        traceback.print_exc()


def fetch_sessions_for_export(dog_name, range_type, start_value, end_value, sort_order, get_connection_func):
    """Fetch sessions from database based on criteria"""
    from sqlalchemy import text
    
    sessions = []
    
    with get_connection_func() as conn:
        # Build query based on range type
        if range_type == "Date":
            query = text("""
                SELECT id, date, session_number, handler, session_purpose, field_support,
                       location, search_area_size, num_subjects, handler_knowledge,
                       weather, temperature, wind_direction, wind_speed, search_type,
                       drive_level, subjects_found, comments, image_files
                FROM training_sessions
                WHERE dog_name = :dog_name
                  AND date >= :start_value
                  AND date <= :end_value
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
                       drive_level, subjects_found, comments, image_files
                FROM training_sessions
                WHERE dog_name = :dog_name
                  AND session_number >= :start_value
                  AND session_number <= :end_value
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
            if row[18]:  # image_files column
                try:
                    image_files = json.loads(row[18])
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
                'comments': row[17],
                'image_files': image_files,
                'terrains': terrains,
                'subject_responses': subject_responses
            }
            
            sessions.append(session_data)
    
    return sessions


def generate_pdf(filepath, dog_name, sessions, trail_maps_folder):
    """Generate the PDF document"""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    
    # Create PDF
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
        
        # Session information section
        session_info_data = []
        
        def add_field(label, value):
            if value and str(value).strip():
                session_info_data.append([
                    Paragraph(f"<b>{label}:</b>", label_style),
                    Paragraph(str(value), value_style)
                ])
        
        add_field("Handler", session['handler'])
        add_field("Session Purpose", session['session_purpose'])
        add_field("Field Support", session['field_support'])
        
        if session_info_data:
            info_table = Table(session_info_data, colWidths=[1.5*inch, 5*inch])
            info_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.1*inch))
        
        # Search parameters section
        story.append(Paragraph("<b>Search Parameters</b>", heading_style))
        search_data = []
        
        add_field("Location", session['location'])
        add_field("Search Area Size", session['search_area_size'])
        add_field("Number of Subjects", session['num_subjects'])
        add_field("Handler Knowledge", session['handler_knowledge'])
        add_field("Search Type", session['search_type'])
        
        # Add terrain types
        if session['terrains']:
            terrain_text = ", ".join(session['terrains'])
            add_field("Terrain Types", terrain_text)
        
        if search_data:
            search_table = Table(search_data, colWidths=[1.5*inch, 5*inch])
            search_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(search_table)
            story.append(Spacer(1, 0.1*inch))
        
        # Weather conditions section
        story.append(Paragraph("<b>Weather Conditions</b>", heading_style))
        weather_data = []
        
        add_field("Weather", session['weather'])
        add_field("Temperature", session['temperature'])
        add_field("Wind Direction", session['wind_direction'])
        add_field("Wind Speed", session['wind_speed'])
        
        if weather_data:
            weather_table = Table(weather_data, colWidths=[1.5*inch, 5*inch])
            weather_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(weather_table)
            story.append(Spacer(1, 0.1*inch))
        
        # Search results section
        story.append(Paragraph("<b>Search Results</b>", heading_style))
        results_data = []
        
        add_field("Drive Level", session['drive_level'])
        add_field("Subjects Found", session['subjects_found'])
        
        if results_data:
            results_table = Table(results_data, colWidths=[1.5*inch, 5*inch])
            results_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(results_table)
            story.append(Spacer(1, 0.1*inch))
        
        # Subject responses section
        if session['subject_responses']:
            story.append(Paragraph("<b>Subject Responses</b>", heading_style))
            
            # Create table for subject responses
            subject_table_data = [["Subject #", "TFR", "Re-find"]]  # Header row
            for subj_num, tfr, refind in session['subject_responses']:
                subject_table_data.append([
                    str(subj_num),
                    str(tfr) if tfr else "",
                    str(refind) if refind else ""
                ])
            
            subject_table = Table(subject_table_data, colWidths=[1.5*inch, 2.5*inch, 2.5*inch])
            subject_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E0E0E0')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 10),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('TOPPADDING', (0,0), (-1,0), 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(subject_table)
            story.append(Spacer(1, 0.1*inch))
        
        # Comments section
        if session['comments'] and str(session['comments']).strip():
            story.append(Paragraph("<b>Comments</b>", heading_style))
            comments_text = str(session['comments']).replace('\n', '<br/>')
            story.append(Paragraph(comments_text, value_style))
            story.append(Spacer(1, 0.1*inch))
        
        # Maps and images section
        if session['image_files'] and trail_maps_folder:
            story.append(Paragraph("<b>Maps and Images</b>", heading_style))
            
            for image_file in session['image_files']:
                if image_file:
                    image_path = os.path.join(trail_maps_folder, image_file)
                    
                    if os.path.exists(image_path):
                        try:
                            # Check file extension
                            file_ext = os.path.splitext(image_file)[1].lower()
                            
                            if file_ext in ['.jpg', '.jpeg', '.png']:
                                # Regular image file
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
                        except Exception as e:
                            error_text = f"<i>{image_file}</i><br/><font color='red'>Error loading image: {str(e)}</font>"
                            story.append(Paragraph(error_text, value_style))
                            story.append(Spacer(1, 0.1*inch))
                    else:
                        error_text = f"<i>{image_file}</i><br/><font color='red'>File not found</font>"
                        story.append(Paragraph(error_text, value_style))
                        story.append(Spacer(1, 0.1*inch))
    
    # Build PDF
    doc.build(story)
