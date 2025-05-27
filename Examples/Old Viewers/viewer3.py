import argparse
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State

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

# Task colors
task_colors = {
    "defaultTask": "rgb(255, 99, 132)",  # Red
    "myTaskA": "rgb(54, 162, 235)",      # Blue
    "myTaskB": "rgb(75, 192, 192)",      # Green
    "myTaskC": "rgb(255, 206, 86)",      # Yellow
    "IDLE": "rgb(153, 102, 255)",        # Purple
    "Tmr Svc": "rgb(255, 159, 64)"       # Orange
}

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("TimeDoctor Time Viewer"),
    
    html.Div([
        html.Button('Set Marker 1', id='set-marker1-btn', n_clicks=0),
        html.Button('Set Marker 2', id='set-marker2-btn', n_clicks=0),
        html.Button('Clear Markers', id='clear-markers-btn', n_clicks=0),
    ], style={'margin': '10px 0'}),
    
    dcc.Graph(id='task-timeline', config={'scrollZoom': True}),
    
    html.Div([
        html.Div([
            html.H4("Marker Information"),
            html.Div(id='marker-info'),
        ], style={'padding': '10px', 'backgroundColor': '#f9f9f9', 'borderRadius': '5px'})
    ]),
    
    dcc.Store(id='marker1-position', data=None),
    dcc.Store(id='marker2-position', data=None),
    dcc.Store(id='active-marker', data=1), # 1 for marker1, 2 for marker2
])

@app.callback(
    Output('marker1-position', 'data'),
    Output('marker2-position', 'data'),
    Output('active-marker', 'data'),
    Input('task-timeline', 'clickData'),
    Input('set-marker1-btn', 'n_clicks'),
    Input('set-marker2-btn', 'n_clicks'),
    Input('clear-markers-btn', 'n_clicks'),
    State('marker1-position', 'data'),
    State('marker2-position', 'data'),
    State('active-marker', 'data'),
)
def update_markers(click_data, marker1_clicks, marker2_clicks, clear_clicks, marker1_pos, marker2_pos, active_marker):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return marker1_pos, marker2_pos, active_marker
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'task-timeline' and click_data:
        x = click_data['points'][0]['x']
        
        if 'base' in click_data['points'][0]:
            x = click_data['points'][0]['base'] + x
            
        if active_marker == 1:
            marker1_pos = x
        else:
            marker2_pos = x
            
    elif trigger_id == 'set-marker1-btn':
        active_marker = 1
    elif trigger_id == 'set-marker2-btn':
        active_marker = 2
    elif trigger_id == 'clear-markers-btn':
        marker1_pos = None
        marker2_pos = None
        active_marker = 1
    
    return marker1_pos, marker2_pos, active_marker

@app.callback(
    Output('task-timeline', 'figure'),
    Input('marker1-position', 'data'),
    Input('marker2-position', 'data')
)
def update_graph(marker1_pos, marker2_pos):
    fig = go.Figure()
    
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
            ))
    
    max_time = df["End (ms)"].max()
    min_time = df["Start (ms)"].min()
    
    fig.update_layout(
        xaxis_title="Time (ms)",
        yaxis_title="Tasks",
        barmode='overlay',
        bargap=0.2,
        plot_bgcolor='white',
        height=400 + 50 * len(unique_tasks),
        xaxis=dict(range=[min_time, max_time], type='linear'),
        yaxis=dict(categoryorder='array', categoryarray=unique_tasks),
        margin=dict(l=100, r=50, t=50, b=50)
    )
    
    shapes = []
    annotations = []
    
    if marker1_pos is not None:
        shapes.append({
            'type': 'line',
            'x0': marker1_pos,
            'y0': 0,
            'x1': marker1_pos,
            'y1': 1,
            'yref': 'paper',
            'line': {
                'color': 'magenta',
                'width': 2,
            }
        })
        
        annotations.append({
            'x': marker1_pos,
            'y': 1.05,
            'xref': 'x',
            'yref': 'paper',
            'text': f'M1: {marker1_pos:.3f} ms',
            'showarrow': True,
            'arrowhead': 0,
            'ax': 0,
            'ay': -10,
            'font': {'color': 'magenta'}
        })
    
    if marker2_pos is not None:
        shapes.append({
            'type': 'line',
            'x0': marker2_pos,
            'y0': 0,
            'x1': marker2_pos,
            'y1': 1,
            'yref': 'paper',
            'line': {
                'color': 'yellow',
                'width': 2,
            }
        })
        
        annotations.append({
            'x': marker2_pos,
            'y': 1.05,
            'xref': 'x',
            'yref': 'paper',
            'text': f'M2: {marker2_pos:.3f} ms',
            'showarrow': True,
            'arrowhead': 0,
            'ax': 0,
            'ay': -10,
            'font': {'color': 'red'}
        })
    
    if marker1_pos is not None and marker2_pos is not None:
        x0 = min(marker1_pos, marker2_pos)
        x1 = max(marker1_pos, marker2_pos)
        
        shapes.append({
            'type': 'rect',
            'x0': x0,
            'y0': 0,
            'x1': x1,
            'y1': 1,
            'yref': 'paper',
            'fillcolor': 'rgba(128, 0, 128, 0.1)',
            'line': {'width': 0},
            'layer': 'below'
        })
    
    fig.update_layout(shapes=shapes, annotations=annotations)
    
    return fig

@app.callback(
    Output('marker-info', 'children'),
    Input('marker1-position', 'data'),
    Input('marker2-position', 'data')
)
def update_marker_info(marker1_pos, marker2_pos):
    info = []
    
    if marker1_pos is not None:
        info.append(html.P(f"Marker 1: {marker1_pos:.3f} ms"))
    
    if marker2_pos is not None:
        info.append(html.P(f"Marker 2: {marker2_pos:.3f} ms"))
    
    if marker1_pos is not None and marker2_pos is not None:
        time_diff = abs(marker2_pos - marker1_pos)
        info.append(html.H5(f"Time Difference: {time_diff:.3f} ms", 
                            style={'color': 'purple', 'fontWeight': 'bold'}))
        
        x0 = min(marker1_pos, marker2_pos)
        x1 = max(marker1_pos, marker2_pos)
        
        tasks_in_range = df[((df["Start (ms)"] <= x1) & (df["End (ms)"] >= x0))]["Task Name"].unique()
        
        if len(tasks_in_range) > 0:
            info.append(html.P("Tasks in range:"))
            task_list = [html.Li(task) for task in tasks_in_range]
            info.append(html.Ul(task_list))
    
    return info if info else "No markers set. Click on the graph or use the buttons above to set markers."

if __name__ == '__main__':
    app.run(debug=True)