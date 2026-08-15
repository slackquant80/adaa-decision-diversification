from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 8,
    "axes.grid": True,
    "grid.alpha": 0.18,
    "grid.linewidth": 0.8,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "svg.hashsalt": "adaa-final-house-sync-v1.1.6",
})

FIGURES = {
    "Figure 1": ("FIGURE_1_SOURCE_DATA_v0.22.csv", "Figure_1_Return_Correlation_vs_Decision_Timing_PAPER_v1.25_EXACT"),
    "Figure 2": ("FIGURE_2_SOURCE_DATA_v0.22.csv", "Figure_2_What_When_HowMuch_Decision_Fingerprints_PAPER_v1.25_EXACT"),
    "Figure 3": ("FIGURE_3_SOURCE_DATA_v0.22.csv", "Figure_3_Different_Decision_Clocks_PAPER_v1.25_EXACT"),
    "Figure 4": ("FIGURE_4_SOURCE_DATA_v0.23.csv", "Figure_4_Rolling_60M_Hindsight_Winner_PAPER_v1.25_EXACT"),
    "Figure 5": ("FIGURE_5_SOURCE_DATA_v1.0.1.csv", "Figure_5_Broad_Plateau_Unstable_Optimum_PAPER_v1.25_EXACT"),
    "Figure 6": ("FIGURE_6_SOURCE_DATA_v1.1.csv", "Figure_6_Cumulative_Wealth_PAPER_v1.25_EXACT"),
    "Figure 7": ("FIGURE_7_SOURCE_DATA_v1.1.csv", "Figure_7_Drawdown_Depth_and_Duration_PAPER_v1.25_EXACT"),
    "Figure 8": ("FIGURE_8_SOURCE_DATA_v1.0.1.csv", "Figure_8_Stress_Protection_and_Rapid_Reversal_PAPER_v1.25_EXACT"),
    "Figure A1": ("FIGURE_Z1_SOURCE_DATA_FULL_2023_PAIRWISE_v1.0.csv", "Figure_A1_Full_2023_Pairwise_Decision_Distance_PAPER_v1.25_EXACT"),
    "Figure A2": ("FIGURE_Z2_SOURCE_DATA_FULL_2023_FIVE_RULE_SELECTOR_v1.0.csv", "Figure_A2_Full_2023_Five_Rule_Score_Distribution_PAPER_v1.25_EXACT"),
    "Figure B1": ("FIGURE_FX1_SOURCE_DATA_MONTHLY_PATHS_v1.0.csv", "Figure_B1_Currency_Exposure_Growth_PAPER_v1.25_EXACT"),
    "Figure B2": ("FIGURE_FX2_SOURCE_DATA_v1.1.csv", "Figure_B2_Threshold_Sensitivity_PAPER_v1.25_EXACT"),
}


def _save(fig: plt.Figure, out_base: Path) -> None:
    fig.savefig(Path(str(out_base) + ".png"), dpi=300, metadata={"Software": "matplotlib"})
    fig.savefig(Path(str(out_base) + ".svg"), metadata={"Date": None, "Creator": "matplotlib"})
    plt.close(fig)


def figure_1(df: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.2767, 5.4833))
    ax.scatter(df.return_correlation, df.transition_disagreement, s=60)
    offsets = {
        "HAA–BAA": (5, 5), "HAA–ADM": (-18, -14), "HAA–FAA": (5, 5), "HAA–LAA": (5, 5),
        "BAA–ADM": (-58, -3), "BAA–FAA": (-58, 6), "BAA–LAA": (5, 5), "ADM–FAA": (-35, -14),
        "ADM–LAA": (5, 5), "FAA–LAA": (5, -16),
    }
    for r in df.itertuples():
        dx, dy = offsets.get(r.pair, (5, 5))
        ax.annotate(r.pair.replace("–", "-"), (r.return_correlation, r.transition_disagreement),
                    xytext=(dx, dy), textcoords="offset points", fontsize=9)
    ax.set_xlabel("Monthly return correlation")
    ax.set_ylabel("Decision-timing disagreement\n(1 - transition Jaccard)")
    ax.set_xlim(0.45, 0.90)
    ax.set_ylim(0.25, 1.01)
    fig.subplots_adjust(left=0.13, right=0.98, bottom=0.15, top=0.98)
    _save(fig, out)


def figure_2(df: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.2533, 5.4833))
    sizes = 120 + 520 * (df.mean_rule_defined_defensive_share / df.mean_rule_defined_defensive_share.max())
    ax.scatter(df.mean_active_assets, 100 * df.change_rate, s=sizes, alpha=0.85)
    offsets = {"HAA": (7, 2), "BAA": (7, -2), "ADM": (7, 9), "FAA": (7, -15), "LAA": (7, 4)}
    for r in df.itertuples():
        dx, dy = offsets.get(r.sleeve, (5, 5))
        ax.annotate(r.sleeve, (r.mean_active_assets, 100 * r.change_rate), xytext=(dx, dy),
                    textcoords="offset points", fontsize=9, fontweight="bold")
    ax.set_xlabel("Portfolio breadth: average number of active holdings")
    ax.set_ylabel("Target-change frequency: months with a target-weight change (%)")
    ax.set_xlim(1.55, 6.25)
    ax.set_ylim(-2, 90)
    ax.text(0.02, 0.02, "Marker area: average rule-defined defensive allocation.",
            transform=ax.transAxes, fontsize=8.5)
    fig.subplots_adjust(left=0.13, right=0.98, bottom=0.15, top=0.98)
    _save(fig, out)


def figure_3(df: pd.DataFrame, out: Path) -> None:
    order = ["LAA", "LAA parent", "RAA parent", "BAA", "HAA", "FAA", "ADM"]
    d = df.set_index("rule").loc[order].reset_index()
    d["display_rule"] = d["rule"].replace({"LAA parent": "Published LAA", "RAA parent": "Published RAA"})
    fig, ax = plt.subplots(figsize=(8.3033, 5.6867))
    y = np.arange(len(d))
    ax.barh(y, d.mean_constant_weight_run_months)
    ax.set_yticks(y, d.display_rule)
    ax.invert_yaxis()
    ax.set_xlabel("Average months with unchanged target weights")
    for i, r in d.iterrows():
        ax.text(r.mean_constant_weight_run_months + 0.4, i,
                f"{r.mean_constant_weight_run_months:.1f} mo  (max {int(r.max_constant_weight_run_months)})",
                va="center", fontsize=8.5)
    ax.set_xlim(0, max(34, d.mean_constant_weight_run_months.max() + 6))
    fig.subplots_adjust(left=0.18, right=0.97, bottom=0.14, top=0.98)
    _save(fig, out)


def figure_4(df: pd.DataFrame, out: Path) -> None:
    d = df.copy()
    d["holding_month"] = pd.to_datetime(d.holding_month)
    order = ["HAA", "BAA", "ADM", "FAA", "LAA"]
    pos = {x: i for i, x in enumerate(order)}
    fig, ax = plt.subplots(figsize=(8.6967, 4.9867))
    y = [pos.get(x, np.nan) for x in d.best_sleeve]
    ax.scatter(d.holding_month, y, s=17)
    ax.set_yticks(range(len(order)), order)
    ax.invert_yaxis()
    ax.set_xlabel("End of trailing 60-month window")
    ax.set_ylabel("Standalone sleeve with highest trailing Sharpe")
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="y", alpha=0.08)
    fig.subplots_adjust(left=0.16, right=0.98, bottom=0.18, top=0.98)
    _save(fig, out)


def figure_5(df: pd.DataFrame, out: Path) -> None:
    x = np.arange(len(df))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 3.78), sharey=True, gridspec_kw={"wspace": 0.10})

    # Panel A: full-sample near-optimal region. Endpoints are the observed
    # minimum and maximum sleeve weights among the 100,000 feasible portfolios
    # retaining at least 95% of the full-sample maximum Sharpe.
    for i, r in enumerate(df.itertuples()):
        ax1.vlines(i, r.near95_min, r.near95_max, linewidth=3.0, alpha=0.78)
        ax1.hlines([r.near95_min, r.near95_max], i - 0.09, i + 0.09, linewidth=1.3)
    ax1.scatter(x, df.later_practitioner_weight, marker="D", s=40, label="Practitioner weights", zorder=4)
    ax1.scatter(x, df.full_sample_expost_optimum, marker="x", s=58, linewidths=1.6,
                label="Full-sample ex-post max-Sharpe weights", zorder=5)
    ax1.axhline(0.10, linestyle="--", linewidth=0.9, alpha=0.65)
    ax1.set_xticks(x, df.sleeve)
    ax1.set_ylabel("Sleeve weight")
    ax1.set_title("A. Near-optimal Monte Carlo weight ranges", fontsize=9.4, pad=7)
    ax1.legend(frameon=False, fontsize=6.8, loc="upper right")

    # Panel B: instability of the ex-post optimum. Solid blue capped ranges are
    # block-bootstrap 2.5-97.5 percentiles; dotted orange capped ranges are the
    # observed min-max over trailing 60-month estimation windows. Explicit
    # colors are used so the rendered intervals match the legend. Caps remain
    # visible when a range collapses to a single value (e.g., the 10% floor).
    bootstrap_color = "tab:blue"
    rolling_color = "tab:orange"
    constraint_color = "0.55"
    for i, r in enumerate(df.itertuples()):
        xb = i - 0.07
        xr = i + 0.07
        ax2.vlines(xb, r.bootstrap_q025, r.bootstrap_q975, color=bootstrap_color, linewidth=2.1, alpha=0.85, zorder=3)
        ax2.hlines([r.bootstrap_q025, r.bootstrap_q975], xb - 0.055, xb + 0.055, color=bootstrap_color, linewidth=1.2, zorder=4)
        ax2.vlines(xr, r.rolling_min, r.rolling_max, color=rolling_color, linestyles="dotted", linewidth=2.0, alpha=0.95, zorder=4)
        ax2.hlines([r.rolling_min, r.rolling_max], xr - 0.055, xr + 0.055, color=rolling_color, linewidth=1.2, zorder=5)
    ax2.scatter(x, df.full_sample_expost_optimum, marker="x", s=50, linewidths=1.5,
                color=bootstrap_color, label="Full-sample ex-post optimum", zorder=6)
    # Legend proxies so the interval semantics are explicit without implying a
    # central bootstrap or rolling estimate that is not contained in source data.
    ax2.plot([], [], color=bootstrap_color, linewidth=2.1, label="Bootstrap optimum: 2.5-97.5% range")
    ax2.plot([], [], color=rolling_color, linestyle="dotted", linewidth=2.0, label="Rolling 60-month optimum: min-max")
    ax2.axhline(0.10, color=constraint_color, linestyle="--", linewidth=0.9, alpha=0.75, label="10% minimum weight constraint", zorder=1)
    ax2.set_xticks(x, df.sleeve)
    ax2.set_title("B. Estimated optimum moves", fontsize=9.4, pad=7)
    ax2.legend(frameon=False, fontsize=6.6, loc="upper right")

    for ax in (ax1, ax2):
        ax.set_ylim(0.08, 0.62)
        ticks = np.arange(0.10, 0.61, 0.10)
        ax.set_yticks(ticks)
        ax.set_yticklabels([f"{int(v*100)}%" for v in ticks])
        ax.grid(axis="x", alpha=0.04)

    fig.subplots_adjust(left=0.09, right=0.985, bottom=0.14, top=0.91)
    _save(fig, out)

def figure_6(df: pd.DataFrame, out: Path) -> None:
    d = df.copy()
    d["holding_month"] = pd.to_datetime(d.holding_month)
    order = ["ADAA practitioner weights", "HAA hindsight strongest sleeve", "60/40 SPY/IEF", "SPY"]
    display = {"ADAA practitioner weights": "ADAA (practitioner weights)", "HAA hindsight strongest sleeve": "HAA (full-sample winner)", "60/40 SPY/IEF": "SPY/IEF 60/40", "SPY": "SPY"}
    fig, ax = plt.subplots(figsize=(8.5333, 4.9667))
    for label in order:
        g = d[d.portfolio == label]
        ax.plot(g.holding_month, g.growth_of_1, linewidth=1.6, label=display[label])
    ax.set_ylabel("Growth of $1 (gross)")
    ax.set_xlabel("")
    ax.legend(frameon=False, loc="upper left")
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.subplots_adjust(left=0.11, right=0.98, bottom=0.14, top=0.98)
    _save(fig, out)


def figure_7(df: pd.DataFrame, out: Path) -> None:
    label_map = {
        "ADAA practitioner weights": "ADAA (practitioner weights)",
        "ADAA equal 20%": "ADAA (equal 20%)",
        "HAA hindsight strongest sleeve": "HAA (full-sample winner)",
        "60/40 SPY/IEF": "SPY/IEF 60/40",
        "SPY": "SPY",
    }
    fig, ax = plt.subplots(figsize=(7.88, 4.8967))
    # Publication orientation follows the manuscript: drawdown depth on x,
    # longest underwater spell on y.
    ax.scatter(df.MDD_depth_percent, df.max_underwater_months, s=75)
    offsets = {
        "ADAA practitioner weights": (6, 6), "ADAA equal 20%": (6, -14), "HAA hindsight strongest sleeve": (6, 5),
        "60/40 SPY/IEF": (6, 6), "SPY": (-25, 6),
    }
    for r in df.itertuples():
        lab = label_map.get(r.portfolio, r.portfolio)
        dx, dy = offsets.get(r.portfolio, (5, 5))
        ax.annotate(lab, (r.MDD_depth_percent, r.max_underwater_months), xytext=(dx, dy),
                    textcoords="offset points", fontsize=8.5)
    ax.set_xlabel("Maximum drawdown depth (%)")
    ax.set_ylabel("Longest underwater spell (months)")
    fig.subplots_adjust(left=0.12, right=0.98, bottom=0.15, top=0.98)
    _save(fig, out)

def figure_8(df: pd.DataFrame, out: Path) -> None:
    d = df.copy().iloc[::-1].reset_index(drop=True)
    d["label"] = d["label"].replace({
        "GFC sample window\n2008-06 to 2009-03": "GFC period covered by sample\n2008-06 to 2009-03",
    })
    exploratory = d.selection_basis.str.contains("data-defined diagnostic", case=False, na=False)
    d.loc[exploratory, "label"] = "Exploratory rapid-reversal diagnostic\nmean of 7 flagged one-month outcomes"
    vals = 100 * d.active_return_vs_60_40
    fig, ax = plt.subplots(figsize=(8.4633, 4.9467))
    y = np.arange(len(d))
    bars = ax.barh(y, vals)
    for bar, is_exploratory in zip(bars, exploratory):
        if is_exploratory:
            bar.set_facecolor("0.72")
            bar.set_edgecolor("0.35")
            bar.set_hatch("///")
            bar.set_linewidth(0.8)
    ax.set_yticks(y, d.label)
    ax.set_xlabel("ADAA minus 60/40 return difference (percentage points)")
    ax.set_xlim(min(-5.5, float(vals.min()) - 1.0), max(20.0, float(vals.max()) + 2.0))
    ax.axvline(0, linewidth=0.9)
    for i, v in enumerate(vals):
        if bool(exploratory.iloc[i]) and v < 0:
            x_text, ha = v + 0.30, "left"
        else:
            x_text, ha = v + (0.25 if v >= 0 else -0.25), ("left" if v >= 0 else "right")
        ax.text(x_text, i, f"{v:+.1f} pp", va="center", ha=ha, fontsize=8.5)
    ax.grid(axis="y", alpha=0.05)
    fig.subplots_adjust(left=0.31, right=0.97, bottom=0.16, top=0.98)
    _save(fig, out)


def figure_z1(df: pd.DataFrame, out: Path) -> None:
    names = sorted(set(df.strategy_a).union(df.strategy_b))
    mat = pd.DataFrame(np.eye(len(names)), index=names, columns=names, dtype=float)
    np.fill_diagonal(mat.values, 0.0)
    for r in df.itertuples():
        mat.loc[r.strategy_a, r.strategy_b] = r.primary_decision_distance
        mat.loc[r.strategy_b, r.strategy_a] = r.primary_decision_distance
    fig, ax = plt.subplots(figsize=(10.2633, 9.0867))
    im = ax.imshow(mat.values, vmin=0, vmax=1, cmap="viridis")
    display_names = [n.replace("BAA_Aggressive", "BAA Aggressive").replace("BAA_Balanced", "BAA Balanced") for n in names]
    ax.set_xticks(range(len(names)), display_names, rotation=45, ha="right")
    ax.set_yticks(range(len(names)), display_names)
    for i in range(len(names)):
        for j in range(len(names)):
            val = mat.iat[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=6.2, color="white" if val < 0.42 else "black")
    cbar = fig.colorbar(im, ax=ax, fraction=0.038, pad=0.025)
    cbar.set_label("Pairwise Decision-Space distance")
    fig.subplots_adjust(left=0.10, right=0.92, bottom=0.12, top=0.98)
    _save(fig, out)


def figure_z2(df: pd.DataFrame, out: Path) -> None:
    hist = df.loc[df.historical_2023_set.astype(bool)].iloc[0]
    best = df.iloc[0]
    fig, ax = plt.subplots(figsize=(8.70, 5.4833))
    ax.hist(df.mean_decision_distance, bins=32)
    ax.axvline(hist.mean_decision_distance, linestyle="--", linewidth=1.25,
               label=f"2023 portfolio (rank {int(hist['rank']):,}/{len(df):,})")
    ax.axvline(best.mean_decision_distance, linestyle=":", linewidth=1.25,
               label="Highest-diversity combination")
    ax.set_xlabel("Average Decision-Space score")
    ax.set_ylabel("Number of five-rule combinations")
    ax.legend(frameon=False, fontsize=8.0, loc="upper left")
    fig.subplots_adjust(left=0.11, right=0.98, bottom=0.14, top=0.98)
    _save(fig, out)


def figure_fx1(df: pd.DataFrame, out: Path) -> None:
    d = df[df.base_return_path == "gross_underlying"].copy()
    d["holding_month"] = pd.to_datetime(d.holding_month)
    labels = {
        "fully_hedged_proxy": "Hedged proxy",
        "fixed_50_unhedged": "Fixed 50% unhedged",
        "fully_unhedged": "Fully unhedged",
        "legacy_dynamic_90_50_10": "Historical dynamic 90/50/10",
    }
    fig, ax = plt.subplots(figsize=(9.0833, 5.73))
    for variant, label in labels.items():
        g = d[d.variant == variant].sort_values("holding_month")
        wealth = (1.0 + g.portfolio_return).cumprod()
        ax.plot(g.holding_month, wealth, linewidth=1.5, label=label)
    ax.set_yscale("log")
    ax.set_ylabel("Wealth index (initial value = 1, log scale)")
    ax.set_xlabel("")
    ax.legend(frameon=False, loc="upper left")
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    # The execution caveat is stated in the manuscript caption, not duplicated inside the plot.
    fig.subplots_adjust(left=0.11, right=0.98, bottom=0.14, top=0.98)
    _save(fig, out)


def figure_fx2(df: pd.DataFrame, out: Path) -> None:
    d = df[df.base_return_path == "gross_underlying"].copy()
    lows = sorted(d.low_threshold.unique())
    highs = sorted(d.high_threshold.unique())
    cagr = d.pivot(index="low_threshold", columns="high_threshold", values="cagr_improvement_vs_fixed50").loc[lows, highs]
    mdd = d.pivot(index="low_threshold", columns="high_threshold", values="max_drawdown").loc[lows, highs]

    fig, ax = plt.subplots(figsize=(8.50, 5.73))
    im = ax.imshow(100 * cagr.values, aspect="auto", origin="lower", cmap="viridis")
    ax.set_xticks(range(len(highs)), [f"{x:.1f}" for x in highs])
    ax.set_yticks(range(len(lows)), [f"{x:.1f}" for x in lows])
    ax.set_xlabel("High z-score threshold: reduce USD exposure above this level")
    ax.set_ylabel("Low z-score threshold: increase USD exposure below this level")

    for i, low in enumerate(lows):
        for j, high in enumerate(highs):
            depth = 100 * abs(float(mdd.loc[low, high]))
            ax.text(j, i, f"{depth:.1f}%", ha="center", va="center", fontsize=8.1,
                    color="white" if (100 * cagr.loc[low, high]) < (100 * cagr.values).mean() else "black")

    legacy = d[d.is_legacy_rule.astype(bool)].iloc[0]
    li = lows.index(legacy.low_threshold)
    hj = highs.index(legacy.high_threshold)
    from matplotlib.patches import Rectangle
    ax.add_patch(Rectangle((hj - 0.5, li - 0.5), 1, 1, fill=False, linewidth=2.0))
    ax.text(hj, li - 0.36, "Historical", ha="center", va="top", fontsize=7.2, fontweight="bold")

    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.035)
    cbar.set_label("CAGR improvement vs fixed 50% unhedged (percentage points)")
    ax.set_title("Cell text = maximum drawdown depth", fontsize=9.2, pad=7)
    fig.subplots_adjust(left=0.15, right=0.92, bottom=0.17, top=0.91)
    _save(fig, out)


RENDERERS = [figure_1, figure_2, figure_3, figure_4, figure_5, figure_6, figure_7, figure_8,
             figure_z1, figure_z2, figure_fx1, figure_fx2]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=Path(__file__).resolve().parents[2] / "05_Practical_Paper" / "03_Figures")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args()

    source_dir = args.source_dir.resolve()
    output_dir = (args.output_dir or source_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for (exhibit, (src_name, out_name)), renderer in zip(FIGURES.items(), RENDERERS):
        src = source_dir / src_name
        if not src.exists():
            raise FileNotFoundError(src)
        df = pd.read_csv(src)
        out_base = output_dir / out_name
        renderer(df, out_base)
        png = Path(str(out_base) + ".png")
        svg = Path(str(out_base) + ".svg")
        rows.append({
            "exhibit": exhibit,
            "source_data": src_name,
            "source_sha256": sha256(src),
            "render_script": Path(__file__).name,
            "publication_png": png.name,
            "png_sha256": sha256(png),
            "publication_svg": svg.name,
            "svg_sha256": sha256(svg),
        })

    manifest = args.manifest or (output_dir / "EXACT_FIGURE_RENDER_MANIFEST_v1.1.6.csv")
    pd.DataFrame(rows).to_csv(manifest, index=False)
    print(f"Rendered {len(rows)} figures")
    print(manifest)


if __name__ == "__main__":
    main()
