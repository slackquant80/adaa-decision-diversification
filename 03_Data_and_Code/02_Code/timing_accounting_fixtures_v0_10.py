from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from math import isfinite
from pathlib import Path
from typing import Iterable, Mapping, Sequence


def add_months(d: date, months: int) -> date:
    idx = d.year * 12 + (d.month - 1) + months
    year, month0 = divmod(idx, 12)
    return date(year, month0 + 1, min(d.day, monthrange(year, month0 + 1)[1]))


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def month_end(d: date) -> date:
    return date(d.year, d.month, monthrange(d.year, d.month)[1])


def first_date_after(anchor: date, available_dates: Sequence[date]) -> date:
    for d in sorted(available_dates):
        if d > anchor:
            return d
    raise ValueError(f"no available date after {anchor.isoformat()}")


def first_date_in_month(target_month: date, available_dates: Sequence[date]) -> date:
    target = month_start(target_month)
    candidates = [d for d in sorted(available_dates) if d.year == target.year and d.month == target.month]
    if not candidates:
        raise ValueError(f"no available date in {target:%Y-%m}")
    return candidates[0]


@dataclass(frozen=True)
class LaaTiming:
    observation_month: date
    release_month: date
    weight_date: date
    effective_date: date


def laa_stated_two_month_timing(observation_month: date, trading_dates: Sequence[date]) -> LaaTiming:
    """Stated convention: observation t, release t+1, allocation effective in t+2."""
    obs = month_start(observation_month)
    release = month_start(add_months(obs, 1))
    effective_month = month_start(add_months(obs, 2))
    effective = first_date_in_month(effective_month, trading_dates)
    # Signal is finalized after the prior month close and before the effective holding month.
    weight_date = month_end(add_months(obs, 1))
    return LaaTiming(obs, release, weight_date, effective)


def laa_dashboard_row_alignment(observation_month: date, trading_dates: Sequence[date]) -> LaaTiming:
    """Frozen dashboard chronology: UNRATE observation t is row-paired with market month t+1.

    The dashboard starts the selected UNRATE table one month before the first market month.
    A weight stamped at market month-end t+1 is then effective from the first return date in t+2.
    This reproduces the observed frozen-panel alignment; it is still an implicit row-offset
    implementation and should be replaced by explicit observation/release/effective dates.
    """
    obs = month_start(observation_month)
    release = month_start(add_months(obs, 1))
    weight_date = month_end(add_months(obs, 1))
    effective = first_date_after(weight_date, trading_dates)
    return LaaTiming(obs, release, weight_date, effective)


def month_distance(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


def performanceanalytics_effective_dates(
    weight_dates: Sequence[date], return_dates: Sequence[date]
) -> dict[date, list[date]]:
    """Emulate the documented Return.portfolio interval convention.

    A weight stamped at date w applies to return observations strictly after w and through the
    next weight date, inclusive. The next weight then starts strictly after its own timestamp.
    """
    w = sorted(weight_dates)
    r = sorted(return_dates)
    out: dict[date, list[date]] = {}
    for i, anchor in enumerate(w):
        next_anchor = w[i + 1] if i + 1 < len(w) else None
        out[anchor] = [d for d in r if d > anchor and (next_anchor is None or d <= next_anchor)]
    return out


def average_ranks(values: Mapping[str, float]) -> dict[str, float]:
    """Equivalent to base R rank() default ties.method='average', ascending."""
    if any(not isfinite(float(v)) for v in values.values()):
        raise ValueError("rank inputs must be finite")
    ordered = sorted((float(v), k) for k, v in values.items())
    out: dict[str, float] = {}
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][0] == ordered[i][0]:
            j += 1
        # one-based positions i+1,...,j
        avg = ((i + 1) + j) / 2.0
        for _, key in ordered[i:j]:
            out[key] = avg
        i = j
    return out


def legacy_rank_threshold_selection(values: Mapping[str, float], top_n: int) -> list[str]:
    ranks = average_ranks(values)
    return [k for k in values if ranks[k] <= top_n]


def stable_exact_n_selection(values: Mapping[str, float], top_n: int, order: Sequence[str]) -> list[str]:
    if set(values) != set(order):
        raise ValueError("order must contain exactly the ranked assets")
    idx = {k: i for i, k in enumerate(order)}
    return sorted(values, key=lambda k: (float(values[k]), idx[k]))[:top_n]


def gross_traded_notional(old: Mapping[str, float], new: Mapping[str, float]) -> float:
    assets = set(old) | set(new)
    return sum(abs(float(new.get(a, 0.0)) - float(old.get(a, 0.0))) for a in assets)


def one_way_turnover(old: Mapping[str, float], new: Mapping[str, float]) -> float:
    return 0.5 * gross_traded_notional(old, new)


def transaction_cost(old: Mapping[str, float], new: Mapping[str, float], rate_per_traded_dollar: float) -> float:
    if rate_per_traded_dollar < 0:
        raise ValueError("cost rate must be non-negative")
    return gross_traded_notional(old, new) * rate_per_traded_dollar


def aggregate_sleeves(
    sleeves: Sequence[tuple[float, Mapping[str, float]]]
) -> dict[str, float]:
    out: dict[str, float] = {}
    for sleeve_weight, weights in sleeves:
        for asset, weight in weights.items():
            out[asset] = out.get(asset, 0.0) + sleeve_weight * float(weight)
    return out


def independent_sleeve_cost(
    old_sleeves: Sequence[tuple[float, Mapping[str, float]]],
    new_sleeves: Sequence[tuple[float, Mapping[str, float]]],
    rate: float,
) -> float:
    if len(old_sleeves) != len(new_sleeves):
        raise ValueError("old and new sleeve lists must match")
    total = 0.0
    for (ow, old), (nw, new) in zip(old_sleeves, new_sleeves):
        if abs(ow - nw) > 1e-12:
            raise ValueError("sleeve capital weights must be unchanged for this diagnostic")
        total += ow * transaction_cost(old, new, rate)
    return total


def cross_netted_cost(
    old_sleeves: Sequence[tuple[float, Mapping[str, float]]],
    new_sleeves: Sequence[tuple[float, Mapping[str, float]]],
    rate: float,
) -> float:
    return transaction_cost(aggregate_sleeves(old_sleeves), aggregate_sleeves(new_sleeves), rate)


def extract_block(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise ValueError(f"start marker not found: {start_marker}")
    end = text.find(end_marker, start + len(start_marker))
    if end < 0:
        raise ValueError(f"end marker not found: {end_marker}")
    return text[start:end]


def audit_dashboard_source(rmd_path: str | Path) -> dict[str, bool]:
    text = Path(rmd_path).read_text(encoding="utf-8")
    laa = extract_block(text, "######## Lethargic Asset Allocation(LAA) ########", "## 1) Autonomous Dynamic Asset Allocation")
    faa = extract_block(text, "######## Flexible Asset Allocation(FAA) ########", "######## Lethargic Asset Allocation(LAA) ########")
    data = extract_block(text, "### 데이터 다운로드", "ADAA_ret <- eventReactive")
    return {
        "laa_has_explicit_plus_two_month_shift": "months(2)" in laa or "months (2)" in laa,
        "laa_row_binds_market_and_unrate": "cbind(prices_LAA_m, unrate)" in laa,
        "laa_uses_return_portfolio_xts_weights": "weights = LAA_wt_xts" in laa,
        "faa_equal_weight_reference_includes_all_assets": "rowMeans(rtn_FAA_m[2:13])" in faa,
        "faa_uses_default_average_rank": "rank(as.numeric" in faa and "ties.method" not in faa,
        "proxy_splice_uses_na_row_counts": "n_na <- na_counts[col]" in data and "rows <- 1:(n_na + 1)" in data,
        "post_2010_unbounded_locf": "filter(Date >= date_temp) %>%" in data and "na.locf()" in data,
    }
