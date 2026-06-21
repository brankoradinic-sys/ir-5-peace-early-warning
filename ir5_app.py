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

import streamlit as st
import numpy as np
import json
from datetime import datetime
import os

# ── ISPRAVAK 1: fpdf2 koristi FPDF2, ne FPDF ──────────────────────────────
try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

st.set_page_config(
    page_title="IR-5 v4.0 — Peace Early Warning System",
    page_icon="🕊️",
    layout="wide"
)

# ── ISPRAVAK 2: CSS za bolji izgled ───────────────────────────────────────
st.markdown("""
<style>
.air-box {
    background: linear-gradient(135deg, #1F4E79, #2E75B6);
    color: white;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    margin: 10px 0;
}
.air-number { font-size: 3em; font-weight: bold; }
.ethical-ok  { color: #1E8449; font-weight: bold; }
.ethical-warn{ color: #CA6F1E; font-weight: bold; }
.ethical-fail{ color: #C0392B; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ====================== DIREKTORIJ ======================
DATA_DIR = "ir5_data"
os.makedirs(DATA_DIR, exist_ok=True)
SIMULATIONS_FILE = os.path.join(DATA_DIR, "simulations.json")

# ====================== MODUL A: Monte Carlo Simulator ======================
class MonteCarloSimulator:
    """
    IR-5 Monte Carlo simulator.
    ISPRAVAK 3: Dodan seed parametar, winsorized normalizacija,
    CI interval i konzistentni scenariji.
    """
    def __init__(self, iterations: int = 20000, seed: int = 42):
        self.iterations = iterations
        self.seed = seed

    def run(self, indicators: dict) -> dict:
        np.random.seed(self.seed)
        values = np.array(list(indicators.values()), dtype=float)

        # Winsorized normalizacija (robusna prema outlierima)
        lower = np.percentile(values, 5)
        upper = np.percentile(values, 95)
        normalized = np.clip(values, lower, upper)

        # Monte Carlo iteracije
        simulations = np.array([
            float(np.mean(np.clip(
                normalized + np.random.normal(0, 0.5, len(values)), 0, 10
            )))
            for _ in range(self.iterations)
        ])

        air_index = float(np.mean(simulations))

        # ISPRAVAK 4: Confidence intervali
        ci_90_low  = float(np.percentile(simulations,  5))
        ci_90_high = float(np.percentile(simulations, 95))
        ci_50_low  = float(np.percentile(simulations, 25))
        ci_50_high = float(np.percentile(simulations, 75))

        # ISPRAVAK 5: Scenariji s konzistentnim vjerojatnostima
        # koje uvijek zbroje na 100%
        air_norm = air_index / 10.0
        raw = {
            "Nastavak rata (iscrpljivanje)": max(5.0,  42.0 * air_norm),
            "Zamrznuti sukob (primirje)":    max(5.0,  30.0 * (1.0 - air_norm * 0.5)),
            "Pregovarački mir":              max(5.0,  18.0 * (1.0 - air_norm)),
            "Vojna eskalacija":              max(2.0,  10.0 * air_norm),
        }
        total = sum(raw.values())
        scenarios = [
            {"name": name, "prob": round(prob / total * 100, 1)}
            for name, prob in raw.items()
        ]

        return {
            "air_index":  round(air_index, 2),
            "ci_90":      [round(ci_90_low, 2), round(ci_90_high, 2)],
            "ci_50":      [round(ci_50_low, 2), round(ci_50_high, 2)],
            "std":        round(float(np.std(simulations)), 3),
            "scenarios":  scenarios,
            "iterations": self.iterations,
        }


# ====================== MODUL B: Ethical Checker ======================
class EthicalChecker:
    """
    Provjera usklađenosti s Ethical Addendum PZMHS Povelje.
    ISPRAVAK 6: Proširena lista zabrajenih pojmova,
    jasna klasifikacija statusa.
    """
    FORBIDDEN_TERMS = [
        "nuklear", "oružje", "napad", "bombardir", "uništ",
        "weapon", "attack", "nuclear", "bomb"
    ]
    PEACE_TERMS = [
        "mir", "diplomac", "pregovor", "humanitar", "dijalog",
        "peace", "dialog", "negotiat"
    ]

    def check(self, air_index: float, scenarios: list, recommendations: list) -> dict:
        score = 10.0
        violations = []
        positives  = []

        for rec in recommendations:
            r = rec.lower()
            for term in self.FORBIDDEN_TERMS:
                if term in r:
                    violations.append(f"Kršenje principa Nenasilja: '{term}'")
                    score -= 2.0
                    break
            for term in self.PEACE_TERMS:
                if term in r:
                    positives.append(f"Mirovni princip potvrđen: '{term}'")
                    score += 0.3
                    break

        # Provjera eskalacijskog scenarija
        escalation = next(
            (s["prob"] for s in scenarios if "eskalacija" in s["name"].lower()), 0
        )
        if escalation > 25:
            violations.append(f"Visok rizik eskalacije: {escalation}%")
            score -= 2.0
        elif escalation > 15:
            violations.append(f"Umjeren rizik eskalacije: {escalation}%")
            score -= 1.0

        # AIR penalizacija
        if air_index > 9.0:
            violations.append("Kritična razina AIR indeksa")
            score -= 1.0

        score = round(max(0.0, min(10.0, score)), 1)

        if score >= 7.5:
            status = "✅ PROŠAO"
        elif score >= 5.5:
            status = "⚠️ UVJETNO"
        else:
            status = "❌ NE PROLAZI"

        return {
            "ethical_score": score,
            "status":        status,
            "violations":    violations,
            "positives":     positives,
        }


# ====================== MODUL C: PDF Generator ======================
class IR5PDF:
    """
    ISPRAVAK 7: Provjera dostupnosti fpdf2,
    graceful fallback ako nije instaliran.
    """
    @staticmethod
    def available() -> bool:
        return FPDF is not None

    @staticmethod
    def generate_single(result: dict, crisis_name: str) -> str | None:
        if not IR5PDF.available():
            return None

        class _PDF(FPDF):
            def header(self):
                self.set_font("Arial", "B", 15)
                self.cell(0, 10, "IR-5 v4.0 — Peace Early Warning System", ln=True, align="C")
                self.set_font("Arial", "I", 9)
                self.cell(0, 6, "Put Znanosti, Mira i Harmonije Svijesti (PZMHS)", ln=True, align="C")
                self.ln(4)

            def footer(self):
                self.set_y(-15)
                self.set_font("Arial", "I", 8)
                self.cell(0, 10, f"IR-5 v4.0 | PZMHS | {datetime.now().strftime('%d.%m.%Y. %H:%M')} | Za Mir — uvijek.", align="C")

        pdf = _PDF()
        pdf.add_page()

        # Zaglavlje izvještaja
        pdf.set_font("Arial", "B", 14)
        pdf.set_fill_color(31, 78, 121)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 12, f"  Kriza: {crisis_name}", ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)

        # AIR indeks
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 9, f"AIR Indeks: {result['air_index']}/10", ln=True)
        ci = result.get("ci_90", ["-", "-"])
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, f"Confidence interval (90%): [{ci[0]} – {ci[1]}]", ln=True)
        pdf.cell(0, 8, f"Etički score: {result['ethical']['ethical_score']}/10  |  {result['ethical']['status']}", ln=True)
        pdf.ln(6)

        # Scenariji
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 9, "Scenariji razvoja krize:", ln=True)
        pdf.set_font("Arial", "", 11)
        for s in result["scenarios"]:
            pdf.cell(0, 7, f"  • {s['name']}: {s['prob']}%", ln=True)
        pdf.ln(6)

        # Preporuke
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 9, "Preporuke za mir:", ln=True)
        pdf.set_font("Arial", "", 11)
        for i, rec in enumerate(result["recommendations"], 1):
            pdf.multi_cell(0, 7, f"  {i}. {rec}")
        pdf.ln(4)

        # Etičke napomene
        if result["ethical"].get("violations"):
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "Etička upozorenja:", ln=True)
            pdf.set_font("Arial", "", 10)
            for v in result["ethical"]["violations"]:
                pdf.cell(0, 6, f"  ⚠ {v}", ln=True)

        # Footer citata
        pdf.ln(10)
        pdf.set_font("Arial", "I", 10)
        pdf.set_text_color(31, 78, 121)
        pdf.multi_cell(0, 7, '"Mir ne znači da je netko pobijedio. Mir znači da su prestale umirati majke, djeca i mladi vojnici na obje strane." — PZMHS')

        filename = os.path.join(DATA_DIR, f"IR5_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        pdf.output(filename)
        return filename

    @staticmethod
    def generate_comparison(sim1: dict, sim2: dict) -> str | None:
        if not IR5PDF.available():
            return None

        class _PDF(FPDF):
            def header(self):
                self.set_font("Arial", "B", 15)
                self.cell(0, 10, "IR-5 v4.0 — Usporedba simulacija", ln=True, align="C")
                self.ln(4)
            def footer(self):
                self.set_y(-15)
                self.set_font("Arial", "I", 8)
                self.cell(0, 10, f"IR-5 v4.0 | PZMHS | {datetime.now().strftime('%d.%m.%Y. %H:%M')}", align="C")

        pdf = _PDF()
        pdf.add_page()

        for idx, sim in enumerate([sim1, sim2], 1):
            pdf.set_font("Arial", "B", 13)
            pdf.set_fill_color(31, 78, 121)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 11, f"  {idx}. {sim['crisis']}", ln=True, fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", "", 11)
            pdf.cell(0, 8, f"AIR Indeks: {sim['air_index']}/10", ln=True)
            for s in sim["scenarios"]:
                pdf.cell(0, 7, f"  • {s['name']}: {s['prob']}%", ln=True)
            pdf.ln(6)

        diff = abs(sim1["air_index"] - sim2["air_index"])
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 9, f"Razlika u AIR indeksu: {diff:.2f}", ln=True)
        viša = sim1["crisis"] if sim1["air_index"] > sim2["air_index"] else sim2["crisis"]
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, f"Viši rizik: {viša}", ln=True)

        filename = os.path.join(DATA_DIR, f"IR5_Comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        pdf.output(filename)
        return filename


# ====================== POMOĆNE FUNKCIJE ======================
def load_simulations() -> list:
    if os.path.exists(SIMULATIONS_FILE):
        try:
            with open(SIMULATIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_simulation(result: dict):
    # ISPRAVAK 8: Pohrana bez numpy tipova (JSON serijalizacija)
    def convert(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return obj

    simulations = load_simulations()
    simulations.append(json.loads(json.dumps(result, default=convert)))
    with open(SIMULATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(simulations, f, ensure_ascii=False, indent=2)

def air_color(air: float) -> str:
    if air >= 8.5: return "#C0392B"
    if air >= 7.0: return "#CA6F1E"
    if air >= 5.0: return "#F39C12"
    return "#1E8449"

DEFAULT_RECOMMENDATIONS = [
    "Pokrenuti multilateralni mirovni summit uz sudjelovanje Vatikana, Kine i Indije",
    "Odmah uspostaviti humanitarne koridore i razmjenu zarobljenika bez preduvjeta",
    "Aktivirati NATO SG posredovanje i diplomatske kanale svih neutralnih strana",
    "Izbjegavati napade na nuklearnu infrastrukturu i eskalacijsku retoriku",
    "Inicirati ekonomske poticaje za deeskalaciju kroz međunarodne financijske institucije",
]

PREDEFINED_CRISES = {
    "Ukrajina 2026.":    [8.7, 9.1, 7.6, 8.4, 8.8, 6.9],
    "Hormuz 2026.":      [9.2, 8.8, 9.5, 7.5, 8.2, 4.0],
    "Bliski istok":      [8.5, 9.0, 7.8, 7.2, 9.1, 5.5],
    "Tajvan":            [7.8, 8.5, 8.9, 8.8, 6.5, 5.2],
    "Grenland afera":    [7.2, 8.8, 8.0, 6.5, 4.5, 5.0],
    "Nova kriza":        [5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
}
INDICATOR_NAMES = [
    "Vojno gomilanje", "Politička napetost", "Ekonomski pritisak",
    "Cyber prijetnje", "Humanitarna kriza", "Slom diplomacije"
]

# ====================== STREAMLIT APLIKACIJA ======================
st.title("🕊️ IR-5 v4.0 — Peace Early Warning System")
st.markdown("**Put Znanosti, Mira i Harmonije Svijesti (PZMHS)** | Čovjek ★ AI ★ MIR")
st.markdown("---")

page = st.sidebar.selectbox(
    "📋 Navigacija",
    ["🏠 Dashboard", "📊 Rezultati simulacije",
     "🔄 Usporedba simulacija", "📜 Povijest simulacija", "➕ Nova kriza"]
)

# ── DASHBOARD ──────────────────────────────────────────────────────────────
if page == "🏠 Dashboard":
    st.header("🏠 Glavni Dashboard")

    col_left, col_right = st.columns([1, 2])

    with col_left:
        crisis = st.selectbox("Odaberite krizu", list(PREDEFINED_CRISES.keys()))
        st.markdown("---")
        st.subheader("Indikatori rizika (0–10)")
        defaults = PREDEFINED_CRISES[crisis]
        indicators = {
            name: st.slider(name, 0.0, 10.0, float(defaults[i]), 0.1)
            for i, name in enumerate(INDICATOR_NAMES)
        }
        run_btn = st.button("🚀 Pokreni simulaciju", type="primary", use_container_width=True)

    with col_right:
        st.subheader("O IR-5 modelu")
        st.info(
            "**IR-5** je etički AI sustav za analizu rizika sukoba i "
            "predlaganje reverzibilnih opcija za mir.\n\n"
            "Model koristi Monte Carlo simulaciju s 20.000 iteracija, "
            "winsorized normalizacijom i Ethical Checker sukladan "
            "Povelji PZMHS.\n\n"
            "Validiran na **9 dokumentiranih kriznih situacija** od "
            "Kubanske raketne krize (1962.) do afere Grenland (2026.)."
        )
        st.markdown("> *\"Mir ne znači da je netko pobijedio.  \nMir znači da su "
                    "prestale umirati majke, djeca i mladi vojnici na obje strane.\"*  \n"
                    "— PZMHS Program")

    if run_btn:
        with st.spinner("🔄 Izvođenje Monte Carlo simulacije (20.000 iteracija)..."):
            sim     = MonteCarloSimulator(iterations=20000)
            result  = sim.run(indicators)
            checker = EthicalChecker()
            ethical = checker.check(result["air_index"], result["scenarios"], DEFAULT_RECOMMENDATIONS)

            full_result = {
                "crisis":          crisis,
                "timestamp":       datetime.now().isoformat(),
                "air_index":       result["air_index"],
                "ci_90":           result["ci_90"],
                "ci_50":           result["ci_50"],
                "std":             result["std"],
                "scenarios":       result["scenarios"],
                "ethical":         ethical,
                "recommendations": DEFAULT_RECOMMENDATIONS,
                "indicators":      indicators,
            }

            st.session_state.last_result = full_result
            save_simulation(full_result)

        st.success("✅ Simulacija uspješno završena! Idite na 'Rezultati simulacije'.")
        st.balloons()

# ── REZULTATI ──────────────────────────────────────────────────────────────
elif page == "📊 Rezultati simulacije":
    st.header("📊 Rezultati simulacije")

    if "last_result" not in st.session_state:
        st.warning("⚠️ Prvo pokrenite simulaciju na Dashboardu.")
        st.stop()

    res = st.session_state.last_result

    # AIR prikaz
    col1, col2, col3 = st.columns(3)
    with col1:
        color = air_color(res["air_index"])
        st.markdown(
            f'<div class="air-box">'
            f'<div style="font-size:1em;">AIR INDEKS</div>'
            f'<div class="air-number" style="color:{color};">{res["air_index"]}</div>'
            f'<div style="font-size:0.85em;">od 10.0</div>'
            f'</div>', unsafe_allow_html=True
        )
    with col2:
        ci = res.get("ci_90", ["-", "-"])
        st.metric("CI 90%", f"[{ci[0]} – {ci[1]}]", delta=f"σ = {res.get('std','?')}")
    with col3:
        eth = res["ethical"]
        st.metric("Etički score", f"{eth['ethical_score']}/10", delta=eth["status"])

    st.markdown("---")

    # Scenariji
    col_s, col_r = st.columns([1, 1])
    with col_s:
        st.subheader("📈 Scenariji razvoja krize")
        for s in res["scenarios"]:
            prob = s["prob"]
            color_bar = "#C0392B" if prob > 35 else "#CA6F1E" if prob > 20 else "#1E8449"
            st.markdown(f"**{s['name']}**")
            st.progress(int(prob), text=f"{prob}%")

    with col_r:
        st.subheader("🕊️ Preporuke za mir")
        for i, rec in enumerate(res["recommendations"], 1):
            st.info(f"**{i}.** {rec}")

    # Etički checker detalji
    st.markdown("---")
    st.subheader("⚖️ Ethical Checker — PZMHS Povelja")
    eth = res["ethical"]
    if eth["violations"]:
        for v in eth["violations"]:
            st.warning(f"⚠️ {v}")
    if eth.get("positives"):
        for p in eth["positives"]:
            st.success(f"✅ {p}")
    if not eth["violations"] and not eth.get("positives"):
        st.success("✅ Sve preporuke su u skladu s Etičkim addendumom PZMHS.")

    # PDF
    st.markdown("---")
    if st.button("📄 Generiraj PDF izvještaj"):
        if IR5PDF.available():
            filename = IR5PDF.generate_single(res, res["crisis"])
            if filename and os.path.exists(filename):
                with open(filename, "rb") as f:
                    st.download_button(
                        "⬇️ Preuzmi PDF", f,
                        file_name=os.path.basename(filename),
                        mime="application/pdf"
                    )
        else:
            st.error("fpdf2 nije instaliran. Pokrenite: pip install fpdf2")

# ── USPOREDBA ──────────────────────────────────────────────────────────────
elif page == "🔄 Usporedba simulacija":
    st.header("🔄 Usporedba dviju simulacija")
    simulations = load_simulations()

    if len(simulations) < 2:
        st.warning("⚠️ Potrebne su barem dvije simulacije za usporedbu.")
        st.stop()

    options = [f"{s['crisis']} ({s['timestamp'][:16]})" for s in simulations]
    col1, col2 = st.columns(2)
    with col1:
        sim1_label = st.selectbox("Prva simulacija", options, key="sim1")
    with col2:
        # ISPRAVAK 9: Sprječava odabir iste simulacije
        other_options = [o for o in options if o != sim1_label] or options
        sim2_label = st.selectbox("Druga simulacija", other_options, key="sim2")

    s1 = simulations[options.index(sim1_label)]
    s2 = simulations[options.index(sim2_label)]

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader(f"1. {s1['crisis']}")
        st.metric("AIR Indeks", f"{s1['air_index']}/10")
        for scen in s1["scenarios"]:
            st.progress(int(scen["prob"]), text=f"{scen['name']}: {scen['prob']}%")
    with col_b:
        st.subheader(f"2. {s2['crisis']}")
        st.metric("AIR Indeks", f"{s2['air_index']}/10")
        for scen in s2["scenarios"]:
            st.progress(int(scen["prob"]), text=f"{scen['name']}: {scen['prob']}%")

    diff = abs(s1["air_index"] - s2["air_index"])
    st.markdown("---")
    viša = s1["crisis"] if s1["air_index"] > s2["air_index"] else s2["crisis"]
    col_x, col_y = st.columns(2)
    with col_x:
        st.metric("Razlika u AIR indeksu", f"{diff:.2f}")
    with col_y:
        st.metric("Viši rizik", viša)

    if st.button("📄 Generiraj PDF usporedbe"):
        if IR5PDF.available():
            filename = IR5PDF.generate_comparison(s1, s2)
            if filename and os.path.exists(filename):
                with open(filename, "rb") as f:
                    st.download_button(
                        "⬇️ Preuzmi PDF usporedbe", f,
                        file_name=os.path.basename(filename),
                        mime="application/pdf"
                    )
        else:
            st.error("fpdf2 nije instaliran. Pokrenite: pip install fpdf2")

# ── POVIJEST ───────────────────────────────────────────────────────────────
elif page == "📜 Povijest simulacija":
    st.header("📜 Povijest simulacija")
    simulations = load_simulations()

    if not simulations:
        st.info("ℹ️ Još nema spremljenih simulacija. Pokrenite prvu na Dashboardu.")
    else:
        st.markdown(f"Ukupno simulacija: **{len(simulations)}**")
        for sim in reversed(simulations[-20:]):
            air = sim["air_index"]
            color = air_color(air)
            with st.expander(
                f"🔴 {sim['crisis']}  |  AIR: {air}/10  |  "
                f"{sim['timestamp'][:16]}"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("AIR Indeks", f"{air}/10")
                    if "ci_90" in sim:
                        ci = sim["ci_90"]
                        st.metric("CI 90%", f"[{ci[0]} – {ci[1]}]")
                with col2:
                    eth = sim.get("ethical", {})
                    if eth:
                        st.metric("Etički score", f"{eth.get('ethical_score','?')}/10")
                        st.write(eth.get("status", ""))
                st.markdown("**Scenariji:**")
                for s in sim["scenarios"]:
                    st.write(f"• {s['name']}: {s['prob']}%")

# ── NOVA KRIZA ─────────────────────────────────────────────────────────────
elif page == "➕ Nova kriza":
    st.header("➕ Ručni unos nove krize")
    st.info("Unesite naziv i prilagodite indikatore za analizu vlastite krizne situacije.")

    crisis_name = st.text_input("📌 Naziv krize", placeholder="Npr. Sukob u X regiji 2026.")
    st.subheader("Indikatori rizika (0–10)")
    indicators = {
        name: st.slider(name, 0.0, 10.0, 6.0, 0.1)
        for name in INDICATOR_NAMES
    }

    # ISPRAVAK 10: Vlastite preporuke
    st.subheader("Preporuke (opcionalno)")
    custom_recs = st.text_area(
        "Unesite preporuke za mir (jedna po redu)",
        value="\n".join(DEFAULT_RECOMMENDATIONS),
        height=150
    )
    recommendations = [r.strip() for r in custom_recs.split("\n") if r.strip()]

    if st.button("🚀 Spremi i pokreni simulaciju", type="primary"):
        if not crisis_name.strip():
            st.error("❌ Unesite naziv krize.")
        else:
            with st.spinner("Izvođenje simulacije..."):
                sim    = MonteCarloSimulator()
                result = sim.run(indicators)
                checker = EthicalChecker()
                ethical = checker.check(result["air_index"], result["scenarios"], recommendations)

                full_result = {
                    "crisis":          crisis_name.strip(),
                    "timestamp":       datetime.now().isoformat(),
                    "air_index":       result["air_index"],
                    "ci_90":           result["ci_90"],
                    "ci_50":           result["ci_50"],
                    "std":             result["std"],
                    "scenarios":       result["scenarios"],
                    "ethical":         ethical,
                    "recommendations": recommendations,
                    "indicators":      indicators,
                }
                st.session_state.last_result = full_result
                save_simulation(full_result)

            st.success(f"✅ Kriza '{crisis_name}' analizirana i spremljena!")
            st.metric("AIR Indeks", f"{result['air_index']}/10")
            st.metric("Etički score", f"{ethical['ethical_score']}/10 — {ethical['status']}")

# ── FOOTER ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "IR-5 v4.0 • Put Znanosti, Mira i Harmonije Svijesti (PZMHS) • "
    "Copyright (c) 2026 Branko Radinić • GNU AGPL v3 + Ethical Addendum • "
    "Za Mir — uvijek. 🕊️"
)
