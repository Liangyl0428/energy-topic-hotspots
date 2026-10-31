# -*- coding: utf-8 -*-
"""
词条级热点判定。

设计要点：

1. **增长率用份额口径。** 所有增长、斜率、规模都在"占当期语料份额"上计算。
   语料本身从 2021Q3 的 6.2 万篇/季涨到 2026Q2 的 11.9 万篇/季（五年年化约 +14%，
   近一年同比 +27.5%）；若直接用原始计数相比，每个词条都会白得同样的增长，
   "任何词条都是新兴"。
2. **判定不截断。** 入选完全由门槛决定；`shortlist_size` 只标记对外展示哪几条，
   全量合格名单始终保留在报表里。
3. **领域通用语与跨域泛化词不是热点。** 近期文档频率 ≥ `background_df_max` 的词条
   判为领域通用语（电池、储能、一氧化碳…）；能源语境 lift 过低的词条可选判为
   跨域泛化词（默认关闭锚点，见 `use_anchor_lift`）。两者只写 `excluded_reason`，
   不单独成类、不删除。
4. **类别互斥。** `hotspot_class` 只有 core / emerging / potential，按
   emerging > core > potential 的优先级给出唯一类别，同时保留 `pass_*`
   原始门槛结果以便审计。

所有门槛来自 config/hotspot_rules.json，可用 `--rules` 覆盖；本文档中的数值与
仓库内 config 保持一致，二者不一致视为 bug。
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Sequence

REPO = Path(__file__).resolve().parents[3]
RULES_PATH = REPO / "config" / "hotspot_rules.json"

# ---------------- 窗口（季度口径，与 METHOD.md 冻结一致）----------------


def _all_quarters():
    return [f"{y}Q{q}" for y in range(2020, 2031) for q in range(1, 5)]


def window_quarters(start_y, start_q, end_y, end_q):
    all_q = _all_quarters()
    i = all_q.index(f"{start_y}Q{start_q}")
    return all_q[i:i + (end_y - start_y) * 4 + (end_q - start_q) + 1]


HISTORY_Q = window_quarters(2021, 3, 2026, 2)   # 2021-07-01 .. 2026-06-30
CORE_Q = window_quarters(2023, 3, 2026, 2)      # 近三年
RECENT_Q = window_quarters(2025, 3, 2026, 2)    # 近一年
PREV_Q = window_quarters(2024, 3, 2025, 2)      # 上一年
BASELINE_Q = window_quarters(2021, 3, 2023, 2)  # 背景期：core 之前两年（2021-07 .. 2023-06，8 季）

EPS = 0.5  # 与 METHOD.md 的平滑项一致，避免极小量词条比率爆炸


# 默认门槛。**必须与 config/hotspot_rules.json 完全一致**（tests/test_hotspot_rules.py
# 有守卫）：config 缺失时（wheel 安装、只拷 src）会静默退回这里，两套值不同等于换了一套判据。
DEFAULT_RULES = {
    "version": "v2",
    "background_df_max": 0.025,
    "off_domain_lift_min": 0.85,
    "cross_domain_df_min": 0.004,
    "shortlist_size": 50,
    "use_anchor_lift": False,
    "core": {
        "hits_3y_min": 150.0,
        "scale_pct_min": 0.9,
        "df_recent_min": 0.0008,
        "yoy_min": 0.9,
        "stability_min": 0.8,
    },
    "emerging": {
        "hits_recent_min": 120.0,
        "yoy_min": 1.30,
        "vs_3y_min": 1.20,
        "slope_min": 0.0,
    },
    "potential": {
        "hits_3y_min": 40.0,
        "yoy_min": 0.90,
        "patents_recent_min": 20.0,
        "patent_growth_min": 1.25,
        "patent_growth_vs_paper": True,
        "policies_recent_min": 10.0,
        "policy_growth_min": 1.20,
    },
}


def load_rules(path: Path | None = None) -> dict:
    p = Path(path) if path else RULES_PATH
    rules = json.loads(json.dumps(DEFAULT_RULES))  # deep copy
    if p.exists():
        user = json.loads(p.read_text(encoding="utf-8"))
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(rules.get(k), dict):
                rules[k].update(v)
            elif not k.startswith("_"):
                rules[k] = v
    return rules


# ---------------- 组合指标 ------------------------------------------------


def _log(x: float) -> float:
    return math.log(x) if x > 0 else float("-inf")


def log_slope(values: Sequence[float], xs: Sequence[int] | None = None) -> float:
    """对数最小二乘斜率。跳过 0 值点；有效点 < 8 时返回 0（不足以下结论）。"""
    xs = list(xs) if xs is not None else list(range(len(values)))
    pts = [(x, math.log(v)) for x, v in zip(xs, values) if v > 0]
    if len(pts) < 8:
        return 0.0
    n = len(pts)
    xb = sum(p[0] for p in pts) / n
    yb = sum(p[1] for p in pts) / n
    cov = sum((x - xb) * (y - yb) for x, y in pts)
    var = sum((x - xb) ** 2 for x, _ in pts)
    return cov / var if var else 0.0


def _sum(d, keys):
    return float(sum(d.get(k, 0.0) for k in keys))


def compute_metrics(row_q: dict, row_anch_q: dict, doc_totals: dict, doc_anch: dict,
                    cited_sum: float = 0.0, cited_n: int = 0,
                    patents: dict | None = None, policies: dict | None = None) -> dict:
    """单个词条的指标。份额 = 命中数 / 同窗口语料文档数，等价于文档频率。"""
    patents = patents or {}
    policies = policies or {}

    def win_docs(keys):
        return float(sum(doc_totals.get(q, 0.0) for q in keys))

    hits_hist = _sum(row_q, HISTORY_Q)
    hits_3y = _sum(row_q, CORE_Q)
    hits_recent = _sum(row_q, RECENT_Q)
    hits_prev = _sum(row_q, PREV_Q)
    hits_base = _sum(row_q, BASELINE_Q)
    anch_3y = _sum(row_anch_q, CORE_Q)

    d_hist = win_docs(HISTORY_Q)
    d_3y = win_docs(CORE_Q)
    d_recent = win_docs(RECENT_Q)
    d_prev = win_docs(PREV_Q)
    d_base = win_docs(BASELINE_Q)

    share_recent = hits_recent / d_recent if d_recent else 0.0
    share_prev = hits_prev / d_prev if d_prev else 0.0
    share_3y = hits_3y / d_3y if d_3y else 0.0
    share_base = hits_base / d_base if d_base else 0.0

    # 季度份额序列与对数斜率
    q_share = []
    for q in CORE_Q:
        dq = doc_totals.get(q, 0.0)
        q_share.append((row_q.get(q, 0.0) / dq) if dq else 0.0)
    slope = log_slope(q_share)

    # 稳定性：把 12 个季度里命中数达到自身中位数一半的季度占比（对量级不敏感）
    q_hits = [row_q.get(q, 0.0) for q in CORE_Q]
    pos = sorted(v for v in q_hits if v > 0)
    if len(pos) >= 4:
        med = pos[len(pos) // 2]
        stability = sum(1 for v in q_hits if v >= 0.5 * med) / len(q_hits)
    else:
        stability = 0.0

    # 能源语境 lift：命中文档中同时命中锚点的比例 / 语料中锚点文档基准比例
    anch_base = (sum(doc_anch.get(q, 0.0) for q in CORE_Q) / d_3y) if d_3y else 0.0
    ecs = (anch_3y / hits_3y) if hits_3y > 0 else 0.0
    # 没有锚点数据时 lift 取中性值 1.0，避免把"缺少分母"误判成域外
    energy_lift = (ecs / anch_base) if anch_base > 0 else 1.0

    pat_recent = float(sum(patents.get(y, 0.0) for y in ("2024", "2025")))
    pat_base = float(sum(patents.get(y, 0.0) for y in ("2022", "2023")))
    pol_recent = float(sum(policies.get(y, 0.0) for y in ("2024", "2025", "2026")))
    pol_base = float(sum(policies.get(y, 0.0) for y in ("2021", "2022", "2023")))

    return {
        "hits_hist": hits_hist, "hits_3y": hits_3y, "hits_recent": hits_recent,
        "hits_prev": hits_prev, "hits_base": hits_base, "hits_3y_anch": anch_3y,
        "df_recent": share_recent, "df_prev": share_prev,
        "df_3y": share_3y, "df_base": share_base,
        "yoy": (share_recent + EPS / d_recent) / (share_prev + EPS / d_prev) if (d_recent and d_prev) else 0.0,
        "vs_3y": (share_recent + EPS / d_recent) / (share_3y + EPS / d_3y) if (d_recent and d_3y) else 0.0,
        "slope": slope,
        "stability": stability,
        "energy_context": ecs, "energy_lift": energy_lift,
        "citation_mean": (cited_sum / cited_n) if cited_n else 0.0,
        "patents_recent": pat_recent, "patents_base": pat_base,
        "patent_growth": (pat_recent + 1.0) / (pat_base + 1.0),
        "policies_recent": pol_recent, "policies_base": pol_base,
        "policy_growth": (pol_recent + 1.0) / (pol_base + 1.0),
    }


# ---------------- 分位与判定 ---------------------------------------------


def _percentile(values: List[float], v: float) -> float:
    if not values:
        return 0.0
    n = len(values)
    lo = sum(1 for x in values if x <= v)
    return lo / n


def assign_percentiles(results: Dict[str, dict]) -> None:
    """分位在**全词典**上计算。若只在查询子集上算，单条查询的分位恒为 1.0。"""
    fields = ["hits_3y", "hits_recent", "df_recent", "yoy", "vs_3y", "slope",
              "stability", "energy_lift", "citation_mean", "patent_growth",
              "patents_recent", "policies_recent"]
    for f in fields:
        vals = sorted(v.get(f, 0.0) for v in results.values())
        for v in results.values():
            v[f"{f}_pct"] = _percentile(vals, v.get(f, 0.0))
    for v in results.values():
        v["core_score"] = round(100 * (
            0.40 * v["hits_3y_pct"] + 0.25 * v["df_recent_pct"]
            + 0.20 * v["stability_pct"] + 0.15 * v["citation_mean_pct"]), 2)
        v["emerging_score"] = round(100 * (
            0.40 * v["yoy_pct"] + 0.25 * v["slope_pct"]
            + 0.20 * v["vs_3y_pct"] + 0.15 * v["hits_recent_pct"]), 2)
        v["potential_score"] = round(100 * (
            0.35 * v["patent_growth_pct"] + 0.20 * v["patents_recent_pct"]
            + 0.20 * v["yoy_pct"] + 0.15 * v["policies_recent_pct"]
            + 0.10 * v["hits_3y_pct"]), 2)


def classify(results: Dict[str, dict], rules: dict | None = None) -> Dict[str, dict]:
    """写入 pass_* / hotspot_class / rank_*。判定只依赖门槛，不截断。"""
    rules = rules or load_rules()
    bg_max = rules["background_df_max"]
    lift_min = rules["off_domain_lift_min"]
    cd_df_min = rules.get("cross_domain_df_min", 0.004)
    # 锚点 lift 可整体关闭（默认关闭）：它对结果的影响仅 34 条标记 / 约 7 条进榜，
    # 却引入「手工词表 + 自锚定 + 材料侧覆盖偏差」三个已知缺陷。
    # 关闭后 energy_lift 仍作为诊断列输出，只是不再参与判定。
    use_lift = bool(rules.get("use_anchor_lift", False))
    c, e, p = rules["core"], rules["emerging"], rules["potential"]

    for v in results.values():
        v["is_background"] = bool(v["df_recent"] >= bg_max)
        # "跨域泛化"要求同时满足：能源语境 lift 低 + 确实被广泛使用（df_3y 有量级）。
        # 只满足前者的窄口径词（全固态电池 0.21%/0.77、锂金属负极 0.17%/0.56）
        # 多半是锚点覆盖不足（材料类能源论文不写"电网/发电"），不能当成泛化词误杀。
        low_lift = bool(use_lift and v["hits_3y"] > 0 and v["energy_lift"] < lift_min)
        v["is_cross_domain"] = bool(low_lift and v["df_3y"] >= cd_df_min)
        v["low_anchor_coverage"] = bool(low_lift and not v["is_cross_domain"])
        v["pass_core"] = v["pass_emerging"] = v["pass_potential"] = False

    # 规模分位只在"候选域"（非背景词、非跨域泛化词、有命中）内计算：
    # 这样 0.90 的含义是"候选词条里规模前 10%"，不会因为词典里塞进
    # 更多泛化词而漂移。
    eligible = [v for v in results.values()
                if not v["is_background"] and not v["is_cross_domain"] and v["hits_3y"] > 0]
    scale_vals = sorted(v["hits_3y"] for v in eligible)
    for v in results.values():
        v["scale_pct"] = _percentile(scale_vals, v["hits_3y"]) if eligible else 0.0

    for v in eligible:
        v["pass_core"] = bool(
            v["hits_3y"] >= c["hits_3y_min"]
            and v["scale_pct"] >= c["scale_pct_min"]
            and v["df_recent"] >= c["df_recent_min"]
            and v["yoy"] >= c["yoy_min"]
            and v["stability"] >= c["stability_min"]
        )
        v["pass_emerging"] = bool(
            v["hits_recent"] >= e["hits_recent_min"]
            and v["yoy"] >= e["yoy_min"]
            and v["vs_3y"] >= e["vs_3y_min"]
            and v["slope"] > e["slope_min"]
        )
        # 跨源领先：专利是"近两年/前两年"的两年比率，年化后与论文份额年比 yoy 对齐，
        # 即要求 sqrt(patent_growth) 至少不慢于论文的份额增速。若只要求专利绝对
        # 增长，几乎所有成熟词条都会入选（电池、储能、电力系统都会混进 potential）。
        pat_bar = max(p["patent_growth_min"], v["yoy"] ** 2) if p.get("patent_growth_vs_paper", True) \
            else p["patent_growth_min"]
        v["pass_potential"] = bool(
            v["hits_3y"] >= p["hits_3y_min"]
            and v["yoy"] >= p["yoy_min"]
            and ((v["patents_recent"] >= p["patents_recent_min"]
                  and v["patent_growth"] >= pat_bar)
                 or (v["policies_recent"] >= p["policies_recent_min"]
                     and v["policy_growth"] >= p["policy_growth_min"]))
        )
    # 只有三类热点；未被选中的词条 hotspot_class 留空，原因写在 excluded_reason：
    #   domain_umbrella  近一年 DF ≥ background_df_max，属于领域通用语（电池/储能/一氧化碳…）
    #   cross_domain     能源语境 lift 过低且被广泛使用（光催化/合金/MXene…）
    #   below_gate       过了排除检查但没达到任何一类门槛
    # 这样 hotspot_class 只有 3 个取值，界面不必解释"背景词/跨域词"是什么，
    # 而排查"为什么没进榜"时答案仍然逐条可查。
    for v in results.values():
        if v["is_cross_domain"]:
            cls, reason = "", "cross_domain"
        elif v["is_background"]:
            cls, reason = "", "domain_umbrella"
        elif v["pass_emerging"]:
            cls, reason = "emerging", ""
        elif v["pass_core"]:
            cls, reason = "core", ""
        elif v["pass_potential"]:
            cls, reason = "potential", ""
        else:
            cls, reason = "", "below_gate"
        v["hotspot_class"] = cls
        v["excluded_reason"] = reason
        for k in ("core", "emerging", "potential"):
            v[f"is_{k}"] = cls == k

    # 类别内排序（仅供展示：分数不参与入选）
    for k, score in (("core", "core_score"), ("emerging", "emerging_score"),
                     ("potential", "potential_score")):
        members = [v for v in results.values() if v["hotspot_class"] == k]
        members.sort(key=lambda v: (-v[score], -v["hits_3y"]))
        for i, v in enumerate(members, 1):
            v[f"rank_{k}"] = i
        for v in results.values():
            v.setdefault(f"rank_{k}", 0)
    # 发布配额（shortlist）：门槛不变，只标记"对外展示哪几条"。
    # 配额不能反过来改变判定：pass_* 保持门槛原样，in_shortlist 只是标记，
    # 全量合格名单照旧留在报表里，可随时改 shortlist_size。
    size = int(rules.get("shortlist_size", 0) or 0)
    for v in results.values():
        v["in_shortlist"] = 0
        cls = v["hotspot_class"]
        if cls in ("core", "emerging", "potential"):
            rk = v.get(f"rank_{cls}", 0)
            if size <= 0 or 1 <= rk <= size:
                v["in_shortlist"] = 1
    return results


def summarize(results: Dict[str, dict]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for v in results.values():
        out[v["hotspot_class"]] = out.get(v["hotspot_class"], 0) + 1
        reason = v.get("excluded_reason")
        if reason:
            out[f"reason_{reason}"] = out.get(f"reason_{reason}", 0) + 1
    for k in ("core", "emerging", "potential"):
        out[f"pass_{k}_gate_only"] = sum(1 for v in results.values() if v[f"pass_{k}"])
        out[f"shortlist_{k}"] = sum(
            1 for v in results.values() if v["hotspot_class"] == k and v.get("in_shortlist"))
    return out
