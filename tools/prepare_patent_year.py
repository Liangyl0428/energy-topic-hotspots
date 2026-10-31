# -*- coding: utf-8 -*-
"""把 data/patent_v3/exports_2026 的 JSONL 导出转成与历年一致的专利 CSV。

只保留与 2021–2025 相同的 IPC 小组（见 data/patent/progress.json 的 query_ipcs），
输出列与 H*_YYYY.csv 对齐：ipc_prefix, year, publication_number, country_code,
publication_date, title, abstract。

用法（仓库根目录）：
    python tools/prepare_patent_year.py \
        --exports data/patent_v3/exports_2026 \
        --out-dir data/patent \
        --year 2026
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

# 与历年采集一致的 IPC 小组（来自 data/patent/progress.json 的 query_ipcs）。
GROUPS = {
    "H01F": ["H01F27/", "H01F29/", "H01F30/", "H01F36/", "H01F37/", "H01F38/", "H01F41/"],
    "H02B": ["H02B1/", "H02B11/", "H02B13/", "H02B15/", "H02B3/", "H02B5/", "H02B7/", "H02B99/"],
    "H02G": ["H02G1/", "H02G11/", "H02G13/", "H02G15/", "H02G3/", "H02G5/", "H02G7/", "H02G9/"],
    "H02H": ["H02H1/", "H02H11/", "H02H3/", "H02H5/", "H02H6/", "H02H7/", "H02H9/", "H02H99/"],
    "H02J": ["H02J1/", "H02J11/", "H02J13/", "H02J15/", "H02J3/", "H02J4/", "H02J50/", "H02J7/", "H02J9/"],
    "H02M": ["H02M1/", "H02M11/", "H02M3/", "H02M5/", "H02M7/", "H02M9/"],
}
PREFIXES = [(prefix, group) for prefix, groups in GROUPS.items() for group in groups]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_files(exports: Path) -> list[Path]:
    return sorted(exports.glob("patents_2026_part*.jsonl"))


def pick_ipc_prefix(ipcs: list[str]) -> str:
    for prefix, group in PREFIXES:
        if any(str(ipc).startswith(group) for ipc in ipcs):
            return prefix
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exports", default="data/patent_v3/exports_2026")
    ap.add_argument("--out-dir", default="data/patent")
    ap.add_argument("--year", type=int, default=2026)
    args = ap.parse_args()

    exports = Path(args.exports)
    out_dir = Path(args.out_dir)
    files = export_files(exports)
    if not files:
        raise SystemExit(f"no patents_2026_part*.jsonl under {exports}")

    out = out_dir / f"{args.year}.csv"
    seen: set[str] = set()
    rows = 0
    by_prefix: dict[str, int] = {}
    by_month: dict[str, int] = {}
    missing_text = 0
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["ipc_prefix", "year", "publication_number", "country_code",
                         "publication_date", "title", "abstract"])
        for path in files:
            for line in path.open(encoding="utf-8"):
                if not line.strip():
                    continue
                record = json.loads(line)
                detail = record.get("detail") or {}
                summary = record.get("summary") or {}
                pub = str(detail.get("publicationNumber") or record.get("pub") or "")
                if not pub or pub in seen:
                    continue
                ipcs = [str(x) for x in (detail.get("ipcs") or [])]
                prefix = pick_ipc_prefix(ipcs)
                if not prefix:
                    continue
                pubdate = str(detail.get("publicationDate") or summary.get("publicationDate") or "")
                if pubdate[:4] != str(args.year):
                    continue
                title = (detail.get("enName") or detail.get("zhName")
                         or summary.get("enName") or summary.get("zhName") or "")
                abstract = (detail.get("enAbstract") or detail.get("zhAbstract")
                            or summary.get("enAbstract") or summary.get("zhAbstract") or "")
                if not str(title).strip() and not str(abstract).strip():
                    missing_text += 1
                    continue
                seen.add(pub)
                rows += 1
                by_prefix[prefix] = by_prefix.get(prefix, 0) + 1
                by_month[pubdate[:7]] = by_month.get(pubdate[:7], 0) + 1
                writer.writerow([prefix, args.year, pub,
                                 detail.get("countryCode") or summary.get("countryCode") or "",
                                 pubdate, str(title).replace("\n", " "),
                                 str(abstract).replace("\n", " ")])

    manifest = {
        "year": args.year,
        "source_files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)} for p in files],
        "ipc_groups": GROUPS,
        "filter": "any IPC starts with one of the groups (same as historical progress.json query_ipcs)",
        "rows": rows,
        "by_prefix": dict(sorted(by_prefix.items())),
        "by_month": dict(sorted(by_month.items())),
        "skipped_missing_text": missing_text,
        "output": out.name,
        "output_sha256": sha256(out),
    }
    (out_dir / f"{args.year}_CSV_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out} ({rows:,} rows); manifest {args.year}_CSV_MANIFEST.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
