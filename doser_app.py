import io, json, math
import pandas as pd
import streamlit as st

# ===================== Config & Visual =====================
st.set_page_config(page_title="Doser • Plantado", page_icon="💧", layout="wide")

PRIMARY_BG = "#0b1220"
CARD_BG    = "#0f172a"
BORDER     = "#1f2937"
TEXT       = "#e2e8f0"
MUTED      = "#94a3b8"
ACCENT     = "#60a5fa"
GOOD       = "#22c55e"
WARN       = "#fbbf24"
BAD        = "#ef4444"

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
  :root {{
    --primary: {ACCENT}; --text: {TEXT}; --muted:{MUTED};
    --bg: {PRIMARY_BG}; --card: {CARD_BG}; --border:{BORDER};
    --good:{GOOD}; --warn:{WARN}; --bad:{BAD};
  }}
  html, body, .stApp {{ font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }}
  .stApp {{
    background: radial-gradient(1100px 500px at 10% -10%, #0e1a35 10%, var(--bg) 60%);
    color: var(--text);
  }}
  .hero {{
    padding: 18px 18px 8px; border-bottom:1px solid var(--border);
    background: linear-gradient(180deg, rgba(96,165,250,0.08), rgba(0,0,0,0));
    margin-bottom: 8px;
  }}
  .hero h1 {{ margin:0; font-size: 24px; letter-spacing:0.2px; }}
  .muted {{ color: var(--muted); font-size: 13px; }}
  .card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 14px; padding: 14px; margin: 8px 0;
    animation: fadeIn .35s ease-out;
  }}
  .hr {{ border-top:1px solid var(--border); margin: 10px 0; }}
  .pill {{ display:inline-block; padding:6px 10px; border-radius:999px;
           border:1px solid var(--border); background:#111827; color:var(--muted); margin-right:6px; font-size:12px; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}

  /* KPI grid */
  .kpi {{
    display:flex; flex-direction:column; gap:6px; padding:14px; border-radius:16px;
    border:1px solid var(--border); background:linear-gradient(180deg, rgba(2,6,23,0.4), rgba(2,6,23,0.2));
    box-shadow: 0 1px 0 rgba(255,255,255,0.03) inset;
  }}
  .kpi .label {{ font-size:12px; color:var(--muted); }}
  .kpi .value {{ font-size:22px; font-weight:700; letter-spacing:0.2px; }}
  .kpi .sub {{ font-size:12px; color:var(--muted); }}
  .good {{ color: var(--good); }}
  .warn {{ color: var(--warn); }}
  .bad  {{ color: var(--bad);  }}

  /* Accordion tweaks */
  details summary {{
    cursor: pointer; list-style: none; outline: none;
  }}
  @keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(4px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}
  table.dataframe {{ border-collapse: collapse; width: 100%; }}
  table.dataframe th, table.dataframe td {{ border: 1px solid var(--border); padding: 6px 8px; }}
  table.dataframe th {{ background:#0d162c; color:var(--text); }}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>💧 Doser – Plantado & Camarões</h1>
  <div class="muted">Correção com/sem TPA, alvo por PO₄ (recomendado) ou NO₃, Redfield, GH (pó) e KH+.
  Visual compacto e otimizado para celular.</div>
</div>
""", unsafe_allow_html=True)


# ===================== Helpers & Core =====================
def conversions(density_g_per_ml: float, pctN: float, pctP: float):
    """mg por mL de NO3 e PO4 a partir de %N e %P (elementares) e densidade."""
    mgN_per_mL = pctN/100.0 * density_g_per_ml * 1000.0
    mgP_per_mL = pctP/100.0 * density_g_per_ml * 1000.0
    mgNO3_per_mL = mgN_per_mL * (62.0/14.0)   # N -> NO3
    mgPO4_per_mL = mgP_per_mL * (95.0/31.0)   # P -> PO4
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
    """Retorna razão NO3:PO4 (ppm) e status vs ~10:1."""
    if po4_ppm <= 0: return math.inf, "bad"
    r = no3_ppm / po4_ppm
    if 8 <= r <= 15: status = "good"
    elif 6 <= r <= 18: status = "warn"
    else: status = "bad"
    return r, status

def kpi(title, value, subtitle="", cls=""):
    return f"""
    <div class="kpi">
      <div class="label">{title}</div>
      <div class="value {cls}">{value}</div>
      <div class="sub">{subtitle}</div>
    </div>
    """

# ===================== Sidebar (compact inputs) =====================
with st.sidebar:
    st.markdown("## ⚙️ Parâmetros do aquário")
    vol = st.number_input("Volume útil (L)", min_value=1.0, value=50.0, step=1.0)
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
        no3_min, no3_max = st.select_slider("Faixa desejada de NO₃ (ppm)", options=[8,9,10,11,12,13,14,15,16,17,18,19,20], value=(10,15))
        no3_target = (no3_min + no3_max)/2
    else:
        no3_target = st.number_input("Alvo de NO₃ (ppm)", min_value=0.0, value=12.0, step=0.5)
        po4_min, po4_max = st.select_slider("Faixa desejada de PO₄ (ppm)", options=[0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2], value=(0.6,1.0))
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
    st.markdown("### 🧱 Alvos GH & KH (ReeFlowers)")
    gh_target = st.number_input("GH alvo (°dH)", min_value=0.0, value=7.0, step=0.5)
    g_per_dGH_100L = st.number_input("Shrimp Minerals (pó): g p/ +1°dGH /100 L", min_value=0.1, value=2.0, step=0.1)
    remin_mix_to = st.number_input("Remineralizar água da TPA até GH (°dH)", min_value=0.0, value=gh_target, step=0.5)
    kh_target = st.number_input("KH alvo (°dKH)", min_value=0.0, value=3.0, step=0.5)
    ml_khplus_per_dKH_100L = st.number_input("KH+ (mL) p/ +1°dKH /100 L", min_value=1.0, value=30.0, step=1.0)


# ===================== Cálculos Macro =====================
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

# ===================== Cálculos GH / KH (ReeFlowers) =====================
# GH (pó): 2 g/100L → +1°dGH  (≈ 1,15 mL/g se quiser medir em mL)
dGH_tank = max(0.0, gh_target - gh_now)
g_shrimp_tank = dGH_tank * (vol/100.0) * g_per_dGH_100L
ml_per_g_powder = 2.3/2.0   # ≈1,15 mL por grama
ml_shrimp_tank_approx = g_shrimp_tank * ml_per_g_powder

g_shrimp_tpa = remin_mix_to * (tpa/100.0) * g_per_dGH_100L
ml_shrimp_tpa_approx = g_shrimp_tpa * ml_per_g_powder

# KH+ : 30 mL/100L → +1°dKH ; manutenção 2 mL/100L/dia
dKH_tank = max(0.0, kh_target - kh_now)
ml_khplus_tank = dKH_tank * (vol/100.0) * ml_khplus_per_dKH_100L
ml_khplus_tpa  = kh_target * (tpa/100.0) * ml_khplus_per_dKH_100L
ml_khplus_daily = 2.0 * (vol/100.0)

# ===================== KPI Cards =====================
kpi_cols = st.columns(5)
with kpi_cols[0]:
    st.markdown(kpi("🎯 Dose agora (macro)", f"{mL_now:.2f} mL", "para atingir o alvo"), unsafe_allow_html=True)
with kpi_cols[1]:
    st.markdown(kpi("🗓️ Manutenção diária", f"{mL_day_macro:.2f} mL/dia", "macro baseado em PO₄"), unsafe_allow_html=True)
with kpi_cols[2]:
    rf_cls = "good" if status_after=="good" else ("warn" if status_after=="warn" else "bad")
    st.markdown(kpi("📈 Redfield pós-dose", f"{r_after:.2f}:1", "NO₃:PO₄ (ppm)", rf_cls), unsafe_allow_html=True)
with kpi_cols[3]:
    st.markdown(kpi("🧱 GH (aquário)", f"{g_shrimp_tank:.2f} g", f"{dGH_tank:.2f} °dH → Shrimp Minerals"), unsafe_allow_html=True)
with kpi_cols[4]:
    st.markdown(kpi("🧪 KH (aquário)", f"{ml_khplus_tank:.2f} mL", f"{dKH_tank:.2f} °dKH → KH+"), unsafe_allow_html=True)

# ===================== Resumo & Correção =====================
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
    st.caption("Se o macro acoplar demais N e P, use sais isolados (KNO₃ / KH₂PO₄) para correções finas.")
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Redfield & pH")
    st.write(f"Antes da dose: **{r_before:.2f}:1**  |  Depois: **{r_after:.2f}:1**")
    st.write(f"pH atual: **{pH_now:.1f}**")
    st.caption("Guia prático para íons (ppm): ~10:1 (verde 8–15, amarelo 6–18).")
    st.markdown('</div>', unsafe_allow_html=True)

# ===================== Agenda semanal =====================
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
csv_bytes = df_sched.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Baixar agenda (CSV)", data=csv_bytes, file_name="agenda_dosagem.csv", mime="text/csv")
st.markdown('</div>', unsafe_allow_html=True)

# ===================== GH & KH (detalhe) =====================
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## GH – Shrimp Minerals (pó)")
    st.write(f"Δ GH (aquário): **{dGH_tank:.2f} °dH** → **{g_shrimp_tank:.2f} g** (≈ {ml_shrimp_tank_approx:.2f} mL).")
    if do_tpa and tpa > 0:
        st.write(f"Remineralizar TPA: alvo **{remin_mix_to:.2f} °dH** em **{tpa:.0f} L** → **{g_shrimp_tpa:.2f} g** (≈ {ml_shrimp_tpa_approx:.2f} mL).")
    st.caption("Regra do fabricante: 2 g (~2,3 mL) elevam +1 °dH em 100 L. Dose diária sugerida: 2 g/100 L até atingir o GH desejado.")
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## KH – ReeFlowers KH+")
    st.write(f"Δ KH (aquário): **{dKH_tank:.2f} °dKH** → **{ml_khplus_tank:.2f} mL** de KH+.")
    if do_tpa and tpa > 0:
        st.write(f"Preparar TPA: alvo **{kh_target:.2f} °dKH** em **{tpa:.0f} L** → **{ml_khplus_tpa:.2f} mL** de KH+.")
    st.write(f"Manutenção diária sugerida: **{ml_khplus_daily:.2f} mL/dia** (2 mL/100 L). Ajuste conforme teste.")
    st.caption("Regra do fabricante: 30 mL/100 L → +1 °dKH.")
    st.markdown('</div>', unsafe_allow_html=True)

# ===================== Tabela de faixas (com realce) =====================
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

# marca verde quando seus valores ATUAIS estão dentro da faixa
styles = pd.DataFrame('', index=df_display.index, columns=df_display.columns)
for i in df_display.index:
    row = df_params.loc[i]
    if row["pH_min"] <= pH_now <= row["pH_max"]:
        styles.at[i, "pH"] = 'background-color:#065f46; color:#ecfeff; font-weight:600;'
    if row["GH_min"] <= gh_now <= row["GH_max"]:
        styles.at[i, "GH (°dH)"] = 'background-color:#065f46; color:#ecfeff; font-weight:600;'
    if row["KH_min"] <= kh_now <= row["KH_max"]:
        styles.at[i, "KH (°dKH)"] = 'background-color:#065f46; color:#ecfeff; font-weight:600;'

styled = df_display.style.set_table_styles([
    {'selector':'th', 'props':[('text-align','left')]},
    {'selector':'td', 'props':[('text-align','left')]},
]).set_properties(**{'text-align':'left'}).set_table_attributes('class="dataframe"').set_td_classes(styles)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("## Faixas recomendadas (realce pelos seus valores atuais)")
st.markdown(styled.to_html(), unsafe_allow_html=True)
st.caption("Misturar Neo e Caridina exige compromisso: pH ~6,8–7,0; GH 6–7; KH 2–3 costuma ser confortável para Neocaridinas e tolerável para algumas Caridinas, mas não ideal para linhagens sensíveis.")
st.markdown('</div>', unsafe_allow_html=True)

# ===================== Export config =====================
config = {
    "tank": {"volume_L": vol, "do_tpa_now": do_tpa, "tpa_L": tpa},
    "tests": {"pH": pH_now, "NO3_ppm": no3_now, "PO4_ppm": po4_now, "GH_dH": gh_now, "KH_dKH": kh_now},
    "targets": {"mode": "PO4" if target_mode.startswith("PO₄") else "NO3",
                "PO4_ppm": po4_target, "NO3_ppm": no3_target, "GH_dH": gh_target, "KH_dKH": kh_target},
    "macro": {"pctN": pctN, "pctP": pctP, "density_g_per_ml": density,
              "ppm_per_mL": {"PO4": dPO4_per_mL, "NO3": dNO3_per_mL},
              "dose_now_mL": mL_now, "after": {"NO3_ppm": no3_after, "PO4_ppm": po4_after},
              "daily_macro_mL": mL_day_macro, "NO3_drift_ppm_day": no3_drift},
    "gh_kh": {
        "g_per_dGH_100L": g_per_dGH_100L,
        "dose_tank_g": g_shrimp_tank, "dose_tank_mL_approx": ml_shrimp_tank_approx,
        "TPA_mix_to_GH": remin_mix_to, "dose_TPA_g": g_shrimp_tpa, "dose_TPA_mL_approx": ml_shrimp_tpa_approx,
        "ml_khplus_per_dKH_100L": ml_khplus_per_dKH_100L, "KHplus_mL_tank": ml_khplus_tank,
        "KHplus_mL_TPA": ml_khplus_tpa, "KHplus_mL_daily_hint": ml_khplus_daily
    },
    "redfield": {"before_NO3_PO4": r_before, "after_NO3_PO4": r_after}
}
buf = io.BytesIO(json.dumps(config, indent=2, ensure_ascii=False).encode("utf-8"))
st.download_button("💾 Salvar configuração (JSON)", data=buf, file_name="config_doser.json", mime="application/json")

st.markdown('<div class="muted">Versão 1.5 • KPIs e layout compacto • Dicas: use doses fracionadas e ajuste consumos após 1–2 semanas de medições.</div>', unsafe_allow_html=True)
