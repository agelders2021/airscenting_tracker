"""
SPDX-License-Identifier: GPL-3.0-or-later

Copyright (C) 2026 Al Gelders

This file is part of the airscenting and trailing logging programs

Status Bar Manager
Common module for managing status bar with 3 priority queues:
- Error (highest priority, red flashing)
- Warning (medium priority, orange)
- Info/Normal (lowest priority, black)
"""
import tkinter as tk
from datetime import datetime


class StatusBarManager:
    """
    Manages status bar with 3 priority queues and timeout behavior.
    
    Features:
    - Three separate queues: error, warning, info (each is a stack - LIFO)
    - Error messages always shown first (red, flashing)
    - Warning messages shown when no errors (orange)
    - Info messages shown when no errors or warnings (black)
    - Cancel button removes current message from its queue
    - Left/right arrows navigate within current priority queue
    - 15-second inactivity timeout reverts to highest priority message
    - Warning generated when any queue reaches 5 messages
    """
    
    def __init__(self, root, status_var, status_label, left_arrow, right_arrow, cancel_button):
        """
        Initialize the status bar manager.
        
        Args:
            root: Tkinter root window (for after() scheduling)
            status_var: StringVar for status text
            status_label: Label widget for status display
            left_arrow: Button for navigating to older messages
            right_arrow: Button for navigating to newer messages
            cancel_button: Button for dismissing current message
        """
        self.root = root
        self.status_var = status_var
        self.status_label = status_label
        self.left_arrow = left_arrow
        self.right_arrow = right_arrow
        self.cancel_button = cancel_button
        
        # Three priority queues (stacks - most recent at end)
        self.error_queue = []    # Highest priority
        self.warning_queue = []  # Medium priority
        self.info_queue = []     # Lowest priority
        
        # Current navigation state
        self.current_queue = None  # 'error', 'warning', 'info', or None
        self.current_index = -1    # -1 = most recent, 0+ = older messages
        
        # Flashing state
        self.is_flashing = False
        self.flash_state = False
        self.flash_after_id = None
        
        # Inactivity timeout
        self.inactivity_after_id = None
        self.INACTIVITY_TIMEOUT = 15000  # 15 seconds in milliseconds
        
        # Queue size warning threshold
        self.QUEUE_WARNING_THRESHOLD = 5
        self._warning_shown = {}  # Track which queues have shown warnings
        
        # Bind button commands
        self.left_arrow.config(command=self.prev_message)
        self.right_arrow.config(command=self.next_message)
        self.cancel_button.config(command=self.dismiss_message)
        
        # Initial state
        self._update_display()
    
    def show_message(self, message, msg_type="info"):
        """
        Add a message to the appropriate queue and display it.
        
        Args:
            message: Message text to display
            msg_type: "error", "warning", or "info"
        """
        timestamp = datetime.now()
        
        # Add to appropriate queue
        if msg_type == "error":
            self.error_queue.append((message, timestamp))
            self._check_queue_warning("error", len(self.error_queue))
        elif msg_type == "warning":
            self.warning_queue.append((message, timestamp))
            self._check_queue_warning("warning", len(self.warning_queue))
        else:
            self.info_queue.append((message, timestamp))
            self._check_queue_warning("info", len(self.info_queue))
        
        # Debug: show queue counts
        counts = self.get_queue_counts()
        total = counts['error'] + counts['warning'] + counts['info']
        # print(f"Status bar: Added {msg_type} message. Queues: E={counts['error']}, W={counts['warning']}, I={counts['info']} (Total: {total})")
        
        # Reset to most recent of highest priority
        self._reset_to_highest_priority()
        self._update_display()
        self._reset_inactivity_timer()
    
    def _check_queue_warning(self, queue_name, queue_len):
        """Generate warning when queue reaches threshold"""
        if queue_len == self.QUEUE_WARNING_THRESHOLD:
            if queue_name not in self._warning_shown:
                self._warning_shown[queue_name] = True
                # print(f"Status bar: {queue_name.capitalize()} queue has {queue_len} messages")
        elif queue_len < self.QUEUE_WARNING_THRESHOLD:
            # Reset warning flag when queue drops below threshold
            if queue_name in self._warning_shown:
                del self._warning_shown[queue_name]
    
    def _reset_to_highest_priority(self):
        """Reset navigation to most recent message of highest priority queue"""
        if self.error_queue:
            self.current_queue = 'error'
        elif self.warning_queue:
            self.current_queue = 'warning'
        elif self.info_queue:
            self.current_queue = 'info'
        else:
            self.current_queue = None
        
        self.current_index = -1  # Most recent
    
    def _get_current_queue(self):
        """Get the list for the current queue"""
        if self.current_queue == 'error':
            return self.error_queue
        elif self.current_queue == 'warning':
            return self.warning_queue
        elif self.current_queue == 'info':
            return self.info_queue
        return []
    
    def _get_current_message(self):
        """Get the currently displayed message and its type"""
        queue = self._get_current_queue()
        if not queue:
            return None, None
        
        # current_index: -1 = most recent (end), 0 = second most recent from end, etc.
        if self.current_index == -1:
            idx = len(queue) - 1
        else:
            idx = len(queue) - 1 - self.current_index
        
        if 0 <= idx < len(queue):
            return queue[idx][0], self.current_queue
        return None, None
    
    def prev_message(self):
        """Navigate to previous (older) message in current queue"""
        self._reset_inactivity_timer()
        
        queue = self._get_current_queue()
        if not queue:
            return
        
        # Move to older message (increase index)
        max_index = len(queue) - 1
        
        if self.current_index == -1:
            # Currently at most recent, go to second most recent
            if len(queue) >= 2:
                self.current_index = 1
        elif self.current_index < max_index:
            self.current_index += 1
        
        self._update_display()
    
    def next_message(self):
        """Navigate to next (newer) message in current queue"""
        self._reset_inactivity_timer()
        
        queue = self._get_current_queue()
        if not queue:
            return
        
        # Move to newer message (decrease index)
        if self.current_index > 0:
            self.current_index -= 1
        elif self.current_index == 0:
            # At second most recent, go to most recent
            self.current_index = -1
        
        self._update_display()
    
    def dismiss_message(self, event=None):
        """Remove the current message from its queue"""
        self._reset_inactivity_timer()
        self._stop_flash()
        
        queue = self._get_current_queue()
        if not queue:
            self.status_var.set("")
            self._update_arrow_states()
            return
        
        # Calculate actual index in list
        if self.current_index == -1:
            idx = len(queue) - 1
        else:
            idx = len(queue) - 1 - self.current_index
        
        # Remove the message
        if 0 <= idx < len(queue):
            queue.pop(idx)
        
        # If queue is now empty, switch to next priority
        if not queue:
            self._reset_to_highest_priority()
        else:
            # Stay in same queue, adjust index if needed
            if self.current_index >= len(queue):
                self.current_index = -1
        
        self._update_display()
    
    def _update_display(self):
        """Update the status bar display based on current state"""
        message, msg_type = self._get_current_message()
        
        if message is None:
            self.status_var.set("")
            self._stop_flash()
            self.status_label.config(fg="black", bg="SystemButtonFace", 
                                    font=("TkDefaultFont", 9, "normal"))
        elif msg_type == 'error':
            self.status_var.set(message)
            self._start_flash()
        elif msg_type == 'warning':
            self._stop_flash()
            self.status_var.set(message)
            self.status_label.config(fg="orange", bg="SystemButtonFace",
                                    font=("TkDefaultFont", 9, "normal"))
        else:  # info
            self._stop_flash()
            self.status_var.set(message)
            self.status_label.config(fg="black", bg="SystemButtonFace",
                                    font=("TkDefaultFont", 9, "normal"))
        
        self._update_arrow_states()
    
    def _update_arrow_states(self):
        """Update arrow button states based on current queue and position"""
        queue = self._get_current_queue()
        
        if not queue or len(queue) <= 1:
            # No messages or only one message - disable both arrows
            self.left_arrow.config(state="disabled")
            self.right_arrow.config(state="disabled")
            return
        
        queue_len = len(queue)
        
        # Left arrow (older messages)
        if self.current_index == -1:
            # At most recent - can go older if there are older messages
            left_state = "normal" if queue_len >= 2 else "disabled"
            self.left_arrow.config(state=left_state)
        elif self.current_index < queue_len - 1:
            # Not at oldest - can go older
            self.left_arrow.config(state="normal")
        else:
            # At oldest
            self.left_arrow.config(state="disabled")
        
        # Right arrow (newer messages)
        if self.current_index == -1:
            # At most recent - can't go newer
            self.right_arrow.config(state="disabled")
        else:
            # Not at most recent - can go newer
            self.right_arrow.config(state="normal")
        
        # Debug output
        left_state = self.left_arrow.cget('state')
        right_state = self.right_arrow.cget('state')
        # print(f"Status bar arrows: queue={self.current_queue}, len={queue_len}, idx={self.current_index}, left={left_state}, right={right_state}")
    
    def _start_flash(self):
        """Start flashing for error messages"""
        if self.is_flashing:
            return  # Already flashing
        
        self.is_flashing = True
        self.flash_state = False
        self._flash_step()
    
    def _flash_step(self):
        """Single step of flash animation"""
        if not self.is_flashing:
            return
        
        if self.flash_state:
            # Flash ON - red background, white text
            self.status_label.config(bg="red", fg="white", 
                                    font=("TkDefaultFont", 9, "bold"))
        else:
            # Flash OFF - normal background, red text
            self.status_label.config(bg="SystemButtonFace", fg="red",
                                    font=("TkDefaultFont", 9, "bold"))
        
        self.flash_state = not self.flash_state
        self.flash_after_id = self.root.after(300, self._flash_step)
    
    def _stop_flash(self):
        """Stop flash animation"""
        self.is_flashing = False
        if self.flash_after_id:
            try:
                self.root.after_cancel(self.flash_after_id)
            except:
                pass
            self.flash_after_id = None
        
        # Reset to normal appearance (will be updated by _update_display)
        self.status_label.config(bg="SystemButtonFace", fg="black",
                                font=("TkDefaultFont", 9, "normal"))
    
    def _reset_inactivity_timer(self):
        """Reset the inactivity timer"""
        # Cancel existing timer
        if self.inactivity_after_id:
            try:
                self.root.after_cancel(self.inactivity_after_id)
            except:
                pass
        
        # Start new timer
        self.inactivity_after_id = self.root.after(
            self.INACTIVITY_TIMEOUT, 
            self._on_inactivity_timeout
        )
    
    def _on_inactivity_timeout(self):
        """Called when user has been inactive for 15 seconds"""
        # Revert to highest priority, most recent message
        self._reset_to_highest_priority()
        self._update_display()
    
    def clear_all(self):
        """Clear all queues"""
        self._stop_flash()
        self.error_queue.clear()
        self.warning_queue.clear()
        self.info_queue.clear()
        self.current_queue = None
        self.current_index = -1
        self._update_display()
    
    def get_queue_counts(self):
        """Get count of messages in each queue"""
        return {
            'error': len(self.error_queue),
            'warning': len(self.warning_queue),
            'info': len(self.info_queue)
        }
