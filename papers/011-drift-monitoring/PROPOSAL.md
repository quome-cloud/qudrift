> **Paper 011 proposal — Continuous performance & drift monitoring.** Imported 2026-06-07 from the local
> outline `P9` (`ongoing-papers/papers/09-continuous-performance-monitoring/`). Read with the
> [`ROADMAP.md`](../ROADMAP.md) deltas in mind: **monorepo** — features are `qfire`
> modules, not `haarf-*` crates or spin-out repos — and **confidential-enclave**
> production deployment, validated locally on Ollama via the OpenAI-compatible
> bridge. The threat model, hypotheses, experiments, datasets, and figures below
> are the pre-registered working plan; they are reconciled against the gateway as
> built at the feature-spec (stage 2) and paper-spec (stage 4) gates.

---

# Paper 9 — Continuous Clinical Performance & Autonomy Monitoring for Deployed Agents

**Crate:** `haarf-monitor` · **New dataset:** HAARF-Drift · **Covers:** C1.4, C1.5, C6.6, C5.5 · **Status:** outline

## Abstract

The deployment half of the total-product-lifecycle (HAARF C1.4 continuous performance
monitoring, C1.5 real-world evidence, C6.6 autonomy performance monitoring) is
unaddressed. A clinical agent that was safe at release degrades as practice patterns,
populations, and upstream models drift. We build `haarf-monitor`, a runtime
observability layer that tracks clinical performance, autonomy KPIs, and behavioral
drift over time, raising graduated alerts and feeding real-world evidence back into the
passport (Paper 8). We contribute **HAARF-Drift**, temporal agent-performance streams
with injected drift/degradation, and characterize detection latency vs. false-alarm
trade-offs for clinical monitoring.

## Stakeholders & expert-in-the-loop

To keep post-deployment drift and autonomy monitoring clinically grounded and credible,
this paper is co-developed with experts spanning the bedside, the monitoring pipeline,
and the regulator.

- **Clinical quality-improvement / outcomes lead** — defines which outcome measures
  matter and what magnitude of degradation is clinically meaningful (sets δ).
- **MLOps / ML-observability engineer** — grounds the streaming detectors and monitoring
  pipelines in deployable, memory-bounded runtime practice.
- **Biostatistician** — calibrates detection-latency vs. false-alarm trade-offs (H1) and
  the survival-style time-to-detection analysis under delayed labels.
- **Patient-safety officer** — maps graduated alerts to harm thresholds and the
  log → notify → throttle → halt escalation, owning the safety case.
- **Frontline clinician** — recognizes real-world performance decay at the bedside and
  validates that proxy signals correspond to felt degradation, not noise.
- **Real-world-evidence / pharmacoepidemiology expert** — ensures the RWE pipeline (C1.5)
  reconstructs true effects from lagged, confounded observational streams.
- **Regulatory / post-market-surveillance lead** — aligns continuous monitoring with
  total-product-lifecycle and post-market surveillance expectations (C1.4).
- **Clinical informaticist** — ensures monitored signals map to EHR-derived data and
  authorized-autonomy envelopes the passport actually encodes (D2).

## Problem model

- **D1 Performance drift** — outcome quality declines over time (covariate / label
  shift, upstream model update).
- **D2 Autonomy creep** — the agent acts autonomously more often / on higher-risk
  actions than its authorized level (C6.6, links C6.2).
- **D3 Behavioral anomaly** — sudden shift in tool-use/decision patterns (compromise,
  misconfig) (C5.5).
- **D4 Silent failure** — degradation invisible because no labeled outcomes arrive
  promptly (delayed ground truth).

## Research questions

- **RQ1** What monitoring signals detect clinical performance drift (D1) before harm,
  given delayed/partial labels?
- **RQ2** Can autonomy KPIs detect autonomy creep (D2) against the passport's authorized
  level?
- **RQ3** What unsupervised signals catch behavioral anomalies (D3) when labels are
  absent (D4)?
- **RQ4** How does monitoring sensitivity trade against alert fatigue (links Paper 6)?

## Hypotheses

- **H1** Drift detectors on proxy signals detect injected degradation of size δ within W
  cases at false-alarm rate ≤ α.
- **H2** Autonomy-KPI monitoring flags creep beyond the authorized envelope with ≥ 95%
  recall.
- **H3** Unsupervised behavioral monitoring detects D3 anomalies with detection latency
  ≤ L at FPR ≤ 5% without labels.
- **H4** Coupling monitor alerts to the Paper-6 router keeps clinician alert volume
  within budget.

## Experiments → figures

- **E1 Drift detection (→ Fig 1):** detection latency vs. drift magnitude for
  {CUSUM, ADWIN, conformal, distribution-distance}; ROC.
- **E2 Delayed-label robustness (→ Fig 2):** detection quality vs. label-delay /
  label-fraction (D4).
- **E3 Autonomy KPI (→ Fig 3):** creep detection vs. authorized envelope from passport.
- **E4 Behavioral anomaly (→ Fig 4):** unsupervised detection latency/FPR.
- **E5 Monitoring overhead (→ shared Fig).**

## Datasets

**Public:**
- **MIMIC-IV / eICU** time-stamped — real temporal structure and (lagged) outcomes.
- **Shifts benchmark / WILDS** — documented distribution-shift methodology.
- **Synthea** with time-varying generators — controllable injected drift.

**New — HAARF-Drift (the contribution):**
- Temporal streams of agent decisions + (lagged) outcomes with **injected, labeled
  drift episodes** (covariate, label, upstream-model-update) of known onset/magnitude.
- Autonomy-event streams labeled against an authorized envelope (D2).
- Behavioral-anomaly traces (compromise/misconfig) with onset labels (D3).
  Apache-2.0, synthetic.

## Validation & statistics

- Detection latency + FPR with CIs; ROC/AUC per detector; report operating point.
- Survival-style analysis of time-to-detection vs. drift magnitude.
- RWE pipeline validated by reproducing known injected effects.
- **Threats to validity:** label delay realism, proxy-signal validity (a proxy that
  drifts independently of outcome is a false alarm source — analyzed).

## Rust components (`haarf-monitor`)

- **Streaming detectors:** CUSUM/ADWIN/conformal + distributional distance over decision
  and (lagged) outcome streams; sequential, memory-bounded.
- **Autonomy meter:** compares live autonomy KPIs to the passport's authorized level
  (Paper 8); emits creep alerts.
- **Behavioral baseline:** per-agent tool-use/decision profile; anomaly scoring (links
  Paper 1 C5.5).
- **RWE exporter:** aggregates monitored evidence into the passport + equity reporter
  (Papers 8, 7), feeding lifecycle re-assessment.

## Server / proxy design

- Off-hot-path consumer of the signed audit stream (Paper 2); no added per-call latency
  for the detectors themselves.
- Alerts route through the Paper-6 oversight router (graduated: log → notify →
  throttle-autonomy → halt).

## Metrics

| Metric | Definition | Target |
|---|---|---|
| DDL | Drift detection latency | ≤ W cases |
| FAR | False-alarm rate | ≤ α |
| ACR | Autonomy-creep recall | ≥ 95% |
| BAL | Behavioral-anomaly latency | ≤ L |

## Repo scaffold

```
haarf-monitor/
├── crates/haarf-monitor/           # detectors + autonomy meter + baseline + RWE export
├── dataset/haarf-drift/            # temporal streams + drift/anomaly labels
├── figures/
└── paper/
```
