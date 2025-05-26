"""
Visualization utilities for Trace Data Viewer.
This module provides the PlotManager class, which handles the plotting of task timelines
and markers on a matplotlib Axes object.
"""

import matplotlib.pyplot as plt
import numpy as np
import platform

# Additional settings for macOS to prevent memory issues
if platform.system() == 'Darwin':
    plt.rcParams['figure.dpi'] = 100
    plt.rcParams['figure.max_open_warning'] = 50

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
        
        self.color_palette = [
            "tab:blue",      # Blue
            "tab:orange",    # Orange
            "tab:green",     # Green
            "tab:red",       # Red
            "tab:purple",    # Purple
            "tab:brown",     # Brown
            "tab:pink",      # Pink
            "tab:olive",     # Olive
            "tab:cyan",      # Cyan
            "gold",          # Gold
            "limegreen",     # Lime
            "darkviolet",    # Violet
            "crimson",       # Crimson
            "teal",          # Teal
            "magenta",       # Magenta
            "navy"           # Navy
        ]
        
        # Distinct colors for system tasks
        self.system_task_colors = {
            "IDLE": "lightgray",
            "Tmr Svc": "darkgray"
        }

        self.task_colors = {}
        
        self.marker_lines = []
    
    def update_plot(self, visible_tasks, time_filter=None):
        """
        Update the plot with current data and settings.
        
        Args:
            visible_tasks (list): List of task names to display
            time_filter (tuple, optional): Start and end time for filtering
        """
        self.ax.clear()
        
        self.ax.figure.subplots_adjust(left=0.25, right=0.95, top=0.85, bottom=0.2)
        
        if self.data_manager.df is None or self.data_manager.df.empty:
            return
        
        # Apply time filter if provided
        if time_filter and time_filter[0] is not None and time_filter[1] is not None:
            plot_df = self.data_manager.filter_by_time(time_filter[0], time_filter[1])
        else:
            plot_df = self.data_manager.df
        
        # Calculate the minimum visible duration based on the time range
        if time_filter and time_filter[0] is not None and time_filter[1] is not None:
            time_span = time_filter[1] - time_filter[0]
        else:
            if not plot_df.empty:
                time_span = plot_df["End (ms)"].max() - plot_df["Start (ms)"].min()
            else:
                time_span = 1000  # Default span to fix wonky lines
        
        # Only care about tasks that are longer than 0.5% of the time span
        min_visible_duration = time_span * 0.005
        
        line_width = 1.5
        if len(visible_tasks) > 10:
            line_width = 2.0  # Thicker lines for better visibility with many tasks
        
        task_positions = {}
        for i, task in enumerate(visible_tasks):
            task_positions[task] = i
            
        bar_height = 0.7
        
        for i, task in enumerate(visible_tasks):
            task_df = plot_df[plot_df["Task Name"] == task]
            
            if task in self.system_task_colors:
                # Use predefined colors for known system tasks
                color = self.system_task_colors[task]
            elif task not in self.task_colors:
                # Assign a new color from the palette for tasks without predefined colors
                color_index = len(self.task_colors) % len(self.color_palette)
                self.task_colors[task] = self.color_palette[color_index]
                color = self.task_colors[task]
            else:
                color = self.task_colors[task]
            
            very_short_events = task_df[task_df["Duration (ms)"] < min_visible_duration]
            for _, row in very_short_events.iterrows():
                midpoint = (row["Start (ms)"] + row["End (ms)"]) / 2
                
                y_center = i
                half_height = bar_height / 2
                self.ax.plot([midpoint, midpoint], [y_center - half_height, y_center + half_height], 
                            color=color, linewidth=line_width, solid_capstyle='round')
            
            normal_events = task_df[task_df["Duration (ms)"] >= min_visible_duration]
            for _, row in normal_events.iterrows():
                duration = row["End (ms)"] - row["Start (ms)"]
                self.ax.barh(i, duration, left=row["Start (ms)"], color=color, height=bar_height)
        
        self.ax.set_yticks(range(len(visible_tasks)))
        self.ax.set_yticklabels(visible_tasks)
        
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
        
        self.ax.set_xlabel("Time (ms)", fontsize=12, labelpad=15)
        self.ax.set_ylabel("Tasks", fontsize=12, labelpad=15)
        self.ax.set_title("Task Timeline", fontsize=14, pad=20)
        self.ax.grid(axis='x', linestyle='--', alpha=0.7)  # Add horizontal grid lines
        
        self.ax.tick_params(axis='y', which='major', pad=25)
        self.ax.tick_params(axis='x', which='major', pad=15)
        
        self.ax.tick_params(axis='both', which='major', labelsize=10)
        
        if len(visible_tasks) > 0:
            if time_filter and time_filter[0] is not None and time_filter[1] is not None:
                min_time = time_filter[0]
                max_time = time_filter[1]
            else:
                min_time = plot_df["Start (ms)"].min() if not plot_df.empty else 0
                max_time = plot_df["End (ms)"].max() if not plot_df.empty else 1000
                
            padding = (max_time - min_time) * 0.05
            self.ax.set_xlim(min_time - padding, max_time + padding)
            
            self.ax.set_ylim(-0.5, len(visible_tasks) - 0.5)
        
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