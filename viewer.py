import argparse
import matplotlib.pyplot as plt
import mplcursors

SystemCoreClock = 32_000_000
task_names = {}
events = []

parser = argparse.ArgumentParser(description='TimeDoctor Visualizer')
parser.add_argument('logfile', type=str, help='Logfile to be plotted')
parser.add_argument('--zoom', type=int, default=1, help='Zoom factor (default: 1)')
parser.add_argument('--filter', type=str, help='Filter task by task number (e.g. "1,2,3")')
parser.add_argument('--interactive', action='store_true', help='Enable hover events')
args = parser.parse_args()

with open(args.logfile) as f:
    lines = f.readlines()

for line in lines:
    tokens = line.split()
    if not tokens:
        continue
    timestamp = int(tokens[0]) * 1e3 / SystemCoreClock
    action = tokens[1]
    task = int(tokens[2])

    if action == 'TI':
        t_start = timestamp
    elif action == 'TO':
        t_stop = timestamp
        if t_start is None:
            print(f'Error: TI missing before TO at timestamp {timestamp}!')
            quit()
        events.append({'task': task, 't_start': t_start, 't_stop': t_stop})
        t_start = None
    elif action == 'TC':
        task_names[task] = ' '.join(tokens[3:])
    elif action == 'CC':
        SystemCoreClock = int(tokens[2])
    else:
        print(f'Warning: Unknown action "{action}" ignored: {line}')

if args.filter:
    filtered_tasks = set(map(int, args.filter.split(',')))
    events = [e for e in events if e['task'] in filtered_tasks]

events.sort(key=lambda e: e['t_start'])

categories = sorted(set([e['task'] for e in events]))
task_name_map = {task: task_names.get(task, f"Task {task}") for task in categories}

plt.figure(figsize=(10, 6))
plt.title("Task Execution Timeline")
plt.xlabel("Time [ms]")
plt.ylabel("Task ID")

plt.minorticks_on()
plt.grid(which='both', axis='x')

plt.yticks(categories, [task_name_map[key] for key in categories])

for e in events:
    plt.hlines(e['task'], e['t_start'], e['t_stop'], color=f"C{e['task'] % 10}", linewidth=6, label=f"Task {e['task']}" if e['task'] not in plt.gca().get_legend_handles_labels()[1] else "")

if args.interactive:
    mplcursors.cursor(hover=True)

plt.tight_layout()
plt.legend(loc='upper left', fontsize='small')
plt.show()
