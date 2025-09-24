# doser_app.py — v2.7 (top banner full-width + fix histórico)
import io, json, math, datetime as dt
import pandas as pd
import streamlit as st

# ===================== Config base (cores "default") =====================
st.set_page_config(page_title="Doser • Aquários", page_icon="💧", layout="wide")

PRIMARY_BG = "#0b1220"
CARD_BG    = "#0f172a"
BORDER     = "#1f2937"
TEXT       = "#e2e8f0"
MUTED      = "#94a3b8"
ACCENT     = "#60a5fa"  # será sobrescrito pelo tema dinâmico
GOOD       = "#22c55e"
WARN       = "#fbbf24"
BAD        = "#ef4444"

# ===================== CSS base =====================
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
  :root {{
    --primary: {ACCENT};
    --text: {TEXT}; --muted:{MUTED};
    --bg: {PRIMARY_BG}; --card: {CARD_BG}; --border:{BORDER};
    --good:{GOOD}; --warn:{WARN}; --bad:{BAD};
  }}
  html, body, .stApp {{ font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }}
  .stApp {{
    background: radial-gradient(1100px 500px at 10% -10%, #0e1a35 10%, var(--bg) 60%);
    color: var(--text);
  }}

  /* FULL-WIDTH TOP BANNER */
  .block-container {{ padding-top: 0rem; }}
  .top-banner {{
    width: 100vw;
    margin-left: calc(-50vw + 50%); /* sai das margens do container */
    border-bottom: 1px solid var(--border);
  }}
  .top-banner svg {{ display:block; width:100%; height: 160px; }}
  @media (max-width: 640px) {{
    .top-banner svg {{ height: 110px; }}
  }}
  @media (max-width: 420px) {{
    .top-banner svg {{ height: 90px; }}
  }}

  .hero {{
    padding: 18px 18px 8px; border-bottom:1px solid var(--border);
    background: linear-gradient(180deg, rgba(96,165,250,0.08), rgba(0,0,0,0));
    margin-bottom: 6px;
  }}
  .hero h1 {{ margin:0; font-size: 24px; letter-spacing:0.2px; }}
  .muted {{ color: var(--muted); font-size: 13px; }}

  .card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 14px; padding: 14px; margin: 8px 0;
  }}
  .hr {{ border-top:1px solid var(--border); margin: 10px 0; }}
  .pill {{ display:inline-block; padding:6px 10px; border-radius:999px;
           border:1px solid var(--border); background:#111827; color:#9ca3af; margin-right:6px; font-size:12px; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}

  /* KPI */
  .kpi {{
    display:flex; flex-direction:column; gap:6px; padding:14px; border-radius:16px;
    border:1px solid var(--border); background:linear-gradient(180deg, rgba(2,6,23,0.4), rgba(2,6,23,0.2));
    box-shadow: 0 1px 0 rgba(255,255,255,0.03) inset;
  }}
  .kpi .label {{ font-size:12px; color:var(--muted); }}
  .kpi .value {{ font-size:22px; font-weight:700; letter-spacing:0.2px; }}
  .kpi .sub {{ font-size:12px; color:var(--muted); }}
  .good {{ color: var(--good) !important; }}
  .warn {{ color: var(--warn) !important; }}
  .bad  {{ color: var(--bad) !important;  }}

  /* Badges */
  .badge-row {{ display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 10px; }}
  .badge {{
    display:inline-flex; align-items:center; gap:8px;
    padding:6px 12px; border-radius:999px; font-weight:600;
    border:1px solid var(--border); background:#0b1220; color:#e5e7eb;
    box-shadow: 0 1px 0 rgba(255,255,255,0.03) inset;
    transition: transform .2s ease, box-shadow .2s ease, filter .2s ease;
  }}
  .badge .emoji {{ font-size:16px; line-height:1; animation: float 6s ease-in-out infinite; }}
  .badge:hover {{ transform: translateY(-1px) scale(1.02); box-shadow: 0 6px 20px rgba(0,0,0,.35); filter: saturate(1.05); }}
  .badge.green {{ background:linear-gradient(180deg, rgba(34,197,94,.18), rgba(2,6,23,.25)); border-color:#14532d; color:#d1fae5; }}
  .badge.pink  {{ background:linear-gradient(180deg, rgba(236,72,153,.18), rgba(2,6,23,.25)); border-color:#831843; color:#ffe4f1; }}
  .badge.blue  {{ background:linear-gradient(180deg, rgba(59,130,246,.18), rgba(2,6,23,.25)); border-color:#1e3a8a; color:#dbeafe; }}
  .badge.slate {{ background:linear-gradient(180deg, rgba(100,116,139,.18), rgba(2,6,23,.25)); border-color:#334155; color:#e2e8f0; }}

  @keyframes float {{
    0%,100% {{ transform: translateY(0); }}
    50%     {{ transform: translateY(-2px); }}
  }}

  /* Tabelas */
  table.dataframe {{ border-collapse: collapse; width: 100%; }}
  table.dataframe th, table.dataframe td {{ border: 1px solid var(--border); padding: 6px 8px; }}
  table.dataframe th {{ background:#0d162c; color:#e5e7eb; }}
</style>
""", unsafe_allow_html=True)

# ============== Tema dinâmico ==============
def theme_css(mode: str) -> str:
    if mode == "Doce + Camarões":
        return "<style>:root{--primary:#22c55e}</style>"
    else:
        return "<style>:root{--primary:#60a5fa}</style>"

# ============== Helpers comuns ==============
def kpi(title, value, subtitle="", cls=""):
    cls_class = f" {cls}" if cls else ""
    return f"""
    <div class="kpi">
      <div class="label">{title}</div>
      <div class="value{cls_class}">{value}</div>
      <div class="sub">{subtitle}</div>
    </div>
    """

def render_badges(mode: str) -> str:
    if mode == "Doce + Camarões":
        return """
        <div class="badge-row">
          <span class="badge green"><span class="emoji">🌿</span>Plantado</span>
          <span class="badge pink"><span class="emoji">🦐</span>Camarões</span>
          <span class="badge slate"><span class="emoji">⚗️</span>Macro & Micro</span>
        </div>
        """
    else:
        return """
        <div class="badge-row">
          <span class="badge blue"><span class="emoji">🪸</span>Reef</span>
          <span class="badge slate"><span class="emoji">⚗️</span>Fusion 1 & 2</span>
        </div>
        """

def render_top_banner_svg(mode: str) -> str:
    """Banner topo full-width com ondas e gradiente por modo."""
    if mode == "Doce + Camarões":
        stops = [("#34d399", "0%"), ("#60a5fa", "60%"), ("#f472b6", "100%")]
        overlay = "#0ea5e9"
    else:
        stops = [("#60a5fa", "0%"), ("#3b82f6", "45%"), ("#7c3aed", "100%")]
        overlay = "#22d3ee"
    grad_stops = "\n".join([f'<stop offset="{pos}" stop-color="{col}" stop-opacity="1"/>' for col, pos in stops])
    return f"""
    <div class="top-banner">
      <svg viewBox="0 0 1200 160" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
        <defs><linearGradient id="gradMain" x1="0" y1="0" x2="1" y2="0">{grad_stops}</linearGradient></defs>
        <rect width="1200" height="160" fill="url(#gradMain)"/>
        <path d="M0,90 C300,150 900,30 1200,90 L1200,160 L0,160 Z" fill="{overlay}" opacity="0.25"/>
        <path d="M0,110 C300,170 900,50 1200,110 L1200,160 L0,160 Z" fill="white" opacity="0.06"/>
      </svg>
    </div>
    """

# -------- Plantado helpers --------
def conversions(density_g_per_ml: float, pctN: float, pctP: float):
    mgN_per_mL = pctN/100.0 * density_g_per_ml * 1000.0
    mgP_per_mL = pctP/100.0 * density_g_per_ml * 1000.0
    mgNO3_per_mL = mgN_per_mL * (62.0/14.0)
    mgPO4_per_mL = mgP_per_mL * (95.0/31.0)
    return mgNO3_per_mL, mgPO4_per_mL

def schedule_days(start_day: str, freq: int):
    days = ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"]
    idx = days.index(start_day)
    order = [days[(idx+i)%7] for i in range(7)]
    if freq == 1:  micros = [order[2]]
    elif freq == 2: micros = [order[2], order[5]]
    elif freq == 3: micros = [order[1], order[3], order[5]]
    else:           micros = []
    return order, micros

def ratio_redfield(no3_ppm: float, po4_ppm: float):
    if po4_ppm <= 0: return math.inf, "bad"
    r = no3_ppm / po4_ppm
    if 8 <= r <= 15: status = "good"
    elif 6 <= r <= 18: status = "warn"
    else: status = "bad"
    return r, status

# -------- Reef helpers --------
def dkh_from_meq(meq): return meq * 2.8
def meq_from_dkh(dkh): return dkh / 2.8

# ===================== Header & modo =====================
# seletor de modo (topo)
colh1, colh2 = st.columns([1,1.2])
with colh2:
    mode = st.radio("Tipo de aquário", ["Doce + Camarões", "Marinho (Reef)"], horizontal=True, index=0)

# injeta tema e banner por modo
st.markdown(theme_css(mode), unsafe_allow_html=True)
st.markdown(render_top_banner_svg(mode), unsafe_allow_html=True)

# título + badges dentro do container (abaixo do banner)
with colh1:
    st.markdown("""
    <div class="hero">
      <h1>💧 Doser – Aquários</h1>
      <div class="muted">Escolha o modo: Plantado + Camarões ou Marinho (Reef). Cálculos e UI se adaptam ao modo.</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(render_badges(mode), unsafe_allow_html=True)

# ===================== SIDEBAR (inputs) =====================
with st.sidebar:
    st.markdown("## ⚙️ Parâmetros do aquário")
    vol = st.number_input("Volume útil (L)", min_value=1.0, value=50.0, step=1.0)

    if mode == "Doce + Camarões":
        do_tpa = st.checkbox("Vou fazer TPA agora", value=True)
        tpa = st.number_input("Volume da TPA (L)", min_value=0.0, value=20.0 if do_tpa else 0.0, step=1.0, disabled=not do_tpa)

        st.markdown("---")
        st.markdown("### 🧪 Testes atuais")
        pH_now  = st.number_input("pH", min_value=4.5, max_value=8.5, value=6.8, step=0.1, format="%.1f")
        no3_now = st.number_input("NO₃ (ppm)", min_value=0.0, value=10.0, step=0.5)
        po4_now = st.number_input("PO₄ (ppm)", min_value=0.0, value=0.40, step=0.05)
        gh_now  = st.number_input("GH (°dH)", min_value=0.0, value=6.0, step=0.5)
        kh_now  = st.number_input("KH (°dKH)", min_value=0.0, value=2.0, step=0.5)

        st.markdown("---")
        st.markdown("### 🎯 Alvo da correção (macro)")
        target_mode = st.radio("Nutriente alvo", ["PO₄ (recomendado)", "NO₃"], index=0)
        if target_mode.startswith("PO₄"):
            po4_target = st.number_input("Alvo de PO₄ (ppm)", min_value=0.0, value=0.90, step=0.05)
            no3_min, no3_max = st.select_slider(
                "Faixa desejada de NO₃ (ppm)",
                options=[8,9,10,11,12,13,14,15,16,17,18,19,20],
                value=(10,15)
            )
            no3_target = (no3_min + no3_max)/2
        else:
            no3_target = st.number_input("Alvo de NO₃ (ppm)", min_value=0.0, value=12.0, step=0.5)
            po4_min, po4_max = st.select_slider(
                "Faixa desejada de PO₄ (ppm)",
                options=[0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2],
                value=(0.6,1.0)
            )
            po4_target = (po4_min + po4_max)/2

        st.markdown("---")
        st.markdown("### 🧪 Macro (líquido)")
        pctN = st.number_input("% N (elementar)", min_value=0.0, value=1.37, step=0.01, format="%.2f")
        pctP = st.number_input("% P (elementar)", min_value=0.0, value=0.34, step=0.01, format="%.2f")
        density = st.number_input("Densidade (g/mL)", min_value=0.5, value=1.00, step=0.01, format="%.2f")

        st.markdown("---")
        st.markdown("### 📅 Consumo & Agenda")
        tpa_day = st.selectbox("Dia da TPA (para agenda)", options=["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"], index=1)
        po4_daily = st.number_input("Consumo diário de PO₄ (ppm/dia)", min_value=0.0, value=0.20, step=0.05, format="%.2f")
        no3_daily = st.number_input("Consumo diário de NO₃ (ppm/dia)", min_value=0.0, value=1.50, step=0.10, format="%.2f")
        micro_per30 = st.number_input("Micro mL/30 L (por aplicação)", min_value=0.0, value=1.25, step=0.05, format="%.2f")
        micro_freq = st.selectbox("Aplicações de micro/semana", options=[1,2,3], index=1)

        st.markdown("---")
        st.markdown("### 🌿 Fertilizante de Nitrogênio (isolado)")
        dose_mL_per_100L = st.number_input("mL por dose (por 100 L)", min_value=0.1, value=6.0, step=0.1)
        adds_ppm_per_100L = st.number_input("ppm de NO₃ adicionados por dose (100 L)", min_value=0.1, value=4.8, step=0.1)

        st.markdown("---")
        st.markdown("### 🧱 Alvos GH & KH (ReeFlowers)")
        gh_target = st.number_input("GH alvo (°dH)", min_value=0.0, value=7.0, step=0.5)
        g_per_dGH_100L = st.number_input("Shrimp Minerals (pó): g p/ +1°dGH /100 L", min_value=0.1, value=2.0, step=0.1)
        remin_mix_to = st.number_input("Remineralizar água da TPA até GH (°dH)", min_value=0.0, value=gh_target, step=0.5)
        kh_target = st.number_input("KH alvo (°dKH)", min_value=0.0, value=3.0, step=0.5)
        ml_khplus_per_dKH_100L = st.number_input("KH+ (mL) p/ +1°dKH /100 L", min_value=1.0, value=30.0, step=1.0)

    else:
        st.markdown("---")
        st.markdown("### 🧪 Testes atuais (Reef)")
        kh_now = st.number_input("KH atual (°dKH)", min_value=0.0, value=8.0, step=0.1)
        ca_now = st.number_input("Cálcio atual (ppm)", min_value=200.0, value=420.0, step=5.0)
        mg_now = st.number_input("Magnésio atual (ppm)", min_value=800.0, value=1300.0, step=10.0)

        st.markdown("---")
        st.markdown("### 🎯 Alvos (Reef)")
        kh_target = st.number_input("KH ideal (°dKH)", min_value=6.0, value=9.0, step=0.1)
        ca_target = st.number_input("Ca ideal (ppm)", min_value=340.0, value=430.0, step=5.0)
        mg_target = st.number_input("Mg ideal (ppm)", min_value=1100.0, value=1300.0, step=10.0)

        st.markdown("---")
        st.markdown("### 📉 Consumo diário (estimado)")
        kh_cons = st.number_input("Consumo diário de KH (°dKH/dia)", min_value=0.0, value=0.20, step=0.05)
        ca_cons = st.number_input("Consumo diário de Ca (ppm/dia)", min_value=0.0, value=2.0, step=0.5)
        mg_cons = st.number_input("Consumo diário de Mg (ppm/dia)", min_value=0.0, value=1.0, step=0.5)

        st.markdown("---")
        st.markdown("### 🧪 Potência (Fusion 1 & 2)")
        ca_ppm_per_ml_per_25L = st.number_input("Fusion 1: +ppm Ca por 1 mL/25 L", min_value=0.1, value=4.0, step=0.1)
        alk_meq_per_ml_per_25L = st.number_input("Fusion 2: +meq/L por 1 mL/25 L", min_value=0.01, value=0.176, step=0.001)
        max_ml_per_25L_day = st.number_input("Máx. mL por 25 L por dia (cada)", min_value=0.5, value=4.0, step=0.5)
        max_kh_raise_net = st.number_input("Limite de aumento líquido de KH por dia (°dKH)", min_value=0.2, value=1.0, step=0.1)

# ======================================================================
# ===================== DOCE + CAMARÕES ================================
# ======================================================================
if mode == "Doce + Camarões":
    tpa_eff = tpa if do_tpa else 0.0
    f_dilution = 1.0 - (tpa_eff/vol)

    no3_base = no3_now * f_dilution
    po4_base = po4_now * f_dilution

    mgNO3_per_mL, mgPO4_per_mL = conversions(density, pctN, pctP)
    dNO3_per_mL = mgNO3_per_mL / vol
    dPO4_per_mL = mgPO4_per_mL / vol

    if target_mode.startswith("PO₄"):
        dPO4_needed = max(0.0, po4_target - po4_base)
        mL_now = (dPO4_needed / dPO4_per_mL) if dPO4_per_mL > 0 else 0.0
        po4_after = po4_base + mL_now * dPO4_per_mL
        no3_after = no3_base + mL_now * dNO3_per_mL
        warn_po4 = False
        warn_no3 = not (no3_min <= no3_after <= no3_max)
    else:
        dNO3_needed = max(0.0, no3_target - no3_base)
        mL_now = (dNO3_needed / dNO3_per_mL) if dNO3_per_mL > 0 else 0.0
        no3_after = no3_base + mL_now * dNO3_per_mL
        po4_after = po4_base + mL_now * dPO4_per_mL
        warn_no3 = False
        warn_po4 = not (po4_min <= po4_after <= po4_max)

    mL_day_macro = (po4_daily / dPO4_per_mL) if dPO4_per_mL > 0 else 0.0
    no3_from_daily = mL_day_macro * dNO3_per_mL
    no3_drift = no3_from_daily - no3_daily

    r_before, status_before = ratio_redfield(no3_base, po4_base)
    r_after,  status_after  = ratio_redfield(no3_after, po4_after)

    # N isolado (6 mL/100L -> +4.8 ppm NO3)
    ppm_per_mL_per_100L = adds_ppm_per_100L / dose_mL_per_100L
    ppm_per_mL_tank = ppm_per_mL_per_100L * (100.0 / vol)
    need_N_by_ratio = (r_after < 8)
    need_N_by_range = (target_mode.startswith("PO₄") and (no3_after < no3_min))
    suggest_N = (ppm_per_mL_tank > 0) and (need_N_by_ratio or need_N_by_range)
    N_target_ppm = (no3_min + no3_max)/2 if target_mode.startswith("PO₄") else no3_target
    N_dose_mL = max(0.0, (N_target_ppm - no3_after) / ppm_per_mL_tank) if suggest_N else 0.0

    # KPIs
    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        st.markdown(kpi("🎯 Dose agora (macro)", f"{mL_now:.2f} mL", "para atingir o alvo"), unsafe_allow_html=True)
    with kpi_cols[1]:
        st.markdown(kpi("🗓️ Manutenção diária", f"{mL_day_macro:.2f} mL/dia", "macro baseado em PO₄"), unsafe_allow_html=True)
    with kpi_cols[2]:
        rf_cls = "good" if status_after=="good" else ("warn" if status_after=="warn" else "bad")
        st.markdown(kpi("📈 Redfield pós-dose", f"{r_after:.2f}:1", "NO₃:PO₄ (ppm)", rf_cls), unsafe_allow_html=True)
    with kpi_cols[3]:
        st.markdown(kpi("GH alvo", f"{gh_target:.0f} °dH", "ReeFlowers (pó)"), unsafe_allow_html=True)
    with kpi_cols[4]:
        st.markdown(kpi("KH alvo", f"{kh_target:.0f} °dKH", "KH+"), unsafe_allow_html=True)

    # Resumo macro
    left, right = st.columns([1.1, 1])
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## Resumo (macro)")
        st.write(f"{'Com' if do_tpa else 'Sem'} TPA agora • Diluição aplicada: **{f_dilution*100:.1f}%**")
        st.write(f"NO₃: {no3_now:.2f} → **{no3_base:.2f} ppm**  |  PO₄: {po4_now:.2f} → **{po4_base:.2f} ppm**")
        st.write(f"Fertilizante: **{pctN:.2f}% N**, **{pctP:.2f}% P**, densidade **{density:.2f} g/mL**")
        st.write(f"→ em {vol:.0f} L: **{dPO4_per_mL:.3f} ppm PO₄/mL** | **{dNO3_per_mL:.3f} ppm NO₃/mL**")
        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
        st.write(f"**Correção agora:** **{mL_now:.2f} mL**  → após dose: NO₃ **{no3_after:.2f} ppm**, PO₄ **{po4_after:.2f} ppm**.")
        if target_mode.startswith("PO₄") and (warn_no3):
            st.markdown('<span class="bad">Atenção:</span> NO₃ fora da faixa desejada.', unsafe_allow_html=True)
        if (not target_mode.startswith("PO₄")) and (warn_po4):
            st.markdown('<span class="bad">Atenção:</span> PO₄ fora da faixa desejada.', unsafe_allow_html=True)
        if suggest_N and N_dose_mL > 0.0001:
            st.write(
                f"Adicionar **{N_dose_mL:.2f} mL** de fertilizante de **Nitrogênio** "
                f"para atingir **{N_target_ppm:.2f} ppm** de **NO₃** desejado."
            )
            st.caption(
                f"Regra: {dose_mL_per_100L:.1f} mL/100 L → +{adds_ppm_per_100L:.1f} ppm NO₃ "
                f"(≈ {(adds_ppm_per_100L/dose_mL_per_100L):.2f} ppm/mL em 100 L; "
                f"no seu aquário: {ppm_per_mL_tank:.2f} ppm/mL)."
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## Redfield & pH")
        st.write(f"Antes da dose: **{r_before:.2f}:1**  |  Depois: **{r_after:.2f}:1**")
        st.write(f"pH atual: **{pH_now:.1f}**")
        st.caption("Guia prático (ppm íons): alvo ~10:1 (verde 8–15, amarelo 6–18).")
        st.markdown('</div>', unsafe_allow_html=True)

    # Agenda semanal
    order_days, micro_days = schedule_days(tpa_day, micro_freq)
    micro_per_app = micro_per30 * (vol / 30.0)
    rows = []
    for j, d in enumerate(order_days):
        macro = mL_day_macro
        micro = micro_per_app if d in micro_days else 0.0
        note = []
        if j == 0 and do_tpa: note.append("TPA")
        if j == 0 and mL_now > 1e-4: note.append("Correção")
        rows.append({"Dia": d, "Macro (mL)": round(macro, 2), "Micro (mL)": round(micro, 2), "Obs.": " + ".join(note)})
    df_sched = pd.DataFrame(rows)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Agenda semanal (macro & micro)")
    st.dataframe(df_sched, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Baixar agenda (CSV)", data=df_sched.to_csv(index=False).encode(), file_name="agenda_dosagem.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

    # GH / KH detalhes
    dGH_tank = max(0.0, gh_target - gh_now)
    g_shrimp_tank = dGH_tank * (vol/100.0) * g_per_dGH_100L
    ml_per_g_powder = 2.3/2.0
    ml_shrimp_tank_approx = g_shrimp_tank * ml_per_g_powder

    g_shrimp_tpa = remin_mix_to * (tpa/100.0) * g_per_dGH_100L
    ml_shrimp_tpa_approx = g_shrimp_tpa * ml_per_g_powder

    dKH_tank = max(0.0, kh_target - kh_now)
    ml_khplus_tank = dKH_tank * (vol/100.0) * ml_khplus_per_dKH_100L
    ml_khplus_tpa  = kh_target * (tpa/100.0) * ml_khplus_per_dKH_100L
    ml_khplus_daily = 2.0 * (vol/100.0)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## GH – Shrimp Minerals (pó)")
        st.write(f"Δ GH (aquário): **{dGH_tank:.0f} °dH** → **{g_shrimp_tank:.2f} g** (≈ {ml_shrimp_tank_approx:.2f} mL).")
        if do_tpa and tpa > 0:
            st.write(f"Remineralizar TPA: alvo **{remin_mix_to:.0f} °dH** em **{tpa:.0f} L** → **{g_shrimp_tpa:.2f} g** (≈ {ml_shrimp_tpa_approx:.2f} mL).")
        st.caption("Regra: 2 g (~2,3 mL) elevam +1 °dH em 100 L.")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## KH – ReeFlowers KH+")
        st.write(f"Δ KH (aquário): **{dKH_tank:.0f} °dKH** → **{ml_khplus_tank:.2f} mL** de KH+.")
        if do_tpa and tpa > 0:
            st.write(f"Preparar TPA: alvo **{kh_target:.0f} °dKH** em **{tpa:.0f} L** → **{ml_khplus_tpa:.2f} mL** de KH+.")
        st.write(f"Manutenção diária sugerida: **{ml_khplus_daily:.2f} mL/dia** (2 mL/100 L). Ajuste conforme teste.")
        st.caption("Regra: 30 mL/100 L → +1 °dKH.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Tabela faixas (Doce – camarões)
    data = [
        {"Grupo": "Neocaridina davidi (Red Cherry, etc.)", "pH_range": (6.5, 7.8), "GH_range": (6.0, 12.0), "KH_range": (3.0, 8.0)},
        {"Grupo": "Caridina cantonensis (Crystal/Bee/Taiwan Bee)", "pH_range": (5.5, 6.5), "GH_range": (4.0, 6.0), "KH_range": (0.0, 2.0)},
    ]
    df_params = pd.DataFrame({
        "Grupo": [d["Grupo"] for d in data],
        "pH": [f"{d['pH_range'][0]:.1f}–{d['pH_range'][1]:.1f}" for d in data],
        "pH_min": [d["pH_range"][0] for d in data],
        "pH_max": [d["pH_range"][1] for d in data],
        "GH (°dH)": [f"{d['GH_range'][0]:.0f}–{d['GH_range'][1]:.0f}" for d in data],
        "GH_min": [d["GH_range"][0] for d in data],
        "GH_max": [d["GH_range"][1] for d in data],
        "KH (°dKH)": [f"{d['KH_range'][0]:.0f}–{d['KH_range'][1]:.0f}" for d in data],
        "KH_min": [d["KH_range"][0] for d in data],
        "KH_max": [d["KH_range"][1] for d in data],
    })
    df_display = df_params[["Grupo", "pH", "GH (°dH)", "KH (°dKH)"]].copy()

    def _highlight_fw(df_show, df_params=df_params, pH_now=pH_now, gh_now=gh_now, kh_now=kh_now):
        styles = pd.DataFrame('', index=df_show.index, columns=df_show.columns)
        for i in df_show.index:
            row = df_params.loc[i]
            if row["pH_min"] <= pH_now <= row["pH_max"]:
                styles.at[i, "pH"] = 'background-color:#065f46; color:#ecfeff; font-weight:600;'
            if row["GH_min"] <= gh_now <= row["GH_max"]:
                styles.at[i, "GH (°dH)"] = 'background-color:#065f46; color:#ecfeff; font-weight:600;'
            if row["KH_min"] <= kh_now <= row["KH_max"]:
                styles.at[i, "KH (°dKH)"] = 'background-color:#065f46; color:#ecfeff; font-weight:600;'
        return styles

    styled = df_display.style.apply(_highlight_fw, axis=None)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Faixas recomendadas (Doce – camarões)")
    st.markdown(styled.to_html(), unsafe_allow_html=True)
    st.caption("Compromisso p/ Neo + Caridina: pH ~6,8–7,0; GH 6–7; KH 2–3.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Export config básica
    config = {
        "mode": "freshwater_shrimp",
        "tank": {"volume_L": vol, "do_tpa_now": do_tpa, "tpa_L": tpa},
        "tests": {"pH": pH_now, "NO3_ppm": no3_now, "PO4_ppm": po4_now, "GH_dH": gh_now, "KH_dKH": kh_now},
        "targets": {"mode": "PO4" if target_mode.startswith("PO₄") else "NO3",
                    "PO4_ppm": po4_target, "NO3_ppm": no3_target, "GH_dH": gh_target, "KH_dKH": kh_target},
    }
    st.download_button("💾 Salvar configuração (JSON)", data=json.dumps(config, indent=2, ensure_ascii=False).encode(), file_name="config_doser_fw.json", mime="application/json")

    st.markdown('<div class="muted">Versão 2.7 • Banner full-width + mobile friendly • Fix histórico</div>', unsafe_allow_html=True)

# ======================================================================
# ===================== MODO MARINHO (REEF) ============================
# ======================================================================
else:
    # Potência por mL (no seu aquário)
    ca_per_ml_ppm = ca_ppm_per_ml_per_25L * (25.0 / vol)
    kh_per_ml_dkh = dkh_from_meq(alk_meq_per_ml_per_25L) * (25.0 / vol)
    max_ml_day_tank = max_ml_per_25L_day * (vol / 25.0)

    # Deltas até alvo
    dKH_needed = max(0.0, kh_target - kh_now)
    dCa_needed = max(0.0, ca_target - ca_now)
    dMg_needed = max(0.0, mg_target - mg_now)

    # Plano diário pareado (segue limites e consumo)
    desired_kh_increase_today = min(dKH_needed, max_kh_raise_net + kh_cons)
    ml_f2_for_kh_today = (desired_kh_increase_today / kh_per_ml_dkh) if kh_per_ml_dkh > 0 else 0.0
    ml_f1_maint = (ca_cons / ca_per_ml_ppm) if ca_per_ml_ppm > 0 else 0.0

    ml_pair = max(ml_f2_for_kh_today, ml_f1_maint)
    limited = False
    if ml_pair > max_ml_day_tank:
        ml_pair = max_ml_day_tank
        limited = True

    kh_gain = ml_pair * kh_per_ml_dkh
    ca_gain = ml_pair * ca_per_ml_ppm
    kh_net = kh_gain - kh_cons
    ca_net = ca_gain - ca_cons

    days_kh = math.inf
    if kh_net > 0:
        days_kh = math.ceil(dKH_needed / min(kh_net, max_kh_raise_net))

    # KPIs Reef
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.markdown(kpi("🧪 Dose diária Fusion 1", f"{ml_pair:.1f} mL", f"{ca_gain:.1f} ppm Ca/dia (bruto)"), unsafe_allow_html=True)
    with kpi_cols[1]:
        st.markdown(kpi("🧪 Dose diária Fusion 2", f"{ml_pair:.1f} mL", f"{kh_gain:.2f} °dKH/dia (bruto)"), unsafe_allow_html=True)
    with kpi_cols[2]:
        cls = "good" if (8 <= round(kh_now) <= 12 and 380 <= round(ca_now) <= 450 and 1250 <= round(mg_now) <= 1350) else "bad"
        st.markdown(kpi("🎛️ Estado atual", f"KH {kh_now:.1f} • Ca {ca_now:.0f} • Mg {mg_now:.0f}", "verde=ok, vermelho=fora", cls), unsafe_allow_html=True)
    with kpi_cols[3]:
        st.markdown(kpi("📅 Dias p/ KH alvo", "—" if days_kh==math.inf else f"~{days_kh} dias", f"alvo {kh_target:.0f} °dKH"), unsafe_allow_html=True)

    # Resumo Reef
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Resumo (Reef) – Reef Fusion 1 & 2 (pareados)")
    st.write(f"**Plano diário (pareado)**: adicionar **{ml_pair:.1f} mL** de **Fusion 1** e **{ml_pair:.1f} mL** de **Fusion 2**.")
    st.write(f"→ Efeito bruto estimado: **+{kh_gain:.2f} °dKH/dia** e **+{ca_gain:.1f} ppm Ca/dia**.")
    st.write(f"→ Considerando consumo: KH líquido ~ **{kh_net:.2f} °dKH/dia**, Ca líquido ~ **{ca_net:.1f} ppm/dia**.")
    if limited:
        st.markdown('<span class="bad">Limitado pelo fabricante:</span> dose diária capada ao máximo permitido.', unsafe_allow_html=True)
    st.caption("Regras: dosar as partes em locais diferentes; não exceder 4 mL/25 L/dia de cada. Nunca misture.")

    # ---------------- Visualização: Histórico / Projeção ----------------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Visualização")
    view_mode = st.radio("Mostrar", ["Histórico (valores medidos)", "Projeção (simulada)"], horizontal=True, index=0)

    if view_mode.startswith("Histórico"):
        st.markdown("### Gráfico histórico (KH, Ca, Mg) por data")
        if "reef_history" in st.session_state and not st.session_state.reef_history.empty:
            dfh = st.session_state.reef_history.copy()
            dfh["timestamp"] = pd.to_datetime(dfh["timestamp"], errors="coerce")
            dfh = dfh.dropna(subset=["timestamp"]).sort_values("timestamp")
            df_plot = dfh.set_index("timestamp")[["KH_atual","Ca_atual","Mg_atual"]]
            st.line_chart(df_plot)

            # -------- FIX: consumo observado sem usar index.shift (evita NullFrequencyError)
            dt_days = df_plot.index.to_series().diff().dt.total_seconds().div(86400.0)
            # evita divisões por zero / NaN
            dt_days = dt_days.replace([0, None], pd.NA).fillna(1.0)

            df_obs = df_plot.copy()
            for col in ["KH_atual","Ca_atual","Mg_atual"]:
                delta = df_obs[col].diff()
                per_day = (delta / dt_days).replace([pd.NA, float("inf"), -float("inf")], 0)
                df_obs[col+"_dday"] = per_day

            def med_cons(series, clamp=None):
                s = pd.to_numeric(series, errors="coerce").dropna()
                if clamp is not None:
                    s = s.clip(lower=-clamp, upper=clamp)
                # consumo = negativo da variação/dia (queda)
                return float(max(0.0, round(-s.median(), 3))) if not s.empty else 0.0

            kh_cons_obs = med_cons(df_obs["KH_atual_dday"], clamp=3.0)
            ca_cons_obs = med_cons(df_obs["Ca_atual_dday"], clamp=50.0)
            mg_cons_obs = med_cons(df_obs["Mg_atual_dday"], clamp=20.0)

            k1, k2, k3 = st.columns(3)
            with k1: st.markdown(kpi("KH – consumo observado", f"{kh_cons_obs:.2f} °dKH/dia"), unsafe_allow_html=True)
            with k2: st.markdown(kpi("Ca – consumo observado", f"{ca_cons_obs:.1f} ppm/dia"), unsafe_allow_html=True)
            with k3: st.markdown(kpi("Mg – consumo observado", f"{mg_cons_obs:.1f} ppm/dia"), unsafe_allow_html=True)

            st.caption("Consumo observado = mediana das variações diárias entre medições (robusto a intervalos irregulares).")
        else:
            st.info("Seu histórico ainda está vazio. Adicione linhas no card abaixo e o gráfico aparece aqui.")
    else:
        # Projeção por data
        st.markdown("### Projeção por data (KH, Ca, Mg)")
        default_start_date = dt.date.today()
        if "reef_history" in st.session_state and not st.session_state.reef_history.empty:
            try:
                last_ts = pd.to_datetime(st.session_state.reef_history["timestamp"], errors="coerce").dropna()
                if not last_ts.empty: default_start_date = last_ts.max().date()
            except Exception:
                pass
        proj_start = st.date_input("Iniciar projeção em", value=default_start_date)
        proj_days = st.slider("Dias para projetar", min_value=7, max_value=30, value=14, step=1)

        dates = pd.date_range(proj_start, periods=proj_days+1, freq="D")
        kh_list, ca_list, mg_list = [], [], []
        kh_val, ca_val, mg_val = kh_now, ca_now, mg_now

        kh_list.append(kh_val); ca_list.append(ca_val); mg_list.append(mg_val)
        for _ in range(proj_days):
            kh_increment = min(kh_gain - kh_cons, max_kh_raise_net)
            ca_increment = (ca_gain - ca_cons)
            mg_increment = -mg_cons
            kh_val = min(kh_target, kh_val + max(0.0, kh_increment))
            ca_val = min(ca_target, ca_val + ca_increment)
            mg_val = max(0.0, mg_val + mg_increment)
            kh_list.append(kh_val); ca_list.append(ca_val); mg_list.append(mg_val)

        df_proj = pd.DataFrame({"Data": dates, "KH (°dKH)": kh_list, "Ca (ppm)": ca_list, "Mg (ppm)": mg_list}).set_index("Data")
        st.line_chart(df_proj)
        st.caption("Projeção assume dose pareada diária constante e consumo fixo; Mg cai apenas pelo consumo.")

    st.markdown('</div>', unsafe_allow_html=True)

    # ---------------- Histórico Reef (CSV offline) ----------------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Histórico Reef (CSV offline)")
    if "reef_history" not in st.session_state:
        st.session_state.reef_history = pd.DataFrame(columns=[
            "timestamp","volume_L",
            "KH_atual","Ca_atual","Mg_atual",
            "KH_ideal","Ca_ideal","Mg_ideal",
            "KH_cons","Ca_cons","Mg_cons",
            "dose_pair_mL","KH_gain_dia","Ca_gain_dia",
            "KH_liq_dia","Ca_liq_dia","obs"
        ])

    up = st.file_uploader("Carregar CSV existente", type="csv")
    if up is not None:
        try:
            st.session_state.reef_history = pd.read_csv(up)
            st.success("Histórico carregado.")
        except Exception as e:
            st.error(f"Não consegui ler o CSV: {e}")

    obs = st.text_input("Observações (opcional)")
    if st.button("➕ Adicionar linha desta sessão"):
        row = {
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
            "volume_L": vol,
            "KH_atual": kh_now, "Ca_atual": ca_now, "Mg_atual": mg_now,
            "KH_ideal": kh_target, "Ca_ideal": ca_target, "Mg_ideal": mg_target,
            "KH_cons": kh_cons, "Ca_cons": ca_cons, "Mg_cons": mg_cons,
            "dose_pair_mL": round(ml_pair,2),
            "KH_gain_dia": round(kh_gain,3), "Ca_gain_dia": round(ca_gain,2),
            "KH_liq_dia": round(kh_net,3), "Ca_liq_dia": round(ca_net,2),
            "obs": obs or ""
        }
        st.session_state.reef_history = pd.concat([st.session_state.reef_history, pd.DataFrame([row])], ignore_index=True)
        st.success("Linha adicionada ao histórico local.")

    st.dataframe(st.session_state.reef_history, use_container_width=True)
    st.download_button("⬇️ Baixar histórico (CSV)",
                       data=st.session_state.reef_history.to_csv(index=False).encode(),
                       file_name="reef_history.csv",
                       mime="text/csv")
    st.caption("Dica: na próxima sessão, faça upload deste CSV para continuar seu log.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ---- Tabela de faixas Reef ----
    reef_df = pd.DataFrame({
        "Parâmetro": ["KH (°dKH)", "Ca (ppm)", "Mg (ppm)"],
        "Atual": [kh_now, ca_now, mg_now],
        "Faixa": ["8–12", "380–450", "1250–1350"],
        "min": [8.0, 380.0, 1350.0 - 100.0],  # 1250
        "max": [12.0, 450.0, 1350.0],
    })
    reef_df.loc[2, "min"] = 1250.0  # clareza

    reef_display = reef_df[["Parâmetro", "Atual", "Faixa"]].copy()

    def _style_reef(df_show, limits=reef_df[["min","max"]]):
        styles = pd.DataFrame('', index=df_show.index, columns=df_show.columns)
        for i in df_show.index:
            mn, mx = limits.loc[i,"min"], limits.loc[i,"max"]
            val = df_show.loc[i,"Atual"]
            if mn <= val <= mx:
                styles.at[i, "Atual"] = 'background-color:#065f46; color:#ecfeff; font-weight:600;'
            else:
                styles.at[i, "Atual"] = 'background-color:#7f1d1d; color:#fee2e2; font-weight:600;'
        return styles

    styled_reef = reef_display.style.apply(_style_reef, axis=None)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Faixas recomendadas (Reef)")
    st.markdown(styled_reef.to_html(), unsafe_allow_html=True)
    st.caption("Padrão: KH 8–12 • Ca 380–450 ppm • Mg 1250–1350 ppm.")

    cfg_reef = {
        "mode": "reef",
        "tank": {"volume_L": vol},
        "tests": {"KH_dKH": kh_now, "Ca_ppm": ca_now, "Mg_ppm": mg_now},
        "targets": {"KH_dKH": kh_target, "Ca_ppm": ca_target, "Mg_ppm": mg_target},
        "consumption_daily": {"KH_dKH": kh_cons, "Ca_ppm": ca_cons, "Mg_ppm": mg_cons},
        "fusion": {
            "ca_ppm_per_ml_per_25L": ca_ppm_per_ml_per_25L,
            "alk_meq_per_ml_per_25L": alk_meq_per_ml_per_25L,
            "kh_dkh_per_ml_tank": kh_per_ml_dkh,
            "ca_ppm_per_ml_tank": ca_per_ml_ppm,
            "max_ml_per_25L_day": max_ml_per_25L_day,
            "max_ml_day_tank": max_ml_day_tank,
            "daily_pair_ml": ml_pair,
            "daily_effect": {"KH_gain_dKH": kh_gain, "Ca_gain_ppm": ca_gain,
                             "KH_net_dKH": kh_net, "Ca_net_ppm": ca_net},
            "days_kh_to_target": None if days_kh==math.inf else days_kh
        }
    }
    st.download_button("💾 Salvar configuração Reef (JSON)",
                       data=json.dumps(cfg_reef, indent=2, ensure_ascii=False).encode(),
                       file_name="config_doser_reef.json",
                       mime="application/json")

    st.markdown('<div class="muted">Versão 2.7 • Banner full-width + mobile friendly • Fix histórico</div>', unsafe_allow_html=True)
