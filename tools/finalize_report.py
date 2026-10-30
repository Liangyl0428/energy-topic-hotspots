# -*- coding: utf-8 -*-
"""从已建计数产物重算 terms_report.csv（不扫语料）。

保留这个入口只是为了兼容旧命令；实际实现已收敛到 CLI 的 `report` 子命令，
避免两份代码路径各算一套指标（否则同一词条会给出不同判定）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_hotspots.term_hotspots.cli import run_report  # noqa: E402


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else None
    run_report(out_csv=out)
