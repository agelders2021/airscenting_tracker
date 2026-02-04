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
Trailing UI Module
Contains only tkinter widget construction for the Trailing Training Session tab.
Uses TrailingEntryTab from ui_trailing.py which handles the actual widget creation.
Helper methods are in trail_helper.py
"""
from ui_trailing import TrailingEntryTab


def setup_trailing_tab(ui):
    """
    Setup the Trailing Training Session Entry tab.
    
    Args:
        ui: The main TrainingLoggerUI instance
    
    Creates the TrailingEntryTab and stores reference on ui.trailing_entry.
    The TrailingEntryTab class handles all widget creation internally.
    """
    # Create callbacks for the trailing entry tab
    # These connect the TrailingEntryTab to methods on the main ui
    callbacks = {
        'on_save': ui.on_trailing_session_save,
        'get_next_session_number': ui.get_trailing_next_session_number,
        'on_load_prior_session': ui.on_trailing_load_prior_session,
        'on_navigate_previous': ui.on_trailing_navigate_previous,
        'on_navigate_next': ui.on_trailing_navigate_next,
        'on_export_pdf': ui.on_trailing_export_pdf,
        'on_resume_session': ui.on_trailing_resume_session,
        'on_hide_session': ui.on_trailing_hide_session,
    }
    
    # Create the trailing entry tab
    # TrailingEntryTab creates all widgets internally
    ui.trailing_entry = TrailingEntryTab(ui.trailing_tab, ui, callbacks)
