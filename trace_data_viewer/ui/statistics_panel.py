"""
Statistics panel for Trace Data Viewer application.
This module provides the StatisticsPanel class, which displays task statistics
and allows users to view task counts, average durations, and other metrics.
"""

import tkinter as tk
from tkinter import ttk

class StatisticsPanel:
    def __init__(self, parent):
        """
        Initialize the statistics panel.
        
        Args:
            parent: Parent widget
        """
        # Create statistics panel
        self.frame = ttk.Frame(parent)
        
        # Create task statistics table
        columns = ("Task", "Count", "Avg Duration", "Min Duration", "Max Duration", "Total Duration")
        self.stats_tree = ttk.Treeview(self.frame, columns=columns, show="headings", height=6)
        
        # Configure columns
        for col in columns:
            self.stats_tree.heading(col, text=col)
            self.stats_tree.column(col, anchor=tk.CENTER, width=100)
        self.stats_tree.column("Task", anchor=tk.W, width=150)
        
        # Add scrollbar
        stats_scroll = ttk.Scrollbar(self.frame, orient="vertical", command=self.stats_tree.yview)
        self.stats_tree.configure(yscrollcommand=stats_scroll.set)
        
        self.stats_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        stats_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def update_statistics(self, stats_data):
        """
        Update the statistics display with new data.
        
        Args:
            stats_data (list): List of dictionaries with statistics data
        """
        # Clear existing data
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)
        
        # Add new data
        for stat in stats_data:
            self.stats_tree.insert("", "end", values=(
                stat["Task"], 
                stat["Count"], 
                f"{stat['Avg Duration (ms)']:.3f} ms", 
                f"{stat['Min Duration (ms)']:.3f} ms", 
                f"{stat['Max Duration (ms)']:.3f} ms", 
                f"{stat['Total Duration (ms)']:.3f} ms"
            ))