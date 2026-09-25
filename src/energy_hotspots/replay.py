"""Portable aggregate replay plus same-record potential evidence recomputation."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys


def repository_root():
    return Path(os.environ.get('ENERGY_HOTSPOTS_REPOSITORY', Path(__file__).resolve().parents[2])).resolve()


def replay(output, experiments=False):
    root = repository_root()
    out = Path(output).resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f'Output must be empty: {out}')
    snapshot = root / 'assets/snapshot_20260925/hotspots'
    out.mkdir(parents=True, exist_ok=True)
    for name in ['results', 'data', 'evidence', 'review', 'reliability']:
        shutil.copytree(snapshot/name, out/name, dirs_exist_ok=True)
    env = os.environ.copy()
    env['ENERGY_HOTSPOTS_RUN'] = str(out)
    env['ENERGY_HOTSPOTS_REPOSITORY'] = str(root)
    env['PYTHONPATH'] = str(root/'src') + os.pathsep + env.get('PYTHONPATH', '')
    command = [sys.executable, str(root/'pipelines/hotspots/replay_snapshot.py')]
    if experiments:
        command.append('--experiments')
    subprocess.run(command, env=env, check=True)
    return json.loads((out/'REPLAY_VALIDATION.json').read_text())
