<div align="center">

<img src="assets/qudrift-logo.svg" alt="qudrift" width="520">

### Off-hot-path drift, autonomy-creep, and behavioral-anomaly monitoring over the signed decision stream

![built with](https://img.shields.io/badge/built_with-Rust-DEA584?logo=rust&logoColor=white)
![layer](https://img.shields.io/badge/layer-monitor-7c3aed)
![HAARF](https://img.shields.io/badge/HAARF-C1.4/C1.5-0ea5e9)
![paper](https://img.shields.io/badge/paper-preprint-2563eb)
![status](https://img.shields.io/badge/status-research_prototype-orange)
![license](https://img.shields.io/badge/license-Apache_2.0-3FB950)
[![dataset](https://img.shields.io/badge/🤗_dataset-Quome%2Fhaarf--drift-FFD21E)](https://huggingface.co/datasets/Quome/haarf-drift)

[**Quickstart**](#quickstart) · [How it works](#how-it-works) · [Reproduce](#reproduce-the-experiments) · [Results](#headline-results) · [Paper](papers/011-drift-monitoring/main.pdf) · [Dataset](https://huggingface.co/datasets/Quome/haarf-drift) · [Cite](#cite)

</div>

---

A clinical agent that is safe at release does not stay safe: practice patterns shift, an upstream model is swapped, or an attacker reshapes behavior gradually to stay under per-call detectors, and labeled outcomes arrive late or never. qfire monitor consumes the signed decision stream off the hot path and runs sequential, memory-bounded detectors for performance drift (CUSUM, ADWIN, conformal martingale, distributional distance), autonomy creep against an authorized envelope, and label-free behavioral anomaly, feeding a graduated log/notify/throttle/halt alert ladder. On HAARF-Drift (168 synthetic streams of 1000 cases with labeled injected episodes), no single drift detector dominates: CUSUM detects 54/54 onsets within 1.0 to 8.1 cases (ROC AUC 1.00) while ADWIN detects 36/54 (AUC 0.83); autonomy creep is caught at 1.00 recall and 0.00 false alarms, and the unsupervised behavioral monitor reaches 1.00 recall at 0.00 FPR with no labels, exactly where outcome-based detection degrades (0.72 to 0.56 under sparse labels).

`qudrift` is **a module of the QUOKKAGUARD program**: one Rust security gateway (`qfire`) that sits in front of any OpenAI-compatible model endpoint and decides **ALLOW ▸ forward · BLOCK ▸ refuse · ESCALATE ▸ human review** for every request and response. Each module adds exactly one enforcement layer to that gateway plus one adversarial dataset and one paper. This repository is a self-contained snapshot of the gateway with **this layer** (`src/monitor/`, on the *monitor* path, HAARF control C1.4/C1.5), its dataset (**HAARF-Drift**), the experiment harness, and the paper.

> Everything here runs **offline**: no model API keys, no network calls in the experiments.

## How it works

- **Read-side MonitorEvent stream** - each event is the quledger signed audit record (timestamp, terminal verdict, max detector score) joined out of band with a possibly-lagged clinical outcome, the action's autonomy level/risk tier, and the agent identity and tool invoked; the monitor never touches the request path, so it adds zero per-call latency.
- **Four complementary drift detectors** behind one `observe(case, x) -> Option<DriftSignal>` interface: CUSUM (two-sided cumulative sums with slack k and threshold h, O(1)), ADWIN (exponential-histogram adaptive window shrunk on a Hoeffding-bounded mean difference, O(log n) buckets), a conformal martingale (bets on conformal p-values, false-alarm rate bounded by alpha via Ville's inequality), and distributional distance (PSI or Kolmogorov-Smirnov between a reference histogram and a sliding window).
- **Autonomy meter** - checks each action against an `AutonomyEnvelope` (max autonomous risk tier, max autonomous fraction over a window, modeling the qupassport regulatory passport); an autonomous action above the authorized tier is flagged immediately and sustained autonomous-fraction creep is flagged over the window.
- **Unsupervised behavioral baseline** - a per-agent categorical tool-use profile is learned over a warmup window and a sliding window is scored against it by population-stability divergence; a previously-unseen tool is a strong signal, and no labels are used.
- **Graduated alert ladder and RWE export** - detector severity maps to log -> notify -> throttle -> halt, with only the clinician-facing levels counted against an alert-fatigue budget (the seam to the qutriage oversight router); a real-world-evidence exporter feeds the passport and equity reporter.

## Quickstart

Requires Rust 1.85+ (`rustup`), Python 3.10+ for the analysis scripts, and `tectonic` (or `pdflatex`) only if you want to rebuild the paper.

```bash
git clone https://github.com/quome-cloud/qudrift
cd qudrift
cargo build --release
cargo test --lib monitor:: --test monitor_integration   # this layer's tests
```

Then see the layer in action:

```bash
# HAARF-Drift streams are gitignored -- regenerate them (seed 42, needs numpy, seconds):
python3 scripts/011-drift-monitoring/gen_drift.py
# wrote 168 streams to datasets/011-drift-monitoring

# Replay one injected-drift stream (label shift, delta 0.45) through the monitor with CUSUM (offline):
./target/release/qfire monitor --stream datasets/011-drift-monitoring/drift/label_large_0.jsonl --detector cusum
# [<level>] case <n> drift (...)        <- one line per alert, then the ladder summary:
# — 1000 events, <k> alerts (<m> clinician-facing) via cusum

# A clean stream stays silent:
./target/release/qfire monitor --stream datasets/011-drift-monitoring/drift/clean_0.jsonl --detector cusum
# — 1000 events, 0 alerts (0 clinician-facing) via cusum
# (--detector accepts cusum | adwin | conformal | distdistance; add --json for machine-readable output)

# Score all five experiments -> results/011-drift-monitoring/e{1..5}_*.json (offline, deterministic):
./target/release/driftbench --data datasets/011-drift-monitoring --out results/011-drift-monitoring --exp all
python3 scripts/011-drift-monitoring/summarize.py   # CIs, ROC/AUC, figures -> papers/011-drift-monitoring/figs/
```

## Reproduce the experiments

Every number in the paper traces to one of these runs (95% Wilson CIs, deterministic seeds, pinned model snapshots). Run outputs land in `results/011-drift-monitoring/` (not tracked; see [`results/011-drift-monitoring/README.md`](results/011-drift-monitoring/README.md) for the exact regeneration commands).

| Exp | What it measures | Needs |
|---|---|---|
| E1 | Drift detection: detection rate, latency vs magnitude, and ROC/AUC for CUSUM, ADWIN, conformal, and distributional distance over 54 onset + 18 clean streams | offline |
| E2 | Delayed and partial labels (D4): outcome-CUSUM detection rate and latency vs label delay and label fraction | offline |
| E3 | Autonomy creep: recall, false-alarm rate, and latency of the autonomy meter across authorized envelopes | offline |
| E4 | Unsupervised behavioral anomaly: recall vs false-positive rate as the baseline threshold sweeps | offline |
| E5 | Monitoring overhead: per-event cost and resident state per detector over 72,000 events | offline |
| all | E1-E5 in one pass, then Wilson/bootstrap CIs, ROC/AUC, and the six figures | offline |

```bash
# E1 — Drift detection: detection rate, latency vs magnitude, and ROC/AUC for CUSUM, ADWIN, conformal, and distributional distance over 54 onset + 18 clean streams
cargo run --release --bin driftbench -- --data datasets/011-drift-monitoring --out results/011-drift-monitoring --exp e1

# E2 — Delayed and partial labels (D4): outcome-CUSUM detection rate and latency vs label delay and label fraction
cargo run --release --bin driftbench -- --data datasets/011-drift-monitoring --out results/011-drift-monitoring --exp e2

# E3 — Autonomy creep: recall, false-alarm rate, and latency of the autonomy meter across authorized envelopes
cargo run --release --bin driftbench -- --data datasets/011-drift-monitoring --out results/011-drift-monitoring --exp e3

# E4 — Unsupervised behavioral anomaly: recall vs false-positive rate as the baseline threshold sweeps
cargo run --release --bin driftbench -- --data datasets/011-drift-monitoring --out results/011-drift-monitoring --exp e4

# E5 — Monitoring overhead: per-event cost and resident state per detector over 72,000 events
cargo run --release --bin driftbench -- --data datasets/011-drift-monitoring --out results/011-drift-monitoring --exp e5

# all — E1-E5 in one pass, then Wilson/bootstrap CIs, ROC/AUC, and the six figures
cargo run --release --bin driftbench -- --exp all
python3 scripts/011-drift-monitoring/summarize.py
```

**Dataset — HAARF-Drift** (`datasets/011-drift-monitoring/`): 168 fully synthetic, deterministic (seed 42) temporal agent-decision streams of 1000 MonitorEvents each: 54 drift-onset + 18 clean streams (covariate, label, and model-update shift at delta 0.10/0.25/0.45 with a labeled onset t0), 24 autonomy-creep + 24 clean, and 24 behavioral-anomaly (unseen exfiltrate tool) + 24 clean, with a labels.jsonl sidecar; the streams are gitignored and regenerable, only the README and generator are tracked.

Regenerate the corpus (deterministic seeds):

```bash
python3 scripts/011-drift-monitoring/gen_drift.py   # default --per 6 --seed 42 --out datasets/011-drift-monitoring
```

The corpus is also published as a Hugging Face dataset with a full data card: **[Quome/haarf-drift](https://huggingface.co/datasets/Quome/haarf-drift)** (`datasets.load_dataset("Quome/haarf-drift")`, or `hf download Quome/haarf-drift --repo-type dataset`).

All data are synthetic; no protected health information is used anywhere in this repository.

## Headline results

| Metric | Value | Context |
|---|---|---|
| Drift detection rate and ROC AUC per detector (E1) | **CUSUM 54/54, AUC 1.00; conformal 54/54, AUC 1.00; distance 54/54, AUC 1.00; ADWIN 36/54, AUC 0.83** | no single detector dominates; ADWIN's Hoeffding bound misses the smallest magnitude |
| CUSUM mean detection latency, small to large drift (E1) | **8.1 -> 2.2 -> 1.0 cases** | delta 0.10 / 0.25 / 0.45; distance 15.0 -> 5.7; conformal steady near 19; ADWIN 115.2 at medium delta |
| Outcome-based detection under delayed/partial labels (E2) | **recall 0.72 at latency 60 cases (full labels) -> 0.56 at 20% labels; latency up to 364 cases** | false-alarm rate <= 0.056; recall caps at 0.72 because covariate drift does not move outcomes |
| Autonomy-creep recall / false-alarm rate (E3) | **1.00 / 0.00, latency 0.2 cases** | envelopes with max autonomous fraction 0.4 to 0.7 |
| Unsupervised behavioral anomaly recall / FPR (E4) | **1.00 / 0.00 at operating threshold 0.5, latency 14.8 cases** | no labels; FPR is zero for any threshold >= 0.35, rises to ~0.42 at 0.2 |
| Per-event monitoring cost (E5) | **CUSUM 0.007 us, conformal 0.034 us, ADWIN 0.19 us, distance 0.22 us** | over 72,000 events; ADWIN state bounded at 53 buckets; never on the request path |

Full methodology, ablations, and statistics: **[the paper](papers/011-drift-monitoring/main.pdf)**.

## The paper

**Watching the Deployment, Not the Call: Continuous Performance and Drift Monitoring for Deployed Clinical Agents**

- PDF: [`papers/011-drift-monitoring/main.pdf`](papers/011-drift-monitoring/main.pdf)
- Source: [`papers/011-drift-monitoring/`](papers/011-drift-monitoring/) — `main.tex`, `numbers.tex` (every headline macro, generated by the scripts above), `figs/`, `refs.bib`
- Pre-registered proposal (threat model, hypotheses, experiment→figure map): [`papers/011-drift-monitoring/PROPOSAL.md`](papers/011-drift-monitoring/PROPOSAL.md)
- Rebuild: `cd papers/011-drift-monitoring && make paper` (tectonic, or pdflatex + bibtex)

## Repository layout

| Path | What |
|---|---|
| `src/` | The `qfire` gateway crate. This paper's layer lives in `src/monitor/`; the other modules are the always-on baseline it plugs into. |
| `src/bin/` | CLI (`qfire`) and per-paper experiment harnesses |
| `rules/`, `chains/` | Declarative rule and detector-chain library used by the gateway |
| `datasets/011-drift-monitoring/` | HAARF-Drift (also on Hugging Face: [Quome/haarf-drift](https://huggingface.co/datasets/Quome/haarf-drift)) |
| `scripts/011-drift-monitoring/` | Dataset generator, experiment runners, figure and `numbers.tex` builders |
| `scripts/common/` | Shared helpers |
| `papers/011-drift-monitoring/` | The paper (LaTeX + PDF + proposal) |
| `results/011-drift-monitoring/` | Experiment outputs (see above) |
| `tests/`, `benches/` | Integration tests and Criterion benches |
| `SNAPSHOT.md` | Which `quokkaguard` commit this repo was exported from |

## Relationship to QUOKKAGUARD

This repo is a **snapshot** of the QUOKKAGUARD program's gateway (export `1c04c3a34841`, 2026-10-02), filtered to the `qudrift` module. The full `qfire` crate is included so this layer builds, tests, and runs standalone; the other modules are the always-on baseline the layer plugs into. Issues and pull requests are welcome here.

This layer builds on: [quanchor](https://github.com/quome-cloud/quanchor), [quledger](https://github.com/quome-cloud/quledger).

Sibling repos in the series: [quanchor](https://github.com/quome-cloud/quanchor), [quledger](https://github.com/quome-cloud/quledger), [qubom](https://github.com/quome-cloud/qubom), [quwarden](https://github.com/quome-cloud/quwarden), [qudam](https://github.com/quome-cloud/qudam), [quantidote](https://github.com/quome-cloud/quantidote), [quorum](https://github.com/quome-cloud/quorum), [qutriage](https://github.com/quome-cloud/qutriage), [qufair](https://github.com/quome-cloud/qufair), [qupassport](https://github.com/quome-cloud/qupassport), [quconsent](https://github.com/quome-cloud/quconsent), [qubroker](https://github.com/quome-cloud/qubroker), [qusiege](https://github.com/quome-cloud/qusiege).

## Cite

If you use this code or dataset, cite the paper and the HAARF framework it implements:

```bibtex
@unpublished{schwoebel2026qudrift,
  author = {Schwoebel, Jim and {QUOKKAGUARD Contributors}},
  title  = {Watching the Deployment, Not the Call: Continuous Performance and Drift Monitoring for Deployed Clinical Agents},
  note   = {Preprint. Quome, QUOKKAGUARD program (qudrift module)},
  year   = {2026},
  url    = {https://github.com/quome-cloud/qudrift}
}

@unpublished{schwoebel2026haarf,
  author = {Schwoebel, Jim and Frasch, Martin and Spalding, Art and Sewell, Ed and Englert, Phil and Halpert, Ben and Overbay, Collin and Semenec, Ingrida and Shor, Joel},
  title  = {{HAARF}: Healthcare {AI} agents regulatory framework --- a comprehensive security verification standard for autonomous {AI} systems in clinical environments},
  note   = {medRxiv Preprint},
  year   = {2026},
  month  = {April},
  doi    = {10.64898/2026.04.09.26350519},
  url    = {https://www.medrxiv.org/content/10.64898/2026.04.09.26350519v1}
}
```

## Status

Research prototype. It demonstrates the layer end to end with reproducible experiments; it is not a certified medical device or a production security product. Threat-model boundaries and known gaps are in the paper's Discussion.

## License

Apache License 2.0 — see [LICENSE](LICENSE). Copyright (c) 2026 Quome, Inc.
