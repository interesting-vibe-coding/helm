#!/usr/bin/env python3
"""
helm-telemetry: local-only usage metrics for YOUR Helm instance.
No data leaves your machine. Use this to understand your own agent workflow.
"""
import json, pathlib, datetime
from collections import defaultdict

HELM_DIR = pathlib.Path.home() / '.helm'
INDEX = HELM_DIR / 'sessions' / 'index.json'

def load_index():
    if not INDEX.exists(): return []
    return json.loads(INDEX.read_text())

def compute_metrics(sessions):
    by_harness = defaultdict(list)
    for s in sessions: by_harness[s.get('harness','unknown')].append(s)
    
    print('Helm Local Telemetry')
    print('===================')
    print(f'Total sessions indexed: {len(sessions)}')
    print()
    for h, ss in sorted(by_harness.items()):
        print(f'  {h:<15} {len(ss):>4} sessions')
    print()
    
    # Sessions per day (last 7 days)
    today = datetime.date.today()
    print('Sessions last 7 days:')
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_str = day.isoformat()
        count = sum(1 for s in sessions if s.get('last_active','')[:10] == day_str)
        bar = '█' * min(count, 30)
        print(f'  {day_str}  {bar} {count}')

if __name__ == '__main__':
    compute_metrics(load_index())
