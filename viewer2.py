import argparse
import plotly.graph_objects as go
import pandas as pd

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

# https://plotly.com/python/graph-objects/
# Use graph objects instead of express
fig = go.Figure()

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
        ))

max_time = df["End (ms)"].max()
fig.update_layout(
    title="TimeDoctor Time Viewer",
    xaxis_title="Time (ms)",
    yaxis_title="Tasks",
    barmode='overlay',
    bargap=0.2,
    plot_bgcolor='white',
    height=400 + 50 * len(unique_tasks),
    xaxis=dict(range=[0, max_time], type='linear'),
    yaxis=dict(categoryorder='array', categoryarray=unique_tasks),
    margin=dict(l=100, r=50, t=50, b=50)
)

fig.show()
