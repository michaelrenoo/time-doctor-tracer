"""
Export panel for Trace Data Viewer application.
This module provides the ExportPanel class, which contains controls for exporting data
and images from the application.
"""

import tkinter as tk
from tkinter import ttk

class ExportPanel:
    def __init__(self, parent, main_window):
        """
        Initialize the export panel.
        
        Args:
            parent: Parent widget
            main_window (MainWindow): Reference to main window
        """
        self.main_window = main_window
        
        # Create export panel
        self.frame = ttk.Frame(parent)
        
        ttk.Button(self.frame, text="Export Statistics CSV", 
                  command=self.main_window.export_statistics).pack(padx=10, pady=10)
        
        ttk.Button(self.frame, text="Export Plot Image", 
                  command=self.main_window.export_image).pack(padx=10, pady=10)
        
        ttk.Button(self.frame, text="Export Marker Data", 
                  command=self.main_window.export_marker_data).pack(padx=10, pady=10)