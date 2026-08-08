"""Performance-blind proxy transition helpers for ADAA G2.

No live market data are downloaded here. The functions define the canonical
calendar-keyed splice behavior and are tested only on synthetic fixtures.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import pandas as pd


@dataclass(frozen=True)
class TransitionResult:
    returns: pd.Series
    transition_date: pd.Timestamp
    source: pd.Series


def canonical_splice(primary_price: pd.Series, proxy_price: pd.Series) -> TransitionResult:
    """Splice returns by date, never by row count.

    Primary becomes canonical on the first date where both P_t and P_{t-1}
    exist, allowing a genuine primary return to be calculated. Before that
    date the proxy return is used. After transition, missing primary returns
    raise rather than silently reverting to the proxy.
    """
    p = primary_price.sort_index().astype(float)
    q = proxy_price.sort_index().astype(float)
    idx = p.index.union(q.index).sort_values()
    p = p.reindex(idx)
    q = q.reindex(idx)
    pr = p.pct_change(fill_method=None)
    qr = q.pct_change(fill_method=None)

    valid = pr.notna()
    if not valid.any():
        raise ValueError("primary series never provides a valid return")
    transition = valid[valid].index[0]

    out = pd.Series(index=idx, dtype=float, name="return")
    src = pd.Series(index=idx, dtype="object", name="source")
    pre = idx < transition
    out.loc[pre] = qr.loc[pre]
    src.loc[pre] = "proxy"
    post = idx >= transition
    if pr.loc[post].isna().any():
        bad = list(pr.loc[post][pr.loc[post].isna()].index.astype(str))
        raise ValueError(f"primary missing after transition: {bad}")
    out.loc[post] = pr.loc[post]
    src.loc[post] = "primary"
    return TransitionResult(out, transition, src)


def legacy_rowcount_overwrite(primary_ret: pd.Series, proxy_ret: pd.Series) -> pd.Series:
    """Minimal synthetic analogue of the dashboard row-count overwrite."""
    p = primary_ret.copy()
    n_na = int(p.isna().sum())
    if n_na > 0:
        # Legacy behavior uses leading rows based on total NA count rather than date keys.
        rows = p.index[: n_na + 1]
        vals = proxy_ret.iloc[: n_na + 1].to_numpy()
        p.loc[rows] = vals
    return p
