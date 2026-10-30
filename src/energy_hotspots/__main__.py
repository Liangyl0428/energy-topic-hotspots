# -*- coding: utf-8 -*-
"""`python -m energy_hotspots` 等价于 `python -m energy_hotspots.term_hotspots`。

仓库只有词条级一条流水线。这个入口曾经指向已删除的 `energy_hotspots.cli`，
会让 `python -m energy_hotspots` 直接 ModuleNotFoundError。
"""
from .term_hotspots.cli import main

if __name__ == "__main__":
    main()
