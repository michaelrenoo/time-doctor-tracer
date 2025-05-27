# Real-Time Tracing Tool for FreeRTOS and Python Trace Data Viewer for Trace Events

## Overview
The tool consists of three main components:

- **Tracer Library:** A lightweight C library that integrates with FreeRTOS to capture task switching events and transmit trace event data in binary form through UART.
- **Tracer Receiver Tool:** A Python program that uses serial communication to receive UART transmission and parses binary trace event data back into text format logs to be used in Trace Data Viewer.
- **Visualization Tool:** Trace Data Viewer - A Python-based viewer that generates interactive timeline visualizations of task execution using pandas, matplotlib, numpy, and tkinter libraries.

## System Architecture

![System Architecture](/docs/images/system_architecture.png "System Architecture")

The real-time tracing tool runs on the STM32 with FreeRTOS and transmits binary trace data over UART. This data is received on the host computer using the Python trace data receiver program (trace_data_receiver.py), which parses the binary data and outputs it as text data. The Trace Data Viewer can then visualize these trace events.

## Getting Started

### Prerequisites

**For the STM32 Tracer:**
- STM32 device running FreeRTOS
- USB connection to host computer

**For the Trace Data Receiver:**
- Python 3.6 or higher (Python 3.11.5 recommended)
- Required Python packages:
  - pyserial

**For the Visualization Tool:**
- Python 3.6 or higher (Python 3.11.5 recommended)
- Required Python packages:
  - pandas
  - matplotlib
  - numpy
  - plotly (for older viewers - viewer2.py)

### Installation of Python packages

```bash
# For Trace Data Receiver
pip3 install pyserial

# For Trace Data Viewer
pip3 install pandas matplotlib numpy
```

## Usage

### Running the Tracer on STM32

The tracer tool is part of an STM32 project. To use it:

1. Build the project using either VSCode with STM32 plugin, STM32CubeIDE, or `make`
2. Flash the project to your STM32 device
3. The tracer will automatically run in the background, capturing and transmitting trace events via UART by overriding FreeRTOS trace hook macros

### Receiving and Parsing Trace Data

Use the `trace_data_receiver.py` script to receive binary trace data from the STM32:

```bash
python3 trace_data_receiver.py --port /dev/tty.usbmodem1203 --output trace_data.log
```

Parameters:
- `--port`: Serial port of the STM32 (required)
- `--baud`: Baud rate (default: 921600)
- `--output`: Output file for the parsed trace data
- `--cpu-freq`: CPU frequency in Hz (default: 32000000)
- `--verbose`: Enable verbose output
- `--task-names`: CSV file with task_id,name pairs

When running with verbose output, you'll see real-time information about the received packets:

![Trace Data Terminal](/docs/images/trace_data_terminal.png "Trace Data Terminal Output")

The output format looks like this:
```bash
Format example:
    0 CC 32000000
    1233456 TC 1 defaultTask
    1234455 TC 2 taskA
    1234557 TC 3 taskB
    1234568 TI 1
    1234570 TI 2
    1236435 TO 1
    1268696 TI 3
    1301235 TI 1
    1325433 TO 1
    1335674 TO 2
```

### Visualization

#### Using the Trace Data Viewer

The current visualization tool is a Python module-based application:

```bash
python3 -m trace_data_viewer.main [logfile]
```

Optional arguments:
- `--filter`: Filter by task IDs (comma-separated)

The Trace Data Viewer provides an interactive GUI with the following features:
- Task timeline visualization
- Task filtering
- Marker placement for measuring time intervals
- Statistics calculation
- Search functionality
- Data export options

Example logfiles:
- tasks_in_out.log
- logfile

#### Example:

Trace Data Viewer Example: Markers
![Trace Data Viewer example](/docs/images/trace_data_viewer_gui.png "Trace Data Viewer Markers Example - with trace_data.log file")

Trace Data Viewer Example: Tasks and Time Filters
![Trace Data Viewer example](/docs/images/trace_data_viewer_filters.png "Trace Data Viewer Filters Example - with func_test_30s_1.log file")


## Older Viewers

Previous versions of the viewer are still available:
- `viewer3.py`: Plotly/Dash-based viewer
- `viewer2.py`: Plotly-based viewer
- `time_doctor_viewer.py`: Matplotlib's PyPlot-based viewer
- Other viewer files in the repository



## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Limitations and Constraints

This project was created as part of my Master's thesis to improve and expand on the functionality of [TimeDoctor tool](https://sourceforge.net/projects/timedoctor/) for RTOS event visualization.

## Notes on Implementation

### FreeRTOS Trace Hook Macros

Especially important in the creation of the tool is the correct usage of some FreeRTOS definition in `FreeRTOSConfig.h`. To use the FreeRTOS Trace Hook Macros, it is imperative to set the `configUSE_TRACE_FACILITY` definition to `1`.

```C
#define configUSE_TRACE_FACILITY                 1
```

Aside from that, the macros can then be defined either directly in `FreeRTOSConfig.h` or in `tracer.h` (where all the tracing functions and declarations live). Examples on how to define the macros can be found on [FreeRTOS website](https://freertos.org/Documentation/02-Kernel/02-Kernel-features/09-RTOS-trace-feature). It will look something like:

```C
#define traceTASK_CREATE(pxNewTCB) tracer_TASK_CREATE(pxNewTCB->uxTCBNumber, pxNewTCB->pcTaskName);
#define traceTASK_SWITCHED_IN() tracer_TASK_SWITCHED_IN(pxCurrentTCB->uxTCBNumber);
#define traceTASK_SWITCHED_OUT() tracer_TASK_SWITCHED_OUT(pxCurrentTCB->uxTCBNumber);
```

### Folder Structure

To make the submission of the master's thesis easier, the tools are all placed in one repository instead of 3 different ones. Here is an overview on where each tool is located:

- Tracing Tool is the base project in the repository. Building the root folder with STM32 plug-in, or importing and building the project in STM32CubeIDE will build the tracer tool.
- `trace_data_receiver.py` Python trace receiver is located in the root folder to ease program invocation. The output format can also be a path (e.g., `--output Tests/test_data.log`).
- The Trace Data Viewer is a Python module located inside `trace_data_viewer/` folder. It has its own `main.py` and `__init__.py` and the instructions in the earlier section will run the whole module as one Python application.
- The `Tests/` folder includes some log outputs from the functional tests done for the master's thesis.
- The `Examples/` folder includes log files (old and new) and old Python viewers.


## Contributions

The idea behind this project is to make it available for fellow students that are interested in the Real-Time OS, or the FreeRTOS kernel and STM32. That being said, contributions to the project are always welcome -- Maybe after the thesis defense :D

*Thank you!*