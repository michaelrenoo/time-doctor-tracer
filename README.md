# Time Doctor Tracer

## Overview
The tool consists of two main components:

- **Tracer Library:** A lightweight C library that integrates with FreeRTOS to capture task switching events.
- **Visualization Tool:** A Python-based viewer that generates interactive timeline visualizations of task execution.

## Getting Started
### Prerequisites
**For the Visualization Tool**:
- Python 3.6 or higher (I use Python 3.11.5)
- Required Python packages:
  - plotly
  - pandas
  - argparse

### Installation of Python packages
```bash
pip3 install plotly pandas argparse
```

## Usage
### Visualization

Currently the most recent viewer is the `viewer2.py`.

For testing purposes, the logfile used is on the same parent folder, called `logfile`.

#### Using the Python viewer
Use the python module to visualize the logged trace data:

```python
python3 viewer2.py logfile
```

To filter tasks, based on the order the tasks occured:

```python
python3 viewer2.py logfile --filter 1,2,3
```

#### Example:

![TimeDoctor Viewer example](/viewer_example.png "Viewer Example")

# TODOs
- Improve README with more info on TimeDoctor and tracing tool
- Maybe include explanation on how to incorporate the tracing tool on other FreeRTOS projects
- Format of log file? Or the binary?
- Output, common issues, etc
- License also on README?
  