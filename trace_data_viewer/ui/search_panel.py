"""
Search panel for Trace Data Viewer application.
This module provides the SearchPanel class, which allows users to search for tasks
and view their statistics, including counts, average durations, and longest durations.
"""

import tkinter as tk
from tkinter import ttk

class SearchPanel:
    def __init__(self, parent, main_window):
        """
        Initialize the search panel.
        
        Args:
            parent: Parent widget
            main_window (MainWindow): Reference to main window
        """
        self.main_window = main_window
        
        # Create search panel
        self.frame = ttk.Frame(parent)
        
        search_control_frame = ttk.Frame(self.frame)
        search_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_control_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        ttk.Entry(search_control_frame, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_control_frame, text="Search", command=self.search_tasks).pack(side=tk.LEFT, padx=5)
        
        self.search_result = tk.Text(self.frame, height=6, wrap=tk.WORD)
        self.search_result.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def search_tasks(self):
        """Search for tasks matching the search term."""
        search_term = self.search_var.get()
        if not search_term:
            self.search_result.delete(1.0, tk.END)
            self.search_result.insert(tk.END, "Enter a search term")
            return
        
        # Get search results from data manager
        results = self.main_window.data_manager.search_tasks(search_term)
        
        # Display results
        self.search_result.delete(1.0, tk.END)
        
        if results:
            result_text = "Matching tasks:\n\n"
            
            for task, data in results.items():
                result_text += f"{task} ({data['count']} occurrences, avg: {data['avg_duration']:.3f} ms)\n"
                
                # Show longest durations
                if data['longest_durations']:
                    result_text += "Longest durations:\n"
                    for duration in data['longest_durations']:
                        result_text += f"  {duration['duration']:.3f} ms at {duration['start_time']:.3f} ms\n"
                
                result_text += "\n"
        else:
            result_text = f"No tasks found matching '{search_term}'"
        
        self.search_result.insert(tk.END, result_text)