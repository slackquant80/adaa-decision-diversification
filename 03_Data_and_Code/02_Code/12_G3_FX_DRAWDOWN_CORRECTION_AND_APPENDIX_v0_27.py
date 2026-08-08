#!/usr/bin/env python3
"""ADAA v0.27 — FX appendix drawdown correction and publication exhibits.

Purpose
-------
Recompute drawdown-dependent FX-extension diagnostics with the standard definition that
includes initial wealth W0=1 as a valid running peak, following the independently validated
v0.26 core drawdown convention. Return paths, FX signals, thresholds, portfolio weights,
costs, and sample dates are NOT changed.

This script deliberately reads frozen v0.19/v0.20 inputs and writes NEW v0.27 outputs.
Historical v0.20 outputs are retained for provenance.

Important interpretation limit
------------------------------
The "fully hedged" leg remains the legacy zero-carry/zero-hedge-cost proxy. Forward/NDF
carry, hedge transaction costs, collateral/funding, tax and operational constraints are not
modeled. The appendix is therefore a currency-exposure illustration, not an executable
KRW-hedging P&L study.
"""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

SEED = 20260807
B = 10000
BLOCK = 12
TOL = 1e-12


def drawdown_stats(x):
    """Standard drawdown stats with initial wealth W0=1 included."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    wealth = np.r_[1.0, np.cumprod(1.0 + x)]
    peaks = np.maximum.accumulate(wealth)
    dd = wealth / peaks - 1.0
    mdd_i = int(np.argmin(dd))
    mdd = float(dd[mdd_i])

    # Months below a prior high, excluding W0 index from the count.
    underwater = dd[1:] < -1e-12
    total_underwater = int(underwater.sum())

    # Longest consecutive time-under-water run in months.
    longest = 0
    current = 0
    for flag in underwater:
        if flag:
            current += 1
            longest = max(longest, current)
        else:
            current = 0

    # Drawdown area: sum of monthly percentage shortfalls from running peak.
    dd_area = float((-np.minimum(dd[1:], 0.0)).sum())
    recovery_required = float(-mdd / (1.0 + mdd)) if mdd > -1.0 else np.inf

    return {
        "max_drawdown": mdd,
        "recovery_return_required": recovery_required,
        "months_underwater": total_underwater,
        "share_months_underwater": total_underwater / len(x) if len(x) else np.nan,
        "longest_underwater_run_months": int(longest),
        "drawdown_area_months": dd_area,
    }


def perf(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    growth = float(np.prod(1.0 + x))
    cagr = float(growth ** (12.0 / n) - 1.0)
    vol = float(np.std(x, ddof=1) * np.sqrt(12.0))
    ann = float(np.mean(x) * 12.0)
    zero_sharpe = float(ann / vol) if vol > 0 else np.nan
    d = {
        "months": n,
        "CAGR": cagr,
        "annualized_arithmetic_mean": ann,
        "annualized_volatility": vol,
        "zero_rate_Sharpe": zero_sharpe,
        "ending_growth_of_1": growth,
    }
    d.update(drawdown_stats(x))
    return d


def overlay_return(base, fx, u):
    base = np.asarray(base, dtype=float)
    fx = np.asarray(fx, dtype=float)
    u = np.asarray(u, dtype=float)
    krw_unhedged = (1.0 + base) * (1.0 + fx) - 1.0
    return (1.0 - u) * base + u * krw_unhedged


def max_dd_rows(arr2d):
    """Vectorized standard MDD for bootstrap rows, including W0=1."""
    wealth = np.cumprod(1.0 + arr2d, axis=1)
    wealth = np.concatenate([np.ones((arr2d.shape[0], 1)), wealth], axis=1)
    peaks = np.maximum.accumulate(wealth, axis=1)
    return (wealth / peaks - 1.0).min(axis=1)


def circular_boot(a, b, block=12, B=10000, seed=SEED):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    n = len(a)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(B, nb))
    offs = np.arange(block)
    idx = (starts[:, :, None] + offs[None, None, :]) % n
    idx = idx.reshape(B, nb * block)[:, :n]
    A = a[idx]
    C = b[idx]
    ann = (A.mean(1) - C.mean(1)) * 12.0
    cagr = np.prod(1.0 + A, axis=1) ** (12.0 / n) - np.prod(1.0 + C, axis=1) ** (12.0 / n)
    vol_adv = C.std(1, ddof=1) * np.sqrt(12.0) - A.std(1, ddof=1) * np.sqrt(12.0)
    dda = max_dd_rows(A)
    ddc = max_dd_rows(C)
    return pd.DataFrame({
        "delta_ann_mean": ann,
        "delta_CAGR": cagr,
        "vol_advantage_fixed50_minus_dynamic": vol_adv,
        "MDD_advantage_dynamic_minus_fixed50": dda - ddc,
    })


def boot_summary(b):
    rows = []
    for c in b.columns:
        v = b[c].to_numpy(float)
        rows.append({
            "metric": c,
            "p025": np.quantile(v, 0.025),
            "median": np.quantile(v, 0.5),
            "p975": np.quantile(v, 0.975),
            "probability_gt_zero": np.mean(v > 0),
        })
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=str(Path(__file__).resolve().parents[2]))
    args = ap.parse_args()
    root = Path(args.project_root).resolve()
    out = root / "03_Data_and_Code" / "04_Outputs"
    figdir = root / "05_Practical_Paper" / "03_Figures"
    tabdir = root / "05_Practical_Paper" / "04_Tables"
    figdir.mkdir(parents=True, exist_ok=True)
    tabdir.mkdir(parents=True, exist_ok=True)

    # Frozen inputs.
    rmon = pd.read_csv(out / "G3_FX_MONTHLY_SIGNAL_AND_RETURNS_R_v0_19.csv")
    rmon["month"] = pd.PeriodIndex(rmon["month"], freq="M")
    thr = pd.read_csv(out / "G3_FX_THRESHOLD_GRID_WEIGHTS_R_v0_19.csv")
    thr["month"] = pd.PeriodIndex(thr["month"], freq="M")
    win = pd.read_csv(out / "G3_FX_WINDOW_SENSITIVITY_R_v0_19.csv")
    win["month"] = pd.PeriodIndex(win["month"], freq="M")
    paths = pd.read_csv(out / "G6_PRIMARY_MONTHLY_RETURN_TURNOVER_PATHS_v0_17.csv")
    paths = paths[paths["portfolio"] == "ADAA_historical_weights_canonical"].copy()
    paths["holding_month"] = pd.PeriodIndex(paths["holding_month"], freq="M")
    if len(paths) != 218 or paths["holding_month"].iloc[0] != pd.Period("2008-06", "M") or paths["holding_month"].iloc[-1] != pd.Period("2026-07", "M"):
        raise RuntimeError("primary ADAA holding window drift")

    fx_current = rmon[["month", "fx_return"]].rename(columns={"month": "holding_month"})
    fx_signal = rmon[["month", "legacy_unhedged_weight", "z1306_legacy_fill1"]].copy()
    fx_signal["holding_month"] = fx_signal["month"] + 1
    fx_signal = fx_signal.drop(columns="month")
    m = paths.merge(fx_current, on="holding_month", how="left").merge(fx_signal, on="holding_month", how="left")
    if m[["fx_return", "legacy_unhedged_weight"]].isna().any().any():
        raise RuntimeError("primary FX merge missing")

    # Reconstruct same core paths and prove they match v0.20 monthly paths.
    variant_rows = []
    path_frames = []
    for base_col, base_label in [("gross_return", "gross_underlying"), ("net_return_25bps", "net25_underlying")]:
        base = m[base_col].to_numpy(float)
        fxr = m["fx_return"].to_numpy(float)
        specs = {
            "fully_hedged_proxy": np.zeros(len(m)),
            "fixed_50_unhedged": np.full(len(m), 0.5),
            "fully_unhedged": np.ones(len(m)),
            "legacy_dynamic_90_50_10": m["legacy_unhedged_weight"].to_numpy(float),
        }
        for nm, u in specs.items():
            rr = overlay_return(base, fxr, u)
            d = perf(rr)
            d.update({
                "base_return_path": base_label,
                "variant": nm,
                "average_unhedged_weight": float(np.mean(u)),
                "state_changes": int(np.sum(np.abs(np.diff(u)) > TOL)),
            })
            variant_rows.append(d)
            path_frames.append(pd.DataFrame({
                "holding_month": m["holding_month"].astype(str),
                "base_return_path": base_label,
                "variant": nm,
                "unhedged_weight": u,
                "portfolio_return": rr,
            }))

    variants = pd.DataFrame(variant_rows)
    new_paths = pd.concat(path_frames, ignore_index=True)
    old_paths = pd.read_csv(out / "G3_FX_EXTENSION_MONTHLY_PATHS_v0_20.csv")
    chk = new_paths.merge(old_paths, on=["holding_month", "base_return_path", "variant"], suffixes=("_new", "_old"), validate="one_to_one")
    max_return_diff = float(np.max(np.abs(chk["portfolio_return_new"] - chk["portfolio_return_old"])))
    max_weight_diff = float(np.max(np.abs(chk["unhedged_weight_new"] - chk["unhedged_weight_old"])))
    if max_return_diff > TOL or max_weight_diff > TOL:
        raise RuntimeError(f"v0.20 return-path drift: return={max_return_diff}, weight={max_weight_diff}")

    variants.to_csv(out / "G3_FX_EXTENSION_VARIANT_PERFORMANCE_CORRECTED_v0_27.csv", index=False)
    new_paths.to_csv(out / "G3_FX_EXTENSION_MONTHLY_PATHS_RECONFIRMED_v0_27.csv", index=False)

    # Threshold surface with corrected drawdown metrics.
    threshold_rows = []
    for (lo, hi), g in thr.groupby(["low_threshold", "high_threshold"]):
        gg = g[["month", "unhedged_weight"]].copy()
        gg["holding_month"] = gg["month"] + 1
        mm = m.merge(gg[["holding_month", "unhedged_weight"]], on="holding_month", how="left")
        if mm["unhedged_weight"].isna().any():
            raise RuntimeError("threshold path missing")
        for base_col, base_label in [("gross_return", "gross_underlying"), ("net_return_25bps", "net25_underlying")]:
            rr = overlay_return(mm[base_col], mm["fx_return"], mm["unhedged_weight"])
            d = perf(rr)
            d.update({
                "low_threshold": float(lo),
                "high_threshold": float(hi),
                "base_return_path": base_label,
                "is_legacy_rule": bool(abs(lo + 0.5) < TOL and abs(hi - 2.0) < TOL),
                "average_unhedged_weight": float(mm["unhedged_weight"].mean()),
                "state_changes": int(np.sum(np.abs(np.diff(mm["unhedged_weight"])) > TOL)),
            })
            threshold_rows.append(d)
    threshold_perf = pd.DataFrame(threshold_rows)
    threshold_perf.to_csv(out / "G3_FX_THRESHOLD_PERFORMANCE_SURFACE_CORRECTED_v0_27.csv", index=False)

    # Window-length sensitivity on common post-warm-up sample.
    first = win.dropna(subset=["unhedged_weight"]).groupby("window_days")["month"].min()
    common_holding = max(first) + 1
    window_rows = []
    for ww, g in win.groupby("window_days"):
        gg = g[["month", "unhedged_weight"]].copy()
        gg["holding_month"] = gg["month"] + 1
        mm = m[m["holding_month"] >= common_holding].merge(gg[["holding_month", "unhedged_weight"]], on="holding_month", how="left").dropna(subset=["unhedged_weight"])
        for base_col, base_label in [("gross_return", "gross_underlying"), ("net_return_25bps", "net25_underlying")]:
            rr = overlay_return(mm[base_col], mm["fx_return"], mm["unhedged_weight"])
            d = perf(rr)
            d.update({
                "window_days": int(ww),
                "base_return_path": base_label,
                "common_start": str(common_holding),
                "first_holding_month": str(mm["holding_month"].iloc[0]),
                "last_holding_month": str(mm["holding_month"].iloc[-1]),
                "average_unhedged_weight": float(mm["unhedged_weight"].mean()),
            })
            window_rows.append(d)
    window_perf = pd.DataFrame(window_rows)
    window_perf.to_csv(out / "G3_FX_WINDOW_PERFORMANCE_COMMON_SAMPLE_CORRECTED_v0_27.csv", index=False)

    # Component decomposition, net-25bp underlying path.
    z = m["z1306_legacy_fill1"].to_numpy(float)
    specs = {
        "fixed_50": np.full(len(m), 0.5),
        "high_side_only": np.where(z > 2.0, 0.1, 0.5),
        "low_side_only": np.where(z < -0.5, 0.9, 0.5),
        "full_legacy": m["legacy_unhedged_weight"].to_numpy(float),
    }
    decomp = []
    for nm, u in specs.items():
        rr = overlay_return(m["net_return_25bps"], m["fx_return"], u)
        d = perf(rr)
        d.update({
            "component": nm,
            "average_unhedged_weight": float(np.mean(u)),
            "state_changes": int(np.sum(np.abs(np.diff(u)) > TOL)),
        })
        decomp.append(d)
    decomp = pd.DataFrame(decomp)
    decomp.to_csv(out / "G3_FX_LEGACY_COMPONENT_DECOMPOSITION_CORRECTED_v0_27.csv", index=False)

    # Paired dependence-aware diagnostic versus fixed 50%, net-25bp underlying path.
    fixed = overlay_return(m["net_return_25bps"], m["fx_return"], np.full(len(m), 0.5))
    dyn = overlay_return(m["net_return_25bps"], m["fx_return"], m["legacy_unhedged_weight"])
    boot = circular_boot(dyn, fixed, B=B, block=BLOCK)
    bs = boot_summary(boot)
    boot.to_csv(out / "G3_FX_LEGACY_VS_FIXED50_BLOCK_BOOTSTRAP_DRAWS_CORRECTED_v0_27.csv", index=False)
    bs.to_csv(out / "G3_FX_LEGACY_VS_FIXED50_BLOCK_BOOTSTRAP_SUMMARY_CORRECTED_v0_27.csv", index=False)

    # Audit old versus corrected metrics. Non-drawdown metrics MUST be invariant.
    oldv = pd.read_csv(out / "G3_FX_EXTENSION_VARIANT_PERFORMANCE_v0_20.csv")
    av = variants.merge(oldv, on=["base_return_path", "variant"], suffixes=("_v027", "_v020"), validate="one_to_one")
    invariant_cols = ["months", "CAGR", "annualized_arithmetic_mean", "annualized_volatility", "zero_rate_Sharpe", "ending_growth_of_1", "average_unhedged_weight", "state_changes"]
    invariant_diffs = {}
    for c in invariant_cols:
        invariant_diffs[c] = float(np.max(np.abs(av[f"{c}_v027"].astype(float) - av[f"{c}_v020"].astype(float))))
        if invariant_diffs[c] > 1e-11:
            raise RuntimeError(f"non-drawdown metric changed: {c} diff={invariant_diffs[c]}")
    av["old_max_drawdown_v0_20"] = av["max_drawdown_v020"]
    av["corrected_max_drawdown_v0_27"] = av["max_drawdown_v027"]
    av["MDD_correction_v027_minus_v020"] = av["max_drawdown_v027"] - av["max_drawdown_v020"]
    audit_cols = ["base_return_path", "variant", "old_max_drawdown_v0_20", "corrected_max_drawdown_v0_27", "MDD_correction_v027_minus_v020"]
    av[audit_cols].to_csv(out / "G3_FX_DRAWDOWN_DEFINITION_CORRECTION_AUDIT_v0_27.csv", index=False)

    # Publication Table FX-1: core variants.
    table1 = variants[[
        "base_return_path", "variant", "CAGR", "annualized_volatility", "zero_rate_Sharpe",
        "max_drawdown", "recovery_return_required", "longest_underwater_run_months",
        "average_unhedged_weight", "state_changes"
    ]].copy()
    table1.to_csv(tabdir / "TABLE_FX1_CORE_CURRENCY_EXPOSURE_VARIANTS_v0.27.csv", index=False)

    # Publication Table FX-2: sensitivity summary.
    gross_thr = threshold_perf[threshold_perf["base_return_path"] == "gross_underlying"].copy()
    gross_win = window_perf[window_perf["base_return_path"] == "gross_underlying"].copy()
    fixed50 = variants[(variants["base_return_path"] == "gross_underlying") & (variants["variant"] == "fixed_50_unhedged")].iloc[0]
    legacy = variants[(variants["base_return_path"] == "gross_underlying") & (variants["variant"] == "legacy_dynamic_90_50_10")].iloc[0]
    legacy_thr = gross_thr[gross_thr["is_legacy_rule"]].iloc[0]
    table2_rows = [
        {
            "diagnostic": "threshold_grid_16_cells",
            "value_1_name": "CAGR_range",
            "value_1": f"{gross_thr['CAGR'].min():.6f} to {gross_thr['CAGR'].max():.6f}",
            "value_2_name": "legacy_CAGR",
            "value_2": f"{legacy_thr['CAGR']:.6f}",
            "interpretation": "Legacy thresholds are not the ex-post CAGR maximum; grid is descriptive, not a reselection exercise."
        },
        {
            "diagnostic": "threshold_grid_16_cells",
            "value_1_name": "cells_CAGR_above_fixed50",
            "value_1": str(int((gross_thr['CAGR'] > fixed50['CAGR']).sum())),
            "value_2_name": "cells_MDD_shallower_than_fixed50",
            "value_2": str(int((gross_thr['max_drawdown'] > fixed50['max_drawdown']).sum())),
            "interpretation": "Assesses whether the legacy result is isolated to one threshold pair."
        },
        {
            "diagnostic": "window_756_1306_1827_common_sample",
            "value_1_name": "CAGR_range",
            "value_1": f"{gross_win['CAGR'].min():.6f} to {gross_win['CAGR'].max():.6f}",
            "value_2_name": "MDD_range",
            "value_2": f"{gross_win['max_drawdown'].min():.6f} to {gross_win['max_drawdown'].max():.6f}",
            "interpretation": "Lookback-length sensitivity on a common post-warm-up sample."
        },
        {
            "diagnostic": "legacy_dynamic_vs_fixed50",
            "value_1_name": "CAGR_difference",
            "value_1": f"{legacy['CAGR'] - fixed50['CAGR']:.6f}",
            "value_2_name": "MDD_difference",
            "value_2": f"{legacy['max_drawdown'] - fixed50['max_drawdown']:.6f}",
            "interpretation": "Historical application only; no forward-carry or hedge-implementation cost is modeled."
        },
    ]
    pd.DataFrame(table2_rows).to_csv(tabdir / "TABLE_FX2_SENSITIVITY_AND_LIMITATIONS_v0.27.csv", index=False)

    # Figure FX-1: cumulative growth, gross path.
    gp = new_paths[new_paths["base_return_path"] == "gross_underlying"].copy()
    gp["holding_month_dt"] = pd.to_datetime(gp["holding_month"] + "-01")
    plt.figure(figsize=(9.2, 5.7))
    order = ["fully_hedged_proxy", "fixed_50_unhedged", "fully_unhedged", "legacy_dynamic_90_50_10"]
    labels = {
        "fully_hedged_proxy": "Hedged proxy",
        "fixed_50_unhedged": "Fixed 50% unhedged",
        "fully_unhedged": "Fully unhedged",
        "legacy_dynamic_90_50_10": "Legacy dynamic 90/50/10",
    }
    for v in order:
        g = gp[gp["variant"] == v].sort_values("holding_month_dt")
        wealth = np.cumprod(1.0 + g["portfolio_return"].to_numpy(float))
        plt.plot(g["holding_month_dt"], wealth, label=labels[v])
    plt.yscale("log")
    plt.ylabel("Growth of 1 (log scale)")
    plt.xlabel("")
    plt.title("FX Figure 1. KRW/USD currency-exposure variants")
    plt.legend(frameon=False)
    plt.grid(alpha=0.18)
    plt.figtext(0.5, 0.005, "The hedged leg is a zero-carry/zero-hedge-cost proxy, not an executable forward/NDF return.", ha="center", fontsize=8.5)
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    plt.savefig(figdir / "Figure_FX1_Currency_Exposure_Growth_v0.27.png", dpi=300, bbox_inches="tight")
    plt.savefig(figdir / "Figure_FX1_Currency_Exposure_Growth_v0.27.svg", bbox_inches="tight")
    plt.close()

    # Figure FX-2: threshold sensitivity on the predeclared threshold grid.
    # Marker area represents CAGR improvement over fixed 50% unhedged; labels show corrected MDD.
    plt.figure(figsize=(8.6, 5.7))
    improvement = np.maximum(gross_thr["CAGR"].to_numpy(float) - float(fixed50["CAGR"]), 0.0)
    sizes = 140 + 18000 * improvement
    plt.scatter(gross_thr["high_threshold"], gross_thr["low_threshold"], s=sizes, alpha=0.72)
    for _, r in gross_thr.iterrows():
        label = f"{100*r['max_drawdown']:.1f}%"
        if bool(r["is_legacy_rule"]):
            label += "\nLEGACY"
        plt.annotate(label, (r["high_threshold"], r["low_threshold"]), ha="center", va="center", fontsize=7.1, fontweight="bold" if bool(r["is_legacy_rule"]) else "normal")
    plt.xticks(sorted(gross_thr["high_threshold"].unique()))
    plt.yticks(sorted(gross_thr["low_threshold"].unique()))
    plt.xlabel("High z-score threshold: reduce USD exposure above this level")
    plt.ylabel("Low z-score threshold: increase USD exposure below this level")
    plt.title("FX Figure 2. Threshold sensitivity is broad rather than knife-edge")
    plt.grid(alpha=0.18)
    plt.figtext(0.5, 0.005, "Marker area = CAGR improvement over fixed 50% unhedged; labels = corrected maximum drawdown.", ha="center", fontsize=8.5)
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    plt.savefig(figdir / "Figure_FX2_Threshold_Sensitivity_v0.27.png", dpi=300, bbox_inches="tight")
    plt.savefig(figdir / "Figure_FX2_Threshold_Sensitivity_v0.27.svg", bbox_inches="tight")
    plt.close()

    # Publication record.
    audit = pd.read_csv(out / "G3_FX_DRAWDOWN_DEFINITION_CORRECTION_AUDIT_v0_27.csv")
    record = {
        "version": "v0.27",
        "verdict": "CONDITIONAL PASS FOR APPENDIX / HISTORICAL KOREA-INVESTOR APPLICATION",
        "drawdown_definition": "standard running-peak drawdown including initial wealth W0=1",
        "core_drawdown_definition_independent_R_validation": {
            "status": "PASS / CLOSED",
            "max_abs_R_Python_difference": 2.576e-14,
            "source": "G6_DRAWDOWN_R_RUNTIME_VALIDATION_RECORD_v0.27.txt",
        },
        "return_path_invariance_vs_v0_20": {
            "max_abs_portfolio_return_difference": max_return_diff,
            "max_abs_unhedged_weight_difference": max_weight_diff,
            "non_drawdown_metric_max_abs_differences": invariant_diffs,
        },
        "core_variants_gross": variants[variants["base_return_path"] == "gross_underlying"].to_dict(orient="records"),
        "threshold_grid_gross": {
            "cells": int(len(gross_thr)),
            "CAGR_min": float(gross_thr["CAGR"].min()),
            "CAGR_max": float(gross_thr["CAGR"].max()),
            "legacy_CAGR": float(legacy_thr["CAGR"]),
            "MDD_min": float(gross_thr["max_drawdown"].min()),
            "MDD_max": float(gross_thr["max_drawdown"].max()),
            "cells_CAGR_above_fixed50": int((gross_thr["CAGR"] > fixed50["CAGR"]).sum()),
            "cells_MDD_shallower_than_fixed50": int((gross_thr["max_drawdown"] > fixed50["max_drawdown"]).sum()),
        },
        "mdd_definition_correction_rows": audit.to_dict(orient="records"),
        "limitations": [
            "legacy thresholds have outcome-linked historical provenance and are not treated as ex-ante optimal",
            "fully hedged leg is a zero-carry/zero-hedge-cost proxy; forward/NDF carry, transaction costs, collateral/funding and tax are not modeled",
            "zero-rate Sharpe is diagnostic only and is not proposed as a Korean-investor benchmark",
            "FX extension remains separate from the global Decision Diversification contribution",
        ],
    }
    (out / "G3_FX_EXTENSION_PUBLICATION_RECORD_v0_27.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")

    print("PASS: v0.27 FX appendix drawdown correction and exhibits written.")
    print(f"Return-path invariance vs v0.20: max return diff={max_return_diff:.3e}; max FX-weight diff={max_weight_diff:.3e}")
    print("Drawdown definition: standard W0=1 running peak, already independently validated in base R on core paths.")
    print("No FX signal, threshold, window, ADAA rule, return path, portfolio weight, cost, or sample was changed.")


if __name__ == "__main__":
    main()
