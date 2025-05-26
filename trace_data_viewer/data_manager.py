"""
Data management and processing for Trace Data Viewer, based on TimeDoctor.
This Python class handles parsing log files, storing task data, calculating statistics,
and providing methods for filtering and searching tasks.
"""

import pandas as pd
import numpy as np

class DataManager:
    def __init__(self):
        """Initialize the data manager."""
        self.df = None
        self.task_names = {}
        self.events = []
        self.system_core_clock = 32_000_000
        self.time_range = (0, 0)
        self.marker1_pos = None
        self.marker2_pos = None
        
    def parse_log_file(self, filename, task_filter=None):
        """
        Parse the log file and populate the data structures.
        
        Args:
            filename (str): Path to the log file
            task_filter (str, optional): Comma-separated list of task IDs to filter - the idea is to allow users to focus on specific tasks.
              If None, no filtering is applied.
            
        Returns:
            DataFrame: The processed data
        """
        self.task_names = {}
        self.events = []
        self.marker1_pos = None
        self.marker2_pos = None
        self.system_core_clock = 32_000_000
        
        with open(filename) as f:
            lines = f.readlines()
        
        task_start_times = {}
        active_tasks = set()
        
        for line in lines:
            tokens = line.strip().split()
            if not tokens:
                continue

            if tokens[1] == "CC":
                self.system_core_clock = int(tokens[2])
            elif tokens[1] == "TC":
                task_id = int(tokens[2])
                self.task_names[task_id] = " ".join(tokens[3:])
            elif tokens[1] == "TI":
                task_id = int(tokens[2])
                timestamp = int(tokens[0]) * 1000 / self.system_core_clock  # in ms
                task_start_times[task_id] = timestamp
                active_tasks.add(task_id)
            elif tokens[1] == "TO":
                task_id = int(tokens[2])
                timestamp = int(tokens[0]) * 1000 / self.system_core_clock  # in ms
                
                if task_id in task_start_times and task_id in active_tasks:
                    t_start = task_start_times[task_id]
                    t_end = timestamp
                    
                    # Create a task event entry
                    self.events.append({
                        "Task ID": task_id,
                        "Task Name": self.task_names.get(task_id, f"Task {task_id}"),
                        "Start (ms)": float(t_start),
                        "End (ms)": float(t_end),
                        "Duration (ms)": round(float(t_end - t_start), 3)
                    })
                    active_tasks.remove(task_id)
        
        # Handle any tasks that never got a TO event (end of trace)
        for task_id in active_tasks:
            if task_id in task_start_times:
                # Use the last timestamp as end time if the task is still active
                if self.events:
                    last_event_time = max(event["End (ms)"] for event in self.events)
                else:
                    # If no events, just add 1ms to start time
                    last_event_time = task_start_times[task_id] + 1
                
                self.events.append({
                    "Task ID": task_id,
                    "Task Name": self.task_names.get(task_id, f"Task {task_id}"),
                    "Start (ms)": float(task_start_times[task_id]),
                    "End (ms)": float(last_event_time),
                    "Duration (ms)": round(float(last_event_time - task_start_times[task_id]), 3)
                })
        
        if task_filter:
            task_ids = set(map(int, task_filter.split(',')))
            self.events = [e for e in self.events if e["Task ID"] in task_ids]
        
        # Create DataFrame
        self.df = pd.DataFrame(self.events)
        
        if not self.df.empty:
            self.df["Start (ms)"] = self.df["Start (ms)"].astype(float)
            self.df["End (ms)"] = self.df["End (ms)"].astype(float)
            self.df["Duration (ms)"] = self.df["Duration (ms)"].astype(float)
            
            self.time_range = (self.df["Start (ms)"].min(), self.df["End (ms)"].max())
        
        return self.df
    
    def get_task_statistics(self):
        """
        Calculate statistics for all tasks.
        
        Returns:
            list: List of dictionaries containing task statistics
        """
        if self.df is None or self.df.empty:
            return []
            
        stats_data = []
        for task in self.df["Task Name"].unique():
            task_df = self.df[self.df["Task Name"] == task]
            stats_data.append({
                "Task": task,
                "Count": len(task_df),
                "Avg Duration (ms)": task_df["Duration (ms)"].mean(),
                "Min Duration (ms)": task_df["Duration (ms)"].min(),
                "Max Duration (ms)": task_df["Duration (ms)"].max(),
                "Total Duration (ms)": task_df["Duration (ms)"].sum()
            })
            
        return stats_data
    
    def filter_by_time(self, start_time, end_time):
        """
        Return data filtered by time range.
        
        Args:
            start_time (float): Start time in ms
            end_time (float): End time in ms
            
        Returns:
            DataFrame: Filtered data
        """
        if self.df is None or self.df.empty:
            return pd.DataFrame()
            
        return self.df[(self.df["Start (ms)"] < end_time) & 
                       (self.df["End (ms)"] > start_time)]
    
    def get_tasks_in_range(self, start_time, end_time):
        """
        Get tasks that are active in the specified time range.
        
        Args:
            start_time (float): Start time in ms
            end_time (float): End time in ms
            
        Returns:
            dict: Task activity data
        """
        if self.df is None or self.df.empty:
            return {}
            
        time_diff = end_time - start_time
        tasks_in_range = self.filter_by_time(start_time, end_time)
        
        task_data = {}
        for task in tasks_in_range["Task Name"].unique():
            task_df = tasks_in_range[tasks_in_range["Task Name"] == task]
            active_periods = []
            
            for _, row in task_df.iterrows():
                start = max(row["Start (ms)"], start_time)
                end = min(row["End (ms)"], end_time)
                active_periods.append({
                    "start": float(start),
                    "end": float(end),
                    "duration": float(end - start)
                })
            
            total_active_time = sum(period["duration"] for period in active_periods)
            percentage = (total_active_time / time_diff) * 100
            
            task_data[task] = {
                "periods": active_periods,
                "total_active_time": float(total_active_time),
                "percentage": float(percentage)
            }
            
        return task_data
    
    def get_unique_tasks(self):
        """
        Get list of unique task names.
        
        Returns:
            list: List of task names
        """
        if self.df is None or self.df.empty:
            return []
        return self.df["Task Name"].unique().tolist()
    
    def search_tasks(self, search_term):
        """
        Search for tasks matching the search term.
        
        Args:
            search_term (str): Search term to match against task names
            
        Returns:
            dict: Search results with task statistics
        """
        if self.df is None or self.df.empty or not search_term:
            return {}
            
        search_term = search_term.lower()
        matching_tasks = [task for task in self.df["Task Name"].unique() 
                         if search_term in task.lower()]
        
        results = {}
        for task in matching_tasks:
            task_df = self.df[self.df["Task Name"] == task]
            
            # Find the 3 longest durations for this task
            longest = task_df.nlargest(3, "Duration (ms)")
            longest_list = []
            
            for _, row in longest.iterrows():
                longest_list.append({
                    "duration": float(row["Duration (ms)"]),
                    "start_time": float(row["Start (ms)"])
                })
            
            results[task] = {
                "count": len(task_df),
                "avg_duration": float(task_df["Duration (ms)"].mean()),
                "longest_durations": longest_list
            }
            
        return results
    
    def set_marker(self, marker_num, position):
        """
        Set marker position.
        
        Args:
            marker_num (int): Marker number (1 or 2)
            position (float): Position in ms
        """
        if marker_num == 1:
            self.marker1_pos = position
        else:
            self.marker2_pos = position