"""
Visualization utilities for Trace Data Viewer.
This module provides the PlotManager class, which handles the plotting of task timelines
and markers on a matplotlib Axes object.
"""

import matplotlib.pyplot as plt
import numpy as np

class PlotManager:
    def __init__(self, ax, data_manager):
        """
        Initialize the plot manager.
        
        Args:
            ax (matplotlib.axes.Axes): The matplotlib axes for plotting
            data_manager (DataManager): The data manager instance
        """
        self.ax = ax
        self.data_manager = data_manager
        self.task_colors = {
            "defaultTask": "tab:red",  # Red
            "myTaskA": "tab:blue",     # Blue
            "myTaskB": "tab:green",    # Green
            "myTaskC": "tab:olive",    # Yellow
            "IDLE": "tab:purple",      # Purple
            "Tmr Svc": "tab:orange"    # Orange
        }
        self.marker_lines = []
    
    def update_plot(self, visible_tasks, time_filter=None):
        """
        Update the plot with current data and settings.
        
        Args:
            visible_tasks (list): List of task names to display
            time_filter (tuple, optional): Start and end time for filtering
        """
        self.ax.clear()
        
        if self.data_manager.df is None or self.data_manager.df.empty:
            return
        
        # Apply time filter if provided
        if time_filter and time_filter[0] is not None and time_filter[1] is not None:
            plot_df = self.data_manager.filter_by_time(time_filter[0], time_filter[1])
        else:
            plot_df = self.data_manager.df
        
        for i, task in enumerate(visible_tasks):
            task_df = plot_df[plot_df["Task Name"] == task]
            color = self.task_colors.get(task, f"C{i % 10}")
            
            for _, row in task_df.iterrows():
                duration = row["End (ms)"] - row["Start (ms)"]
                self.ax.barh(row["Task Name"], duration, left=row["Start (ms)"], color=color)
        
        # Draw markers
        if self.data_manager.marker1_pos is not None:
            line1 = self.ax.axvline(self.data_manager.marker1_pos, color='magenta', linestyle='-', linewidth=2)
            self.ax.text(self.data_manager.marker1_pos, len(visible_tasks) + 0.5, 
                    f'M1: {self.data_manager.marker1_pos:.3f} ms', 
                    color='magenta', verticalalignment='bottom')
        
        if self.data_manager.marker2_pos is not None:
            line2 = self.ax.axvline(self.data_manager.marker2_pos, color='yellow', linestyle='-', linewidth=2)
            self.ax.text(self.data_manager.marker2_pos, len(visible_tasks) + 0.5, 
                    f'M2: {self.data_manager.marker2_pos:.3f} ms', 
                    color='red', verticalalignment='bottom')
        
        # Add shaded region ONLY if both markers are set
        if self.data_manager.marker1_pos is not None and self.data_manager.marker2_pos is not None:
            x0, x1 = sorted([self.data_manager.marker1_pos, self.data_manager.marker2_pos])
            self.ax.axvspan(x0, x1, alpha=0.2, color='purple')
        
        self.ax.set_xlabel("Time (ms)")
        self.ax.set_ylabel("Tasks")
        self.ax.set_title("Task Timeline")
        
        if len(visible_tasks) > 0:
            if time_filter and time_filter[0] is not None and time_filter[1] is not None:
                min_time = time_filter[0]
                max_time = time_filter[1]
            else:
                min_time = plot_df["Start (ms)"].min() if not plot_df.empty else 0
                max_time = plot_df["End (ms)"].max() if not plot_df.empty else 1000
                
            # Add some padding to the x-axis limits for better visualization
            padding = (max_time - min_time) * 0.05
            self.ax.set_xlim(min_time - padding, max_time + padding)
        
        return {
            'min_time': min_time if 'min_time' in locals() else 0,
            'max_time': max_time if 'max_time' in locals() else 1000
        }
    
    def get_marker_info_text(self):
        """
        Generate text information about markers.
        
        Returns:
            str: Formatted text with marker information
        """
        info_text = ""
        
        if self.data_manager.marker1_pos is not None:
            info_text += f"Marker 1: {self.data_manager.marker1_pos:.3f} ms\n"
        
        if self.data_manager.marker2_pos is not None:
            info_text += f"Marker 2: {self.data_manager.marker2_pos:.3f} ms\n"
        
        if self.data_manager.marker1_pos is not None and self.data_manager.marker2_pos is not None:
            x0, x1 = sorted([self.data_manager.marker1_pos, self.data_manager.marker2_pos])
            time_diff = x1 - x0
            info_text += f"\nTime Difference: {time_diff:.3f} ms\n\n"
            
            # Get tasks active in the marker range
            task_data = self.data_manager.get_tasks_in_range(x0, x1)
            
            if task_data:
                info_text += "Tasks active between markers:\n"
                
                for task_name, data in task_data.items():
                    info_text += f"- {task_name}: {data['total_active_time']:.3f} ms ({data['percentage']:.1f}%)\n"
                
                # Calculate total CPU utilization, based on active tasks in the range
                total_active_time = sum(data['total_active_time'] for data in task_data.values())
                utilization = (total_active_time / time_diff) * 100
                info_text += f"\nTotal CPU utilization: {utilization:.1f}%\n"
        
        if not info_text:
            info_text = "No markers set. Click on the graph to set markers."
        
        return info_text