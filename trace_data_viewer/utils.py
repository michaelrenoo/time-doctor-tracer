"""
Utility functions for Trace Data Viewer.
This module provides helper functions for formatting time and converting time to string representations.
"""

def time_to_str(time_ms):
    """
    Convert time in milliseconds to a formatted string.
    
    Args:
        time_ms (float): Time in milliseconds
        
    Returns:
        str: Formatted time string
    """
    if time_ms < 1:
        return f"{time_ms * 1000:.3f} μs"
    elif time_ms < 1000:
        return f"{time_ms:.3f} ms"
    else:
        seconds = time_ms / 1000
        if seconds < 60:
            return f"{seconds:.3f} s"
        else:
            minutes = int(seconds / 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.3f}s"