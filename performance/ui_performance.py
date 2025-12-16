"""
UI Performance Optimizations
Implements virtual scrolling, debouncing, lazy loading, and other
UI performance enhancements for responsive user experience.
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import logging
from typing import Optional, Dict, List, Any, Callable, TypeVar
from dataclasses import dataclass
from functools import wraps
from collections import OrderedDict

logger = logging.getLogger(__name__)

T = TypeVar('T')


def debounce(wait_ms: int = 300):
    """
    Debounce decorator - delays execution until calls stop
    
    Useful for search inputs, window resize handlers, etc.
    
    Usage:
        @debounce(300)
        def on_search_changed(query):
            perform_search(query)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., None]:
        timer = None
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal timer
            
            if timer is not None:
                timer.cancel()
            
            def call_func():
                func(*args, **kwargs)
            
            timer = threading.Timer(wait_ms / 1000, call_func)
            timer.start()
        
        return wrapper
    return decorator


def throttle(interval_ms: int = 100):
    """
    Throttle decorator - limits execution rate
    
    Useful for scroll handlers, mouse move events, etc.
    
    Usage:
        @throttle(100)
        def on_scroll(event):
            update_visible_items()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        last_call = 0
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            nonlocal last_call
            now = time.monotonic() * 1000
            
            if now - last_call >= interval_ms:
                last_call = now
                return func(*args, **kwargs)
            return None
        
        return wrapper
    return decorator


class VirtualScrollList(tk.Frame):
    """
    Virtual Scrolling List Widget
    
    Only renders visible items, enabling smooth scrolling
    through thousands of items without performance issues.
    
    Features:
    - Renders only visible items
    - Smooth scrolling
    - Dynamic item heights
    - Selection support
    - Keyboard navigation
    """
    
    def __init__(
        self,
        parent,
        item_height: int = 60,
        buffer_items: int = 5,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.item_height = item_height
        self.buffer_items = buffer_items
        self._items: List[Dict] = []
        self._visible_widgets: Dict[int, tk.Frame] = {}
        self._selected_index: Optional[int] = None
        self._render_func: Optional[Callable] = None
        
        self._setup_ui()
        self._bind_events()
    
    def _setup_ui(self) -> None:
        """Setup UI components"""
        # Canvas for scrolling
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        
        # Container for items
        self.container = tk.Frame(self.canvas)
        
        # Pack components
        self.scrollbar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        
        # Create window in canvas
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.container,
            anchor='nw'
        )
        
        # Configure scrolling
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
    
    def _bind_events(self) -> None:
        """Bind event handlers"""
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Button-4>', self._on_mousewheel)  # Linux
        self.canvas.bind('<Button-5>', self._on_mousewheel)  # Linux
        
        # Keyboard navigation
        self.bind('<Up>', self._on_key_up)
        self.bind('<Down>', self._on_key_down)
        self.bind('<Return>', self._on_key_enter)
    
    def set_items(self, items: List[Dict]) -> None:
        """Set list items"""
        self._items = items
        self._update_scroll_region()
        self._render_visible()
    
    def set_render_func(self, func: Callable[[tk.Frame, Dict, int], None]) -> None:
        """
        Set function to render each item
        
        Args:
            func: Function(parent_frame, item_data, index) -> None
        """
        self._render_func = func
    
    def _update_scroll_region(self) -> None:
        """Update canvas scroll region"""
        total_height = len(self._items) * self.item_height
        self.container.configure(height=total_height)
        self.canvas.configure(scrollregion=(0, 0, self.winfo_width(), total_height))
    
    def _on_canvas_configure(self, event) -> None:
        """Handle canvas resize"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        self._render_visible()
    
    @throttle(50)
    def _on_mousewheel(self, event) -> None:
        """Handle mouse wheel scrolling"""
        if event.num == 4:  # Linux scroll up
            delta = -1
        elif event.num == 5:  # Linux scroll down
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        
        self.canvas.yview_scroll(delta * 3, 'units')
        self._render_visible()
    
    def _render_visible(self) -> None:
        """Render only visible items"""
        if not self._items or not self._render_func:
            return
        
        # Get visible range
        canvas_height = self.canvas.winfo_height()
        scroll_top = self.canvas.canvasy(0)
        
        first_visible = max(0, int(scroll_top / self.item_height) - self.buffer_items)
        last_visible = min(
            len(self._items),
            int((scroll_top + canvas_height) / self.item_height) + self.buffer_items
        )
        
        # Remove widgets outside visible range
        for idx in list(self._visible_widgets.keys()):
            if idx < first_visible or idx >= last_visible:
                self._visible_widgets[idx].destroy()
                del self._visible_widgets[idx]
        
        # Create widgets for visible items
        for idx in range(first_visible, last_visible):
            if idx not in self._visible_widgets:
                self._create_item_widget(idx)
    
    def _create_item_widget(self, index: int) -> None:
        """Create widget for item at index"""
        if index >= len(self._items):
            return
        
        item = self._items[index]
        
        # Create frame
        frame = tk.Frame(
            self.container,
            height=self.item_height,
            relief='flat',
            borderwidth=1
        )
        frame.place(
            x=0,
            y=index * self.item_height,
            relwidth=1.0,
            height=self.item_height
        )
        
        # Render content
        self._render_func(frame, item, index)
        
        # Bind selection
        frame.bind('<Button-1>', lambda e, i=index: self._on_item_click(i))
        
        # Highlight if selected
        if index == self._selected_index:
            frame.configure(bg='#3d3d3d')
        
        self._visible_widgets[index] = frame
    
    def _on_item_click(self, index: int) -> None:
        """Handle item click"""
        old_selected = self._selected_index
        self._selected_index = index
        
        # Update highlighting
        if old_selected in self._visible_widgets:
            self._visible_widgets[old_selected].configure(bg='')
        if index in self._visible_widgets:
            self._visible_widgets[index].configure(bg='#3d3d3d')
        
        # Trigger selection event
        self.event_generate('<<ItemSelected>>')
    
    def _on_key_up(self, event) -> None:
        """Handle up arrow key"""
        if self._selected_index is not None and self._selected_index > 0:
            self._on_item_click(self._selected_index - 1)
            self._scroll_to_index(self._selected_index)
    
    def _on_key_down(self, event) -> None:
        """Handle down arrow key"""
        if self._selected_index is not None and self._selected_index < len(self._items) - 1:
            self._on_item_click(self._selected_index + 1)
            self._scroll_to_index(self._selected_index)
    
    def _on_key_enter(self, event) -> None:
        """Handle enter key"""
        if self._selected_index is not None:
            self.event_generate('<<ItemActivated>>')
    
    def _scroll_to_index(self, index: int) -> None:
        """Scroll to make index visible"""
        total_height = len(self._items) * self.item_height
        if total_height == 0:
            return
        
        item_top = index * self.item_height
        fraction = item_top / total_height
        self.canvas.yview_moveto(fraction)
        self._render_visible()
    
    def get_selected_item(self) -> Optional[Dict]:
        """Get currently selected item"""
        if self._selected_index is not None and self._selected_index < len(self._items):
            return self._items[self._selected_index]
        return None
    
    def refresh(self) -> None:
        """Refresh visible items"""
        for widget in self._visible_widgets.values():
            widget.destroy()
        self._visible_widgets.clear()
        self._render_visible()


class LazyLoader:
    """
    Lazy Loading Manager
    
    Loads data on-demand as user scrolls, reducing
    initial load time and memory usage.
    """
    
    def __init__(
        self,
        fetch_func: Callable[[int, int], List[Dict]],
        page_size: int = 50,
        prefetch_pages: int = 2
    ):
        self.fetch_func = fetch_func
        self.page_size = page_size
        self.prefetch_pages = prefetch_pages
        
        self._cache: OrderedDict[int, List[Dict]] = OrderedDict()
        self._max_cached_pages = 10
        self._loading_pages: set = set()
        self._lock = threading.Lock()
        self._total_items: Optional[int] = None
    
    def get_items(self, start: int, count: int) -> List[Dict]:
        """
        Get items for range, loading if necessary
        
        Args:
            start: Starting index
            count: Number of items
        
        Returns:
            List of items
        """
        items = []
        
        # Calculate pages needed
        start_page = start // self.page_size
        end_page = (start + count - 1) // self.page_size
        
        for page in range(start_page, end_page + 1):
            page_items = self._get_page(page)
            
            # Calculate slice within page
            page_start = page * self.page_size
            slice_start = max(0, start - page_start)
            slice_end = min(self.page_size, start + count - page_start)
            
            items.extend(page_items[slice_start:slice_end])
        
        # Prefetch next pages in background
        self._prefetch(end_page + 1)
        
        return items
    
    def _get_page(self, page: int) -> List[Dict]:
        """Get page from cache or fetch"""
        with self._lock:
            if page in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(page)
                return self._cache[page]
        
        # Fetch page
        items = self._fetch_page(page)
        
        with self._lock:
            self._cache[page] = items
            
            # Evict old pages
            while len(self._cache) > self._max_cached_pages:
                self._cache.popitem(last=False)
        
        return items
    
    def _fetch_page(self, page: int) -> List[Dict]:
        """Fetch page from data source"""
        try:
            offset = page * self.page_size
            return self.fetch_func(offset, self.page_size)
        except Exception as e:
            logger.error(f"Error fetching page {page}: {e}")
            return []
    
    def _prefetch(self, start_page: int) -> None:
        """Prefetch pages in background"""
        def fetch_pages():
            for page in range(start_page, start_page + self.prefetch_pages):
                if page not in self._cache and page not in self._loading_pages:
                    with self._lock:
                        self._loading_pages.add(page)
                    
                    try:
                        self._get_page(page)
                    finally:
                        with self._lock:
                            self._loading_pages.discard(page)
        
        thread = threading.Thread(target=fetch_pages, daemon=True)
        thread.start()
    
    def invalidate(self, page: Optional[int] = None) -> None:
        """Invalidate cache"""
        with self._lock:
            if page is not None:
                self._cache.pop(page, None)
            else:
                self._cache.clear()
    
    def set_total_items(self, total: int) -> None:
        """Set total item count"""
        self._total_items = total
    
    @property
    def total_pages(self) -> int:
        """Get total number of pages"""
        if self._total_items is None:
            return 0
        return (self._total_items + self.page_size - 1) // self.page_size


class ProgressiveLoader:
    """
    Progressive Loading
    
    Shows partial results immediately while loading more
    in the background.
    """
    
    def __init__(
        self,
        on_items_loaded: Callable[[List[Dict], bool], None],
        initial_load: int = 20,
        batch_size: int = 50
    ):
        self.on_items_loaded = on_items_loaded
        self.initial_load = initial_load
        self.batch_size = batch_size
        
        self._loading = False
        self._cancel = False
    
    def load(
        self,
        fetch_func: Callable[[int, int], List[Dict]],
        total_items: int
    ) -> None:
        """
        Start progressive loading
        
        Args:
            fetch_func: Function(offset, limit) -> items
            total_items: Total number of items to load
        """
        if self._loading:
            self._cancel = True
            time.sleep(0.1)
        
        self._loading = True
        self._cancel = False
        
        def load_thread():
            try:
                # Load initial batch immediately
                initial = fetch_func(0, self.initial_load)
                if self._cancel:
                    return
                
                self.on_items_loaded(initial, False)
                
                # Load remaining in batches
                offset = self.initial_load
                while offset < total_items and not self._cancel:
                    batch = fetch_func(offset, self.batch_size)
                    if self._cancel:
                        return
                    
                    is_complete = offset + len(batch) >= total_items
                    self.on_items_loaded(batch, is_complete)
                    
                    offset += self.batch_size
                    time.sleep(0.05)  # Small delay to keep UI responsive
            
            finally:
                self._loading = False
        
        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()
    
    def cancel(self) -> None:
        """Cancel loading"""
        self._cancel = True


class DebouncedSearch:
    """
    Debounced Search Input
    
    Delays search execution until user stops typing,
    preventing excessive API calls.
    """
    
    def __init__(
        self,
        search_func: Callable[[str], None],
        delay_ms: int = 300,
        min_chars: int = 2
    ):
        self.search_func = search_func
        self.delay_ms = delay_ms
        self.min_chars = min_chars
        
        self._timer: Optional[threading.Timer] = None
        self._last_query = ""
    
    def on_text_changed(self, query: str) -> None:
        """Handle text change event"""
        # Cancel pending search
        if self._timer is not None:
            self._timer.cancel()
        
        # Don't search if too short
        if len(query) < self.min_chars:
            if self._last_query and len(self._last_query) >= self.min_chars:
                # Clear results
                self.search_func("")
            self._last_query = query
            return
        
        # Schedule search
        self._timer = threading.Timer(
            self.delay_ms / 1000,
            self._execute_search,
            args=[query]
        )
        self._timer.start()
    
    def _execute_search(self, query: str) -> None:
        """Execute the search"""
        self._last_query = query
        try:
            self.search_func(query)
        except Exception as e:
            logger.error(f"Search error: {e}")
    
    def cancel(self) -> None:
        """Cancel pending search"""
        if self._timer is not None:
            self._timer.cancel()


class UIUpdateBatcher:
    """
    UI Update Batcher
    
    Batches multiple UI updates into single redraws
    for better performance.
    """
    
    def __init__(self, root: tk.Tk, batch_interval_ms: int = 16):
        self.root = root
        self.batch_interval_ms = batch_interval_ms
        
        self._pending_updates: List[Callable] = []
        self._scheduled = False
        self._lock = threading.Lock()
    
    def schedule_update(self, update_func: Callable) -> None:
        """Schedule a UI update"""
        with self._lock:
            self._pending_updates.append(update_func)
            
            if not self._scheduled:
                self._scheduled = True
                self.root.after(self.batch_interval_ms, self._process_updates)
    
    def _process_updates(self) -> None:
        """Process all pending updates"""
        with self._lock:
            updates = self._pending_updates.copy()
            self._pending_updates.clear()
            self._scheduled = False
        
        for update in updates:
            try:
                update()
            except Exception as e:
                logger.error(f"UI update error: {e}")


class PerformanceMonitor:
    """
    UI Performance Monitor
    
    Tracks frame rate and identifies performance issues.
    """
    
    def __init__(self, target_fps: int = 60):
        self.target_fps = target_fps
        self.target_frame_time = 1000 / target_fps
        
        self._frame_times: List[float] = []
        self._max_samples = 60
        self._last_frame = time.monotonic()
    
    def frame_start(self) -> None:
        """Mark start of frame"""
        self._last_frame = time.monotonic()
    
    def frame_end(self) -> None:
        """Mark end of frame and record timing"""
        frame_time = (time.monotonic() - self._last_frame) * 1000
        
        self._frame_times.append(frame_time)
        if len(self._frame_times) > self._max_samples:
            self._frame_times.pop(0)
        
        if frame_time > self.target_frame_time * 2:
            logger.warning(f"Slow frame: {frame_time:.1f}ms")
    
    @property
    def fps(self) -> float:
        """Get current FPS"""
        if not self._frame_times:
            return 0
        avg_frame_time = sum(self._frame_times) / len(self._frame_times)
        return 1000 / avg_frame_time if avg_frame_time > 0 else 0
    
    @property
    def stats(self) -> Dict[str, float]:
        """Get performance statistics"""
        if not self._frame_times:
            return {'fps': 0, 'avg_ms': 0, 'max_ms': 0}
        
        return {
            'fps': self.fps,
            'avg_ms': sum(self._frame_times) / len(self._frame_times),
            'max_ms': max(self._frame_times),
            'min_ms': min(self._frame_times)
        }


# Utility functions

def run_in_background(func: Callable[..., T]) -> Callable[..., None]:
    """
    Decorator to run function in background thread
    
    Usage:
        @run_in_background
        def heavy_operation():
            # This runs in background
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> None:
        thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        thread.start()
    return wrapper


def run_on_ui_thread(root: tk.Tk):
    """
    Decorator to ensure function runs on UI thread
    
    Usage:
        @run_on_ui_thread(root)
        def update_label(text):
            label.config(text=text)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., None]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> None:
            root.after(0, lambda: func(*args, **kwargs))
        return wrapper
    return decorator
