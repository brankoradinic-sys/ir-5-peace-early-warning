"""
IR-5 v4.0 - Peace Early Warning System
Put Znanosti, Mira i Harmonije Svijesti (PZMHS)

Copyright (c) 2026 Branko Radinić

This file is part of IR-5 v4.0.

IR-5 v4.0 is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

ETHICAL ADDENDUM:
This software is intended to serve peace and human dignity. Any use for
military purposes, autonomous weapons, mass manipulation, or activities
that harm human life is strictly prohibited.
"""


"""
IR-5 v4.0 - Peace Early Warning System
Put Znanosti, Mira i Harmonije Svijesti (PZMHS)

Copyright (c) 2026 Branko Radinić

This file is part of IR-5 v4.0.

IR-5 v4.0 is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

ETHICAL ADDENDUM:
This software is intended to serve peace and human dignity. Any use for
military purposes, autonomous weapons, mass manipulation, or activities
that harm human life is strictly prohibited.
"""


# ================================================================
# IR-5 Monte Carlo Pipeline — v3.0 KOMPLETNI INTEGRIRANI MODUL
# PZMHS-i Program
#
# Integrirane komponente (Poe.com AI dopune):
#   A — Pearson + Spearman korelacije (filter n >= Nmin)
#   B — Provenance metapodaci izvora
#   C — Data-fusion weighted aggregator
#   D — Sanity checks (variance, rolling z-score anomalies)
#   + Postojeći Monte Carlo simulator (IR-5 v2.0)
#   + Export JSON s kompletnim _meta podacima
#
# Upotreba:
#   python3 ir5_pipeline_v3.py
#   ili uvezi kao modul: from ir5_pipeline_v3 import run_full_pipeline
# ================================================================

import numpy as np
from scipy import stats as sp_stats
from scipy.stats import truncnorm
from datetime import datetime
from pathlib import Path
import json
import gzip
from typing import Dict, Any, Optional, List

# ────────────────────────────────────────────────────────────────
# MODUL 1 — Monte Carlo simulator (IR-5 v2.0 osnova)
# ────────────────────────────────────────────────────────────────

def trunc_normal_samples(mean, std, lower, upper, n):
    if std <= 0:
        return np.clip(np.full(n, mean), lower, upper)
    a, b = (lower - mean) / std, (upper - mean) / std
    return truncnorm.rvs(a, b, loc=mean, scale=std, size=n)

def minmax_normalize(x, xmin, xmax):
    xmin = np.asarray(xmin, dtype=float)
    xmax = np.asarray(xmax, dtype=float)
    return np.clip(np.where(xmax == xmin, 0.0, (x - xmin) / (xmax - xmin)), 0.0, 1.0)

def winsorized_normalize(x, xmin, xmax, population=None,
                          lower_pct=0.05, upper_pct=0.95):
    if population is not None and len(population) > 10:
        ql = np.quantile(population, lower_pct)
        qu = np.quantile(population, upper_pct)
    else:
        ql, qu = xmin, xmax
    return minmax_normalize(np.clip(x, ql, qu), ql, qu)

def default_indicators(scenario="hormuz"):
    """Zadani indikatori po scenariju."""
    scenarios = {
        "hormuz": [
            {"name":"diplomatic_tension",   "category":"political", "mean":0.85,"std":0.08,"min":0,"max":1,"w":0.6},
            {"name":"public_rhetoric",      "category":"political", "mean":0.80,"std":0.10,"min":0,"max":1,"w":0.4},
            {"name":"naval_incident_rate",  "category":"military",  "mean":0.90,"std":0.08,"min":0,"max":1,"w":0.5},
            {"name":"troop_readiness",      "category":"military",  "mean":0.85,"std":0.10,"min":0,"max":1,"w":0.5},
            {"name":"insurance_premium",    "category":"economic",  "mean":0.90,"std":0.08,"min":0,"max":1,"w":1.0},
            {"name":"satcom_jamming",       "category":"tech",      "mean":0.75,"std":0.12,"min":0,"max":1,"w":1.0},
            {"name":"weather_disruption",   "category":"climate",   "mean":0.20,"std":0.08,"min":0,"max":1,"w":1.0},
            {"name":"mediation_activity",   "category":"diplomatic","mean":0.35,"std":0.12,"min":0,"max":1,"w":1.0},
        ],
        "grenland": [
            {"name":"territorial_annexation_threat","category":"political", "mean":0.88,"std":0.07,"min":0,"max":1,"w":0.5},
            {"name":"nato_alliance_fracture",       "category":"political", "mean":0.82,"std":0.08,"min":0,"max":1,"w":0.5},
            {"name":"military_force_threat",        "category":"military",  "mean":0.72,"std":0.10,"min":0,"max":1,"w":0.6},
            {"name":"arctic_militarization",        "category":"military",  "mean":0.65,"std":0.11,"min":0,"max":1,"w":0.4},
            {"name":"tariff_economic_coercion",     "category":"economic",  "mean":0.80,"std":0.09,"min":0,"max":1,"w":0.6},
            {"name":"resource_minerals_interest",   "category":"economic",  "mean":0.75,"std":0.10,"min":0,"max":1,"w":0.4},
            {"name":"arctic_climate_access",        "category":"climate",   "mean":0.70,"std":0.10,"min":0,"max":1,"w":0.6},
            {"name":"rare_earth_geopolitics",       "category":"climate",   "mean":0.65,"std":0.11,"min":0,"max":1,"w":0.4},
            {"name":"intelligence_covert_ops",      "category":"tech",      "mean":0.75,"std":0.10,"min":0,"max":1,"w":1.0},
            {"name":"diplomatic_nato_channels",     "category":"diplomatic","mean":0.45,"std":0.12,"min":0,"max":1,"w":0.5},
            {"name":"eu_resistance_framework",      "category":"diplomatic","mean":0.50,"std":0.12,"min":0,"max":1,"w":0.5},
        ]
    }
    return scenarios.get(scenario, scenarios["hormuz"])

def default_category_weights(scenario="hormuz"):
    weights = {
        "hormuz":   {"political":0.25,"military":0.25,"economic":0.20,"tech":0.15,"climate":0.10,"diplomatic":0.05},
        "grenland": {"political":0.30,"military":0.22,"economic":0.20,"climate":0.12,"tech":0.08,"diplomatic":0.08},
    }
    return weights.get(scenario, weights["hormuz"])

def run_monte_carlo(indicators=None, category_weights=None,
                    N=20000, normalize_method="winsorized",
                    perturb_weights=True, seed=42,
                    scenario_name="IR-5 analiza"):
    np.random.seed(seed)
    if indicators is None:
        indicators = default_indicators()
    if category_weights is None:
        category_weights = default_category_weights()

    categories = {}
    for ind in indicators:
        categories.setdefault(ind["category"], []).append(ind)

    # Populacije za winsorized normalizaciju
    populations = {}
    for cat, inds in categories.items():
        for ind in inds:
            populations[ind["name"]] = trunc_normal_samples(
                ind["mean"], ind["std"], ind["min"], ind["max"], 1000)

    air_samples       = np.zeros(N)
    contrib_samples   = {cat: np.zeros(N) for cat in category_weights}
    indicator_sampled = {ind["name"]: np.zeros(N) for ind in indicators}

    for i in range(N):
        if perturb_weights:
            base  = np.array([category_weights[c] for c in category_weights])
            noise = np.random.normal(0.0, 0.02, size=base.shape)
            w_arr = np.clip(base + noise, 1e-6, None)
            w_arr = w_arr / w_arr.sum()
            w_cat = dict(zip(list(category_weights.keys()), w_arr))
        else:
            w_cat = dict(category_weights)

        air_val = 0.0
        for cat, inds in categories.items():
            w_in = np.array([ind["w"] for ind in inds], dtype=float)
            w_in = w_in / w_in.sum()
            sampled = np.array([
                trunc_normal_samples(ind["mean"], ind["std"], ind["min"], ind["max"], 1)[0]
                for ind in inds
            ])
            for j, ind in enumerate(inds):
                indicator_sampled[ind["name"]][i] = sampled[j]

            if normalize_method == "winsorized":
                normed = np.array([
                    float(winsorized_normalize(sampled[j], inds[j]["min"], inds[j]["max"],
                                               population=populations[inds[j]["name"]]))
                    for j in range(len(inds))
                ])
            else:
                xmin = np.array([ind["min"] for ind in inds], dtype=float)
                xmax = np.array([ind["max"] for ind in inds], dtype=float)
                normed = minmax_normalize(sampled, xmin, xmax)

            Ck = float(np.sum(w_in * normed))
            air_val += w_cat.get(cat, 0.0) * Ck
            contrib_samples[cat][i] = w_cat.get(cat, 0.0) * Ck

        air_samples[i] = air_val * 10.0

    # Osnovna sensitivity (Pearson)
    sensitivity = {}
    for ind in indicators:
        corr = np.corrcoef(indicator_sampled[ind["name"]], air_samples)[0, 1]
        sensitivity[ind["name"]] = float(corr)

    return {
        "scenario":          scenario_name,
        "N":                 N,
        "mean":              float(np.mean(air_samples)),
        "median":            float(np.median(air_samples)),
        "std":               float(np.std(air_samples)),
        "p5":                float(np.percentile(air_samples,  5)),
        "p25":               float(np.percentile(air_samples, 25)),
        "p75":               float(np.percentile(air_samples, 75)),
        "p95":               float(np.percentile(air_samples, 95)),
        "air_samples":       air_samples,
        "contrib_samples":   contrib_samples,
        "indicator_sampled": indicator_sampled,
        "sensitivity":       sensitivity,
    }


# ────────────────────────────────────────────────────────────────
# MODUL A — Pearson + Spearman korelacije (Poe dopuna A)
# ────────────────────────────────────────────────────────────────

def compute_correlations(summary: Dict,
                          methods=("pearson", "spearman"),
                          Nmin: int = 50,
                          round_digits: int = 4) -> Dict:
    """
    Pearson i Spearman korelacije između indikatora i AIR.
    Filtrira indikatore s manje od Nmin opservacija.
    """
    air = np.asarray(summary.get("air_samples", []), dtype=float)
    indicators = summary.get("indicator_sampled") or {}
    results = {}

    for name, arr in indicators.items():
        ind = np.asarray(arr, dtype=float)
        m = min(len(ind), len(air))
        a2, i2 = air[:m], ind[:m]
        mask = ~(np.isnan(a2) | np.isnan(i2))
        a2, i2 = a2[mask], i2[mask]
        n = int(len(a2))
        if n < Nmin:
            continue

        entry = {"n": n, "pearson": {}, "spearman": {}}

        # Pearson
        if "pearson" in methods:
            try:
                r, p = sp_stats.pearsonr(a2, i2)
                entry["pearson"] = {
                    "stat": round(float(r), round_digits),
                    "p":    round(float(p), round_digits)
                }
            except Exception:
                entry["pearson"] = {"stat": None, "p": None}

        # Spearman
        if "spearman" in methods:
            try:
                rho, p = sp_stats.spearmanr(a2, i2)
                entry["spearman"] = {
                    "stat": round(float(rho), round_digits),
                    "p":    round(float(p), round_digits)
                }
            except Exception:
                entry["spearman"] = {"stat": None, "p": None}

        results[name] = entry

    # Sortiraj po apsolutnom Pearson r
    def sort_key(item):
        v = item[1]
        r = (v.get("pearson") or {}).get("stat")
        if r is None:
            r = (v.get("spearman") or {}).get("stat") or 0.0
        return abs(r)
    return dict(sorted(results.items(), key=sort_key, reverse=True))


# ────────────────────────────────────────────────────────────────
# MODUL B — Provenance metapodaci (Poe dopuna B)
# ────────────────────────────────────────────────────────────────

def extract_provenance(summary: Dict,
                        indicator_sources: Optional[Dict] = None) -> Dict:
    """
    Izvlači metapodatke pouzdanosti za svaki indikator:
    - missing_rate: udio nedostajućih vrijednosti
    - variance, std: mjere raspršenosti
    - source, last_update: iz registra izvora (ako postoji)
    """
    now_iso = datetime.utcnow().isoformat() + "Z"
    indicators = summary.get("indicator_sampled") or {}
    prov = {}

    for name, arr in indicators.items():
        arr_np = np.asarray(arr, dtype=float)
        total   = arr_np.size
        missing = int(np.isnan(arr_np).sum())
        valid   = arr_np[~np.isnan(arr_np)]
        src_info = (indicator_sources or {}).get(name, {})

        prov[name] = {
            "source":       src_info.get("source",      "javni podaci"),
            "last_update":  src_info.get("last_update",  now_iso),
            "trust_score":  src_info.get("trust_score",  0.75),
            "extracted_at": now_iso,
            "sample_count": int(total),
            "missing_count": int(missing),
            "missing_rate": round(missing / total, 6) if total > 0 else None,
            "var":          round(float(np.var(valid)),  6) if valid.size > 0 else None,
            "std":          round(float(np.std(valid)),  6) if valid.size > 0 else None,
        }
    return prov


# ────────────────────────────────────────────────────────────────
# MODUL C — Data-fusion weighted aggregator (Poe dopuna C)
# ────────────────────────────────────────────────────────────────

def compute_weights_from_provenance(prov: Dict,
                                     trust_map: Optional[Dict] = None,
                                     missing_rate_penalty: float = 1.0) -> Dict:
    """
    Izračunava težine indikatora na temelju provenance metapodataka.
    - Viši trust_score → veća težina
    - Viši missing_rate → manja težina (penalizacija)
    """
    weights = {}
    for name, meta in prov.items():
        trust = (trust_map or {}).get(name, meta.get("trust_score", 0.75))
        missing = meta.get("missing_rate") or 0.0
        w = trust * (1.0 - missing_rate_penalty * missing)
        weights[name] = max(w, 1e-6)
    return weights

def weighted_aggregate_indicators(summary: Dict,
                                    weights: Dict,
                                    flatten: bool = False) -> Dict:
    """
    Provenance-based weighted aggregator.
    Kombinira indikatore u sintetički agregirani signal (fusion_agg).
    """
    indicators = summary.get("indicator_sampled") or {}
    names = [n for n in indicators if n in weights]
    if not names:
        return {"agg": [], "per_indicator": {}, "weights": {}}

    N = len(next(iter(indicators.values())))
    mat = np.vstack([np.asarray(indicators[n], dtype=float) for n in names])
    ws  = np.array([weights[n] for n in names], dtype=float)
    ws  = ws / ws.sum() if ws.sum() > 0 else np.ones(len(ws)) / len(ws)

    agg = (ws[:, None] * mat).sum(axis=0)
    per_ind = {n: mat[i, :].tolist() for i, n in enumerate(names)}

    out = {
        "agg":           agg.tolist(),
        "per_indicator": per_ind,
        "weights":       {n: round(float(w), 6) for n, w in zip(names, ws)}
    }

    if flatten:
        flattened = []
        for i in range(N):
            rec = {"index": i, "agg": float(agg[i])}
            for n in names:
                rec[f"ind_{n}"] = float(per_ind[n][i])
            flattened.append(rec)
        out["flattened"] = flattened

    return out


# ────────────────────────────────────────────────────────────────
# MODUL D — Sanity checks (Poe dopuna D)
# ────────────────────────────────────────────────────────────────

def variance_filter(summary: Dict, var_eps: float = 1e-6) -> List[str]:
    """Vraća listu indikatora s premalim varijancom (gotovo konstantni)."""
    indicators = summary.get("indicator_sampled") or {}
    low_var = []
    for name, arr in indicators.items():
        v = float(np.var(np.asarray(arr, dtype=float)))
        if v < var_eps:
            low_var.append(name)
    return low_var

def rolling_zscore_anomalies(arr: np.ndarray,
                               window: int = 50,
                               z_thresh: float = 4.0) -> List[int]:
    """Detektira anomalije pomoću rolling z-score-a."""
    anomaly_indices = []
    for i in range(window, len(arr)):
        window_data = arr[i - window:i]
        mu  = np.mean(window_data)
        sig = np.std(window_data)
        if sig > 0 and abs((arr[i] - mu) / sig) > z_thresh:
            anomaly_indices.append(i)
    return anomaly_indices

def run_sanity_checks(summary: Dict,
                       var_eps: float = 1e-6,
                       rolling_window: int = 50,
                       z_thresh: float = 4.0) -> Dict:
    """
    Kompletni sanity check za sve indikatore.
    Vraća: low_variance, anomalies, ok liste.
    """
    indicators = summary.get("indicator_sampled") or {}
    low_var    = variance_filter(summary, var_eps=var_eps)
    anomalies  = {}
    ok         = []

    for name, arr in indicators.items():
        arr_np = np.asarray(arr, dtype=float)
        inds   = rolling_zscore_anomalies(arr_np,
                                          window=rolling_window,
                                          z_thresh=z_thresh)
        if inds:
            anomalies[name] = inds[:5]  # prikaži max 5 primjera
        if name not in low_var and name not in anomalies:
            ok.append(name)

    return {
        "low_variance": low_var,
        "anomalies":    {k: len(v) for k, v in anomalies.items()},
        "ok":           ok,
        "n_indicators": len(indicators),
        "n_ok":         len(ok),
        "n_issues":     len(low_var) + len(anomalies)
    }


# ────────────────────────────────────────────────────────────────
# KOMPLETNI PIPELINE — sve komponente zajedno
# ────────────────────────────────────────────────────────────────

def run_full_pipeline(indicators=None,
                       category_weights=None,
                       scenario_name="IR-5 analiza",
                       N=20000,
                       normalize_method="winsorized",
                       seed=42,
                       indicator_sources=None,
                       out_path="ir5_output.json",
                       compress=False,
                       model_version="3.0"):
    """
    Kompletni IR-5 pipeline v3.0:
    1. Monte Carlo simulacija
    2. Sanity checks (D)
    3. Provenance metapodaci (B)
    4. Fusion weights i aggregator (C)
    5. Korelacijska analiza (A)
    6. Export s kompletnim _meta podacima
    """

    print("=" * 60)
    print(f"  IR-5 Pipeline v{model_version} — {scenario_name}")
    print("=" * 60)

    # ── KORAK 1: Monte Carlo ─────────────────────────────────────
    print("  [1/5] Monte Carlo simulacija...")
    summary = run_monte_carlo(
        indicators=indicators,
        category_weights=category_weights,
        N=N,
        normalize_method=normalize_method,
        seed=seed,
        scenario_name=scenario_name
    )
    print(f"        AIR = {summary['mean']:.2f}  CI90 [{summary['p5']:.2f}–{summary['p95']:.2f}]")

    # ── KORAK 2: Sanity checks ───────────────────────────────────
    print("  [2/5] Sanity checks...")
    sanity = run_sanity_checks(summary)
    print(f"        OK: {sanity['n_ok']}/{sanity['n_indicators']}  "
          f"| Problemi: {sanity['n_issues']}")
    if sanity["low_variance"]:
        print(f"        ⚠ Niska varijanca: {sanity['low_variance']}")
    if sanity["anomalies"]:
        print(f"        ⚠ Anomalije: {list(sanity['anomalies'].keys())}")

    # ── KORAK 3: Provenance ──────────────────────────────────────
    print("  [3/5] Provenance metapodaci...")
    prov = extract_provenance(summary, indicator_sources=indicator_sources)
    avg_missing = np.mean([v["missing_rate"] or 0 for v in prov.values()])
    print(f"        Prosječni missing rate: {avg_missing:.4f}")

    # ── KORAK 4: Data fusion ─────────────────────────────────────
    print("  [4/5] Data fusion weighted aggregator...")
    weights = compute_weights_from_provenance(prov)
    fusion  = weighted_aggregate_indicators(summary, weights)
    fusion_mean = float(np.mean(fusion["agg"]))
    print(f"        Fusion AIR srednja vrijednost: {fusion_mean:.4f}")

    # ── KORAK 5: Korelacijska analiza ────────────────────────────
    print("  [5/5] Korelacijska analiza (Pearson + Spearman)...")
    corrs = compute_correlations(summary, Nmin=50)
    top3  = list(corrs.items())[:3]
    for name, val in top3:
        r = (val.get("pearson") or {}).get("stat", "N/A")
        print(f"        {name:<30} r={r}")

    # ── EXPORT ───────────────────────────────────────────────────
    output = {
        "scenario":      summary["scenario"],
        "model_version": model_version,
        "N":             summary["N"],
        "mean":          round(summary["mean"],   4),
        "median":        round(summary["median"], 4),
        "std":           round(summary["std"],    4),
        "p5":            round(summary["p5"],     4),
        "p25":           round(summary["p25"],    4),
        "p75":           round(summary["p75"],    4),
        "p95":           round(summary["p95"],    4),
        "_meta": {
            "exported_at":   datetime.utcnow().isoformat() + "Z",
            "pipeline":      f"IR-5 v{model_version}",
            "correlations":  corrs,
            "provenance":    prov,
            "sanity":        sanity,
            "fusion_mean":   round(fusion_mean, 4),
            "fusion_weights": fusion["weights"],
        }
    }

    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    if compress:
        fname = str(out_p) + ".gz"
        with gzip.open(fname, "wt", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
    else:
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"  Pipeline završen. Output: {out_path}")
    print("=" * 60)

    # Dodaj fusion i corrs u summary za daljnju upotrebu
    summary["fusion"]       = fusion
    summary["correlations"] = corrs
    summary["provenance"]   = prov
    summary["sanity"]       = sanity

    return summary, output


# ────────────────────────────────────────────────────────────────
# ISPIS — formatiran prikaz rezultata
# ────────────────────────────────────────────────────────────────

def print_full_report(summary):
    print("\n" + "=" * 62)
    print("  IR-5 KOMPLETNI IZVJEŠTAJ — Pipeline v3.0")
    print("=" * 62)
    print(f"  Scenarij:    {summary['scenario']}")
    print(f"  Simulacije:  {summary['N']:,}")
    print("-" * 62)
    print(f"  AIR srednja vrijednost : {summary['mean']:.2f} / 10")
    print(f"  AIR medijan            : {summary['median']:.2f} / 10")
    print(f"  Standardna devijacija  : {summary['std']:.2f}")
    print(f"  CI 90%  [{summary['p5']:.2f} – {summary['p95']:.2f}]"
          f"  |  CI 50%  [{summary['p25']:.2f} – {summary['p75']:.2f}]")
    print("-" * 62)

    print("  Doprinos kategorija:")
    for cat, arr in summary["contrib_samples"].items():
        val = float(np.mean(arr)) * 10.0
        bar = "█" * max(0, int(val * 3))
        print(f"  {cat:<14}  {val:.3f}  {bar}")
    print("-" * 62)

    print("  Korelacije (Pearson r | Spearman ρ | p-vrijednost):")
    for name, val in summary["correlations"].items():
        r   = (val.get("pearson")  or {}).get("stat", "N/A")
        rho = (val.get("spearman") or {}).get("stat", "N/A")
        p   = (val.get("pearson")  or {}).get("p", None)
        p_s = f"p={p:.4f}" if p is not None else ""
        bar = "█" * max(0, int(abs(r if isinstance(r, float) else 0) * 15))
        print(f"  {name:<30}  r={r}  ρ={rho}  {p_s}  {bar}")
    print("-" * 62)

    print("  Sanity check:")
    s = summary["sanity"]
    print(f"  OK: {s['n_ok']}/{s['n_indicators']}  "
          f"| Niska varijanca: {s['low_variance'] or 'nema'}"
          f"  | Anomalije: {dict(s['anomalies']) or 'nema'}")
    print("-" * 62)

    print("  Data fusion — provenance težine (top 5):")
    top_weights = sorted(summary["fusion"]["weights"].items(),
                         key=lambda x: x[1], reverse=True)[:5]
    for name, w in top_weights:
        bar = "█" * max(0, int(w * 30))
        print(f"  {name:<30}  w={w:.4f}  {bar}")
    print("=" * 62)


# ────────────────────────────────────────────────────────────────
# POKRETANJE
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # ── TEST 1: Hormuz ───────────────────────────────────────────
    print("\n>>> SCENARIJ 1: Hormuški tjesnac — ožujak 2026.")
    summary_h, _ = run_full_pipeline(
        indicators       = default_indicators("hormuz"),
        category_weights = default_category_weights("hormuz"),
        scenario_name    = "Hormuski tjesnac — ozujak 2026.",
        N                = 10000,
        seed             = 42,
        out_path         = "/mnt/user-data/outputs/IR5_v3_Hormuz.json"
    )
    print_full_report(summary_h)

    # ── TEST 2: Grenland ─────────────────────────────────────────
    print("\n>>> SCENARIJ 2: Afera Grenland — 2025./2026.")
    summary_g, _ = run_full_pipeline(
        indicators       = default_indicators("grenland"),
        category_weights = default_category_weights("grenland"),
        scenario_name    = "Afera Grenland — 2025./2026.",
        N                = 10000,
        seed             = 42,
        out_path         = "/mnt/user-data/outputs/IR5_v3_Grenland.json"
    )
    print_full_report(summary_g)

    print("\n>>> Oba scenarija uspjesno procesirana kroz IR-5 Pipeline v3.0")
    print(">>> Za Mir — uvijek. PZMHS-i Program.")
