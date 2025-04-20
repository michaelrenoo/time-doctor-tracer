import argparse
import plotly.express as px
import pandas as pd
from datetime import timedelta

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

df["Start (ms)"] = df["Start (ms)"].apply(lambda x: float(x) if isinstance(x, (int, float, timedelta)) else x)
df["End (ms)"] = df["End (ms)"].apply(lambda x: float(x) if isinstance(x, (int, float, timedelta)) else x)
df["Duration (ms)"] = df["Duration (ms)"].apply(lambda x: float(x.total_seconds() * 1000) if isinstance(x, timedelta) else float(x))

task_colors = {
    "Task 1": "rgb(255, 99, 132)",  # Red
    "Task 2": "rgb(54, 162, 235)",  # Blue
    "Task 3": "rgb(75, 192, 192)",  # Green
}

fig = px.timeline(
    df,
    x_start="Start (ms)",
    x_end="End (ms)",
    y="Task Name",
    hover_data=["Duration (ms)"],
    title="FreeRTOS Task Timeline",
    color_discrete_map=task_colors
)

max_time = df["End (ms)"].max()

fig.update_layout(
    xaxis_title="Time (ms)",
    yaxis_title="Tasks",
    showlegend=False,
    bargap=0.2,
    plot_bgcolor='white',
    height=400 + 20 * len(set(df["Task ID"])),
    xaxis=dict(range=[0, max_time]),
)

fig.show()
