"""
Main window implementation for Trace Data Viewer for FreeRTOS, based on TimeDoctor.
This class provides the main application window, including data visualization, filtering,
searching, and exporting functionalities.
"""

import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from trace_data_viewer.visualization import PlotManager
from trace_data_viewer.ui.marker_panel import MarkerPanel
from trace_data_viewer.ui.filter_panel import FilterPanel
from trace_data_viewer.ui.statistics_panel import StatisticsPanel
from trace_data_viewer.ui.search_panel import SearchPanel
from trace_data_viewer.ui.export_panel import ExportPanel

class MainWindow:
    def __init__(self, root, data_manager):
        """
        Initialize the main window.
        
        Args:
            root (tk.Tk): The root Tkinter window
            data_manager (DataManager): The data manager instance
        """
        self.root = root
        self.data_manager = data_manager
        self.root.title("Trace Data Viewer for FreeRTOS, based on TimeDoctor")
        self.root.geometry("1280x800")
        
        # State variables
        self.active_marker = 0  # 1 for marker1, 2 for marker2
        self.time_filter_active = False
        self.time_filter_start = None
        self.time_filter_end = None
        self.task_vars = {}  # For task filtering checkboxes
        
        # Set up the UI components
        self.setup_ui()
        
        # Create the menu
        self.create_menu()
    
    def setup_ui(self):
        """Set up the user interface."""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=3)  # Main frame
        self.root.rowconfigure(1, weight=0)  # Status bar
        
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=3)  # Plot area
        main_frame.rowconfigure(1, weight=0)  # Toolbar
        main_frame.rowconfigure(2, weight=0)  # Control panel
        main_frame.rowconfigure(3, weight=1)  # Notebook area
        
        self.fig, self.ax = plt.subplots(figsize=(10, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=main_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        
        # Fixed minimum height for canvas
        self.canvas_widget.config(height=300)
        
        # Initialize plot manager
        self.plot_manager = PlotManager(self.ax, self.data_manager)
        
        # Initialize the navigation toolbar
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.grid(row=1, column=0, sticky="ew")
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()
        
        # Create control panel paned window
        control_pane = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        control_pane.grid(row=2, column=0, sticky="ew", pady=5)
        
        # Create marker control panel
        self.marker_panel = MarkerPanel(control_pane, self)
        control_pane.add(self.marker_panel.frame, weight=1)
        
        # Create filter panel
        self.filter_panel = FilterPanel(control_pane, self)
        control_pane.add(self.filter_panel.frame, weight=1)
        
        # Time filter frame
        time_filter_frame = ttk.LabelFrame(control_pane, text="Time Filter")
        control_pane.add(time_filter_frame, weight=1)
        
        # Time filter controls
        ttk.Label(time_filter_frame, text="Start:").grid(row=0, column=0, padx=2, pady=2)
        self.time_start_var = tk.StringVar()
        ttk.Entry(time_filter_frame, width=10, textvariable=self.time_start_var).grid(row=0, column=1, padx=2, pady=2)
        
        ttk.Label(time_filter_frame, text="End:").grid(row=0, column=2, padx=2, pady=2)
        self.time_end_var = tk.StringVar()
        ttk.Entry(time_filter_frame, width=10, textvariable=self.time_end_var).grid(row=0, column=3, padx=2, pady=2)
        
        ttk.Button(time_filter_frame, text="Apply", command=self.apply_time_filter).grid(row=0, column=4, padx=2, pady=2)
        ttk.Button(time_filter_frame, text="Reset", command=self.reset_time_filter).grid(row=0, column=5, padx=2, pady=2)
        
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=3, column=0, sticky="nsew", pady=5)
        
        self.marker_info_frame = ttk.Frame(notebook)
        notebook.add(self.marker_info_frame, text="Marker Info")
        
        self.marker_info_text = tk.Text(self.marker_info_frame, height=5, wrap=tk.WORD)
        self.marker_info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        # Create statistics panel
        self.stats_panel = StatisticsPanel(notebook)
        notebook.add(self.stats_panel.frame, text="Statistics")
        
        # Create task filter panel
        self.filter_tab = ttk.Frame(notebook)
        notebook.add(self.filter_tab, text="Task Visibility")
        
        # Create search panel
        self.search_panel = SearchPanel(notebook, self)
        notebook.add(self.search_panel.frame, text="Search")
        
        # Create export panel
        self.export_panel = ExportPanel(notebook, self)
        notebook.add(self.export_panel.frame, text="Export")
        
        # Create status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=1, column=0, sticky="ew")
        
        # Connect event handlers
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        
        self.root.bind("<Configure>", self.on_window_resize)
    
    def create_menu(self):
        """Create the application menu."""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Log File...", command=self.open_log_file)
        file_menu.add_separator()
        file_menu.add_command(label="Export Statistics...", command=self.export_statistics)
        file_menu.add_command(label="Export Plot Image...", command=self.export_image)
        file_menu.add_command(label="Export Marker Data...", command=self.export_marker_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Set Marker 1", command=self.set_marker1)
        edit_menu.add_command(label="Set Marker 2", command=self.set_marker2)
        edit_menu.add_command(label="Clear Markers", command=self.clear_markers)
        edit_menu.add_separator()
        edit_menu.add_command(label="Reset View", command=self.reset_view)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Show All Tasks", command=self.show_all_tasks)
        view_menu.add_command(label="Hide All Tasks", command=self.hide_all_tasks)
        view_menu.add_separator()
        view_menu.add_command(label="Zoom to Markers", command=self.zoom_to_markers)
        view_menu.add_command(label="Reset Time Filter", command=self.reset_time_filter)
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def open_log_file(self):
        """Open a log file through a file dialog."""
        filename = filedialog.askopenfilename(
            title="Select Log File",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.load_log_file(filename)
    
    def load_log_file(self, filename, task_filter=None):
        """
        Load and parse a log file.
        
        Args:
            filename (str): Path to the log file
            task_filter (str, optional): Task filter specification
        """
        try:
            self.status_var.set(f"Loading {filename}...")
            self.root.update()
            
            # Load data through the data manager
            self.data_manager.parse_log_file(filename, task_filter)
            
            # Create task filter checkboxes
            self.create_task_filters()
            
            # Update UI
            self.root.title(f"Trace Data Viewer - {os.path.basename(filename)}")
            self.update_plot()
            self.update_statistics()
            self.status_var.set(f"Loaded {len(self.data_manager.events)} events from {os.path.basename(filename)}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load log file: {str(e)}")
            self.status_var.set("Error loading file")
    
    def create_task_filters(self):
        """Create task filter checkboxes."""
        # Clear existing checkboxes
        for widget in self.filter_tab.winfo_children():
            widget.destroy()
        
        # Create frame for filter controls
        controls_frame = ttk.Frame(self.filter_tab)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(controls_frame, text="Select All", command=self.show_all_tasks).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Select None", command=self.hide_all_tasks).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Apply", command=self.apply_task_filter).pack(side=tk.LEFT, padx=5)
        
        checkbox_container = ttk.Frame(self.filter_tab)
        checkbox_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        checkbox_container.columnconfigure(0, weight=1)
        checkbox_container.rowconfigure(0, weight=1)
        
        canvas = tk.Canvas(checkbox_container, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(checkbox_container, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW, width=canvas.winfo_width())
        
        # Create checkboxes for each task
        self.task_vars = {}
        unique_tasks = self.data_manager.get_unique_tasks()
        
        for i, task in enumerate(unique_tasks):
            var = tk.BooleanVar(value=True)
            self.task_vars[task] = var
            
            cb = ttk.Checkbutton(scrollable_frame, text=task, variable=var, width=25)
            cb.grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            
            # Add a color indicator
            color_frame = ttk.Frame(scrollable_frame, width=20, height=20)
            color_frame.grid(row=i, column=1, padx=5, pady=2)
            color = self.plot_manager.task_colors.get(task, f"C{i % 10}")
            try:
                color_frame.configure(style=f"{color}.TFrame")
            except:
                # For simplicity, we'll just ignore style errors here
                pass
        
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas.find_all()[0], width=e.width-4) if canvas.find_all() else None)
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        scrollable_frame.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        
    def show_all_tasks(self):
        """Select all tasks in the filter."""
        for var in self.task_vars.values():
            var.set(True)
    
    def hide_all_tasks(self):
        """Deselect all tasks in the filter."""
        for var in self.task_vars.values():
            var.set(False)
    
    def apply_task_filter(self):
        """Apply task visibility filter."""
        if self.data_manager.df is None or self.data_manager.df.empty:
            return
            
        # Store current view and marker positions
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        marker1_pos = self.data_manager.marker1_pos
        marker2_pos = self.data_manager.marker2_pos
        
        # Clear current figure to prevent overlapping plots
        self.fig.clear()
        self.ax = self.fig.add_subplot(111)
        
        self.plot_manager.ax = self.ax
        
        visible_tasks = [task for task, var in self.task_vars.items() if var.get()]
        
        # Get time filter if active
        time_filter = None
        if self.time_filter_active and self.time_filter_start is not None and self.time_filter_end is not None:
            time_filter = (self.time_filter_start, self.time_filter_end)
        
        self.plot_manager.update_plot(visible_tasks, time_filter)
        
        # Restore view limits
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        
        # Restore markers if they existed
        self.data_manager.marker1_pos = marker1_pos
        self.data_manager.marker2_pos = marker2_pos
        
        # If markers exist, update them
        if marker1_pos is not None or marker2_pos is not None:
            self.update_markers(xlim, ylim)
        
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        
        self.canvas.draw()
        
        self.status_var.set("Task filter applied")
    
    def update_plot(self, preserve_view=False, xlim=None, ylim=None):
        """Update the plot with current data and settings."""
        if self.data_manager.df is None or self.data_manager.df.empty:
            return
        
        if preserve_view and xlim is None and ylim is None:
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
        
        # Get visible tasks based on checkboxes
        visible_tasks = [task for task, var in self.task_vars.items() if var.get()]
        
        # Get time filter if active
        time_filter = None
        if self.time_filter_active and self.time_filter_start is not None and self.time_filter_end is not None:
            time_filter = (self.time_filter_start, self.time_filter_end)
        
        # Clear the figure completely before rerender to prevent overlapping plots
        self.fig.clear()
        self.ax = self.fig.add_subplot(111)
        
        self.plot_manager.ax = self.ax
        
        # Update the plot
        self.plot_manager.update_plot(visible_tasks, time_filter)
        
        if preserve_view and xlim is not None and ylim is not None:
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)
        
        # Update the canvas
        self.fig.set_size_inches(10, 5, forward=True)
        self.canvas.draw()
        
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        
        self.update_marker_info()
    
    def update_markers(self, xlim, ylim):
        """
        Update only the markers without redrawing the entire plot.
        
        Args:
            xlim (tuple): The x-axis limits to preserve
            ylim (tuple): The y-axis limits to preserve
        """
        for line in self.ax.lines[:]:
            if getattr(line, 'is_marker', False):
                line.remove()
        
        for patch in self.ax.patches[:]:
            if getattr(patch, 'is_marker_shading', False):
                patch.remove()
                
        for text in self.ax.texts[:]:
            if getattr(text, 'is_marker_label', False):
                text.remove()
        
        # Draw markers
        visible_tasks = [task for task, var in self.task_vars.items() if var.get()]
        
        if self.data_manager.marker1_pos is not None:
            # Add marker 1 line and label
            line1 = self.ax.axvline(self.data_manager.marker1_pos, color='magenta', 
                                   linestyle='-', linewidth=2)
            line1.is_marker = True
            
            text1 = self.ax.text(self.data_manager.marker1_pos, len(visible_tasks) - 0.5, 
                        f'M1: {self.data_manager.marker1_pos:.3f} ms', 
                        color='magenta', verticalalignment='bottom')
            text1.is_marker_label = True
        
        if self.data_manager.marker2_pos is not None:
            # Add marker 2 line and label
            line2 = self.ax.axvline(self.data_manager.marker2_pos, color='yellow', 
                                   linestyle='-', linewidth=2)
            line2.is_marker = True
            
            text2 = self.ax.text(self.data_manager.marker2_pos, len(visible_tasks) - 0.5, 
                        f'M2: {self.data_manager.marker2_pos:.3f} ms', 
                        color='red', verticalalignment='bottom')
            text2.is_marker_label = True
        
        # Add shaded region ONLY if both markers are set
        if self.data_manager.marker1_pos is not None and self.data_manager.marker2_pos is not None:
            x0, x1 = sorted([self.data_manager.marker1_pos, self.data_manager.marker2_pos])
            patch = self.ax.axvspan(x0, x1, alpha=0.2, color='purple')
            patch.is_marker_shading = True
        
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        
        self.canvas.draw_idle()
        
        self.update_marker_info()
    
    def update_marker_info(self):
        """Update the marker information panel."""
        self.marker_info_text.delete(1.0, tk.END)
        info_text = self.plot_manager.get_marker_info_text()
        self.marker_info_text.insert(tk.END, info_text)
    
    def update_statistics(self):
        """Update the statistics panel."""
        stats_data = self.data_manager.get_task_statistics()
        self.stats_panel.update_statistics(stats_data)
    
    def on_click(self, event):
        """
        Handle mouse click events on the plot.
        
        Args:
            event (matplotlib.backend_bases.MouseEvent): The mouse event
        """
        if event.xdata is not None and event.inaxes == self.ax:
            if self.active_marker == 0:
                return  # No active marker
            elif self.active_marker == 1:
                # Store current view limits
                xlim = self.ax.get_xlim()
                ylim = self.ax.get_ylim()
                
                self.data_manager.set_marker(1, event.xdata)
                self.status_var.set(f"Marker 1 set at {event.xdata:.3f} ms")
                self.active_marker = 0  # Reset active marker after setting
                
                self.update_markers(xlim, ylim)
            else:
                xlim = self.ax.get_xlim()
                ylim = self.ax.get_ylim()
                
                self.data_manager.set_marker(2, event.xdata)
                self.status_var.set(f"Marker 2 set at {event.xdata:.3f} ms")
                self.active_marker = 0  # Reset active marker after setting
                
                self.update_markers(xlim, ylim)
    
    def on_mouse_move(self, event):
        """
        Handle mouse movement events on the plot.
        
        Args:
            event (matplotlib.backend_bases.MouseEvent): The mouse event
        """
        if event.xdata is not None and event.inaxes == self.ax:
            # Update status bar with current position
            self.status_var.set(f"Time: {event.xdata:.3f} ms")
    
    def set_marker1(self):
        """Activate marker 1 for placement."""
        self.active_marker = 1
        self.status_var.set("Click on plot to set Marker 1")
    
    def set_marker2(self):
        """Activate marker 2 for placement."""
        self.active_marker = 2
        self.status_var.set("Click on plot to set Marker 2")
    
    def clear_markers(self):
        """Clear all markers."""
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        self.data_manager.marker1_pos = None
        self.data_manager.marker2_pos = None
        self.active_marker = 0
        
        for line in self.ax.lines[:]:
            if getattr(line, 'is_marker', False):
                line.remove()
        
        for patch in self.ax.patches[:]:
            if getattr(patch, 'is_marker_shading', False):
                patch.remove()
        
        for text in self.ax.texts[:]:
            if getattr(text, 'is_marker_label', False):
                text.remove()
        
        self.canvas.draw_idle()
        
        self.update_marker_info()
        
        self.status_var.set("Markers cleared")
    
    def zoom_to_markers(self):
        """Zoom the plot view to the region between markers."""
        if self.data_manager.marker1_pos is not None and self.data_manager.marker2_pos is not None:
            x0, x1 = sorted([self.data_manager.marker1_pos, self.data_manager.marker2_pos])
            padding = (x1 - x0) * 0.1  # Add 10% padding
            
            # Set the x-axis limits directly to zoom to the markers
            self.ax.set_xlim(x0 - padding, x1 + padding)
            
            self.canvas.draw_idle()
            self.status_var.set(f"Zoomed to markers: {x0:.3f} - {x1:.3f} ms")
        else:
            messagebox.showinfo("Info", "Please set both markers first")
    
    def reset_view(self):
        """Reset the plot view to show all data."""
        if self.data_manager.df is not None and not self.data_manager.df.empty:
            marker1_pos = self.data_manager.marker1_pos
            marker2_pos = self.data_manager.marker2_pos

            self.update_plot()
            
            self.data_manager.marker1_pos = marker1_pos
            self.data_manager.marker2_pos = marker2_pos
            
            if marker1_pos is not None or marker2_pos is not None:
                xlim = self.ax.get_xlim()
                ylim = self.ax.get_ylim()
                self.update_markers(xlim, ylim)
            
            self.status_var.set("View reset")
    
    def apply_time_filter(self):
        """Apply time filter based on user input."""
        try:
            start_time = float(self.time_start_var.get()) if self.time_start_var.get() else None
            end_time = float(self.time_end_var.get()) if self.time_end_var.get() else None
            
            if start_time is not None and end_time is not None:
                if start_time >= end_time:
                    messagebox.showerror("Error", "Start time must be less than end time")
                    return
                
                marker1_pos = self.data_manager.marker1_pos
                marker2_pos = self.data_manager.marker2_pos
                
                self.time_filter_active = True
                self.time_filter_start = start_time
                self.time_filter_end = end_time

                self.fig.clear()
                self.ax = self.fig.add_subplot(111)  # Recreate the axes
                
                self.plot_manager.ax = self.ax
                
                visible_tasks = [task for task, var in self.task_vars.items() if var.get()]
                
                time_filter = (self.time_filter_start, self.time_filter_end)
                
                self.plot_manager.update_plot(visible_tasks, time_filter)
                
                padding = (end_time - start_time) * 0.05
                self.ax.set_xlim(start_time - padding, end_time + padding)
                
                self.data_manager.marker1_pos = marker1_pos
                self.data_manager.marker2_pos = marker2_pos
                
                if marker1_pos is not None or marker2_pos is not None:
                    self.update_markers(self.ax.get_xlim(), self.ax.get_ylim())
                
                self.fig.canvas.mpl_connect('button_press_event', self.on_click)
                self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
                
                self.canvas.draw()
                
                self.status_var.set(f"Time filter applied: {start_time:.3f} - {end_time:.3f} ms")
            else:
                messagebox.showerror("Error", "Please enter both start and end times")
        except ValueError:
            messagebox.showerror("Error", "Invalid time values")
    
    def reset_time_filter(self):
        """Reset the time filter."""
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        marker1_pos = self.data_manager.marker1_pos
        marker2_pos = self.data_manager.marker2_pos
        
        self.time_filter_active = False
        self.time_filter_start = None
        self.time_filter_end = None
        self.time_start_var.set("")
        self.time_end_var.set("")
        
        self.fig.clear()
        self.ax = self.fig.add_subplot(111)
        
        self.plot_manager.ax = self.ax
        
        visible_tasks = [task for task, var in self.task_vars.items() if var.get()]
        
        self.plot_manager.update_plot(visible_tasks, None)
        
        self.data_manager.marker1_pos = marker1_pos
        self.data_manager.marker2_pos = marker2_pos
        
        if marker1_pos is not None or marker2_pos is not None:
            self.update_markers(self.ax.get_xlim(), self.ax.get_ylim())
        
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        
        self.canvas.draw()
        
        self.status_var.set("Time filter reset")
    
    def export_statistics(self):
        """Export statistics to a CSV file."""
        if self.data_manager.df is None or self.data_manager.df.empty:
            messagebox.showinfo("Info", "No data to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Export Statistics"
        )
        
        if filename:
            try:
                # Get statistics data
                stats_data = self.data_manager.get_task_statistics()
                
                # Create DataFrame and export
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_csv(filename, index=False)
                self.status_var.set(f"Statistics exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export statistics: {str(e)}")
    
    def export_image(self):
        """Export the plot as an image file."""
        if self.data_manager.df is None or self.data_manager.df.empty:
            messagebox.showinfo("Info", "No data to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG Files", "*.png"), 
                ("JPEG Files", "*.jpg"), 
                ("PDF Files", "*.pdf"),
                ("SVG Files", "*.svg"),
                ("All Files", "*.*")
            ],
            title="Export Plot Image"
        )
        
        if filename:
            try:
                # Make a high-resolution copy of the current figure
                self.fig.savefig(filename, dpi=300, bbox_inches='tight')
                self.status_var.set(f"Plot exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export image: {str(e)}")
    
    def export_marker_data(self):
        """Export data between markers to a JSON file."""
        if self.data_manager.marker1_pos is None or self.data_manager.marker2_pos is None:
            messagebox.showinfo("Info", "Please set both markers first")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Export Marker Data"
        )
        
        if filename:
            try:
                x0, x1 = sorted([self.data_manager.marker1_pos, self.data_manager.marker2_pos])
                time_diff = x1 - x0
                
                # Get tasks active in the marker range
                task_data = self.data_manager.get_tasks_in_range(x0, x1)
                
                # Create export data structure
                export_data = {
                    "marker1": float(self.data_manager.marker1_pos),
                    "marker2": float(self.data_manager.marker2_pos),
                    "time_difference": float(time_diff),
                    "tasks": task_data,
                    "export_time": datetime.now().isoformat()
                }
                
                # Export to JSON
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
                self.status_var.set(f"Marker data exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export marker data: {str(e)}")
    
    def show_about(self):
        """Show the about dialog."""
        messagebox.showinfo(
            "About TimeDoctor Viewer",
            "TimeDoctor Time Viewer for FreeRTOS\n\n"
            "A visualization tool for analyzing FreeRTOS task execution timings.\n\n"
            "Features:\n"
            "- Task timeline visualization\n"
            "- Time measurement with markers\n"
            "- Task filtering and searching\n"
            "- Statistics and data export"
        )
    
    def on_window_resize(self, event):
        """Handle window resize events to maintain layout proportions."""
        # Only process if this is the root window being resized
        if event.widget == self.root:
            width = event.width
            height = event.height
            
            plot_height = int(height * 0.6)
            
            # Set minimum heights
            self.canvas_widget.config(height=plot_height)
            
            # Also adjust the figure size for matplotlib
            self.fig.set_size_inches(width/100, plot_height/100, forward=True)
            
            self.canvas.draw()