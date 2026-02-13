#!/usr/bin/env python3
"""
Generate help_window.py from a Word Document

This script reads a Word document (.docx) and generates the help_window.py file
for the SAR K9 Training Records application using tkinter (no PyQt6 required).

DOCUMENT STRUCTURE REQUIREMENTS:
--------------------------------
The Word document should be structured with:
- Heading 1 styles for main section titles (these become the navigation items)
- Regular paragraphs for content under each heading
- Bold text is converted to **text** markers
- Italic text is converted to *text* markers  
- Bullet lists are preserved with bullet characters
- Numbered lists are preserved with numbers

Example document structure:
    Getting Started          <- Heading 1
    Welcome to the app...    <- Normal paragraph
    
    Key features:            <- Normal paragraph
    • Feature one            <- Bullet list
    • Feature two            <- Bullet list
    
    Dog Management           <- Heading 1
    This section covers...   <- Normal paragraph

USAGE:
------
    python generate_help_window.py input.docx [output.py]
    
    If output.py is not specified, it defaults to help_window.py

DEPENDENCIES:
-------------
    pip install python-docx --break-system-packages
"""

import sys
import re
from pathlib import Path

try:
    from docx import Document
    from docx.oxml.ns import qn
except ImportError:
    print("Error: python-docx is required.")
    print("Install with: pip install python-docx --break-system-packages")
    sys.exit(1)


def escape_for_python_string(text):
    """Escape text for use in a Python triple-quoted string."""
    text = text.replace('\\', '\\\\')
    text = text.replace('"""', '\\"\\"\\"')
    return text


def convert_unicode_names(text):
    """
    Convert \\N{unicode name} sequences to actual unicode characters.
    
    Examples:
        \\N{BULLET} -> •
        \\N{EM DASH} -> —
        \\N{RIGHT SINGLE QUOTATION MARK} -> '
    """
    import unicodedata
    
    pattern = r'\\N\{([^}]+)\}'
    
    def replace_unicode_name(match):
        name = match.group(1)
        try:
            return unicodedata.lookup(name)
        except KeyError:
            # If name not found, leave it as-is
            print(f"  Warning: Unknown unicode name: {name}")
            return match.group(0)
    
    return re.sub(pattern, replace_unicode_name, text)


def get_run_text(run):
    """Convert a run to text with simple markers for formatting."""
    text = run.text
    if not text:
        return ''
    
    # Apply formatting markers that we'll parse in the Text widget
    if run.bold and run.italic:
        text = f'***{text}***'
    elif run.bold:
        text = f'**{text}**'
    elif run.italic:
        text = f'*{text}*'
    
    return text


def extract_index_entries(text):
    """
    Extract \\I{term} entries from text and return (cleaned_text, list_of_terms).
    
    The \\I{term} markers are removed from the text, leaving just the term.
    """
    pattern = r'\\I\{([^}]+)\}'
    terms = re.findall(pattern, text)
    # Remove the \I{} wrapper, leaving just the term
    cleaned = re.sub(pattern, r'\1', text)
    return cleaned, terms


def get_paragraph_text(paragraph):
    """Convert a paragraph to text."""
    parts = []
    for run in paragraph.runs:
        parts.append(get_run_text(run))
    
    return ''.join(parts)


def is_heading1(paragraph):
    """Check if paragraph is a Heading 1."""
    style_name = paragraph.style.name if paragraph.style else ''
    return style_name == 'Heading 1' or style_name.startswith('Heading 1')


def is_heading2(paragraph):
    """Check if paragraph is a Heading 2."""
    style_name = paragraph.style.name if paragraph.style else ''
    return style_name == 'Heading 2' or style_name.startswith('Heading 2')


def is_heading3(paragraph):
    """Check if paragraph is a Heading 3."""
    style_name = paragraph.style.name if paragraph.style else ''
    return style_name == 'Heading 3' or style_name.startswith('Heading 3')


def is_list_paragraph(paragraph):
    """Check if paragraph is a list item."""
    numPr = paragraph._element.find(qn('w:pPr'))
    if numPr is not None:
        numPr = numPr.find(qn('w:numPr'))
        if numPr is not None:
            return True
    
    style_name = paragraph.style.name if paragraph.style else ''
    if 'List' in style_name:
        return True
    
    return False


def get_list_type(paragraph):
    """Determine if list is bulleted or numbered."""
    style_name = paragraph.style.name if paragraph.style else ''
    if 'Number' in style_name or 'Numbered' in style_name:
        return 'numbered'
    return 'bullet'


def parse_docx(docx_path):
    """
    Parse a Word document and extract sections and index entries.
    
    Returns a tuple: (sections_dict, index_dict)
        sections_dict: {section_title: text_content}
        index_dict: {term: [list of section titles]}
    """
    doc = Document(docx_path)
    
    sections = {}
    index = {}  # {term: [section_titles]}
    current_section = None
    current_content = []
    numbered_counter = 0
    
    def add_index_entries(terms, section):
        """Add terms to the index pointing to the given section."""
        for term in terms:
            if term not in index:
                index[term] = []
            if section not in index[term]:
                index[term].append(section)
    
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        
        # Skip empty paragraphs
        if not text:
            if current_section and current_content and current_content[-1] != '':
                current_content.append('')  # Add blank line
            continue
        
        # Check for Heading 1 - new section
        if is_heading1(paragraph):
            # Save previous section
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = text
            current_content = []
            numbered_counter = 0
            continue
        
        # Skip content before first heading
        if current_section is None:
            continue
        
        # Handle headings within section
        if is_heading2(paragraph):
            content_text = get_paragraph_text(paragraph)
            # Extract index entries
            content_text, terms = extract_index_entries(content_text)
            add_index_entries(terms, current_section)
            current_content.append('')
            current_content.append(f'## {content_text}')
            current_content.append('')
            numbered_counter = 0
            continue
        
        if is_heading3(paragraph):
            content_text = get_paragraph_text(paragraph)
            # Extract index entries
            content_text, terms = extract_index_entries(content_text)
            add_index_entries(terms, current_section)
            current_content.append('')
            current_content.append(f'### {content_text}')
            current_content.append('')
            numbered_counter = 0
            continue
        
        # Handle list items
        if is_list_paragraph(paragraph):
            content_text = get_paragraph_text(paragraph)
            # Extract index entries
            content_text, terms = extract_index_entries(content_text)
            add_index_entries(terms, current_section)
            list_type = get_list_type(paragraph)
            if list_type == 'numbered':
                numbered_counter += 1
                current_content.append(f'  {numbered_counter}. {content_text}')
            else:
                current_content.append(f'  • {content_text}')
            continue
        
        # Regular paragraph
        numbered_counter = 0
        content_text = get_paragraph_text(paragraph)
        # Extract index entries
        content_text, terms = extract_index_entries(content_text)
        add_index_entries(terms, current_section)
        if content_text:
            current_content.append(content_text)
    
    # Save last section
    if current_section and current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections, index


TEMPLATE_HEADER = '''"""
Help Window Module

This module provides a searchable help dialog for the SAR K9 Training Records application.
The help content is organized into sections that users can navigate and search.
An Index tab provides alphabetical access to key terms.

AUTO-GENERATED FILE - Do not edit directly!
Generated by generate_help_window.py from the help documentation Word file.
"""

import tkinter as tk
from tkinter import ttk
import re


# Help content organized by section
HELP_SECTIONS = {
'''

TEMPLATE_MIDDLE = '''
}

# Index mapping terms to sections
HELP_INDEX = {
'''

TEMPLATE_FOOTER = '''
}


class HelpWindow:
    """A searchable help dialog with section navigation and index."""
    
    def __init__(self, parent):
        """
        Initialize the help window.
        
        Args:
            parent: Parent tkinter window
        """
        self.parent = parent
        self.window = None
    
    def show(self):
        """Show the help window (or bring existing window to front)."""
        # If window already exists, just bring it to front
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return
        
        # Create new window
        self.window = tk.Toplevel(self.parent)
        self.window.title("SAR K9 Training Record - User Manual")
        
        # Set window size and position (centered)
        window_width = 1000
        window_height = 700
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.window.minsize(800, 500)
        
        self.setup_ui()
        self.populate_sections()
        self.populate_index()
        
        # Select first section by default
        if self.section_listbox.size() > 0:
            self.section_listbox.selection_set(0)
            self.on_section_selected(None)
        
        # Bind Escape key to close
        self.window.bind("<Escape>", lambda e: self.window.destroy())
        
        # Bind F1 to close (toggle behavior)
        self.window.bind("<F1>", lambda e: self.window.destroy())
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main container with padding
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Search bar at top
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_current_tab)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Paned window for left panel and content
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Left frame - notebook with Topics and Index tabs
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        self.notebook = ttk.Notebook(left_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Topics tab
        topics_frame = ttk.Frame(self.notebook)
        self.notebook.add(topics_frame, text="Topics")
        
        list_frame = ttk.Frame(topics_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        self.section_listbox = tk.Listbox(list_frame, width=30, font=('TkDefaultFont', 10))
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.section_listbox.yview)
        self.section_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.section_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.section_listbox.bind('<<ListboxSelect>>', self.on_section_selected)
        
        # Index tab
        index_frame = ttk.Frame(self.notebook)
        self.notebook.add(index_frame, text="Index")
        
        index_list_frame = ttk.Frame(index_frame)
        index_list_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        self.index_listbox = tk.Listbox(index_list_frame, width=30, font=('TkDefaultFont', 10))
        index_scrollbar = ttk.Scrollbar(index_list_frame, orient=tk.VERTICAL, command=self.index_listbox.yview)
        self.index_listbox.configure(yscrollcommand=index_scrollbar.set)
        
        self.index_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        index_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.index_listbox.bind('<<ListboxSelect>>', self.on_index_selected)
        
        # Right frame - content
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=3)
        
        # Content text widget with scrollbar
        content_frame = ttk.Frame(right_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.content_text = tk.Text(
            content_frame, 
            wrap=tk.WORD, 
            font=('Arial', 12),
            padx=15,
            pady=10,
            bg="white",
            fg="black",
            state=tk.DISABLED
        )
        content_scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.content_text.yview)
        self.content_text.configure(yscrollcommand=content_scrollbar.set)
        
        self.content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        content_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure text tags for formatting
        self.content_text.tag_configure('title', font=('Arial', 16, 'bold'), 
                                         foreground='#2c3e50', spacing3=10)
        self.content_text.tag_configure('heading2', font=('Arial', 14, 'bold'),
                                         foreground='#34495e', spacing1=15, spacing3=5)
        self.content_text.tag_configure('heading3', font=('Arial', 12, 'bold'),
                                         foreground='#7f8c8d', spacing1=10, spacing3=5)
        self.content_text.tag_configure('bold', font=('Arial', 12, 'bold'))
        self.content_text.tag_configure('italic', font=('Arial', 12, 'italic'))
        self.content_text.tag_configure('bolditalic', font=('Arial', 12, 'bold italic'))
        self.content_text.tag_configure('bullet', lmargin1=20, lmargin2=35)
        self.content_text.tag_configure('normal', spacing1=3, spacing3=3)
        self.content_text.tag_configure('link', foreground='#2980b9', underline=True)
        self.content_text.tag_configure('index_term', font=('Arial', 12, 'bold'),
                                         foreground='#2c3e50', spacing1=10)
        self.content_text.tag_configure('index_sections', lmargin1=20, foreground='#2980b9',
                                         underline=True)
        
        # Close button at bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Close", command=self.window.destroy).pack(side=tk.RIGHT)
    
    def populate_sections(self):
        """Populate the section list with all help sections."""
        self.section_listbox.delete(0, tk.END)
        self.all_sections = list(HELP_SECTIONS.keys())
        for section_title in self.all_sections:
            self.section_listbox.insert(tk.END, section_title)
    
    def populate_index(self):
        """Populate the index list with all indexed terms."""
        self.index_listbox.delete(0, tk.END)
        self.all_index_terms = sorted(HELP_INDEX.keys(), key=str.lower)
        for term in self.all_index_terms:
            self.index_listbox.insert(tk.END, term)
    
    def on_section_selected(self, event):
        """Handle section selection change."""
        selection = self.section_listbox.curselection()
        if not selection:
            return
        
        section_title = self.section_listbox.get(selection[0])
        content = HELP_SECTIONS.get(section_title, "")
        
        self.display_content(section_title, content)
    
    def on_index_selected(self, event):
        """Handle index term selection - show sections containing this term."""
        selection = self.index_listbox.curselection()
        if not selection:
            return
        
        term = self.index_listbox.get(selection[0])
        sections = HELP_INDEX.get(term, [])
        
        self.display_index_entry(term, sections)
    
    def display_index_entry(self, term, sections):
        """Display an index entry with clickable section links."""
        self.content_text.configure(state=tk.NORMAL)
        self.content_text.delete(1.0, tk.END)
        
        # Insert term as title
        self.content_text.insert(tk.END, f"Index: {term}\\n\\n", 'title')
        
        self.content_text.insert(tk.END, "Found in:\\n\\n", 'normal')
        
        # Insert each section as a clickable link
        for section in sections:
            # Create a unique tag for this link
            link_tag = f"link_{section.replace(' ', '_')}"
            self.content_text.tag_configure(link_tag, foreground='#2980b9', underline=True)
            
            self.content_text.insert(tk.END, "  • ", 'normal')
            self.content_text.insert(tk.END, section, link_tag)
            self.content_text.insert(tk.END, "\\n", 'normal')
            
            # Bind click event to this link
            self.content_text.tag_bind(link_tag, '<Button-1>', 
                                        lambda e, s=section: self.jump_to_section(s))
            self.content_text.tag_bind(link_tag, '<Enter>',
                                        lambda e: self.content_text.configure(cursor='hand2'))
            self.content_text.tag_bind(link_tag, '<Leave>',
                                        lambda e: self.content_text.configure(cursor=''))
        
        self.content_text.configure(state=tk.DISABLED)
    
    def jump_to_section(self, section_name):
        """Jump to a section from an index link."""
        # Switch to Topics tab
        self.notebook.select(0)
        
        # Find and select the section
        for i in range(self.section_listbox.size()):
            if self.section_listbox.get(i) == section_name:
                self.section_listbox.selection_clear(0, tk.END)
                self.section_listbox.selection_set(i)
                self.section_listbox.see(i)
                self.on_section_selected(None)
                break
    
    def display_content(self, title, content):
        """Display formatted content in the text widget."""
        self.content_text.configure(state=tk.NORMAL)
        self.content_text.delete(1.0, tk.END)
        
        # Insert title
        self.content_text.insert(tk.END, title + "\\n\\n", 'title')
        
        # Process content line by line
        lines = content.split('\\n')
        for line in lines:
            if line.startswith('## '):
                # Heading 2
                self.content_text.insert(tk.END, line[3:] + "\\n", 'heading2')
            elif line.startswith('### '):
                # Heading 3
                self.content_text.insert(tk.END, line[4:] + "\\n", 'heading3')
            elif line.strip().startswith('•') or re.match(r'^\\s*\\d+\\.', line):
                # Bullet or numbered list
                self.insert_formatted_text(line + "\\n", 'bullet')
            elif line.strip():
                # Regular paragraph
                self.insert_formatted_text(line + "\\n", 'normal')
            else:
                # Empty line
                self.content_text.insert(tk.END, "\\n")
        
        self.content_text.configure(state=tk.DISABLED)
    
    def insert_formatted_text(self, text, base_tag):
        """Insert text with bold/italic formatting."""
        # Pattern to match **bold**, *italic*, and ***bolditalic***
        pattern = r'(\\*\\*\\*.*?\\*\\*\\*|\\*\\*.*?\\*\\*|\\*.*?\\*)'
        
        parts = re.split(pattern, text)
        for part in parts:
            if part.startswith('***') and part.endswith('***'):
                self.content_text.insert(tk.END, part[3:-3], ('bolditalic', base_tag))
            elif part.startswith('**') and part.endswith('**'):
                self.content_text.insert(tk.END, part[2:-2], ('bold', base_tag))
            elif part.startswith('*') and part.endswith('*') and len(part) > 2:
                self.content_text.insert(tk.END, part[1:-1], ('italic', base_tag))
            else:
                self.content_text.insert(tk.END, part, base_tag)
    
    def filter_current_tab(self, *args):
        """Filter the currently visible tab based on search text."""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:
            self.filter_sections()
        else:
            self.filter_index()
    
    def filter_sections(self, *args):
        """Filter sections based on search text."""
        search_text = self.search_var.get().lower()
        
        self.section_listbox.delete(0, tk.END)
        
        for section_title in self.all_sections:
            section_content = HELP_SECTIONS.get(section_title, "")
            
            # Show item if search text is in title or content
            if search_text in section_title.lower() or search_text in section_content.lower():
                self.section_listbox.insert(tk.END, section_title)
        
        # Select first visible item
        if self.section_listbox.size() > 0:
            self.section_listbox.selection_set(0)
            self.on_section_selected(None)
    
    def filter_index(self, *args):
        """Filter index based on search text."""
        search_text = self.search_var.get().lower()
        
        self.index_listbox.delete(0, tk.END)
        
        for term in self.all_index_terms:
            if search_text in term.lower():
                self.index_listbox.insert(tk.END, term)
        
        # Select first visible item
        if self.index_listbox.size() > 0:
            self.index_listbox.selection_set(0)
            self.on_index_selected(None)
    
    def show_section(self, section_name):
        """Show a specific section by name."""
        self.notebook.select(0)  # Switch to Topics tab
        for i in range(self.section_listbox.size()):
            if self.section_listbox.get(i) == section_name:
                self.section_listbox.selection_clear(0, tk.END)
                self.section_listbox.selection_set(i)
                self.section_listbox.see(i)
                self.on_section_selected(None)
                break


def show_help_window(parent):
    """
    Show the help window.
    
    Args:
        parent: Parent tkinter window
    """
    help_win = HelpWindow(parent)
    help_win.show()


if __name__ == "__main__":
    # Test the help window standalone
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    help_win = HelpWindow(root)
    help_win.show()
    
    root.mainloop()
'''


def generate_help_window_py(sections, index, output_path):
    """Generate the help_window.py file from parsed sections and index."""
    
    # Build the HELP_SECTIONS dictionary content
    sections_items = []
    for title, content in sections.items():
        # Convert \N{name} sequences to actual unicode characters
        content = convert_unicode_names(content)
        title_converted = convert_unicode_names(title)
        escaped_content = escape_for_python_string(content)
        sections_items.append(f'    "{title_converted}": """{escaped_content}"""')
    
    sections_dict = ',\n\n'.join(sections_items)
    
    # Build the HELP_INDEX dictionary content
    index_items = []
    for term in sorted(index.keys(), key=str.lower):
        term_converted = convert_unicode_names(term)
        sections_list = index[term]
        # Convert section names too
        sections_list = [convert_unicode_names(s) for s in sections_list]
        sections_str = ', '.join(f'"{s}"' for s in sections_list)
        index_items.append(f'    "{term_converted}": [{sections_str}]')
    
    index_dict = ',\n'.join(index_items)
    
    # Combine the template parts
    output = TEMPLATE_HEADER + sections_dict + TEMPLATE_MIDDLE + index_dict + TEMPLATE_FOOTER
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"Generated {output_path}")
    print(f"  - {len(sections)} sections created")
    for title in sections.keys():
        print(f"    • {title}")
    print(f"  - {len(index)} index entries created")
    if index:
        for term in sorted(index.keys(), key=str.lower)[:10]:
            print(f"    • {term}")
        if len(index) > 10:
            print(f"    ... and {len(index) - 10} more")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nError: Please provide the input Word document path.")
        print("Usage: python generate_help_window.py input.docx [output.py]")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("help_window.py")
    
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    
    if not input_path.suffix.lower() == '.docx':
        print(f"Error: Input file must be a .docx file, got: {input_path.suffix}")
        sys.exit(1)
    
    print(f"Reading: {input_path}")
    sections, index = parse_docx(input_path)
    
    if not sections:
        print("Warning: No sections found in document.")
        print("Make sure to use Heading 1 style for section titles.")
        sys.exit(1)
    
    generate_help_window_py(sections, index, output_path)
    print("\nDone!")


if __name__ == "__main__":
    main()
