#!/usr/bin/env python3
"""
SETU Round 3 - ML benchmark: BKT fitted on real public data + a trained baseline.
=====================================================================================
WHAT THIS DOES (all on YOUR machine, CPU only, no pip installs - pure Python stdlib):
  1. Downloads the public ASSISTments 2009-2010 skill-builder dataset (83 MB CSV)
     from its figshare mirror (the dataset is free to use; cite the data page).
  2. Cleans it the standard way (first attempts only, valid skill + 0/1 correct).
  3. Splits by STUDENT (80/20) - no student appears in both train and test.
  4. FITS Bayesian Knowledge Tracing parameters (p_init, p_learn, p_guess, p_slip)
     by EM on the training students - globally, and per skill for the top skills.
  5. TRAINS a small logistic-regression baseline (PFA-style features) on the same
     training students.
  6. MEASURES both on the held-out students: AUC, log-loss, accuracy.
  7. Writes bkt_fitted_params.json with the fitted BKT parameters.

HONESTY CONTRACT (do not remove):
  - Every number this prints is MEASURED ON THIS RUN, on US students from 2009-10.
  - It is NOT Tamil Nadu data. It says nothing about Setu's own content accuracy.
  - The fitted BKT parameters are reference starting values from a public dataset,
    not calibration to Setu's questions. Say exactly that if a judge asks.

Run:  python setu_ml_benchmark.py
Time: ~2-5 minutes on a normal laptop.
"""

import csv, hashlib, json, math, os, sys, time, urllib.request
from collections import defaultdict

DATA_URL = "https://ndownloader.figshare.com/files/44736253"
DATA_FILE = "skill_builder_data.csv"
EXPECTED_BYTES = 83201940
TOP_SKILLS = 50          # per-skill BKT for the 50 most frequent skills
EM_ITERS_GLOBAL = 25
EM_ITERS_SKILL = 10
MIN_SKILL_SEQ = 200      # below this, a skill falls back to global params
LR_EPOCHS = 8
LR_RATE = 0.05


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- download
def download():
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) == EXPECTED_BYTES:
        log(f"dataset already here: {DATA_FILE}")
        return
    log(f"downloading ASSISTments 2009-2010 skill-builder data ({EXPECTED_BYTES/1e6:.0f} MB)...")
    log(f"  source: {DATA_URL}")
    urllib.request.urlretrieve(DATA_URL, DATA_FILE)
    size = os.path.getsize(DATA_FILE)
    if size != EXPECTED_BYTES:
        sys.exit(f"download size mismatch ({size}), delete {DATA_FILE} and retry")


# ---------------------------------------------------------------- load + clean
def load_sequences():
    """Return dict[(user_id, skill_id)] -> list of 0/1 in time order (first attempts)."""
    log("loading and cleaning (first attempts only, valid skill, correct in {0,1})...")
    seqs = defaultdict(list)
    kept = skipped = 0
    with open(DATA_FILE, newline='', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get("attempt_count") != "1":
                skipped += 1
                continue
            skill = (row.get("skill_id") or "").strip()
            corr = (row.get("correct") or "").strip()
            user = (row.get("user_id") or "").strip()
            if not skill or corr not in ("0", "1") or not user:
                skipped += 1
                continue
            seqs[(user, skill)].append((int(row["order_id"]), int(corr)))
            kept += 1
    out = {}
    for k, pairs in seqs.items():
        pairs.sort()
        out[k] = [c for _, c in pairs]
    log(f"kept {kept:,} first-attempt rows ({skipped:,} skipped) in {len(out):,} student-skill sequences")
    return out


# ---------------------------------------------------------------- student split
def student_split(seqs):
    train, test = {}, {}
    for (user, skill), obs in seqs.items():
        bucket = int(hashlib.md5(user.encode()).hexdigest(), 16) % 100  # deterministic
        (train if bucket < 80 else test)[(user, skill)] = obs
    n_tr = sum(len(v) for v in train.values())
    n_te = sum(len(v) for v in test.values())
    log(f"student split: {n_tr:,} train rows / {n_te:,} test rows (no student in both)")
    return train, test


# ---------------------------------------------------------------- BKT (EM)
def bkt_e_step(seqs, p0, pt, pg, ps):
    """One proper Baum-Welch pass (forward-backward with scaling).
    Returns (log-likelihood, new params from expected counts)."""
    ll = 0.0
    n_p0 = d_p0 = 1e-9
    n_pt = d_pt = 1e-9
    n_g = d_g = n_s = d_s = 1e-9
    A = ((1.0 - pt, pt), (0.0, 1.0))
    for obs in seqs:
        T = len(obs)
        emit = [(pg if o else 1.0 - pg, (1.0 - ps) if o else ps) for o in obs]
        # forward (scaled)
        alpha = [[0.0, 0.0] for _ in range(T)]
        scale = [0.0] * T
        alpha[0] = [1.0 - p0, p0]
        for t in range(T):
            for j in (0, 1):
                alpha[t][j] *= emit[t][j]
            tot = alpha[t][0] + alpha[t][1]
            if tot <= 0:
                tot = 1e-300
            scale[t] = tot
            alpha[t][0] /= tot
            alpha[t][1] /= tot
            if t + 1 < T:
                for j in (0, 1):
                    alpha[t + 1][j] = sum(alpha[t][i] * A[i][j] for i in (0, 1))
        ll += sum(math.log(sc) for sc in scale)
        # backward (scaled the same way)
        beta = [[1.0, 1.0] for _ in range(T)]
        for t in range(T - 2, -1, -1):
            for i in (0, 1):
                beta[t][i] = sum(A[i][j] * emit[t + 1][j] * beta[t + 1][j] for j in (0, 1)) / scale[t + 1]
        # smoothed gamma + expected counts
        for t in range(T):
            g = [alpha[t][0] * beta[t][0], alpha[t][1] * beta[t][1]]
            tot = g[0] + g[1]
            if tot <= 0:
                tot = 1e-300
            g0, g1 = g[0] / tot, g[1] / tot
            if t == 0:
                n_p0 += g0
                d_p0 += 1.0
            if obs[t]:
                n_g += g0
                d_g += g0
                d_s += g1
            else:
                d_g += g0
                n_s += g1
                d_s += g1
            if t + 1 < T:
                # xi(0,1): expected learn transitions
                xi01 = alpha[t][0] * pt * emit[t + 1][1] * beta[t + 1][1] / scale[t + 1]
                n_pt += xi01
                d_pt += g0
    return ll, (n_p0 / d_p0, n_pt / d_pt, n_g / d_g if d_g else pg, n_s / d_s if d_s else ps)


def bkt_fit(seq_list, iters, init=(0.20, 0.10, 0.20, 0.10)):
    p0, pt, pg, ps = init
    ll = 0.0
    for _ in range(iters):
        ll, (p0, pt, pg, ps) = bkt_e_step(seq_list, p0, pt, pg, ps)
        pt = min(max(pt, 1e-4), 0.5)
        pg = min(max(pg, 1e-4), 0.45)
        ps = min(max(ps, 1e-4), 0.45)
        p0 = min(max(p0, 1e-4), 0.9)
    return (p0, pt, pg, ps), ll


def bkt_predict_proba_seq(obs, params):
    """Yield P(correct_t) for each t, filtering forward with fitted params."""
    p0, pt, pg, ps = params
    p = p0
    for o in obs:
        yield p * (1.0 - ps) + (1.0 - p) * pg
        # posterior given the actual observation
        num = p * ((1.0 - ps) if o else ps)
        den = num + (1.0 - p) * (pg if o else (1.0 - pg))
        p = (num / den) if den > 0 else p0
        p = p + (1.0 - p) * pt


# ---------------------------------------------------------------- PFA-lite baseline
def pfa_features(seqs_rows):
    """seqs_rows: list of (skill, history_correct, history_wrong, y)."""
    return seqs_rows


def train_pfa(train, skill_diff):
    w = [0.0, 0.4, -0.4, 0.0]             # bias, +succ, -fail, difficulty
    rows = []
    for (user, skill), obs in train.items():
        s = f = 0
        for o in obs:
            rows.append((skill, s, f, o))
            s, f = s + o, f + (1 - o)
    log(f"PFA-lite: training logistic regression on {len(rows):,} rows x {LR_EPOCHS} epochs...")
    for ep in range(LR_EPOCHS):
        for skill, s, f, y in rows:
            x = (1.0, math.log1p(s), math.log1p(f), skill_diff.get(skill, 0.5))
            z = sum(wi * xi for wi, xi in zip(w, x))
            p = 1.0 / (1.0 + math.exp(-max(-30, min(30, z))))
            g = p - y
            for i in range(4):
                w[i] -= LR_RATE * g * x[i]
    return w


def pfa_predict(test, w, skill_diff):
    pts, ys = [], []
    for (user, skill), obs in test.items():
        s = f = 0
        for o in obs:
            x = (1.0, math.log1p(s), math.log1p(f), skill_diff.get(skill, 0.5))
            z = sum(wi * xi for wi, xi in zip(w, x))
            pts.append(1.0 / (1.0 + math.exp(-max(-30, min(30, z)))))
            ys.append(o)
            s, f = s + o, f + (1 - o)
    return pts, ys


# ---------------------------------------------------------------- metrics
def auc(scores, ys):
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    rank_sum, n_pos = 0.0, sum(ys)
    n_neg = len(ys) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    for r, i in enumerate(order, 1):
        if ys[i]:
            rank_sum += r
    return (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def logloss(ps, ys):
    eps = 1e-15
    return -sum(y * math.log(max(eps, p)) + (1 - y) * math.log(max(eps, 1 - p)) for p, y in zip(ps, ys)) / len(ys)


def acc(ps, ys):
    return sum((p >= 0.5) == bool(y) for p, y in zip(ps, ys)) / len(ys)


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    print("=" * 74)
    print("SETU ML BENCHMARK - BKT fitted on ASSISTments 2009-2010 + trained baseline")
    print("Every number below is [MEASURED on this run] - quote it with that label.")
    print("=" * 74)
    download()
    seqs = load_sequences()
    train, test = student_split(seqs)

    # skill difficulty from TRAIN only (for the baseline feature)
    s_sum = defaultdict(lambda: [0, 0])
    for (u, sk), obs in train.items():
        s_sum[sk][0] += sum(obs)
        s_sum[sk][1] += len(obs)
    skill_diff = {sk: c / n for sk, (c, n) in s_sum.items()}

    # ---- global BKT
    log(f"fitting GLOBAL BKT by EM ({EM_ITERS_GLOBAL} iterations)...")
    gparams, gll = bkt_fit(list(train.values()), EM_ITERS_GLOBAL)
    log(f"  global BKT: p_init={gparams[0]:.4f} p_learn={gparams[1]:.4f} p_guess={gparams[2]:.4f} p_slip={gparams[3]:.4f}")

    # ---- per-skill BKT for top skills
    skill_counts = defaultdict(int)
    for (u, sk), obs in train.items():
        skill_counts[sk] += len(obs)
    top = sorted(skill_counts, key=skill_counts.get, reverse=True)[:TOP_SKILLS]
    skill_params = {}
    log(f"fitting PER-SKILL BKT for the top {TOP_SKILLS} skills ({EM_ITERS_SKILL} EM iterations each)...")
    for sk in top:
        rows = [obs for (u, s2), obs in train.items() if s2 == sk]
        if len(rows) < MIN_SKILL_SEQ:
            continue
        skill_params[sk], _ = bkt_fit(rows, EM_ITERS_SKILL, init=gparams)
    log(f"  per-skill params fitted for {len(skill_params)} skills (others use global)")

    # ---- evaluate BKT on held-out students
    pts, ys = [], []
    for (u, sk), obs in test.items():
        prm = skill_params.get(sk, gparams)
        pts.extend(bkt_predict_proba_seq(obs, prm))
        ys.extend(obs)
    bkt_auc, bkt_ll, bkt_ac = auc(pts, ys), logloss(pts, ys), acc(pts, ys)

    # ---- trained baseline
    w = train_pfa(train, skill_diff)
    ppts, pys = pfa_predict(test, w, skill_diff)
    pfa_auc, pfa_ll, pfa_ac = auc(ppts, pys), logloss(ppts, pys), acc(ppts, pys)

    # ---- report
    print()
    print("=" * 74)
    print("RESULTS - held-out students only (student split, no leakage)")
    print("=" * 74)
    print(f"{'model':<34}{'AUC':>10}{'log-loss':>12}{'accuracy':>12}")
    print("-" * 74)
    print(f"{'BKT (EM-fitted, per-skill+global)':<34}{bkt_auc:>10.4f}{bkt_ll:>12.4f}{bkt_ac:>12.4f}")
    print(f"{'PFA-lite logistic regression (trained)':<34}{pfa_auc:>10.4f}{pfa_ll:>12.4f}{pfa_ac:>12.4f}")
    print("-" * 74)
    print(f"test rows: {len(ys):,}   train rows: {sum(len(v) for v in train.values()):,}")
    print(f"dataset: ASSISTments 2009-2010 skill-builder (figshare mirror of the")
    print(f"         official ASSISTments data page release), first attempts only")
    print()
    print("PROVENANCE / HONESTY - read before quoting:")
    print(" * All numbers above are [MEASURED on this run], on US students (2009-10).")
    print(" * This is NOT Tamil Nadu data and NOT Setu's own content.")
    print(" * Fitted BKT parameters are reference starting values from public data;")
    print("   Setu's live engine still says 'uncalibrated' until TN data exists.")
    print()

    out = {
        "label": "BKT parameters fitted by EM on ASSISTments 2009-2010 skill-builder [MEASURED on this run]",
        "fitted_on": "ASSISTments 2009-2010 skill-builder, first attempts, student-split train (80%)",
        "not": "Not Tamil Nadu data. Not calibrated to Setu content. Reference starting values only.",
        "global_params": {
            "p_init": round(gparams[0], 4), "p_learn": round(gparams[1], 4),
            "p_guess": round(gparams[2], 4), "p_slip": round(gparams[3], 4)
        },
        "measured": {"bkt_auc": round(bkt_auc, 4), "baseline_auc": round(pfa_auc, 4)},
    }
    with open("bkt_fitted_params.json", "w") as f:
        json.dump(out, f, indent=2)
    log(f"wrote bkt_fitted_params.json   (total {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
