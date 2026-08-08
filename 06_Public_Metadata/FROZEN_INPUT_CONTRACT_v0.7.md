# Frozen Input Contract — v0.7

## Purpose

The next reconstruction must not call Yahoo, FRED or any other mutable endpoint from the analytical run. Raw acquisitions are frozen first, checksummed and then transformed through versioned code.

## Required tables

### 1. Daily market observations

`contracts/market_observations_schema.csv`

Required concepts:

- `asset_id`: canonical economic asset identifier;
- `series_id`: exact ticker/index/fund series;
- `observation_date`: trading date represented by the value;
- `availability_timestamp`: earliest timestamp at which the observation is usable;
- `adjusted_value`: declared adjusted/total-return-compatible value;
- `source_name` and `retrieval_timestamp`;
- `proxy_role`: primary, pre-inception proxy or none;
- `raw_file_sha256`.

A close observed on date `t` may generate a signal after that close, never a return attributed to the new target on the same bar.

### 2. Macro vintages

`contracts/macro_vintage_schema.csv`

UNRATE must preserve:

- economic observation month;
- first release date;
- value available at first release;
- later vintage date/value when revisions are retained;
- effective signal date under the historical convention.

A current revised FRED series alone is insufficient for a real-time-vintage claim.

### 3. Proxy transition map

`contracts/proxy_transition_schema.csv`

Every splice requires an explicit transition date, economic equivalence rationale, overlap window, return-chain method and audit status. Row-count replacement is prohibited.

### 4. Strategy output ledger

`contracts/strategy_output_schema.csv`

Each monthly output stores the information chain separately:

- observation cutoff;
- macro release cutoff;
- signal timestamp;
- target-weight timestamp;
- effective holding start;
- strategy state;
- asset target weights;
- implementation variant identifier.

## Freeze requirements

- UTC/KST retrieval timestamp;
- raw-file checksum;
- source URL or API identifier;
- transformation code version;
- no silent refresh inside a validated run;
- immutable input manifest for every evidence release.
