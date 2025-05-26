"""
Filter panel for Trace Data Viewer application.
This module provides the FilterPanel class, which contains controls for filtering tasks
and updating the task display based on user input.
"""

import tkinter as tk
from tkinter import ttk

class FilterPanel:
    def __init__(self, parent, main_window):
        """
        Initialize the filter panel.
        
        Args:
            parent: Parent widget
            main_window (MainWindow): Reference to main window
        """
        self.main_window = main_window
        
        # Create filter frame
        self.frame = ttk.LabelFrame(parent, text="Task Filter")
        
        # Filter controls
        ttk.Button(self.frame, text="Show All", 
                   command=self.main_window.show_all_tasks).grid(row=0, column=0, padx=5, pady=5)
        
        ttk.Button(self.frame, text="Hide All", 
                   command=self.main_window.hide_all_tasks).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(self.frame, text="Apply Filter", 
                   command=self.main_window.apply_task_filter).grid(row=0, column=2, padx=5, pady=5)