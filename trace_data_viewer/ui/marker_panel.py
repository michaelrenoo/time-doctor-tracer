"""
Marker panel for Trace Data Viewer application.
This module provides the MarkerPanel class, which contains controls for setting and managing markers
on the task timeline.
It allows users to set two markers, clear them, and zoom the view to the markers.
"""

import tkinter as tk
from tkinter import ttk

class MarkerPanel:
    def __init__(self, parent, main_window):
        """
        Initialize the marker panel.
        
        Args:
            parent: Parent widget
            main_window (MainWindow): Reference to main window
        """
        self.main_window = main_window
        
        # Create marker control frame
        self.frame = ttk.LabelFrame(parent, text="Marker Controls")
        
        # Marker buttons
        ttk.Button(self.frame, text="Set Marker 1", 
                   command=self.main_window.set_marker1).grid(row=0, column=0, padx=5, pady=5)
        
        ttk.Button(self.frame, text="Set Marker 2", 
                   command=self.main_window.set_marker2).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(self.frame, text="Clear Markers", 
                   command=self.main_window.clear_markers).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Button(self.frame, text="Zoom to Markers", 
                   command=self.main_window.zoom_to_markers).grid(row=0, column=3, padx=5, pady=5)