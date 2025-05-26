#!/usr/bin/env python3
"""
Trace Data Viewer for FreeRTOS, based on TimeDoctor - Main entry point
"""

import argparse
import os
import sys
import platform

# Configure matplotlib backend before importing any matplotlib modules
# This helps prevent the autorelease pool corruption on macOS
import matplotlib
if platform.system() == 'Darwin':  # macOS
    matplotlib.use('TkAgg')  # Force TkAgg backend which is more stable on macOS

import tkinter as tk
from trace_data_viewer.ui.main_window import MainWindow
from trace_data_viewer.data_manager import DataManager

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Trace Data Viewer for FreeRTOS Trace Hook Macros Data, based on TimeDoctor')
    parser.add_argument('logfile', type=str, help='Path to log file', nargs='?')
    parser.add_argument('--filter', type=str, help='Filter by task IDs (comma-separated)')
    args = parser.parse_args()
    
    # Initialize data manager
    data_manager = DataManager()
    
    # Create and run UI
    root = tk.Tk()
    app = MainWindow(root, data_manager)
    
    # Load log file if provided
    if args.logfile and os.path.exists(args.logfile):
        app.load_log_file(args.logfile, task_filter=args.filter)
    
    root.mainloop()

if __name__ == "__main__":
    main()