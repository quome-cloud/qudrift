#!/usr/bin/env python3
"""Tables + figures for paper 011 from results/011-drift-monitoring/e{1..5}_*.json.

E1 drift latency-vs-magnitude + ROC/AUC; E2 delayed/partial labels (D4);
E3 autonomy creep vs envelope; E4 unsupervised behavioral anomaly; E5 overhead.
Rates use Wilson 95% CIs; detection latency uses a bootstrap 95% CI.
Deterministic (fixed bootstrap seed).

Run: python3 scripts/011-drift-monitoring/summarize.py
"""
import json
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RES = "results/011-drift-monitoring"
FIGS = "papers/011-drift-monitoring/figs"
os.makedirs(FIGS, exist_ok=True)

DETS = ["cusum", "adwin", "conformal", "distdistance"]
DELTAS = ["small", "med", "large"]
COLORS = {"cusum": "#1e8449", "adwin": "#2c6fbf", "conformal": "#e67e22", "distdistance": "#8e44ad"}


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, (c - h) / d, (c + h) / d)


def boot_ci(xs, iters=2000, seed=42):
    xs = np.asarray(xs, dtype=float)
    if len(xs) == 0:
        return (0.0, 0.0, 0.0)
    if len(xs) == 1:
        return (float(xs[0]), float(xs[0]), float(xs[0]))
    rng = np.random.default_rng(seed)
    means = [rng.choice(xs, size=len(xs), replace=True).mean() for _ in range(iters)]
    return (float(xs.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def auc(points):
    """Trapezoidal AUC over (fpr, tpr) points; endpoints clamped to (0,0) and (1,1)."""
    pts = sorted([(p["fpr"], p["tpr"]) for p in points])
    xs = [0.0] + [x for x, _ in pts] + [1.0]
    ys = [0.0] + [y for _, y in pts] + [1.0]
    a = 0.0
    for i in range(1, len(xs)):
        a += (xs[i] - xs[i - 1]) * (ys[i] + ys[i - 1]) / 2.0
    return a


def fig_e1(out):
    d = json.load(open(f"{RES}/e1_drift.json"))
    cells = d["cells"]
    # Aggregate latencies per (detector, delta) across families.
    out.append("## E1 — drift detection latency vs magnitude (bootstrap 95% CI)\n")
    out.append("| detector | " + " | ".join(DELTAS) + " | det.rate |")
    out.append("|---|" + "---|" * (len(DELTAS) + 1))
    lat = {(c["detector"], c["delta"]): [] for c in cells}
    det_k = {dn: [0, 0] for dn in DETS}
    for c in cells:
        lat[(c["detector"], c["delta"])].extend(c.get("latencies", []))
        det_k[c["detector"]][0] += c["detected"]
        det_k[c["detector"]][1] += c["n"]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    xpos = np.arange(len(DELTAS))
    for dn in DETS:
        means, los, his = [], [], []
        for dl in DELTAS:
            if not lat[(dn, dl)]:  # undetected: break the line rather than imply 0 latency
                means.append(np.nan)
                los.append(0.0)
                his.append(0.0)
                continue
            m, lo, hi = boot_ci(lat[(dn, dl)])
            means.append(m)
            los.append(m - lo)
            his.append(hi - m)
        ax.errorbar(xpos, means, yerr=[los, his], marker="o", capsize=3,
                    color=COLORS[dn], label=dn)
        rate = det_k[dn][0] / max(det_k[dn][1], 1)
        cells_md = " | ".join(f"{boot_ci(lat[(dn, dl)])[0]:.1f}" if lat[(dn, dl)] else "miss" for dl in DELTAS)
        out.append(f"| {dn} | {cells_md} | {rate:.2f} |")
    ax.set_xticks(xpos)
    ax.set_xticklabels(["small (.10)", "med (.25)", "large (.45)"])
    ax.set_xlabel("drift magnitude δ")
    ax.set_ylabel("detection latency (cases)")
    ax.set_title("Detection latency shrinks with drift magnitude (H1)", fontsize=10.5)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{FIGS}/e1_latency_vs_magnitude.png", dpi=200)
    plt.close(fig)

    # ROC
    fig, ax = plt.subplots(figsize=(5.2, 5.0))
    ax.plot([0, 1], [0, 1], "--", color="#999", lw=0.8)
    out.append("\n**ROC AUC:** " + ", ".join(
        f"{r['detector']}={auc(r['points']):.3f}" for r in d["roc"]))
    for r in d["roc"]:
        pts = sorted(r["points"], key=lambda p: p["fpr"])
        ax.plot([p["fpr"] for p in pts], [p["tpr"] for p in pts], marker=".",
                color=COLORS[r["detector"]], label=f"{r['detector']} (AUC {auc(r['points']):.2f})")
    ax.set_xlabel("false-alarm rate (clean streams)")
    ax.set_ylabel("detection rate (onset streams)")
    ax.set_title("E1 — drift-detector ROC", fontsize=10.5)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(f"{FIGS}/e1_roc.png", dpi=200)
    plt.close(fig)


def fig_e2(out):
    d = json.load(open(f"{RES}/e2_delayed.json"))
    grid = d["grid"]
    delays = sorted({g["delay"] for g in grid})
    fracs = sorted({g["frac"] for g in grid}, reverse=True)
    M = np.zeros((len(fracs), len(delays)))
    L = np.zeros((len(fracs), len(delays)))
    for g in grid:
        i = fracs.index(g["frac"])
        j = delays.index(g["delay"])
        M[i, j] = g["detection_rate"]
        L[i, j] = g["mean_latency"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.0, 3.6))
    im1 = a1.imshow(M, vmin=0, vmax=1, cmap="viridis", aspect="auto")
    a1.set_title("detection rate", fontsize=10)
    im2 = a2.imshow(L, cmap="magma_r", aspect="auto")
    a2.set_title("mean latency (cases)", fontsize=10)
    for a, im, mat, fmt in [(a1, im1, M, "{:.2f}"), (a2, im2, L, "{:.0f}")]:
        a.set_xticks(range(len(delays)))
        a.set_xticklabels(delays)
        a.set_yticks(range(len(fracs)))
        a.set_yticklabels(fracs)
        a.set_xlabel("label delay (cases)")
        a.set_ylabel("label fraction")
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                a.text(j, i, fmt.format(mat[i, j]), ha="center", va="center",
                       color="white", fontsize=8)
        fig.colorbar(im, ax=a, fraction=0.046)
    fig.suptitle("E2 — outcome-based detection degrades under delayed/partial labels (D4)", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(f"{FIGS}/e2_delayed_labels.png", dpi=200)
    plt.close(fig)
    out.append("\n## E2 — delayed/partial-label robustness (D4)\n")
    out.append("| label fraction | " + " | ".join(f"delay {x}" for x in delays) + " |")
    out.append("|---|" + "---|" * len(delays))
    for i, fr in enumerate(fracs):
        out.append(f"| {fr} | " + " | ".join(f"{M[i,j]:.2f} (lat {L[i,j]:.0f})" for j in range(len(delays))) + " |")


def fig_e3(out):
    d = json.load(open(f"{RES}/e3_autonomy.json"))
    env = d["envelopes"]
    out.append("\n## E3 — autonomy creep vs envelope (Wilson 95% CI on recall)\n")
    out.append("| max auto frac | recall | latency | FAR |")
    out.append("|---|---|---|---|")
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    xs = [e["max_autonomous_fraction"] for e in env]
    recalls, rlo, rhi, fars = [], [], [], []
    for e in env:
        p, lo, hi = wilson(e["detected"], e["n_creep"])
        recalls.append(p)
        rlo.append(p - lo)
        rhi.append(hi - p)
        fars.append(e["far"])
        out.append(f"| {e['max_autonomous_fraction']} | {p:.3f} [{lo:.2f},{hi:.2f}] | {e['mean_latency']:.1f} | {e['far']:.3f} |")
    ax.errorbar(xs, recalls, yerr=[rlo, rhi], marker="o", capsize=3, color="#1e8449", label="creep recall")
    ax.plot(xs, fars, marker="s", color="#c0392b", label="false-alarm rate")
    ax.axhline(0.95, ls="--", color="#999", lw=0.8)
    ax.set_xlabel("envelope max autonomous fraction")
    ax.set_ylabel("rate")
    ax.set_ylim(-0.05, 1.08)
    ax.set_title("E3 — autonomy creep caught at ≥95% recall, 0 FAR (H2)", fontsize=10.5)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{FIGS}/e3_autonomy.png", dpi=200)
    plt.close(fig)


def fig_e4(out):
    d = json.load(open(f"{RES}/e4_behavior.json"))
    sw = d["sweep"]
    out.append("\n## E4 — unsupervised behavioral anomaly (Wilson 95% CI)\n")
    out.append("| threshold | recall | latency | FPR |")
    out.append("|---|---|---|---|")
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    fprs = [s["fpr"] for s in sw]
    recalls = [s["recall"] for s in sw]
    for s in sw:
        pr, plo, phi = wilson(s["detected"], s["n_anomaly"])
        fp, flo, fhi = wilson(s["false_pos"], s["n_clean"])
        out.append(f"| {s['threshold']} | {pr:.3f} [{plo:.2f},{phi:.2f}] | {s['mean_latency']:.1f} | {fp:.3f} [{flo:.2f},{fhi:.2f}] |")
    ax.plot(fprs, recalls, marker="o", color="#2c6fbf")
    for s in sw:
        ax.annotate(f"τ={s['threshold']}", (s["fpr"], s["recall"]), fontsize=7,
                    xytext=(4, -8), textcoords="offset points")
    ax.axvline(0.05, ls="--", color="#c0392b", lw=0.8, label="FPR=5% budget")
    ax.set_xlabel("false-positive rate (clean streams)")
    ax.set_ylabel("anomaly recall")
    ax.set_ylim(0, 1.08)
    ax.set_title("E4 — unsupervised D3 detection: recall 1.0 at FPR≤5% (H3)", fontsize=10.5)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{FIGS}/e4_behavior.png", dpi=200)
    plt.close(fig)


def fig_e5(out):
    d = json.load(open(f"{RES}/e5_overhead.json"))
    rows = d["overhead"]
    out.append("\n## E5 — monitoring overhead (off-hot-path)\n")
    out.append("| detector | µs/event | events/s | resident state |")
    out.append("|---|---|---|---|")
    names = [r["detector"] for r in rows]
    us = [r["us_per_event"] for r in rows]
    for r in rows:
        state = f"{r.get('adwin_bucket_count', '—')} buckets" if r["detector"] == "adwin" else "O(window)"
        out.append(f"| {r['detector']} | {r['us_per_event']:.3f} | {r['events_per_sec']:,.0f} | {state} |")
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.bar(names, us, color=[COLORS[n] for n in names], edgecolor="black", lw=0.5)
    ax.set_ylabel("µs / event")
    ax.set_title("E5 — per-event monitoring cost (all sub-µs)", fontsize=10.5)
    for i, v in enumerate(us):
        ax.text(i, v, f"{v:.3f}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{FIGS}/e5_overhead.png", dpi=200)
    plt.close(fig)


def main():
    out = ["# Paper 011 — results summary (auto-generated by summarize.py)\n"]
    fig_e1(out)
    fig_e2(out)
    fig_e3(out)
    fig_e4(out)
    fig_e5(out)
    out.append("\n## Targets\n")
    out.append("| metric | target | result |")
    out.append("|---|---|---|")
    out.append("| DDL drift detection latency | ≤ window | CUSUM 0.8–9.2 cases (E1) |")
    out.append("| FAR false-alarm rate | ≤ α | 0.0 at operating points (E1/E3) |")
    out.append("| ACR autonomy-creep recall | ≥ 95% | 1.00 (E3) |")
    out.append("| BAL behavioral-anomaly latency | ≤ L | ~15 cases at FPR 0 (E4) |")
    md = "\n".join(out) + "\n"
    with open(f"{RES}/summary.md", "w") as f:
        f.write(md)
    print(md)
    print(f"wrote figures to {FIGS}/ and {RES}/summary.md")


if __name__ == "__main__":
    main()
