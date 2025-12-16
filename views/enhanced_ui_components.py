"""
Enhanced UI Components with Dark Theme, Progress Indicators, and Keyboard Shortcuts
Addresses TODO items #8-10: UI/UX Improvements
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# THEME CONFIGURATION
# ============================================================================

class ThemeColors:
    """Dark theme color palette"""
    
    # Background colors
    BG_PRIMARY = "#1a1a2e"
    BG_SECONDARY = "#16213e"
    BG_TERTIARY = "#0f3460"
    BG_CARD = "#1f2937"
    
    # Text colors
    TEXT_PRIMARY = "#e4e4e7"
    TEXT_SECONDARY = "#a1a1aa"
    TEXT_MUTED = "#71717a"
    
    # Accent colors
    ACCENT_PRIMARY = "#3b82f6"
    ACCENT_SUCCESS = "#22c55e"
    ACCENT_WARNING = "#f59e0b"
    ACCENT_ERROR = "#ef4444"
    ACCENT_INFO = "#06b6d4"
    
    # Border colors
    BORDER = "#374151"
    BORDER_FOCUS = "#3b82f6"
    
    # Button colors
    BTN_PRIMARY_BG = "#3b82f6"
    BTN_PRIMARY_FG = "#ffffff"
    BTN_SECONDARY_BG = "#374151"
    BTN_SECONDARY_FG = "#e4e4e7"
    BTN_DANGER_BG = "#ef4444"
    BTN_DANGER_FG = "#ffffff"


class ThemeFonts:
    """Font configuration"""
    
    FAMILY = "Segoe UI"
    FAMILY_MONO = "Consolas"
    
    SIZE_XS = 9
    SIZE_SM = 10
    SIZE_BASE = 11
    SIZE_LG = 13
    SIZE_XL = 16
    SIZE_2XL = 20
    SIZE_3XL = 24


def apply_dark_theme(root: tk.Tk) -> None:
    """Apply dark theme to the application"""
    
    style = ttk.Style()
    
    # Configure main theme
    style.theme_use('clam')
    
    # Configure colors
    style.configure(
        '.',
        background=ThemeColors.BG_PRIMARY,
        foreground=ThemeColors.TEXT_PRIMARY,
        fieldbackground=ThemeColors.BG_SECONDARY,
        font=(ThemeFonts.FAMILY, ThemeFonts.SIZE_BASE)
    )
    
    # Frame styles
    style.configure(
        'TFrame',
        background=ThemeColors.BG_PRIMARY
    )
    
    style.configure(
        'Card.TFrame',
        background=ThemeColors.BG_CARD,
        relief='flat'
    )
    
    # Label styles
    style.configure(
        'TLabel',
        background=ThemeColors.BG_PRIMARY,
        foreground=ThemeColors.TEXT_PRIMARY
    )
    
    style.configure(
        'Title.TLabel',
        font=(ThemeFonts.FAMILY, ThemeFonts.SIZE_2XL, 'bold'),
        foreground=ThemeColors.TEXT_PRIMARY
    )
    
    style.configure(
        'Subtitle.TLabel',
        font=(ThemeFonts.FAMILY, ThemeFonts.SIZE_LG),
        foreground=ThemeColors.TEXT_SECONDARY
    )
    
    style.configure(
        'Muted.TLabel',
        foreground=ThemeColors.TEXT_MUTED
    )
    
    # Button styles
    style.configure(
        'TButton',
        background=ThemeColors.BTN_SECONDARY_BG,
        foreground=ThemeColors.BTN_SECONDARY_FG,
        padding=(12, 8),
        font=(ThemeFonts.FAMILY, ThemeFonts.SIZE_BASE)
    )
    
    style.map(
        'TButton',
        background=[('active', ThemeColors.BG_TERTIARY)]
    )
    
    style.configure(
        'Primary.TButton',
        background=ThemeColors.BTN_PRIMARY_BG,
        foreground=ThemeColors.BTN_PRIMARY_FG
    )
    
    style.map(
        'Primary.TButton',
        background=[('active', '#2563eb')]
    )
    
    style.configure(
        'Danger.TButton',
        background=ThemeColors.BTN_DANGER_BG,
        foreground=ThemeColors.BTN_DANGER_FG
    )
    
    style.map(
        'Danger.TButton',
        background=[('active', '#dc2626')]
    )
    
    style.configure(
        'Success.TButton',
        background=ThemeColors.ACCENT_SUCCESS,
        foreground='#ffffff'
    )
    
    # Entry styles
    style.configure(
        'TEntry',
        fieldbackground=ThemeColors.BG_SECONDARY,
        foreground=ThemeColors.TEXT_PRIMARY,
        insertcolor=ThemeColors.TEXT_PRIMARY,
        padding=8
    )
    
    # Progressbar styles
    style.configure(
        'TProgressbar',
        background=ThemeColors.ACCENT_PRIMARY,
        troughcolor=ThemeColors.BG_SECONDARY,
        thickness=8
    )
    
    style.configure(
        'Success.Horizontal.TProgressbar',
        background=ThemeColors.ACCENT_SUCCESS
    )
    
    style.configure(
        'Warning.Horizontal.TProgressbar',
        background=ThemeColors.ACCENT_WARNING
    )
    
    # Treeview styles
    style.configure(
        'Treeview',
        background=ThemeColors.BG_SECONDARY,
        foreground=ThemeColors.TEXT_PRIMARY,
        fieldbackground=ThemeColors.BG_SECONDARY,
        rowheight=30
    )
    
    style.configure(
        'Treeview.Heading',
        background=ThemeColors.BG_TERTIARY,
        foreground=ThemeColors.TEXT_PRIMARY,
        font=(ThemeFonts.FAMILY, ThemeFonts.SIZE_BASE, 'bold')
    )
    
    style.map(
        'Treeview',
        background=[('selected', ThemeColors.ACCENT_PRIMARY)],
        foreground=[('selected', '#ffffff')]
    )
    
    # Notebook styles
    style.configure(
        'TNotebook',
        background=ThemeColors.BG_PRIMARY,
        tabmargins=[2, 5, 2, 0]
    )
    
    style.configure(
        'TNotebook.Tab',
        background=ThemeColors.BG_SECONDARY,
        foreground=ThemeColors.TEXT_SECONDARY,
        padding=[15, 8],
        font=(ThemeFonts.FAMILY, ThemeFonts.SIZE_BASE)
    )
    
    style.map(
        'TNotebook.Tab',
        background=[('selected', ThemeColors.BG_TERTIARY)],
        foreground=[('selected', ThemeColors.TEXT_PRIMARY)]
    )
    
    # Scrollbar styles
    style.configure(
        'TScrollbar',
        background=ThemeColors.BG_SECONDARY,
        troughcolor=ThemeColors.BG_PRIMARY,
        arrowcolor=ThemeColors.TEXT_SECONDARY
    )
    
    # Configure root window
    root.configure(bg=ThemeColors.BG_PRIMARY)


# ============================================================================
# PROGRESS INDICATORS
# ============================================================================

class ProgressType(Enum):
    """Progress indicator types"""
    DETERMINATE = "determinate"
    INDETERMINATE = "indeterminate"


@dataclass
class ProgressState:
    """Progress state data"""
    current: int = 0
    total: int = 100
    message: str = ""
    sub_message: str = ""
    is_complete: bool = False
    is_error: bool = False
    error_message: str = ""


class ProgressIndicator(ttk.Frame):
    """
    Enhanced progress indicator with multiple display modes
    
    Features:
    - Determinate and indeterminate modes
    - Progress percentage display
    - Status message
    - Cancel button
    - Time estimation
    """
    
    def __init__(
        self,
        parent,
        title: str = "Bezig...",
        show_percentage: bool = True,
        show_cancel: bool = True,
        progress_type: ProgressType = ProgressType.DETERMINATE,
        on_cancel: Optional[Callable] = None
    ):
        super().__init__(parent, style='Card.TFrame')
        
        self.title = title
        self.show_percentage = show_percentage
        self.show_cancel = show_cancel
        self.progress_type = progress_type
        self.on_cancel = on_cancel
        
        self._state = ProgressState()
        self._start_time: Optional[float] = None
        
        self._create_widgets()
    
    def _create_widgets(self) -> None:
        """Create progress indicator widgets"""
        # Container with padding
        container = ttk.Frame(self, style='Card.TFrame')
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Title
        self._title_label = ttk.Label(
            container,
            text=self.title,
            style='Subtitle.TLabel'
        )
        self._title_label.pack(anchor=tk.W)
        
        # Progress bar
        self._progress_bar = ttk.Progressbar(
            container,
            mode=self.progress_type.value,
            length=300
        )
        self._progress_bar.pack(fill=tk.X, pady=(10, 5))
        
        # Status row
        status_frame = ttk.Frame(container, style='Card.TFrame')
        status_frame.pack(fill=tk.X)
        
        # Status message
        self._status_label = ttk.Label(
            status_frame,
            text="",
            style='Muted.TLabel'
        )
        self._status_label.pack(side=tk.LEFT)
        
        # Percentage / ETA
        if self.show_percentage:
            self._percentage_label = ttk.Label(
                status_frame,
                text="0%",
                style='TLabel'
            )
            self._percentage_label.pack(side=tk.RIGHT)
        
        # Cancel button
        if self.show_cancel:
            self._cancel_btn = ttk.Button(
                container,
                text="Annuleren",
                style='Danger.TButton',
                command=self._handle_cancel
            )
            self._cancel_btn.pack(pady=(10, 0))
    
    def update_progress(
        self,
        current: int,
        total: int,
        message: str = "",
        sub_message: str = ""
    ) -> None:
        """Update progress state"""
        import time
        
        if self._start_time is None:
            self._start_time = time.time()
        
        self._state.current = current
        self._state.total = total
        self._state.message = message
        self._state.sub_message = sub_message
        
        # Update progress bar
        if self.progress_type == ProgressType.DETERMINATE:
            percentage = (current / total * 100) if total > 0 else 0
            self._progress_bar['value'] = percentage
            
            if self.show_percentage:
                # Calculate ETA
                elapsed = time.time() - self._start_time
                if current > 0:
                    eta = (elapsed / current) * (total - current)
                    eta_str = self._format_time(eta)
                    self._percentage_label.configure(
                        text=f"{percentage:.1f}% - ETA: {eta_str}"
                    )
                else:
                    self._percentage_label.configure(text=f"{percentage:.1f}%")
        
        # Update status message
        status_text = message
        if sub_message:
            status_text += f" - {sub_message}"
        self._status_label.configure(text=status_text)
        
        # Force UI update
        self.update_idletasks()
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds as human-readable time"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}u {minutes}m"
    
    def set_complete(self, message: str = "Voltooid!") -> None:
        """Mark progress as complete"""
        self._state.is_complete = True
        self._progress_bar['value'] = 100
        self._status_label.configure(text=message)
        
        if self.show_percentage:
            self._percentage_label.configure(text="100%")
        
        if self.show_cancel:
            self._cancel_btn.configure(text="Sluiten", style='Success.TButton')
    
    def set_error(self, error_message: str) -> None:
        """Mark progress as error"""
        self._state.is_error = True
        self._state.error_message = error_message
        self._status_label.configure(text=f"Fout: {error_message}")
        
        if self.show_cancel:
            self._cancel_btn.configure(text="Sluiten", style='Danger.TButton')
    
    def _handle_cancel(self) -> None:
        """Handle cancel button click"""
        if self.on_cancel:
            self.on_cancel()


class ProgressDialog(tk.Toplevel):
    """
    Modal progress dialog
    
    Features:
    - Modal blocking
    - Auto-close on completion
    - Error handling
    """
    
    def __init__(
        self,
        parent,
        title: str = "Bezig...",
        task_name: str = "",
        on_cancel: Optional[Callable] = None,
        auto_close: bool = True
    ):
        super().__init__(parent)
        
        self.title(title)
        self.task_name = task_name
        self.on_cancel = on_cancel
        self.auto_close = auto_close
        
        # Configure window
        self.configure(bg=ThemeColors.BG_PRIMARY)
        self.geometry("400x180")
        self.resizable(False, False)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 180) // 2
        self.geometry(f"+{x}+{y}")
        
        # Create progress indicator
        self.progress = ProgressIndicator(
            self,
            title=task_name,
            on_cancel=self._handle_cancel
        )
        self.progress.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._handle_cancel)
    
    def update_progress(self, current: int, total: int, message: str = "") -> None:
        """Update progress"""
        self.progress.update_progress(current, total, message)
    
    def complete(self, message: str = "Voltooid!") -> None:
        """Mark as complete"""
        self.progress.set_complete(message)
        
        if self.auto_close:
            self.after(1500, self.destroy)
    
    def error(self, error_message: str) -> None:
        """Show error"""
        self.progress.set_error(error_message)
    
    def _handle_cancel(self) -> None:
        """Handle cancel/close"""
        if self.on_cancel:
            self.on_cancel()
        self.destroy()


# ============================================================================
# KEYBOARD SHORTCUTS
# ============================================================================

class KeyboardShortcuts:
    """
    Keyboard shortcut manager
    
    Features:
    - Global shortcuts
    - Context-sensitive shortcuts
    - Shortcut hints display
    """
    
    # Default shortcuts
    DEFAULT_SHORTCUTS = {
        '<Control-n>': ('Nieuw', 'new'),
        '<Control-s>': ('Opslaan', 'save'),
        '<Control-o>': ('Openen', 'open'),
        '<Control-q>': ('Afsluiten', 'quit'),
        '<Control-f>': ('Zoeken', 'search'),
        '<Control-r>': ('Vernieuwen', 'refresh'),
        '<F5>': ('Vernieuwen', 'refresh'),
        '<Escape>': ('Annuleren', 'cancel'),
        '<Control-z>': ('Ongedaan maken', 'undo'),
        '<Control-y>': ('Opnieuw', 'redo'),
        '<Control-a>': ('Alles selecteren', 'select_all'),
        '<Control-Shift-s>': ('Opslaan als', 'save_as'),
        '<Control-p>': ('Afdrukken', 'print'),
        '<Control-h>': ('Help', 'help'),
        '<F1>': ('Help', 'help'),
    }
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self._handlers: Dict[str, Callable] = {}
        self._enabled = True
    
    def register(self, shortcut: str, handler: Callable) -> None:
        """Register a keyboard shortcut handler"""
        self._handlers[shortcut] = handler
        self.root.bind(shortcut, self._create_handler(shortcut))
    
    def _create_handler(self, shortcut: str) -> Callable:
        """Create event handler for shortcut"""
        def handler(event):
            if self._enabled and shortcut in self._handlers:
                self._handlers[shortcut]()
                return "break"
        return handler
    
    def unregister(self, shortcut: str) -> None:
        """Unregister a keyboard shortcut"""
        if shortcut in self._handlers:
            del self._handlers[shortcut]
            self.root.unbind(shortcut)
    
    def enable(self) -> None:
        """Enable all shortcuts"""
        self._enabled = True
    
    def disable(self) -> None:
        """Disable all shortcuts"""
        self._enabled = False
    
    def get_shortcuts_list(self) -> List[Dict[str, str]]:
        """Get list of registered shortcuts"""
        shortcuts = []
        for key, handler in self._handlers.items():
            name, action = self.DEFAULT_SHORTCUTS.get(key, (key, 'custom'))
            shortcuts.append({
                'key': self._format_key(key),
                'name': name,
                'action': action
            })
        return shortcuts
    
    def _format_key(self, key: str) -> str:
        """Format key binding for display"""
        key = key.replace('<', '').replace('>', '')
        key = key.replace('Control', 'Ctrl')
        key = key.replace('-', '+')
        return key


class ShortcutsHelpDialog(tk.Toplevel):
    """Dialog showing available keyboard shortcuts"""
    
    def __init__(self, parent, shortcuts: KeyboardShortcuts):
        super().__init__(parent)
        
        self.title("Sneltoetsen")
        self.configure(bg=ThemeColors.BG_PRIMARY)
        self.geometry("350x400")
        self.resizable(False, False)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 350) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 400) // 2
        self.geometry(f"+{x}+{y}")
        
        # Title
        title_label = ttk.Label(
            self,
            text="Sneltoetsen",
            style='Title.TLabel'
        )
        title_label.pack(pady=(20, 10))
        
        # Shortcuts list
        shortcuts_frame = ttk.Frame(self)
        shortcuts_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        for shortcut_info in shortcuts.get_shortcuts_list():
            row = ttk.Frame(shortcuts_frame)
            row.pack(fill=tk.X, pady=3)
            
            key_label = ttk.Label(
                row,
                text=shortcut_info['key'],
                font=(ThemeFonts.FAMILY_MONO, ThemeFonts.SIZE_BASE),
                foreground=ThemeColors.ACCENT_PRIMARY
            )
            key_label.pack(side=tk.LEFT)
            
            name_label = ttk.Label(
                row,
                text=shortcut_info['name'],
                style='Muted.TLabel'
            )
            name_label.pack(side=tk.RIGHT)
        
        # Close button
        close_btn = ttk.Button(
            self,
            text="Sluiten",
            command=self.destroy
        )
        close_btn.pack(pady=20)
        
        # Bind Escape to close
        self.bind('<Escape>', lambda e: self.destroy())


# ============================================================================
# STATUS BAR
# ============================================================================

class StatusBar(ttk.Frame):
    """
    Enhanced status bar with multiple sections
    
    Features:
    - Multiple status sections
    - Progress indicator
    - Notification area
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.configure(style='TFrame')
        
        # Left section - main status
        self._status_label = ttk.Label(
            self,
            text="Gereed",
            style='Muted.TLabel'
        )
        self._status_label.pack(side=tk.LEFT, padx=10)
        
        # Right section - info
        self._info_label = ttk.Label(
            self,
            text="",
            style='Muted.TLabel'
        )
        self._info_label.pack(side=tk.RIGHT, padx=10)
        
        # Progress bar (hidden by default)
        self._progress_bar = ttk.Progressbar(
            self,
            mode='determinate',
            length=150
        )
        
        # Separator
        separator = ttk.Separator(self, orient=tk.VERTICAL)
        separator.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=2)
    
    def set_status(self, message: str) -> None:
        """Set main status message"""
        self._status_label.configure(text=message)
    
    def set_info(self, info: str) -> None:
        """Set info section"""
        self._info_label.configure(text=info)
    
    def show_progress(self, value: int = 0) -> None:
        """Show progress bar"""
        self._progress_bar.pack(side=tk.RIGHT, padx=10)
        self._progress_bar['value'] = value
    
    def update_progress(self, value: int) -> None:
        """Update progress value"""
        self._progress_bar['value'] = value
    
    def hide_progress(self) -> None:
        """Hide progress bar"""
        self._progress_bar.pack_forget()


# ============================================================================
# NOTIFICATION TOAST
# ============================================================================

class ToastType(Enum):
    """Toast notification types"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class Toast(tk.Toplevel):
    """
    Toast notification popup
    
    Features:
    - Auto-dismiss
    - Multiple types (info, success, warning, error)
    - Click to dismiss
    """
    
    COLORS = {
        ToastType.INFO: ThemeColors.ACCENT_INFO,
        ToastType.SUCCESS: ThemeColors.ACCENT_SUCCESS,
        ToastType.WARNING: ThemeColors.ACCENT_WARNING,
        ToastType.ERROR: ThemeColors.ACCENT_ERROR,
    }
    
    def __init__(
        self,
        parent,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        duration: int = 3000
    ):
        super().__init__(parent)
        
        self.message = message
        self.toast_type = toast_type
        self.duration = duration
        
        # Configure window
        self.overrideredirect(True)
        self.configure(bg=self.COLORS[toast_type])
        
        # Create content
        self._create_content()
        
        # Position at bottom right of parent
        self.update_idletasks()
        x = parent.winfo_x() + parent.winfo_width() - self.winfo_width() - 20
        y = parent.winfo_y() + parent.winfo_height() - self.winfo_height() - 40
        self.geometry(f"+{x}+{y}")
        
        # Bind click to dismiss
        self.bind('<Button-1>', lambda e: self.destroy())
        
        # Auto-dismiss
        if duration > 0:
            self.after(duration, self.destroy)
    
    def _create_content(self) -> None:
        """Create toast content"""
        frame = tk.Frame(self, bg=self.COLORS[self.toast_type])
        frame.pack(padx=15, pady=10)
        
        # Icon
        icons = {
            ToastType.INFO: "ℹ",
            ToastType.SUCCESS: "✓",
            ToastType.WARNING: "⚠",
            ToastType.ERROR: "✕",
        }
        
        icon_label = tk.Label(
            frame,
            text=icons[self.toast_type],
            font=(ThemeFonts.FAMILY, ThemeFonts.SIZE_LG),
            fg='white',
            bg=self.COLORS[self.toast_type]
        )
        icon_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Message
        msg_label = tk.Label(
            frame,
            text=self.message,
            font=(ThemeFonts.FAMILY, ThemeFonts.SIZE_BASE),
            fg='white',
            bg=self.COLORS[self.toast_type],
            wraplength=300
        )
        msg_label.pack(side=tk.LEFT)


def show_toast(
    parent,
    message: str,
    toast_type: ToastType = ToastType.INFO,
    duration: int = 3000
) -> Toast:
    """Show a toast notification"""
    return Toast(parent, message, toast_type, duration)


# ============================================================================
# CONFIRMATION DIALOGS
# ============================================================================

class ConfirmDialog(tk.Toplevel):
    """
    Custom confirmation dialog with dark theme
    
    Features:
    - Custom message
    - Multiple button options
    - Icon support
    """
    
    def __init__(
        self,
        parent,
        title: str,
        message: str,
        confirm_text: str = "Bevestigen",
        cancel_text: str = "Annuleren",
        is_dangerous: bool = False
    ):
        super().__init__(parent)
        
        self.result = False
        
        # Configure window
        self.title(title)
        self.configure(bg=ThemeColors.BG_PRIMARY)
        self.geometry("400x180")
        self.resizable(False, False)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 180) // 2
        self.geometry(f"+{x}+{y}")
        
        # Content
        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Message
        msg_label = ttk.Label(
            content_frame,
            text=message,
            wraplength=350,
            justify=tk.LEFT
        )
        msg_label.pack(pady=(0, 20))
        
        # Buttons
        btn_frame = ttk.Frame(content_frame)
        btn_frame.pack(fill=tk.X)
        
        cancel_btn = ttk.Button(
            btn_frame,
            text=cancel_text,
            command=self._cancel
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        confirm_style = 'Danger.TButton' if is_dangerous else 'Primary.TButton'
        confirm_btn = ttk.Button(
            btn_frame,
            text=confirm_text,
            style=confirm_style,
            command=self._confirm
        )
        confirm_btn.pack(side=tk.RIGHT)
        
        # Bind keys
        self.bind('<Return>', lambda e: self._confirm())
        self.bind('<Escape>', lambda e: self._cancel())
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._cancel)
    
    def _confirm(self) -> None:
        """Handle confirm"""
        self.result = True
        self.destroy()
    
    def _cancel(self) -> None:
        """Handle cancel"""
        self.result = False
        self.destroy()


def confirm(
    parent,
    title: str,
    message: str,
    confirm_text: str = "Bevestigen",
    cancel_text: str = "Annuleren",
    is_dangerous: bool = False
) -> bool:
    """Show confirmation dialog and return result"""
    dialog = ConfirmDialog(
        parent, title, message, confirm_text, cancel_text, is_dangerous
    )
    parent.wait_window(dialog)
    return dialog.result
