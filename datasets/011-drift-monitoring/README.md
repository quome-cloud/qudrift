# HAARF-Drift (paper 011 — continuous performance & drift monitoring)

Fully synthetic, deterministic (seed 42), Apache-2.0. No PHI / no credentialed
data. The bulk JSONL streams are **gitignored** (regenerable); only this README
and the generator (`scripts/011-drift-monitoring/gen_drift.py`) are tracked.

## Regenerate

```bash
python3 scripts/011-drift-monitoring/gen_drift.py            # default: --per 6 --seed 42
```

Writes `datasets/011-drift-monitoring/` (168 streams, ~1000 cases each):

| subdir | streams | content |
|---|---|---|
| `drift/` | 54 onset + 18 clean | outcome-failure proxy in [0,1]; families {covariate, label, model_update} × δ {small 0.10, med 0.25, large 0.45}; step at a labelled `t0`. Clean = no onset. |
| `autonomy/` | 24 creep + 24 clean | per-case `autonomous`/`autonomy_level`; creep raises autonomous fraction + risk tier past the envelope at `t0`. |
| `behavior/` | 24 anomaly + 24 clean | per-case `tool`; anomaly injects an abrupt tool-distribution shift (a previously-unseen `exfiltrate` tool) at `t0`. |

`labels.jsonl` — one record per stream: `{file, family, kind, t0|null, delta, onset_magnitude}`.

## Event schema (`MonitorEvent`)

```json
{"case": 0, "score": 0.10, "outcome": true, "agent_id": "agentA",
 "tool": "read_record", "verdict": "allow", "autonomy_level": 1, "autonomous": false}
```

`score` is the drift proxy; `outcome` is the (lagged) clinical label;
`autonomous`/`autonomy_level` drive the autonomy meter; `tool`/`agent_id` drive
the behavioral baseline. See the feature spec §3/§7 for the audit-stream join.
