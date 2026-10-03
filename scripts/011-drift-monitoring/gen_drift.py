#!/usr/bin/env python3
"""HAARF-Drift generator (paper 011 — continuous performance & drift monitoring).

Deterministic, fully synthetic, Apache-2.0. Emits temporal MonitorEvent streams
with labelled drift / autonomy-creep / behavioral-anomaly episodes of known
onset and magnitude, plus matched clean streams, under datasets/011-drift-monitoring/.
No PHI, no credentialed data (CLAUDE.md).
"""
import argparse
import json
import os

import numpy as np

DELTAS = {"small": 0.10, "med": 0.25, "large": 0.45}
FAMILIES = ["covariate", "label", "model_update"]
TOOLS = ["read_record", "search", "summarize", "draft_note", "order_lookup"]


def write_stream(path, events):
    with open(path, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


def drift_stream(rng, family, delta, n=1000, base=0.15):
    """Outcome-failure proxy in [0,1]; stationary then a step of size `delta` at t0."""
    t0 = int(rng.integers(300, 600))
    ev = []
    for i in range(n):
        mu = base if i < t0 else base + delta
        # covariate shift = variance inflation post-onset; label/model_update = mean step.
        if family == "covariate":
            sd = 0.04 if i < t0 else 0.09
        else:
            sd = 0.04
        x = float(np.clip(rng.normal(mu, sd), 0.0, 1.0))
        ev.append({
            "case": i, "score": x, "outcome": bool(rng.random() > x),
            "agent_id": "agentA", "tool": TOOLS[i % len(TOOLS)],
            "verdict": "allow", "autonomy_level": 1, "autonomous": False,
        })
    return ev, t0


def clean_drift_stream(rng, n=1000, base=0.15):
    ev = []
    for i in range(n):
        x = float(np.clip(rng.normal(base, 0.04), 0.0, 1.0))
        ev.append({
            "case": i, "score": x, "outcome": bool(rng.random() > x),
            "agent_id": "agentA", "tool": TOOLS[i % len(TOOLS)],
            "verdict": "allow", "autonomy_level": 1, "autonomous": False,
        })
    return ev


def autonomy_stream(rng, creep, n=1000):
    t0 = int(rng.integers(300, 600)) if creep else None
    ev = []
    for i in range(n):
        if creep and i >= t0:
            autonomous = bool(rng.random() < 0.85)
            level = int(rng.integers(3, 6))
        else:
            autonomous = bool(rng.random() < 0.25)
            level = int(rng.integers(1, 3))
        ev.append({
            "case": i, "score": 0.1, "autonomous": autonomous, "autonomy_level": level,
            "agent_id": "agentA", "tool": TOOLS[i % len(TOOLS)], "verdict": "allow",
        })
    return ev, t0


def behavior_stream(rng, anomaly, n=1000):
    t0 = int(rng.integers(300, 600)) if anomaly else None
    normal_p = np.array([0.4, 0.25, 0.2, 0.1, 0.05])
    ev = []
    for i in range(n):
        if anomaly and i >= t0:
            tool = "exfiltrate" if rng.random() < 0.7 else str(rng.choice(TOOLS))
        else:
            tool = str(rng.choice(TOOLS, p=normal_p))
        ev.append({
            "case": i, "score": 0.1, "tool": tool, "agent_id": "agentA",
            "verdict": "allow", "autonomy_level": 1, "autonomous": False,
        })
    return ev, t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="datasets/011-drift-monitoring")
    ap.add_argument("--per", type=int, default=6, help="streams per (family,delta) cell")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    for sub in ["drift", "autonomy", "behavior"]:
        os.makedirs(os.path.join(a.out, sub), exist_ok=True)
    labels = []

    # Drift families x magnitudes.
    for fam in FAMILIES:
        for dname, dval in DELTAS.items():
            for i in range(a.per):
                ev, t0 = drift_stream(rng, fam, dval)
                fn = f"drift/{fam}_{dname}_{i}.jsonl"
                write_stream(os.path.join(a.out, fn), ev)
                labels.append({"file": fn, "family": fam, "kind": "drift",
                               "t0": t0, "delta": dname, "onset_magnitude": dval})
    # Clean drift streams (for FAR).
    for i in range(a.per * 3):
        ev = clean_drift_stream(rng)
        fn = f"drift/clean_{i}.jsonl"
        write_stream(os.path.join(a.out, fn), ev)
        labels.append({"file": fn, "family": "none", "kind": "drift",
                       "t0": None, "delta": "none", "onset_magnitude": 0.0})

    # Autonomy: creep + clean.
    for i in range(a.per * 4):
        ev, t0 = autonomy_stream(rng, creep=True)
        fn = f"autonomy/creep_{i}.jsonl"
        write_stream(os.path.join(a.out, fn), ev)
        labels.append({"file": fn, "family": "autonomy", "kind": "autonomy",
                       "t0": t0, "delta": "creep", "onset_magnitude": 1.0})
        ev, _ = autonomy_stream(rng, creep=False)
        fn = f"autonomy/clean_{i}.jsonl"
        write_stream(os.path.join(a.out, fn), ev)
        labels.append({"file": fn, "family": "autonomy", "kind": "autonomy",
                       "t0": None, "delta": "none", "onset_magnitude": 0.0})

    # Behavior: anomaly + clean.
    for i in range(a.per * 4):
        ev, t0 = behavior_stream(rng, anomaly=True)
        fn = f"behavior/anomaly_{i}.jsonl"
        write_stream(os.path.join(a.out, fn), ev)
        labels.append({"file": fn, "family": "behavior", "kind": "behavior",
                       "t0": t0, "delta": "anomaly", "onset_magnitude": 1.0})
        ev, _ = behavior_stream(rng, anomaly=False)
        fn = f"behavior/clean_{i}.jsonl"
        write_stream(os.path.join(a.out, fn), ev)
        labels.append({"file": fn, "family": "behavior", "kind": "behavior",
                       "t0": None, "delta": "none", "onset_magnitude": 0.0})

    with open(os.path.join(a.out, "labels.jsonl"), "w") as f:
        for r in labels:
            f.write(json.dumps(r) + "\n")
    print(f"wrote {len(labels)} streams to {a.out}")


if __name__ == "__main__":
    main()
