import io, json, math
import pandas as pd
import streamlit as st

# ---------------------- Config & Style ----------------------
st.set_page_config(page_title="Doser • Plantado", page_icon="💧", layout="centered")

PRIMARY_BG = "#0b1220"
CARD_BG    = "#0f172a"
BORDER     = "#1f2937"
TEXT       = "#e2e8f0"
MUTED      = "#94a3b8"
ACCENT     = "#60a5fa"
GOOD       = "#86efac"
WARN       = "#fbbf24"
BAD        = "#f87171"

st.markdown(f"""
<style>
  .stApp {{ background: radial-gradient(1200px 500px at 10% -10%, #0e1a35 10%, {PRIMARY_BG} 60%); color: {TEXT}; }}
  .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{ color: {ACCENT}; }}
  .card {{ background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 14px; padding: 16px; margin: 10px 0; }}
  .pill {{ display:inline-block; padding:6px 10px; border-radius:999px; border:1px solid {BORDER}; background:#111827; color:{MUTED}; margin-right:6px; font-size:12px; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
  .muted {{ color:{MUTED}; }}
  .good {{ color:{GOOD}; }}
  .warn {{ color:{WARN}; }}
  .bad  {{ color:{BAD};  }}
  .hr {{ border-top:1px solid {BORDER}; margin: 10px 0; }}
  footer {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)

st.markdown("# 💧 Doser – Macro, Micro, GH & KH (Plantado + Camarões)")
st.markdown(
    '<div class="muted">Corrija com ou sem TPA; alvo de correção por PO₄ (recomendado) ou NO₃. '
    'Inclui GH com Shrimp Minerals em pó e KH com ReeFlowers KH+. '
    'Tabela marca em <b>verde</b> quando pH/GH/KH atuais estão dentro das faixas de Neocaridina/Caridina. '
    'Referência Redfield prática: NO₃:PO₄ ≈ 10:1 (ppm).</div>',
    unsafe_allow_html=True
)

# ---------------------- Helpers ----------------------
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

# ---------------------- Sidebar ----------------------
with st.sidebar:
    st.markdown("## ⚙️ Parâmetros do aquário")
    vol = st.number_input("Volume útil (L)", min_value=1.0, value=50.0, step=1.0)
    do_tpa = st.checkbox("Vou fazer TPA agora", value=True)
    tpa = st.number_input("Volume da TPA (L)", min_value=0.0, value=20.0 if do_tpa else 0.0, step=1.0, disabled=not do_tpa)

    st.markdown("---")
    st.markdown("### 🧪 Testes atuais")
    pH_now  = st.number_input("pH atual", min_value=4.5, max_value=8.5, value=6.8, step=0.1, format="%.1f")
    no3_now = st.number_input("NO₃ (ppm)", min_value=0.0, value=10.0, step=0.5)
    po4_now = st.number_input("PO₄ (ppm)", min_value=0.0, value=0.40, step=0.05)

    st.markdown("---")
    st.markdown("### 🎯 Alvo da correção")
    target_mode = st.radio("Escolha o nutriente alvo", ["PO₄ (recomendado)", "NO₃"], index=0)
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
    st.markdown("### 📅 Agenda & Consumo")
    tpa_day = st.selectbox("Dia da TPA (para agenda)", options=["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"], index=1)
    po4_daily = st.number_input("Consumo diário de PO₄ (ppm/dia)", min_value=0.0, value=0.20, step=0.05, format="%.2f")
    no3_daily = st.number_input("Consumo diário de NO₃ (ppm/dia)", min_value=0.0, value=1.50, step=0.10, format="%.2f")

    st.markdown("---")
    st.markdown("### 🧬 Micronutrientes")
    micro_per30 = st.number_input("mL por 30 L por aplicação", min_value=0.0, value=1.25, step=0.05, format="%.2f")
    micro_freq = st.selectbox("Aplicações de micro/semana", options=[1,2,3], index=1)

    st.markdown("---")
    st.markdown("### 🧱 GH & KH (Camarões)")
    # GH (Shrimp Minerals em pó): 2 g/100 L → +1 °dGH ; 2 g ≈ 2,3 mL (≈1,15 mL/g)
    gh_now = st.number_input("GH atual (°dH)", min_value=0.0, value=6.0, step=0.5)
    gh_target = st.number_input("GH alvo do aquário (°dH)", min_value=0.0, value=7.0, step=0.5)
    g_per_dGH_100L = st.number_input("Shrimp Minerals (pó): gramas p/ +1°dGH em 100 L", min_value=0.1, value=2.0, step=0.1)
    remin_mix_to = st.number_input("Remineralizar água da TPA até GH (°dH)", min_value=0.0, value=gh_target, step=0.5)

    # KH (ReeFlowers KH+): 30 mL/100 L → +1 °dKH ; manutenção 2 mL/100 L/dia
    kh_now = st.number_input("KH atual (°dKH)", min_value=0.0, value=2.0, step=0.5)
    kh_target = st.number_input("KH alvo do aquário (°dKH)", min_value=0.0, value=3.0, step=0.5)
    ml_khplus_per_dKH_100L = st.number_input("KH+ (mL) p/ +1°dKH em 100 L", min_value=1.0, value=30.0, step=1.0)

# ---------------------- Cálculos Macro ----------------------
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
    warn_no3 = not (no3_min <= no3_after <= no3_max)
    warn_po4 = False
else:
    dNO3_needed = max(0.0, no3_target - no3_base)
    mL_now = (dNO3_needed / dNO3_per_mL) if dNO3_per_mL > 0 else 0.0
    no3_after = no3_base + mL_now * dNO3_per_mL
    po4_after = po4_base + mL_now * dPO4_per_mL
    warn_po4 = not (po4_min <= po4_after <= po4_max)
    warn_no3 = False

mL_day_macro = (po4_daily / dPO4_per_mL) if dPO4_per_mL > 0 else 0.0
no3_from_daily = mL_day_macro * dNO3_per_mL
no3_drift = no3_from_daily - no3_daily

r_before, status_before = ratio_redfield(no3_base, po4_base)
r_after,  status_after  = ratio_redfield(no3_after, po4_after)

# ---------------------- Cálculos GH / KH ----------------------
# GH com ReeFlowers Shrimp Minerals (pó): 2 g/100L → +1°dGH  (≈ 1,15 mL/g se quiser medir em mL)
dGH_tank = max(0.0, gh_target - gh_now)
g_shrimp_tank = dGH_tank * (vol/100.0) * g_per_dGH_100L
ml_per_g_powder = 2.3/2.0   # ≈1,15 mL por grama (informação do fabricante)
ml_shrimp_tank_approx = g_shrimp_tank * ml_per_g_powder

g_shrimp_tpa = remin_mix_to * (tpa/100.0) * g_per_dGH_100L
ml_shrimp_tpa_approx = g_shrimp_tpa * ml_per_g_powder

# KH com ReeFlowers KH+: 30 mL/100L → +1°dKH
dKH_tank = max(0.0, kh_target - kh_now)
ml_khplus_tank = dKH_tank * (vol/100.0) * ml_khplus_per_dKH_100L
ml_khplus_tpa  = kh_target * (tpa/100.0) * ml_khplus_per_dKH_100L  # preparar TPA com KH alvo

# ---------------------- Saídas ----------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("## Resumo (macro)")
st.write(f"{'Com' if do_tpa else 'Sem'} TPA agora • Diluição aplicada: **{f_dilution*100:.1f}%**")
st.write(f"NO₃: {no3_now:.2f} → **{no3_base:.2f} ppm**  |  PO₄: {po4_now:.2f} → **{po4_base:.2f} ppm**")
st.write(f"Fertilizante: **{pctN:.2f}% N**, **{pctP:.2f}% P**, densidade **{density:.2f} g/mL**")
st.write(f"→ em {vol:.0f} L: **{dPO4_per_mL:.3f} ppm PO₄/mL** | **{dNO3_per_mL:.3f} ppm NO₃/mL**")
st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
st.write(f"**Correção agora:** **{mL_now:.2f} mL**  → após dose: NO₃ **{no3_after:.2f} ppm**, PO₄ **{po4_after:.2f} ppm**.")
if warn_no3: st.markdown('<span class="bad">Atenção:</span> NO₃ fora da faixa desejada.', unsafe_allow_html=True)
if warn_po4: st.markdown('<span class="bad">Atenção:</span> PO₄ fora da faixa desejada.', unsafe_allow_html=True)
st.caption("Se o macro acoplar demais N e P, use sais isolados (KNO₃ / KH₂PO₄) para correções finas.")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("## Redfield (NO₃:PO₄)")
st.write(f"Antes da dose: razão ≈ **{r_before:.2f}:1**  |  Depois da dose: **{r_after:.2f}:1**  •  pH atual: **{pH_now:.1f}**")
st.caption("Referência prática para íons (ppm): ~10:1 (verde 8–15, amarelo 6–18).")
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
csv_bytes = df_sched.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Baixar agenda (CSV)", data=csv_bytes, file_name="agenda_dosagem.csv", mime="text/csv")
st.markdown('</div>', unsafe_allow_html=True)

# GH / KH card (pó + KH+)
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("## GH & KH – Cálculo de dose (ReeFlowers)")

st.write(f"**GH (aquário):** Δ = {dGH_tank:.2f} °dH → Shrimp Minerals (pó) ≈ **{g_shrimp_tank:.2f} g** "
         f"(≈ {ml_shrimp_tank_approx:.2f} mL).")
if do_tpa and tpa > 0:
    st.write(f"**GH (TPA RO):** alvo {remin_mix_to:.2f} °dH em {tpa:.0f} L → **{g_shrimp_tpa:.2f} g** "
             f"(≈ {ml_shrimp_tpa_approx:.2f} mL) de Shrimp Minerals (pó).")
st.caption("Regra do fabricante: 2 g (~2,3 mL) elevam +1 °dH em 100 L. Dose diária sugerida: 2 g/100 L até atingir o GH desejado.")

st.write(f"**KH (aquário):** Δ = {dKH_tank:.2f} °dKH → KH+ ≈ **{ml_khplus_tank:.2f} mL**.")
if do_tpa and tpa > 0:
    st.write(f"**KH (TPA RO):** alvo {kh_target:.2f} °dKH em {tpa:.0f} L → **{ml_khplus_tpa:.2f} mL** de KH+.")
st.caption("Regra do fabricante: 30 mL/100 L → +1 °dKH. Manutenção típica: 2 mL/100 L/dia (ajuste conforme teste).")
st.markdown('</div>', unsafe_allow_html=True)

# Tabela de faixas recomendadas com destaque em verde se atual dentro da faixa
data = [
    {
        "Grupo": "Neocaridina davidi (Red Cherry, etc.)",
        "pH_range": (6.5, 7.8),
        "GH_range": (6.0, 12.0),
        "KH_range": (3.0, 8.0),
    },
    {
        "Grupo": "Caridina cantonensis (Crystal/Bee/Taiwan Bee)",
        "pH_range": (5.5, 6.5),
        "GH_range": (4.0, 6.0),
        "KH_range": (0.0, 2.0),
    },
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

def style_display(_):
    styles = pd.DataFrame('', index=df_display.index, columns=df_display.columns)
    for i in df_display.index:
        row = df_params.loc[i]
        if row["pH_min"] <= pH_now <= row["pH_max"]:
            styles.at[i, "pH"] = 'background-color:#065f46; color:#ecfeff; font-weight:600;'
        if row["GH_min"] <= gh_now <= row["GH_max"]:
            styles.at[i, "GH (°dH)"] = 'background-color:#065f46; color:#ecfeff; font-weight:600;'
        if row["KH_min"] <= kh_now <= row["KH_max"]:
            styles.at[i, "KH (°dKH)"] = 'background-color:#065f46; color:#ecfeff; font-weight:600;'
    return styles

styled = df_display.style.apply(style_display, axis=None)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("## Faixas recomendadas (com destaque pelos seus valores atuais)")
st.dataframe(styled, use_container_width=True)
st.caption("Misturar Neo e Caridina no mesmo aquário exige compromisso: um meio-termo (p.ex., pH ~6,8–7,0; GH 6–7; KH 2–3) "
           "costuma ser confortável para Neocaridinas e tolerável para algumas Caridinas, mas não é ideal para linhagens mais sensíveis.")
st.markdown('</div>', unsafe_allow_html=True)

# Export config
config = {
    "tank": {"volume_L": vol, "do_tpa_now": do_tpa, "tpa_L": tpa},
    "tests": {"pH": pH_now, "NO3_ppm": no3_now, "PO4_ppm": po4_now},
    "targets": {"mode": "PO4" if target_mode.startswith("PO₄") else "NO3",
                "PO4_ppm": po4_target, "NO3_ppm": no3_target},
    "macro": {"pctN": pctN, "pctP": pctP, "density_g_per_ml": density,
              "ppm_per_mL": {"PO4": dPO4_per_mL, "NO3": dNO3_per_mL},
              "dose_now_mL": mL_now, "after": {"NO3_ppm": no3_after, "PO4_ppm": po4_after},
              "daily_macro_mL": mL_day_macro, "NO3_drift_ppm_day": no3_drift},
    "gh_kh": {
        "GH_now": gh_now, "GH_target": gh_target, "g_per_dGH_100L": g_per_dGH_100L,
        "dose_tank_g": g_shrimp_tank, "TPA_mix_to_GH": remin_mix_to, "dose_TPA_g": g_shrimp_tpa,
        "KH_now": kh_now, "KH_target": kh_target, "ml_khplus_per_dKH_100L": ml_khplus_per_dKH_100L,
        "KHplus_mL_tank": ml_khplus_tank, "KHplus_mL_TPA": ml_khplus_tpa
    },
    "redfield": {"before_NO3_PO4": r_before, "after_NO3_PO4": r_after}
}
buf = io.BytesIO(json.dumps(config, indent=2, ensure_ascii=False).encode("utf-8"))
st.download_button("💾 Salvar configuração (JSON)", data=buf, file_name="config_doser.json", mime="application/json")

st.markdown('<span class="pill">Versão 1.3</span> <span class="pill">Redfield • GH/KH (pó & KH+)</span> <span class="pill">Use doses fracionadas</span>', unsafe_allow_html=True)
