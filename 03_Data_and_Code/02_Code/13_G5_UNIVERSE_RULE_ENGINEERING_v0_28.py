#!/usr/bin/env python3
"""ADAA v0.28 — performance-blind universe/rule engineering audit.

Purpose
-------
Connect the source-family Strategy Zoo layer to the actual ADAA practitioner sleeves.
The analysis separates, where feasible:
    P/P = parent rule + parent universe
    P/A = parent rule + ADAA universe/expression
    A/P = ADAA rule + parent universe
    A/A = ADAA rule + ADAA universe

CRITICAL: This script reads target-weight/decision files only. It does not read strategy
returns, CAGR, Sharpe, drawdowns, or other performance outputs. The cross-sleeve comparison
reuses the frozen v0.27 Decision-Space metric without alteration.
"""
from pathlib import Path
import itertools
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '03_Data_and_Code' / '04_Outputs'
FIG = ROOT / '05_Practical_Paper' / '03_Figures'
TAB = ROOT / '05_Practical_Paper' / '04_Tables'
TOL = 1e-10
START = '2008-07'
END = '2026-06'

BUCKET = {
    'SPY':'US_BROAD_EQ','VTI':'US_BROAD_EQ','VFINX':'US_BROAD_EQ',
    'QQQ':'US_TECH_EQ','IWM':'US_SMALL_EQ','IWN':'US_SMALL_VALUE_EQ','IWD':'US_VALUE_EQ',
    'EFA':'DEV_EXUS_EQ','VEA':'DEV_EXUS_EQ','VGK':'EUROPE_EQ','EWJ':'JAPAN_EQ',
    'EEM':'EM_EQ','VWO':'EM_EQ','EWY':'KOREA_EQ',
    'VINEX':'EXUS_SMALL_EQ','VSS':'EXUS_SMALL_EQ','OSMAX':'EXUS_SMALL_EQ',
    'VNQ':'US_REIT','GLD':'GOLD','DBC':'COMMODITY','GSG':'COMMODITY',
    'HYG':'HY_BOND','LQD':'IG_CORP_BOND','TLT':'LONG_TSY','VUSTX':'LONG_TSY',
    'IEF':'INTERMEDIATE_TSY','SHY':'SHORT_TSY','BIL':'TBILL',
    'AGG':'AGG_BOND','BND':'AGG_BOND','TIP':'TIPS','CASH':'CASH'
}


def load(fn):
    d = pd.read_csv(OUT / fn)
    d['signal_month'] = d['signal_month'].astype(str)
    d = d.set_index('signal_month').astype(float)
    return d.loc[(d.index >= START) & (d.index <= END)]


def to_buckets(w):
    z = pd.DataFrame(index=w.index)
    for c in w.columns:
        b = BUCKET.get(c, c)
        if b in z.columns:
            z[b] = z[b] + w[c]
        else:
            z[b] = w[c]
    return z


def pair_metrics(a, b):
    idx = a.index.intersection(b.index)
    A = to_buckets(a.loc[idx])
    B = to_buckets(b.loc[idx])
    cols = sorted(set(A.columns) | set(B.columns))
    A = A.reindex(columns=cols, fill_value=0.0)
    B = B.reindex(columns=cols, fill_value=0.0)

    l1_raw = np.abs(A.values - B.values).sum(axis=1)
    normalized_l1 = float(np.mean(l1_raw) / 2.0)

    hj = []
    for i in range(len(idx)):
        sa = set(np.array(cols)[A.iloc[i].values > TOL])
        sb = set(np.array(cols)[B.iloc[i].values > TOL])
        hj.append(len(sa & sb) / len(sa | sb) if (sa | sb) else 1.0)
    holdings_disagreement = float(1.0 - np.mean(hj))

    ca = np.abs(np.diff(A.values, axis=0)).sum(axis=1) > TOL
    cb = np.abs(np.diff(B.values, axis=0)).sum(axis=1) > TOL
    union = np.logical_or(ca, cb).sum()
    inter = np.logical_and(ca, cb).sum()
    tj = float(inter / union) if union else 1.0
    timing_disagreement = 1.0 - tj
    primary = float(np.mean([normalized_l1, holdings_disagreement, timing_disagreement]))
    return {
        'n_months': len(idx),
        'mean_L1_target_weight_distance': float(np.mean(l1_raw)),
        'normalized_L1_distance': normalized_l1,
        'mean_holdings_jaccard': float(np.mean(hj)),
        'holdings_disagreement': holdings_disagreement,
        'transition_jaccard': tj,
        'transition_timing_disagreement': timing_disagreement,
        'primary_decision_distance': primary,
    }


def set_geometry(mats, label):
    rows = []
    ds = []
    for a, b in itertools.combinations(mats.keys(), 2):
        m = pair_metrics(mats[a], mats[b])
        m.update({'architecture': label, 'strategy_a': a, 'strategy_b': b})
        rows.append(m)
        ds.append(m['primary_decision_distance'])
    return rows, {
        'architecture': label,
        'n_strategies': len(mats),
        'n_pairs': len(ds),
        'mean_primary_decision_distance': float(np.mean(ds)),
        'min_pair_decision_distance': float(np.min(ds)),
        'max_pair_decision_distance': float(np.max(ds)),
    }


def main():
    effects = pd.read_csv(OUT / 'G5_PARENT_VARIANT_DECISION_EFFECTS_v0_16.csv')

    # Universe-only rows for the accessible main-text diagnostic.
    universe_ids = [
        'HAA_universe_effect_parent_rule',
        'BAA_Agg_proxy_expression',
        'FAA_universe_effect_parent_rule',
        'LAA_equity_expression_parent_rule',
    ]
    uni = effects.loc[effects['experiment'].isin(universe_ids)].copy()
    name_map = {
        'HAA_universe_effect_parent_rule':'HAA',
        'BAA_Agg_proxy_expression':'BAA Aggressive',
        'FAA_universe_effect_parent_rule':'FAA',
        'LAA_equity_expression_parent_rule':'LAA',
    }
    uni['sleeve'] = uni['experiment'].map(name_map)
    uni['timing_agreement'] = uni['semantic_transition_jaccard']
    uni['decision_displacement'] = uni['semantic_mean_L1']
    uni['effective_n_change'] = uni['semantic_mean_effective_n_b'] - uni['semantic_mean_effective_n_a']
    uni_out = uni[[
        'sleeve','decision_displacement','timing_agreement','effective_n_change',
        'semantic_identical_weight_rate','semantic_mean_holdings_jaccard',
        'semantic_change_rate_a','semantic_change_rate_b'
    ]].sort_values('decision_displacement')
    uni_out.to_csv(OUT / 'G5_UNIVERSE_ONLY_DECISION_EFFECTS_v0_28.csv', index=False)
    uni_out.to_csv(FIG / 'FIGURE_8_SOURCE_DATA_v0.28.csv', index=False)

    # Explicit engineering audit table; no forced 2x2 for structurally incompatible ADM.
    rows = []
    def row(exp, sleeve, lever, verdict, note):
        r = effects.loc[effects['experiment'].eq(exp)].iloc[0]
        rows.append({
            'sleeve': sleeve,
            'comparison': exp,
            'engineering_lever': lever,
            'semantic_mean_L1': r['semantic_mean_L1'],
            'semantic_identical_weight_rate': r['semantic_identical_weight_rate'],
            'semantic_holdings_jaccard': r['semantic_mean_holdings_jaccard'],
            'semantic_transition_jaccard': r['semantic_transition_jaccard'],
            'effective_n_from': r['semantic_mean_effective_n_a'],
            'effective_n_to': r['semantic_mean_effective_n_b'],
            'verdict': verdict,
            'interpretation': note,
        })
    row('HAA_universe_effect_parent_rule','HAA','universe','MATERIAL',
        'Wider universe changes holdings and transition behavior even with the parent rule held fixed.')
    row('HAA_rule_effect_ADAA_universe','HAA','rule/selection','MATERIAL',
        'Top-N/replacement changes remain material after the universe is fixed to the ADAA expression.')
    row('BAA_Agg_proxy_expression','BAA Aggressive','investable expression','ROLE-PRESERVING / NON-NEUTRAL',
        'The rule architecture largely survives, but ETF expression changes some regime decisions.')
    row('BAA_Agg_current_vs_parent_rule_proxy','BAA Aggressive','residual rule drift','NONE',
        'Current sleeve matches the parent rule exactly once expressed through the ADAA proxy set.')
    row('ADM_parent_to_ADAA','ADM','rule + universe','MAJOR REDESIGN',
        'A mechanically clean 2x2 is not meaningful; the narrow parent and broad Top-6 ADAA architecture are different designs.')
    row('FAA_universe_effect_parent_rule','FAA','universe','MATERIAL',
        'Universe expansion materially changes decisions even before the ADAA rule changes are applied.')
    row('FAA_rule_effect_ADAA_universe','FAA','rule/selection','MATERIAL',
        'Signal and Top-N changes materially alter the already-expanded universe implementation.')
    row('LAA_equity_expression_parent_rule','LAA','persistent equity expression','ROLE-PRESERVING',
        'Holdings change while the transition clock is exactly preserved under the parent timing rule.')
    row('LAA_timing_effect_ADAA_equity','LAA','timing/information policy','SMALL',
        'Timing-policy drift changes very few monthly target states; the persistent role remains intact.')
    eng = pd.DataFrame(rows)
    eng.to_csv(OUT / 'G5_RULE_UNIVERSE_ENGINEERING_DECOMPOSITION_v0_28.csv', index=False)
    eng.to_csv(TAB / 'TABLE_4_PANEL_A_SOURCE_DATA_v0.28.csv', index=False)

    # Frozen v0.27 metric applied to source families and practitioner expressions.
    source_2023 = {
        'BAA Aggressive': load('G5_BAA_AGGRESSIVE_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv'),
        'BAA Balanced': load('G5_BAA_BALANCED_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv'),
        'ADM': load('G5_ADM_PARENT_VINEX_TARGET_WEIGHTS_R_v0_15.csv'),
        'FAA': load('G5_FAA_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv'),
        'LAA': load('G5_LAA_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv'),
    }
    practitioner_2023_like = {
        'BAA Aggressive': load('G2_BAA_AGGRESSIVE_TARGET_WEIGHTS_R_v0_11_1.csv'),
        'BAA Balanced': load('G5_BAA_BALANCED_ADAA_PROXY_EXPRESSION_TARGET_WEIGHTS_R_v0_15.csv'),
        'ADM': load('G2_ADM_TARGET_WEIGHTS_R_v0_11_1.csv'),
        'FAA': load('G3_FAA_CANONICAL_PEER_ONLY_EXACTN_TARGET_WEIGHTS_R_v0_16.csv'),
        'LAA': load('G2_LAA_CARRY_CALENDAR_TARGET_WEIGHTS_v0_11.csv'),
    }
    source_successor = {
        'HAA': load('G5_HAA_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv'),
        'BAA Aggressive': source_2023['BAA Aggressive'],
        'ADM': source_2023['ADM'],
        'FAA': source_2023['FAA'],
        'LAA': source_2023['LAA'],
    }
    current_successor = {
        'HAA': load('G2_HAA_TARGET_WEIGHTS_R_v0_11_1.csv'),
        'BAA Aggressive': practitioner_2023_like['BAA Aggressive'],
        'ADM': practitioner_2023_like['ADM'],
        'FAA': practitioner_2023_like['FAA'],
        'LAA': practitioner_2023_like['LAA'],
    }

    pair_rows = []
    summaries = []
    for mats, label in [
        (source_2023, '2023 selected source-family parents'),
        (practitioner_2023_like, '2023-family practitioner expressions (research-standard)'),
        (source_successor, 'successor source-family parents'),
        (current_successor, 'current successor ADAA variants'),
    ]:
        p, s = set_geometry(mats, label)
        pair_rows.extend(p)
        summaries.append(s)
    pairdf = pd.DataFrame(pair_rows)
    sumdf = pd.DataFrame(summaries)

    # Engineering-delta rows.
    def add_delta(from_label, to_label, comparison):
        a = sumdf.loc[sumdf.architecture.eq(from_label)].iloc[0]
        b = sumdf.loc[sumdf.architecture.eq(to_label)].iloc[0]
        return {
            'comparison': comparison,
            'source_mean_decision_distance': a['mean_primary_decision_distance'],
            'variant_mean_decision_distance': b['mean_primary_decision_distance'],
            'relative_change_pct': 100.0 * (b['mean_primary_decision_distance'] / a['mean_primary_decision_distance'] - 1.0),
            'source_min_pair_distance': a['min_pair_decision_distance'],
            'variant_min_pair_distance': b['min_pair_decision_distance'],
        }
    trade = pd.DataFrame([
        add_delta('2023 selected source-family parents','2023-family practitioner expressions (research-standard)',
                  '2023 selected families: source parents -> practitioner expressions'),
        add_delta('successor source-family parents','current successor ADAA variants',
                  'successor families: source parents -> current ADAA variants'),
    ])
    pairdf.to_csv(OUT / 'G5_PARENT_VS_VARIANT_CROSS_SLEEVE_DECISION_GEOMETRY_v0_28.csv', index=False)
    sumdf.to_csv(OUT / 'G5_PARENT_VS_VARIANT_ARCHITECTURE_SUMMARY_v0_28.csv', index=False)
    trade.to_csv(OUT / 'G5_WITHIN_SLEEVE_VS_BETWEEN_SLEEVE_DIVERSIFICATION_TRADEOFF_v0_28.csv', index=False)
    trade.to_csv(TAB / 'TABLE_4_PANEL_B_SOURCE_DATA_v0.28.csv', index=False)

    record = {
        'version':'v0.28',
        'status':'PERFORMANCE_BLIND_STRUCTURAL_AUDIT_PASS',
        'performance_files_read':False,
        'metric':'frozen v0.27 equal-weight mean of normalized target-weight L1, holdings disagreement, transition-timing disagreement',
        'common_window':[START,END],
        'main_finding':{
            '2023_family_mean_distance_source': float(trade.iloc[0]['source_mean_decision_distance']),
            '2023_family_mean_distance_variant': float(trade.iloc[0]['variant_mean_decision_distance']),
            '2023_relative_change_pct': float(trade.iloc[0]['relative_change_pct']),
            'successor_mean_distance_source': float(trade.iloc[1]['source_mean_decision_distance']),
            'successor_mean_distance_variant': float(trade.iloc[1]['variant_mean_decision_distance']),
            'successor_relative_change_pct': float(trade.iloc[1]['relative_change_pct']),
        },
        'interpretation':'Within-sleeve broadening can improve investability or within-sleeve diversification while simultaneously reducing between-sleeve decision distance. This is a structural trade-off, not a performance verdict.',
        'guardrail':'Do not use this post-hoc structural comparison to rewrite historical motives or reselect sleeves using observed returns.'
    }
    with open(OUT / 'G5_UNIVERSE_RULE_ENGINEERING_RECORD_v0_28.json','w',encoding='utf-8') as f:
        json.dump(record,f,indent=2,ensure_ascii=False)

    print('PASS: v0.28 performance-blind universe/rule engineering audit written.')
    print(f"2023 source->variant mean decision distance: {trade.iloc[0]['source_mean_decision_distance']:.4f} -> {trade.iloc[0]['variant_mean_decision_distance']:.4f} ({trade.iloc[0]['relative_change_pct']:.1f}%)")
    print(f"Successor source->variant mean decision distance: {trade.iloc[1]['source_mean_decision_distance']:.4f} -> {trade.iloc[1]['variant_mean_decision_distance']:.4f} ({trade.iloc[1]['relative_change_pct']:.1f}%)")
    print('No strategy-return or performance input was read.')

if __name__ == '__main__':
    main()
