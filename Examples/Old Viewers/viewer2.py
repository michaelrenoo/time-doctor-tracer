import argparse
import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots

# the log file contains timestamps and a task numbers that is scheduled in
#     3 SC 32000000
#  13169 TC 1 defaultTask
#  30172 TC 2 myTaskA
#  45611 TC 3 myTaskB
#  61050 TC 4 myTaskC
#  75394 TC 5 IDLE
#  92393 TC 6 Tmr Svc
# 102355 TI 4
# 546249 TO 4
# 552488 TI 3
# 1819138 TO 3
# 1830209 TI 2
# 2459150 TO 2

SystemCoreClock = 32_000_000
task_names = {}
events = []

parser = argparse.ArgumentParser(description='TimeDoctor Time Viewer for FreeRTOS')
parser.add_argument('logfile', type=str, help='Path to log file')
parser.add_argument('--filter', type=str, help='Filter by task IDs (comma-separated)')
args = parser.parse_args()

with open(args.logfile) as f:
    lines = f.readlines()

t_start = None
for line in lines:
    tokens = line.strip().split()
    if not tokens:
        continue

    if tokens[1] == "CC":
        SystemCoreClock = int(tokens[2])
    elif tokens[1] == "TC":
        task_id = int(tokens[2])
        task_names[task_id] = " ".join(tokens[3:])
    elif tokens[1] == "TI":
        task_id = int(tokens[2])
        t_start = int(tokens[0]) * 1000 / SystemCoreClock  # in ms
    elif tokens[1] == "TO":
        task_id = int(tokens[2])
        t_end = int(tokens[0]) * 1000 / SystemCoreClock  # in ms
        if t_start is None:
            continue
        events.append({
            "Task ID": task_id,
            "Task Name": task_names.get(task_id, f"Task {task_id}"),
            "Start (ms)": float(t_start),
            "End (ms)": float(t_end),
            "Duration (ms)": round(float(t_end - t_start), 3)
        })
        t_start = None

if args.filter:
    task_ids = set(map(int, args.filter.split(',')))
    events = [e for e in events if e["Task ID"] in task_ids]

df = pd.DataFrame(events)

df["Start (ms)"] = df["Start (ms)"].astype(float)
df["End (ms)"] = df["End (ms)"].astype(float)
df["Duration (ms)"] = df["Duration (ms)"].astype(float)

# TODO: Automate this, or just randomly select colors for all tasks
task_colors = {
    "defaultTask": "rgb(255, 99, 132)",  # Red
    "myTaskA": "rgb(54, 162, 235)",      # Blue
    "myTaskB": "rgb(75, 192, 192)",      # Green
    "myTaskC": "rgb(255, 206, 86)",      # Yellow
    "IDLE": "rgb(153, 102, 255)",        # Purple
    "Tmr Svc": "rgb(255, 159, 64)"       # Orange
}

# Create figure with secondary y-axis for the marker information
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                   vertical_spacing=0.02, row_heights=[0.9, 0.1])

# Separate tasks by name and then plot them
unique_tasks = df["Task Name"].unique()
for i, task in enumerate(unique_tasks):
    task_df = df[df["Task Name"] == task]
    color = task_colors.get(task, f"hsl({i*360/len(unique_tasks)}, 70%, 50%)")
    
    for _, row in task_df.iterrows():
        fig.add_trace(go.Bar(
            x=[row["End (ms)"] - row["Start (ms)"]],
            y=[row["Task Name"]],
            orientation='h',
            base=row["Start (ms)"],
            marker_color=color,
            name=task,
            hoverinfo="text",
            hovertext=f"Task: {task}<br>Duration: {row['Duration (ms)']} ms<br>Start: {row['Start (ms)']} ms<br>End: {row['End (ms)']} ms",
            showlegend=False
        ), row=1, col=1)

# Add empty trace to the second subplot where we'll show marker information
fig.add_trace(
    go.Scatter(
        x=[], 
        y=[], 
        mode='text',
        name='Marker Info',
        text=[],
        textposition="middle center",
        showlegend=False
    ), 
    row=2, col=1
)

max_time = df["End (ms)"].max()
min_time = df["Start (ms)"].min()

# Update layout
fig.update_layout(
    title="TimeDoctor Time Viewer",
    xaxis_title="Time (ms)",
    barmode='overlay',
    bargap=0.2,
    plot_bgcolor='white',
    height=500 + 50 * len(unique_tasks),
    xaxis=dict(range=[min_time, max_time], type='linear'),
    yaxis=dict(title="Tasks", categoryorder='array', categoryarray=unique_tasks),
    yaxis2=dict(title="Markers", showticklabels=False),
    margin=dict(l=100, r=50, t=50, b=50),
    hovermode="closest"
)

# Add buttons and marker functionality
marker_positions = []
marker_shapes = []
marker_annotations = []

# Define the JavaScript function that will update markers
marker_script = """
var markerPositions = [];
var markerShapes = [];
var markerAnnotations = [];
var maxMarkers = 2;  // Only allow 2 markers for distance calculation

// Function to add a marker
function addMarker(timestamp) {
    // If we already have the maximum number of markers, remove the oldest one
    if (markerPositions.length >= maxMarkers) {
        markerPositions.shift();
        
        // Remove corresponding shape and annotation
        var shapes = document.layout.shapes || [];
        var annotations = document.layout.annotations || [];
        
        if (shapes.length > 0) {
            shapes.shift();
        }
        
        if (annotations.length > 0) {
            annotations.shift();
        }
        
        document.layout.shapes = shapes;
        document.layout.annotations = annotations;
    }
    
    // Add the new marker position
    markerPositions.push(timestamp);
    
    // Create a new vertical line shape
    var newShape = {
        type: 'line',
        x0: timestamp,
        y0: 0,
        x1: timestamp,
        y1: 1,
        yref: 'paper',
        line: {
            color: markerPositions.length === 1 ? 'red' : 'blue',
            width: 2,
            dash: 'dash'
        }
    };
    
    // Add annotation for the marker
    var newAnnotation = {
        x: timestamp,
        y: 1.05,
        xref: 'x',
        yref: 'paper',
        text: 'M' + markerPositions.length + ': ' + timestamp.toFixed(3) + ' ms',
        showarrow: true,
        arrowhead: 0,
        ax: 0,
        ay: -10,
        font: {
            color: markerPositions.length === 1 ? 'red' : 'blue'
        }
    };
    
    // Update shapes and annotations
    var shapes = document.layout.shapes || [];
    var annotations = document.layout.annotations || [];
    
    shapes.push(newShape);
    annotations.push(newAnnotation);
    
    document.layout.shapes = shapes;
    document.layout.annotations = annotations;
    
    // If we have two markers, calculate the distance between them
    if (markerPositions.length === 2) {
        var distance = Math.abs(markerPositions[1] - markerPositions[0]);
        
        // Update the text in the second subplot
        Plotly.restyle(document, {
            'text': [['Distance between markers: ' + distance.toFixed(3) + ' ms']]
        }, [markerPositions.length]);
    }
    
    Plotly.redraw(document);
}

// Function to clear all markers
function clearMarkers() {
    markerPositions = [];
    
    // Clear shapes and annotations
    document.layout.shapes = [];
    document.layout.annotations = [];
    
    // Clear the distance text
    Plotly.restyle(document, {
        'text': [['']]
    }, [2]);  // Index of the text trace
    
    Plotly.redraw(document);
}

// Set up click handler for the graph
document.on('plotly_click', function(data) {
    var timestamp = data.points[0].x;
    if (data.points[0].fullData.orientation === 'h') {
        // If clicking on a horizontal bar, use the x-value (time)
        timestamp = data.points[0].x + data.points[0].base;
    }
    addMarker(timestamp);
});

// Add buttons to the graph
var clearButton = {
    name: 'Clear Markers',
    click: function() {
        clearMarkers();
    }
};

// Add the buttons to the modebar
document._context.modeBarButtonsToAdd = [clearButton];
"""

# Update the configuration to enable the custom JavaScript
config = {
    'displayModeBar': True,
    'displaylogo': False,
    'modeBarButtonsToRemove': ['select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d'],
    'toImageButtonOptions': {
        'format': 'png',
        'filename': 'task_timeline',
        'height': 800,
        'width': 1200,
        'scale': 2
    }
}

# Display the figure with the custom JavaScript and configuration
fig.show(config=config, post_script=marker_script)