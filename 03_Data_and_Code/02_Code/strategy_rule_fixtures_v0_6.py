from __future__ import annotations

from datetime import date
from math import isfinite, sqrt
from typing import Dict, Mapping, Sequence


def _top(scores: Mapping[str, float], n: int, order: Sequence[str]) -> list[str]:
    """Deterministic descending selection; ``order`` is the declared tie breaker."""
    if n <= 0:
        raise ValueError("n must be positive")
    missing = set(scores).difference(order)
    if missing:
        raise ValueError(f"tie-break order is missing assets: {sorted(missing)}")
    require_complete_scores(scores)
    idx = {name: i for i, name in enumerate(order)}
    return sorted(scores, key=lambda k: (-scores[k], idx[k]))[:n]


def _add_weight(weights: Dict[str, float], asset: str, amount: float) -> None:
    weights[asset] = weights.get(asset, 0.0) + amount


def require_complete_scores(scores: Mapping[str, float | None]) -> None:
    """Fail closed on missing/non-finite signal inputs; do not silently forward-fill."""
    bad = [k for k, v in scores.items() if v is None or not isfinite(float(v))]
    if bad:
        raise ValueError(f"missing or non-finite scores: {bad}")


def first_eligible_index(*lookbacks: int) -> int:
    """Zero-based index of the first row with all requested trailing lookbacks available."""
    if not lookbacks or any(x < 0 for x in lookbacks):
        raise ValueError("lookbacks must be non-negative integers")
    return max(lookbacks)


def haa_parent_weights(
    offensive_scores: Mapping[str, float],
    tip_score: float,
    defensive_scores: Mapping[str, float],
    offensive_order: Sequence[str],
    defensive_order: Sequence[str],
    top_n: int = 4,
) -> Dict[str, float]:
    best_def = _top(defensive_scores, 1, defensive_order)[0]
    if tip_score <= 0:
        return {best_def: 1.0}
    selected = _top(offensive_scores, top_n, offensive_order)
    out: Dict[str, float] = {}
    for asset in selected:
        _add_weight(out, asset if offensive_scores[asset] > 0 else best_def, 1.0 / top_n)
    return out


def haa_dashboard_legacy_weights(
    offensive_scores: Mapping[str, float],
    tip_score: float,
    defensive_scores: Mapping[str, float],
    offensive_order: Sequence[str],
    defensive_order: Sequence[str],
    top_n: int = 6,
) -> Dict[str, float]:
    best_def = _top(defensive_scores, 1, defensive_order)[0]
    if tip_score <= 0:
        return {best_def: 1.0}
    return {a: 1.0 / top_n for a in _top(offensive_scores, top_n, offensive_order)}


def baa_weights(
    canary_scores: Mapping[str, float],
    offensive_scores: Mapping[str, float],
    defensive_scores: Mapping[str, float],
    offensive_order: Sequence[str],
    defensive_order: Sequence[str],
    bil: str = "BIL",
    offensive_top_n: int = 1,
    defensive_top_n: int = 3,
) -> Dict[str, float]:
    require_complete_scores(canary_scores)
    defensive_mode = any(v < 0 for v in canary_scores.values())
    if not defensive_mode:
        return {a: 1.0 / offensive_top_n for a in _top(offensive_scores, offensive_top_n, offensive_order)}
    if bil not in defensive_scores:
        raise ValueError("BIL fallback asset must be present in defensive scores")
    selected = _top(defensive_scores, defensive_top_n, defensive_order)
    out: Dict[str, float] = {}
    for asset in selected:
        chosen = asset if defensive_scores[asset] >= defensive_scores[bil] else bil
        _add_weight(out, chosen, 1.0 / defensive_top_n)
    return out


def adm_parent_weights(us_score: float, ex_us_small_score: float, treasury: str = "TLT") -> Dict[str, float]:
    require_complete_scores({"US": us_score, "EX_US_SMALL": ex_us_small_score})
    if max(us_score, ex_us_small_score) <= 0:
        return {treasury: 1.0}
    return {"US": 1.0} if us_score >= ex_us_small_score else {"EX_US_SMALL": 1.0}


def adaa_adm_weights(
    risky_scores: Mapping[str, float],
    safe_scores: Mapping[str, float],
    risky_order: Sequence[str],
    safe_order: Sequence[str],
    top_n: int = 6,
) -> Dict[str, float]:
    selected = _top(risky_scores, top_n, risky_order)
    best_safe = _top(safe_scores, 1, safe_order)[0]
    out: Dict[str, float] = {}
    for asset in selected:
        _add_weight(out, asset if risky_scores[asset] > 0 else best_safe, 1.0 / top_n)
    return out


def faa_weights_from_combined_rank(
    combined_loss_scores: Mapping[str, float],
    absolute_momentum: Mapping[str, float],
    cash: str,
    order: Sequence[str],
    top_n: int,
) -> Dict[str, float]:
    """Select the lowest combined-loss ranks with deterministic tie handling."""
    if set(combined_loss_scores) != set(absolute_momentum):
        raise ValueError("combined rank and absolute-momentum assets must match")
    inverse = {k: -v for k, v in combined_loss_scores.items()}
    selected = _top(inverse, top_n, order)
    out: Dict[str, float] = {}
    for asset in selected:
        _add_weight(out, asset if absolute_momentum[asset] > 0 else cash, 1.0 / top_n)
    return out


def peer_equal_weight_series(
    returns: Mapping[str, Sequence[float]], target: str, include_self: bool
) -> list[float]:
    """Build the FAA correlation reference with or without the target asset itself."""
    if target not in returns:
        raise ValueError("target asset is absent")
    names = list(returns) if include_self else [k for k in returns if k != target]
    if not names:
        raise ValueError("at least one peer series is required")
    lengths = {len(returns[k]) for k in names}
    if len(lengths) != 1:
        raise ValueError("return series lengths differ")
    return [sum(float(returns[k][i]) for k in names) / len(names) for i in range(next(iter(lengths)))]


def pearson_correlation(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) != len(y) or len(x) < 2:
        raise ValueError("correlation inputs must have equal length >= 2")
    mx, my = sum(x) / len(x), sum(y) / len(y)
    dx = [v - mx for v in x]
    dy = [v - my for v in y]
    denom = sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    if denom == 0:
        raise ValueError("zero-variance correlation input")
    return sum(a * b for a, b in zip(dx, dy)) / denom


def laa_parent_weights(market_bearish: bool, unemployment_bearish: bool) -> Dict[str, float]:
    out = {"IWD": 0.25, "GLD": 0.25, "IEF": 0.25}
    out["SHY" if market_bearish and unemployment_bearish else "QQQ"] = 0.25
    return out


def adaa_laa_weights(market_bearish: bool, unemployment_bearish: bool) -> Dict[str, float]:
    out = {"SPY": 0.175, "EEM": 0.05, "EWY": 0.025, "IEF": 0.25, "GLD": 0.25}
    out["SHY" if market_bearish and unemployment_bearish else "QQQ"] = 0.25
    return out


def _add_months(d: date, months: int) -> date:
    month_index = d.year * 12 + (d.month - 1) + months
    year, month0 = divmod(month_index, 12)
    return date(year, month0 + 1, 1)


def laa_unemployment_timeline(observation_month: date) -> dict[str, date]:
    """Historical LAA convention: observation t, release t+1, effective allocation t+2."""
    obs = date(observation_month.year, observation_month.month, 1)
    return {
        "observation_month": obs,
        "release_month": _add_months(obs, 1),
        "effective_holding_month": _add_months(obs, 2),
    }


def splice_proxy_series(
    primary: Mapping[date, float | None],
    proxy: Mapping[date, float | None],
    primary_start: date,
) -> Dict[date, float]:
    """Date-keyed splice: proxy strictly before primary_start, primary on/after it."""
    keys = sorted(set(primary) | set(proxy))
    out: Dict[date, float] = {}
    for key in keys:
        value = primary.get(key) if key >= primary_start else proxy.get(key)
        if value is None or not isfinite(float(value)):
            raise ValueError(f"missing splice value at {key.isoformat()}")
        out[key] = float(value)
    return out


def assert_unit_sum(weights: Mapping[str, float], tolerance: float = 1e-12) -> None:
    total = sum(weights.values())
    if abs(total - 1.0) > tolerance:
        raise AssertionError(f"weights sum to {total}, not 1")
