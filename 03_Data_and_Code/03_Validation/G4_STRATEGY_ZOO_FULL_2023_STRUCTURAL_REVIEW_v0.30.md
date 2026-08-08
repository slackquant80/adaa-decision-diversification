# G4 Strategy Zoo — Full Historical 2023 Structural Review v0.30

## Verdict

**STRUCTURAL RECONSTRUCTION PASS / INDEPENDENT R TARGET-WEIGHT VALIDATION OPEN**

This is a falsification-oriented structural challenge, not a performance-selection exercise.

## Full reconstructed historical pool

Sixteen strategies are included over the same 216 signal months (`2008-07` through `2026-06`):

`AAA, ADM, BAA Aggressive, BAA Balanced, DAA, DM, EAA, FAA, GPM, GTAA, KDA, LAA, PAA, QSF, RAA, VAA`.

HAA is excluded from the historical 2023 pool because it is post-2023.

## Frozen selector

The primary selector is unchanged from v0.29. For every strategy pair, it equally averages:

1. normalized target-weight L1 distance;
2. holdings disagreement (`1 - holdings Jaccard`);
3. transition-timing disagreement (`1 - transition Jaccard`).

Obvious fund/proxy aliases are mapped to economic exposure buckets. Strategy performance is not an input.

## Full-pool result

- Rules: **16**
- Five-rule combinations: **4,368**
- Maximum decision-diversity set: **ADM + DM + FAA + LAA + QSF**
- Selected score: **0.894542**
- Historical 2023 ADAA family set: **ADM + BAA Aggressive + BAA Balanced + FAA + LAA**
- Historical score: **0.817137**
- Historical rank: **735 / 4,368**
- Historical percentile under the frozen structural score: **83.2nd percentile**

The historical set is therefore structurally more diverse than most eligible five-rule combinations, but it is **not** the structural optimum and must not be described as algorithmically discovered.

## Strongest anti-assemblage finding

The closest pair in the completed 16-rule pool remains:

**BAA Aggressive + BAA Balanced**

with primary decision-space distance about **0.351**.

This is useful because the 2023 portfolio contained both. A return-free diagnostic therefore identifies a genuine redundancy inside the historical design rather than merely endorsing it.

## What changed when the pool expanded

The 12-rule v0.29 winner was:

`ADM + BAA Aggressive + FAA + LAA + QSF`.

After adding DM, AAA, PAA and KDA, the full-pool winner becomes:

`ADM + DM + FAA + LAA + QSF`.

This is evidence **against** a cosmetic validation exercise. The selector is allowed to disagree with the historical portfolio and does so.

The historical set's score remains exactly the same; only its rank changes as the opportunity set expands.

## Metric sensitivity

Across the predeclared return-free component-weight variants, the historical set ranks between **622 and 1,040** of 4,368 combinations, corresponding roughly to the **76th–86th percentile** range. It remains structurally above the median under every predeclared metric variant but is not uniquely selected.

## Post-2023 exploratory check

Adding HAA as a seventeenth source-family rule is kept separate from the historical challenge. Under the same frozen metric, the current successor **source-family** set (`HAA + BAA Aggressive + ADM + FAA + LAA`) ranks **248 / 6,188**, about the **96.0th percentile**. This is exploratory only. It does not establish the historical reason BAA Balanced was replaced by HAA, and it does not evaluate the final practitioner variants.

## Interpretation boundary

Allowed:
- historical ADAA was a practitioner-selected set with meaningful structural diversity;
- its structural diversity is above most feasible five-rule sets in the completed historical candidate pool;
- the return-free selector detects both useful diversity and historical redundancy;
- three of the five full-pool maximum-diversity families (`ADM`, `FAA`, `LAA`) are also in historical ADAA.

Not allowed:
- historical ADAA was the optimal structural portfolio;
- the algorithm rediscovered all five historical rules;
- the original designer used this algorithm in 2023;
- full Strategy-Zoo structure proves superior future returns.
