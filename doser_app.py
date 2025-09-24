# doser_app.py — v2.12
import io, json, math, datetime as dt, tempfile
import pandas as pd
import altair as alt
import streamlit as st

st.set_page_config(page_title="Doser • Aquários", page_icon="💧", layout="wide")

PRIMARY_BG = "#0b1220"; CARD_BG = "#0f172a"; BORDER = "#1f2937"
TEXT = "#e2e8f0"; MUTED = "#94a3b8"; ACCENT = "#60a5fa"
GOOD = "#22c55e"; WARN = "#fbbf24"; BAD = "#ef4444"

# ---------------- CSS ----------------
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
  :root {{ --primary:{ACCENT}; --text:{TEXT}; --muted:{MUTED};
          --bg:{PRIMARY_BG}; --card:{CARD_BG}; --border:{BORDER};
          --good:{GOOD}; --warn:{WARN}; --bad:{BAD}; }}
  html, body, .stApp {{ font-family:'Inter',system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }}
  .stApp {{ background: radial-gradient(1100px 500px at 10% -10%, #0e1a35 10%, var(--bg) 60%); color: var(--text); }}
  .block-container {{ padding-top: 0rem; }}
  .top-banner {{ width: 100vw; margin-left: calc(-50vw + 50%); border-bottom:1px solid var(--border); }}
  .top-banner svg {{ display:block; width:100%; height:160px; }}
  @media (max-width:640px){{ .top-banner svg{{ height:110px; }} }}
  @media (max-width:420px){{ .top-banner svg{{ height: 90px; }} }}
  .hero {{ padding:18px 18px 8px; border-bottom:1px solid var(--border);
           background:linear-gradient(180deg, rgba(96,165,250,.08), rgba(0,0,0,0)); margin-bottom:6px; }}
  .hero h1 {{ margin:0; font-size:24px; letter-spacing:.2px; }}
  .muted {{ color:var(--muted); font-size:13px; }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:14px; padding:14px; margin:8px 0; }}
  .hr{{ border-top:1px solid var(--border); margin:10px 0; }}
  .kpi{{ display:flex; flex-direction:column; gap:6px; padding:14px; border-radius:16px;
        border:1px solid var(--border); background:linear-gradient(180deg, rgba(2,6,23,.4), rgba(2,6,23,.2)); }}
  .kpi .label{{ font-size:12px; color:var(--muted); }} .kpi .value{{ font-size:22px; font-weight:700; }}
  .good{{ color:var(--good)!important; }} .warn{{ color:var(--warn)!important; }} .bad{{ color:var(--bad)!important; }}
  .badge-row{{ display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 10px; }}
  .badge{{ display:inline-flex; align-items:center; gap:8px; padding:6px 12px; border-radius:999px; font-weight:600;
           border:1px solid var(--border); background:#0b1220; color:#e5e7eb; }}
  .badge.green{{ background:linear-gradient(180deg, rgba(34,197,94,.18), rgba(2,6,23,.25)); border-color:#14532d; color:#d1fae5; }}
  .badge.pink {{ background:linear-gradient(180deg, rgba(236,72,153,.18), rgba(2,6,23,.25)); border-color:#831843; color:#ffe4f1; }}
  .badge.blue {{ background:linear-gradient(180deg, rgba(59,130,246,.18), rgba(2,6,23,.25)); border-color:#1e3a8a; color:#dbeafe; }}
  .badge.slate{{ background:linear-gradient(180deg, rgba(100,116,139,.18), rgba(2,6,23,.25)); border-color:#334155; color:#e2e8f0; }}
  table.dataframe{{ border-collapse:collapse; width:100%; }}
  table.dataframe th, table.dataframe td{{ border:1px solid var(--border); padding:6px 8px; }}
  table.dataframe th{{ background:#0d162c; color:#e5e7eb; }}
</style>
""", unsafe_allow_html=True)

def theme_css(mode:str)->str:
    return "<style>:root{--primary:#22c55e}</style>" if mode=="Doce + Camarões" else "<style>:root{--primary:#60a5fa}</style>"

def kpi(title, value, subtitle="", cls=""):
    cls = f" {cls}" if cls else ""
    return f"""<div class="kpi"><div class="label">{title}</div>
               <div class="value{cls}">{value}</div><div class="sub">{subtitle}</div></div>"""

def render_badges(mode:str)->str:
    return ("""<div class="badge-row"><span class="badge green">🌿 Plantado</span>
               <span class="badge pink">🦐 Camarões</span><span class="badge slate">⚗️ Macro & Micro</span></div>"""
            if mode=="Doce + Camarões" else
            """<div class="badge-row"><span class="badge blue">🪸 Reef</span>
               <span class="badge slate">⚗️ Fusion 1 & 2</span></div>""")

def render_top_banner_svg(mode:str)->str:
    if mode=="Doce + Camarões":
        stops=[("#34d399","0%"),("#60a5fa","60%"),("#f472b6","100%")]; overlay="#0ea5e9"
    else:
        stops=[("#60a5fa","0%"),("#3b82f6","45%"),("#7c3aed","100%")]; overlay="#22d3ee"
    grad="\n".join([f'<stop offset="{p}" stop-color="{c}" />' for c,p in stops])
    return f"""<div class="top-banner"><svg viewBox="0 0 1200 160" preserveAspectRatio="none">
      <defs><linearGradient id="gradMain" x1="0" y1="0" x2="1" y2="0">{grad}</linearGradient></defs>
      <rect width="1200" height="160" fill="url(#gradMain)"/>
      <path d="M0,90 C300,150 900,30 1200,90 L1200,160 L0,160 Z" fill="{overlay}" opacity="0.25"/>
      <path d="M0,110 C300,170 900,50 1200,110 L1200,160 L0,160 Z" fill="white" opacity="0.06"/></svg></div>"""

# -------- Helpers Plantado --------
def conversions(density_g_per_ml: float, pctN: float, pctP: float):
    mgN = pctN/100.0 * density_g_per_ml * 1000.0
    mgP = pctP/100.0 * density_g_per_ml * 1000.0
    return mgN*(62/14), mgP*(95/31)  # mg NO3/mL, mg PO4/mL

def schedule_days(start_day: str, freq: int):
    days=["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"]
    idx=days.index(start_day); order=[days[(idx+i)%7] for i in range(7)]
    micros=[order[2]] if freq==1 else ([order[2],order[5]] if freq==2 else [order[1],order[3],order[5]] if freq==3 else [])
    return order, micros

def ratio_redfield(no3:float, po4:float):
    if po4<=0: return math.inf,"bad"
    r=no3/po4
    return r, ("good" if 8<=r<=15 else "warn" if 6<=r<=18 else "bad")

# -------- Helpers Reef --------
def dkh_from_meq(meq): return meq*2.8

# -------- Loader CSV/XLS/XLSX/NUMBERS --------
def load_history_any(up_file)->pd.DataFrame|None:
    name=(up_file.name or "").lower()
    try:
        if name.endswith(".csv"):
            df=pd.read_csv(up_file)
        elif name.endswith((".xlsx",".xls")):
            df=pd.read_excel(up_file)
        elif name.endswith(".numbers"):
            try:
                from numbers_parser import Document
            except Exception:
                st.error("Para abrir .numbers, instale `numbers-parser` (ou exporte para CSV)."); return None
            with tempfile.NamedTemporaryFile(delete=False,suffix=".numbers") as tmp:
                tmp.write(up_file.getbuffer()); path=tmp.name
            doc=Document(path); chosen=None; want={"timestamp","volume_L","KH_atual","Ca_atual","Mg_atual"}
            for s in doc.sheets:
                for t in s.tables:
                    mat=[]
                    for row in t.rows():
                        cells=getattr(row,"cells",row)
                        mat.append([getattr(c,"value",c) for c in cells])
                    if not mat: continue
                    header=[str(x) for x in mat[0]]
                    if want.issubset(set(header)):
                        chosen=pd.DataFrame(mat[1:],columns=header); break
                if chosen is not None: break
            if chosen is None:
                s=doc.sheets[0]; t=s.tables[0]; mat=[]
                for row in t.rows():
                    cells=getattr(row,"cells",row)
                    mat.append([getattr(c,"value",c) for c in cells])
                header=[str(x) for x in mat[0]] if mat else []
                chosen=pd.DataFrame(mat[1:],columns=header)
            df=chosen
        else:
            st.error("Formato não suportado. Use CSV, XLSX, XLS ou NUMBERS."); return None

        df=df.rename(columns={
            "KH atual":"KH_atual","Ca atual":"Ca_atual","Mg atual":"Mg_atual",
            "KH ideal":"KH_ideal","Ca ideal":"Ca_ideal","Mg ideal":"Mg_ideal",
            "KH/dia":"KH_cons","Ca/dia":"Ca_cons","Mg/dia":"Mg_cons",
            "Dose (mL)":"dose_pair_mL","KH ganho/dia":"KH_gain_dia","Ca ganho/dia":"Ca_gain_dia",
            "KH líquido/dia":"KH_liq_dia","Ca líquido/dia":"Ca_liq_dia",
        })

        def parse_ts(s):
            ts=pd.to_datetime(s,errors="coerce")
            if ts.isna().mean()>0.5: ts=pd.to_datetime(s,errors="coerce",dayfirst=True)
            return ts
        if "timestamp" in df.columns: df["timestamp"]=parse_ts(df["timestamp"])

        numeric=[
            "volume_L","KH_atual","Ca_atual","Mg_atual","KH_ideal","Ca_ideal","Mg_ideal",
            "KH_cons","Ca_cons","Mg_cons","dose_pair_mL","KH_gain_dia","Ca_gain_dia","KH_liq_dia","Ca_liq_dia"
        ]
        for c in numeric:
            if c in df.columns: df[c]=pd.to_numeric(df[c],errors="coerce").round(2)
        return df
    except Exception:
        st.error("Não consegui ler o arquivo. Tente CSV/Excel ou verifique o conteúdo."); return None

# -------------- Banner, header e modo --------------
mode_default=st.session_state.get("mode","Doce + Camarões")
st.markdown(theme_css(mode_default), unsafe_allow_html=True)
st.markdown(render_top_banner_svg(mode_default), unsafe_allow_html=True)

colh1,colh2=st.columns([1,1.2])
with colh1:
    st.markdown("""<div class="hero"><h1>💧 Doser – Aquários</h1>
    <div class="muted">Escolha o modo e os cartões se adaptam (Plantado + Camarões ou Reef).</div></div>""", unsafe_allow_html=True)
with colh2:
    st.radio("Tipo de aquário", ["Doce + Camarões","Marinho (Reef)"], horizontal=True, key="mode", index=0)

mode=st.session_state["mode"]
st.markdown(theme_css(mode), unsafe_allow_html=True)
st.markdown(render_badges(mode), unsafe_allow_html=True)

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("## ⚙️ Parâmetros do aquário")
    vol=st.number_input("Volume útil (L)", min_value=1.0, value=50.0, step=1.0, format="%.2f")

    if mode=="Doce + Camarões":
        do_tpa=st.checkbox("Vou fazer TPA agora", value=True)
        tpa=st.number_input("Volume da TPA (L)", min_value=0.0, value=20.0 if do_tpa else 0.0, step=1.0, disabled=not do_tpa, format="%.2f")

        st.markdown("---"); st.markdown("### 🧪 Testes atuais")
        pH_now=st.number_input("pH", min_value=4.5, max_value=8.5, value=6.8, step=0.1, format="%.2f")
        no3_now=st.number_input("NO₃ (ppm)", min_value=0.0, value=10.0, step=0.5, format="%.2f")
        po4_now=st.number_input("PO₄ (ppm)", min_value=0.0, value=0.40, step=0.05, format="%.2f")
        gh_now=st.number_input("GH (°dH)", min_value=0.0, value=6.0, step=0.5, format="%.2f")
        kh_now=st.number_input("KH (°dKH)", min_value=0.0, value=2.0, step=0.5, format="%.2f")

        st.markdown("---"); st.markdown("### 🎯 Alvo da correção (macro)")
        target_mode=st.radio("Nutriente alvo", ["PO₄ (recomendado)","NO₃"], index=0, horizontal=True)
        if target_mode.startswith("PO₄"):
            po4_target=st.number_input("Alvo de PO₄ (ppm)", min_value=0.0, value=0.90, step=0.05, format="%.2f")
            no3_min,no3_max=st.select_slider("Faixa desejada de NO₃ (ppm)", options=[8,9,10,11,12,13,14,15,16,17,18,19,20], value=(10,15))
            no3_target=(no3_min+no3_max)/2
        else:
            no3_target=st.number_input("Alvo de NO₃ (ppm)", min_value=0.0, value=12.0, step=0.5, format="%.2f")
            po4_min,po4_max=st.select_slider("Faixa desejada de PO₄ (ppm)", options=[0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2], value=(0.6,1.0))
            po4_target=(po4_min+po4_max)/2

        st.markdown("---"); st.markdown("### 🧪 Macro (líquido)")
        pctN=st.number_input("% N (elementar)", min_value=0.0, value=1.37, step=0.01, format="%.2f")
        pctP=st.number_input("% P (elementar)", min_value=0.0, value=0.34, step=0.01, format="%.2f")
        density=st.number_input("Densidade (g/mL)", min_value=0.5, value=1.00, step=0.01, format="%.2f")

        st.markdown("---"); st.markdown("### 📅 Consumo & Agenda")
        tpa_day=st.selectbox("Dia da TPA (para agenda)", options=["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"], index=1)
        po4_daily=st.number_input("Consumo diário de PO₄ (ppm/dia)", min_value=0.0, value=0.20, step=0.05, format="%.2f")
        no3_daily=st.number_input("Consumo diário de NO₃ (ppm/dia)", min_value=0.0, value=1.50, step=0.10, format="%.2f")
        micro_per30=st.number_input("Micro mL/30 L (por aplicação)", min_value=0.0, value=1.25, step=0.05, format="%.2f")
        micro_freq=st.selectbox("Aplicações de micro/semana", options=[1,2,3], index=1)

        st.markdown("---"); st.markdown("### 🌿 Nitrogênio isolado")
        dose_mL_per_100L=st.number_input("mL por dose (100 L)", min_value=0.1, value=6.0, step=0.1, format="%.2f")
        adds_ppm_per_100L=st.number_input("ppm NO₃ por dose (100 L)", min_value=0.1, value=4.8, step=0.1, format="%.2f")

        st.markdown("---"); st.markdown("### 🧱 GH & KH (ReeFlowers)")
        gh_target=st.number_input("GH alvo (°dH)", min_value=0.0, value=7.0, step=0.5, format="%.2f")
        g_per_dGH_100L=st.number_input("Shrimp Minerals (pó): g por +1°dGH/100 L", min_value=0.1, value=2.0, step=0.1, format="%.2f")
        remin_mix_to=st.number_input("Remineralizar TPA até GH (°dH)", min_value=0.0, value=gh_target, step=0.5, format="%.2f")
        kh_target=st.number_input("KH alvo (°dKH)", min_value=0.0, value=3.0, step=0.5, format="%.2f")
        ml_khplus_per_dKH_100L=st.number_input("KH+ mL por +1°dKH/100 L", min_value=1.0, value=30.0, step=1.0, format="%.2f")

    else:
        st.markdown("---"); st.markdown("### 🧪 Testes atuais (Reef)")
        kh_now=st.number_input("KH atual (°dKH)", min_value=0.0, value=8.0, step=0.1, format="%.2f")
        ca_now=st.number_input("Cálcio atual (ppm)", min_value=200.0, value=420.0, step=5.0, format="%.2f")
        mg_now=st.number_input("Magnésio atual (ppm)", min_value=800.0, value=1300.0, step=10.0, format="%.2f")

        st.markdown("---"); st.markdown("### 🎯 Alvos (Reef)")
        kh_target=st.number_input("KH ideal (°dKH)", min_value=6.0, value=9.0, step=0.1, format="%.2f")
        ca_target=st.number_input("Ca ideal (ppm)", min_value=340.0, value=430.0, step=5.0, format="%.2f")
        mg_target=st.number_input("Mg ideal (ppm)", min_value=1100.0, value=1300.0, step=10.0, format="%.2f")

        st.markdown("---"); st.markdown("### 📉 Consumo diário (estimado)")
        kh_cons=st.number_input("Consumo KH (°dKH/dia)", min_value=0.0, value=0.20, step=0.05, format="%.2f")
        ca_cons=st.number_input("Consumo Ca (ppm/dia)", min_value=0.0, value=2.0, step=0.5, format="%.2f")
        mg_cons=st.number_input("Consumo Mg (ppm/dia)", min_value=0.0, value=1.0, step=0.5, format="%.2f")

        st.markdown("---"); st.markdown("### 🧪 Potência (Fusion 1 & 2)")
        ca_ppm_per_ml_per_25L=st.number_input("Fusion 1: +ppm Ca por 1 mL/25 L", min_value=0.1, value=4.0, step=0.1, format="%.2f")
        alk_meq_per_ml_per_25L=st.number_input("Fusion 2: +meq/L por 1 mL/25 L", min_value=0.01, value=0.176, step=0.001, format="%.3f")
        max_ml_per_25L_day=st.number_input("Máx. mL por 25 L/dia (cada)", min_value=0.5, value=4.0, step=0.5, format="%.2f")
        max_kh_raise_net=st.number_input("Limite de aumento líquido KH (°dKH/dia)", min_value=0.2, value=1.0, step=0.1, format="%.2f")

# ---------------- Plantado ----------------
if mode=="Doce + Camarões":
    tpa_eff=tpa if do_tpa else 0.0
    f_dilution=1.0-(tpa_eff/vol)
    no3_base=no3_now*f_dilution; po4_base=po4_now*f_dilution
    mgNO3,mgPO4=conversions(density,pctN,pctP); dNO3=mgNO3/vol; dPO4=mgPO4/vol

    if target_mode.startswith("PO₄"):
        mL_now=max(0.0,(po4_target-po4_base)/dPO4) if dPO4>0 else 0.0
        po4_after=po4_base+mL_now*dPO4; no3_after=no3_base+mL_now*dNO3
        warn_no3=not (no3_min<=no3_after<=no3_max); warn_po4=False
    else:
        mL_now=max(0.0,(no3_target-no3_base)/dNO3) if dNO3>0 else 0.0
        no3_after=no3_base+mL_now*dNO3; po4_after=po4_base+mL_now*dPO4
        warn_po4=not (po4_min<=po4_after<=po4_max); warn_no3=False

    mL_day_macro=(po4_daily/dPO4) if dPO4>0 else 0.0
    no3_from_daily=mL_day_macro*dNO3; no3_drift=no3_from_daily-no3_daily
    r_before,s_before=ratio_redfield(no3_base,po4_base)
    r_after,s_after=ratio_redfield(no3_after,po4_after)

    ppm_per_mL_tank=(adds_ppm_per_100L/dose_mL_per_100L)*(100.0/vol)
    need_N = (r_after<8) or (target_mode.startswith("PO₄") and (no3_after<no3_min))
    N_target_ppm=(no3_min+no3_max)/2 if target_mode.startswith("PO₄") else no3_target
    N_dose_mL=max(0.0,(N_target_ppm-no3_after)/ppm_per_mL_tank) if need_N and ppm_per_mL_tank>0 else 0.0

    k1,k2,k3,k4,k5=st.columns(5)
    with k1: st.markdown(kpi("🎯 Dose agora (macro)", f"{mL_now:.2f} mL","para atingir o alvo"), unsafe_allow_html=True)
    with k2: st.markdown(kpi("🗓️ Manutenção diária", f"{mL_day_macro:.2f} mL/dia","macro baseado em PO₄"), unsafe_allow_html=True)
    with k3:
        cls="good" if s_after=="good" else ("warn" if s_after=="warn" else "bad")
        st.markdown(kpi("📈 Redfield pós-dose", f"{r_after:.2f}:1","NO₃:PO₄ (ppm)", cls), unsafe_allow_html=True)
    with k4: st.markdown(kpi("GH alvo", f"{gh_target:.2f} °dH","ReeFlowers (pó)"), unsafe_allow_html=True)
    with k5: st.markdown(kpi("KH alvo", f"{kh_target:.2f} °dKH","KH+"), unsafe_allow_html=True)

    left,right=st.columns([1.1,1])
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## Resumo (macro)")
        st.write(f"{'Com' if do_tpa else 'Sem'} TPA agora • Diluição aplicada: **{f_dilution*100:.2f}%**")
        st.write(f"NO₃: {no3_now:.2f} → **{no3_base:.2f} ppm** | PO₄: {po4_now:.2f} → **{po4_base:.2f} ppm**")
        st.write(f"Fertilizante: **{pctN:.2f}% N**, **{pctP:.2f}% P**, densidade **{density:.2f} g/mL**")
        st.write(f"→ em {vol:.0f} L: **{dPO4:.2f} ppm PO₄/mL** | **{dNO3:.2f} ppm NO₃/mL**")
        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
        st.write(f"**Correção agora:** **{mL_now:.2f} mL** → após dose: NO₃ **{no3_after:.2f} ppm**, PO₄ **{po4_after:.2f} ppm**.")
        if target_mode.startswith("PO₄") and warn_no3: st.markdown('<span class="bad">Atenção:</span> NO₃ fora da faixa desejada.', unsafe_allow_html=True)
        if (not target_mode.startswith("PO₄")) and warn_po4: st.markdown('<span class="bad">Atenção:</span> PO₄ fora da faixa desejada.', unsafe_allow_html=True)
        if N_dose_mL>0: st.write(f"Adicionar **{N_dose_mL:.2f} mL** de **Nitrogênio** para atingir **{N_target_ppm:.2f} ppm** de **NO₃**.")
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## Redfield & pH")
        st.write(f"Antes: **{r_before:.2f}:1** | Depois: **{r_after:.2f}:1**")
        st.write(f"pH atual: **{pH_now:.2f}**")
        st.caption("Guia: alvo ~10:1 (verde 8–15, amarelo 6–18).")
        st.markdown('</div>', unsafe_allow_html=True)

    # Agenda semanal
    order_days,micro_days=schedule_days(tpa_day,micro_freq)
    micro_per_app=micro_per30*(vol/30.0)
    rows=[]
    for j,d in enumerate(order_days):
        macro=mL_day_macro; micro=micro_per_app if d in micro_days else 0.0; note=[]
        if j==0 and do_tpa: note.append("TPA")
        if j==0 and mL_now>1e-4: note.append("Correção")
        rows.append({"Dia":d,"Macro (mL)":round(macro,2),"Micro (mL)":round(micro,2),"Obs.":" + ".join(note)})
    df_sched=pd.DataFrame(rows)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Agenda semanal (macro & micro)")
    st.dataframe(df_sched, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Baixar agenda (CSV)", data=df_sched.to_csv(index=False).encode(), file_name="agenda_dosagem.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

    # GH/KH
    dGH=max(0.0, gh_target-gh_now); g_shrimp=dGH*(vol/100.0)*g_per_dGH_100L
    ml_per_g=2.3/2.0; ml_shrimp=g_shrimp*ml_per_g
    g_shrimp_tpa=remin_mix_to*(tpa/100.0)*g_per_dGH_100L; ml_shrimp_tpa=g_shrimp_tpa*ml_per_g
    dKH=max(0.0, kh_target-kh_now); ml_kh_tank=dKH*(vol/100.0)*ml_khplus_per_dKH_100L
    ml_kh_tpa=kh_target*(tpa/100.0)*ml_khplus_per_dKH_100L; ml_kh_daily=2.0*(vol/100.0)

    c1,c2=st.columns(2)
    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## GH – Shrimp Minerals (pó)")
        st.write(f"Δ GH: **{dGH:.2f} °dH** → **{g_shrimp:.2f} g** (≈ {ml_shrimp:.2f} mL).")
        if do_tpa and tpa>0: st.write(f"Remineralizar TPA a **{remin_mix_to:.2f} °dH** em **{tpa:.0f} L** → **{g_shrimp_tpa:.2f} g** (≈ {ml_shrimp_tpa:.2f} mL).")
        st.caption("Regra: 2 g (~2,3 mL) elevam +1 °dH em 100 L.")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## KH – ReeFlowers KH+")
        st.write(f"Δ KH: **{dKH:.2f} °dKH** → **{ml_kh_tank:.2f} mL** de KH+.")
        if do_tpa and tpa>0: st.write(f"Preparar TPA: alvo **{kh_target:.2f} °dKH** em **{tpa:.0f} L** → **{ml_kh_tpa:.2f} mL**.")
        st.write(f"Manutenção diária sugerida: **{ml_kh_daily:.2f} mL/dia** (2 mL/100 L).")
        st.caption("Regra: 30 mL/100 L → +1 °dKH.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Faixas camarões
    data=[{"Grupo":"Neocaridina davidi (Red Cherry, etc.)","pH_range":(6.5,7.8),"GH_range":(6.0,12.0),"KH_range":(3.0,8.0)},
          {"Grupo":"Caridina cantonensis (Crystal/Bee/Taiwan Bee)","pH_range":(5.5,6.5),"GH_range":(4.0,6.0),"KH_range":(0.0,2.0)}]
    dfp=pd.DataFrame({
        "Grupo":[d["Grupo"] for d in data],
        "pH":[f"{d['pH_range'][0]:.1f}–{d['pH_range'][1]:.1f}" for d in data],
        "pH_min":[d["pH_range"][0] for d in data],"pH_max":[d["pH_range"][1] for d in data],
        "GH (°dH)":[f"{d['GH_range'][0]:.0f}–{d['GH_range'][1]:.0f}" for d in data],
        "GH_min":[d["GH_range"][0] for d in data],"GH_max":[d["GH_range"][1] for d in data],
        "KH (°dKH)":[f"{d['KH_range'][0]:.0f}–{d['KH_range'][1]:.0f}" for d in data],
        "KH_min":[d["KH_range"][0] for d in data],"KH_max":[d["KH_range"][1] for d in data],
    })
    show=dfp[["Grupo","pH","GH (°dH)","KH (°dKH)"]].copy()
    def _hl(_,dfp=dfp,pH_now=pH_now,gh_now=gh_now,kh_now=kh_now):
        s=pd.DataFrame('', index=show.index, columns=show.columns)
        for i in show.index:
            r=dfp.loc[i]
            if r["pH_min"]<=pH_now<=r["pH_max"]: s.at[i,"pH"]='background-color:#065f46; color:#ecfeff; font-weight:600;'
            if r["GH_min"]<=gh_now<=r["GH_max"]: s.at[i,"GH (°dH)"]='background-color:#065f46; color:#ecfeff; font-weight:600;'
            if r["KH_min"]<=kh_now<=r["KH_max"]: s.at[i,"KH (°dKH)"]='background-color:#065f46; color:#ecfeff; font-weight:600;'
        return s
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Faixas recomendadas (Doce – camarões)")
    st.markdown(show.style.apply(_hl, axis=None).to_html(), unsafe_allow_html=True)
    st.caption("Compromisso p/ Neo + Caridina: pH ~6,8–7,0; GH 6–7; KH 2–3.")
    st.markdown('</div>', unsafe_allow_html=True)

    cfg={"mode":"freshwater_shrimp","tank":{"volume_L":vol,"do_tpa_now":do_tpa,"tpa_L":tpa}}
    st.download_button("💾 Salvar configuração (JSON)",
                       data=json.dumps(cfg,indent=2,ensure_ascii=False).encode(),
                       file_name="config_doser_fw.json", mime="application/json")

# ---------------- Reef ----------------
else:
    ca_per_ml= (st.session_state.get('ca_ppm_per_ml_per_25L', None) or 4.0) * (25.0/vol)
    # Releitura a partir dos widgets (já definidos no sidebar Reef)
    ca_per_ml = st.session_state.get('ca_ppm_per_ml_per_25L', 4.0) * (25.0/vol)
    alk_meq = st.session_state.get('alk_meq_per_ml_per_25L', 0.176)
    kh_per_ml = dkh_from_meq(alk_meq) * (25.0/vol)
    max_ml_tank = st.session_state.get('max_ml_per_25L_day', 4.0) * (vol/25.0)
    max_kh_raise = st.session_state.get('max_kh_raise_net', 1.0)

    # traz do sidebar
    kh_now = st.session_state.get('KH atual (°dKH)', None) or st.session_state.get('kh_now', None) or kh_now
    ca_now = st.session_state.get('Cálcio atual (ppm)', None) or ca_now
    mg_now = st.session_state.get('Magnésio atual (ppm)', None) or mg_now
    kh_target = st.session_state.get('KH ideal (°dKH)', None) or kh_target
    ca_target = st.session_state.get('Ca ideal (ppm)', None) or ca_target
    mg_target = st.session_state.get('Mg ideal (ppm)', None) or mg_target
    kh_cons = st.session_state.get('Consumo KH (°dKH/dia)', None) or kh_cons
    ca_cons = st.session_state.get('Consumo Ca (ppm/dia)', None) or ca_cons
    mg_cons = st.session_state.get('Consumo Mg (ppm/dia)', None) or mg_cons

    dKH_needed = max(0.0, kh_target - kh_now)
    desired_kh_today = min(dKH_needed, max_kh_raise + kh_cons)
    ml_f2 = (desired_kh_today / kh_per_ml) if kh_per_ml>0 else 0.0
    ml_f1 = (ca_cons / ca_per_ml) if ca_per_ml>0 else 0.0
    ml_pair = max(ml_f2, ml_f1); limited=False
    if ml_pair>max_ml_tank: ml_pair=max_ml_tank; limited=True

    kh_gain = ml_pair * kh_per_ml
    ca_gain = ml_pair * ca_per_ml
    kh_net  = kh_gain - kh_cons
    ca_net  = ca_gain - ca_cons
    days_kh = math.inf if kh_net<=0 else math.ceil(dKH_needed / min(kh_net, max_kh_raise))

    k1,k2,k3,k4=st.columns(4)
    with k1: st.markdown(kpi("🧪 Fusion 1 (diário)", f"{ml_pair:.2f} mL", f"{ca_gain:.2f} ppm Ca/dia (bruto)"), unsafe_allow_html=True)
    with k2: st.markdown(kpi("🧪 Fusion 2 (diário)", f"{ml_pair:.2f} mL", f"{kh_gain:.2f} °dKH/dia (bruto)"), unsafe_allow_html=True)
    ok=(8<=round(kh_now)<=12) and (380<=round(ca_now)<=450) and (1250<=round(mg_now)<=1350)
    with k3: st.markdown(kpi("🎛️ Estado atual", f"KH {kh_now:.2f} • Ca {ca_now:.2f} • Mg {mg_now:.2f}", "verde=ok, vermelho=fora", "good" if ok else "bad"), unsafe_allow_html=True)
    with k4: st.markdown(kpi("📅 Dias p/ KH alvo", "—" if days_kh==math.inf else f"~{days_kh}", f"alvo {kh_target:.2f} °dKH"), unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Resumo (Reef) – Fusion 1 & 2 (pareados)")
    st.write(f"**Plano diário**: **{ml_pair:.2f} mL** de **Fusion 1** e **{ml_pair:.2f} mL** de **Fusion 2**.")
    st.write(f"→ Bruto: **+{kh_gain:.2f} °dKH/dia**, **+{ca_gain:.2f} ppm Ca/dia**. | Líquido (consumo): KH **{kh_net:.2f}** / Ca **{ca_net:.2f}** por dia.")
    if limited: st.markdown('<span class="bad">Limitado pelo fabricante (dose capada).</span>', unsafe_allow_html=True)
    st.caption("Dosar as partes em locais diferentes; não exceder 4 mL/25 L/dia de cada.")

    # -------- VISUALIZAÇÃO --------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Visualização")
    view_mode=st.radio("Mostrar", ["Histórico (valores medidos)","Projeção (simulada)"], horizontal=True, index=0)

    if view_mode.startswith("Histórico"):
        st.markdown("### Gráfico histórico (KH, Ca, Mg) por data")
        if "reef_history" in st.session_state and not st.session_state.reef_history.empty:
            dfh=st.session_state.reef_history.copy()
            def parse_ts(s):
                ts=pd.to_datetime(s,errors="coerce")
                if ts.isna().mean()>0.5: ts=pd.to_datetime(s,errors="coerce",dayfirst=True)
                return ts
            dfh["timestamp"]=parse_ts(dfh["timestamp"])
            dfh=dfh.dropna(subset=["timestamp"]).sort_values("timestamp")

            compact_daily=st.checkbox("Compactar por dia (usa o último registro de cada dia)", value=True)

            if compact_daily:
                # === FIXO: um ponto por dia ===
                df_day=(dfh.set_index("timestamp")
                          .resample("D").last()
                          .dropna(subset=["KH_atual","Ca_atual","Mg_atual"], how="all")
                          .reset_index().rename(columns={"timestamp":"Dia"}))
                df_plot=df_day.set_index("Dia")[["KH_atual","Ca_atual","Mg_atual"]]
                df_long=df_day.melt(id_vars=["Dia"], value_vars=["KH_atual","Ca_atual","Mg_atual"],
                                    var_name="Parametro", value_name="Valor")
                x_enc=alt.X('Dia:T', axis=alt.Axis(title='Data', format='%d/%m', labelAngle=-20, tickCount='day'))
            else:
                df_plot=dfh.set_index("timestamp")[["KH_atual","Ca_atual","Mg_atual"]]
                df_long=dfh.melt(id_vars=["timestamp"], value_vars=["KH_atual","Ca_atual","Mg_atual"],
                                 var_name="Parametro", value_name="Valor")
                x_enc=alt.X('timestamp:T', axis=alt.Axis(title='Data', format='%d/%m', labelAngle=-20))

            base=alt.Chart(df_long).encode(
                x=x_enc,
                y=alt.Y('Valor:Q', axis=alt.Axis(title='Valor')),
                color=alt.Color('Parametro:N', legend=alt.Legend(title=None)),
                tooltip=[alt.Tooltip(df_long.columns[0]+':T', title='Data', format='%d/%m/%Y'),
                         alt.Tooltip('Parametro:N', title='Parâmetro'),
                         alt.Tooltip('Valor:Q', title='Valor', format='.2f')]
            )
            st.altair_chart(base.mark_line(interpolate='monotone', strokeWidth=2.5) + base.mark_circle(size=64), use_container_width=True)

            # Consumo observado (mediana das variações entre pontos)
            idx=df_plot.index
            dt_days=idx.to_series().diff().dt.total_seconds().div(86400.0).replace([0, None], pd.NA).fillna(1.0)
            df_obs=df_plot.copy()
            for col in ["KH_atual","Ca_atual","Mg_atual"]:
                per_day=(df_obs[col].diff()/dt_days).replace([pd.NA,float("inf"),-float("inf")],0)
                df_obs[col+"_dday"]=per_day

            def med_cons(s, clamp=None):
                s=pd.to_numeric(s,errors="coerce").dropna()
                if clamp is not None: s=s.clip(lower=-clamp, upper=clamp)
                return float(max(0.0, round(-s.median(),2))) if not s.empty else 0.0

            kh_cons_obs=med_cons(df_obs["KH_atual_dday"], clamp=3.0)
            ca_cons_obs=med_cons(df_obs["Ca_atual_dday"], clamp=50.0)
            mg_cons_obs=med_cons(df_obs["Mg_atual_dday"], clamp=20.0)

            k1,k2,k3=st.columns(3)
            with k1: st.markdown(kpi("KH – consumo observado", f"{kh_cons_obs:.2f} °dKH/dia"), unsafe_allow_html=True)
            with k2: st.markdown(kpi("Ca – consumo observado", f"{ca_cons_obs:.2f} ppm/dia"), unsafe_allow_html=True)
            with k3: st.markdown(kpi("Mg – consumo observado", f"{mg_cons_obs:.2f} ppm/dia"), unsafe_allow_html=True)
            st.caption("Com ‘Compactar por dia’, o ponto é o **último registro** de cada dia (resample D → last).")
        else:
            st.info("Seu histórico ainda está vazio. Adicione linhas no card abaixo e o gráfico aparece aqui.")
    else:
        st.markdown("### Projeção por data (KH, Ca, Mg)")
        default_start=dt.date.today()
        if "reef_history" in st.session_state and not st.session_state.reef_history.empty:
            try:
                last_ts=pd.to_datetime(st.session_state.reef_history["timestamp"], errors="coerce").dropna()
                if not last_ts.empty: default_start=last_ts.max().date()
            except Exception: pass
        start=st.date_input("Iniciar projeção em", value=default_start)
        days=st.slider("Dias para projetar", min_value=7, max_value=30, value=14, step=1)

        dates=pd.date_range(start, periods=days+1, freq="D")
        kh_list,ca_list,mg_list=[],[],[]
        kh_val,ca_val,mg_val=kh_now,ca_now,mg_now
        kh_list.append(kh_val); ca_list.append(ca_val); mg_list.append(mg_val)
        kh_gain=max(0.0, kh_gain); ca_gain=max(0.0, ca_gain)
        for _ in range(days):
            kh_inc=min(kh_gain-kh_cons, max_kh_raise)
            ca_inc=ca_gain-ca_cons
            mg_inc=-mg_cons
            kh_val=min(kh_target, kh_val+max(0.0, kh_inc))
            ca_val=min(ca_target, ca_val+ca_inc)
            mg_val=max(0.0, mg_val+mg_inc)
            kh_list.append(kh_val); ca_list.append(ca_val); mg_list.append(mg_val)

        df_proj=pd.DataFrame({"Data":dates,"KH (°dKH)":kh_list,"Ca (ppm)":ca_list,"Mg (ppm)":mg_list})
        long=df_proj.melt(id_vars=["Data"], var_name="Parametro", value_name="Valor")
        chart=(alt.Chart(long).mark_line(interpolate='monotone', strokeWidth=2.5)
               .encode(x=alt.X('Data:T', axis=alt.Axis(title='Data', format='%d/%m', labelAngle=-20)),
                       y='Valor:Q', color='Parametro:N',
                       tooltip=[alt.Tooltip('Data:T', title='Data', format='%d/%m/%Y'),
                                alt.Tooltip('Parametro:N'), alt.Tooltip('Valor:Q', format='.2f')])
               .properties(height=260))
        st.altair_chart(chart, use_container_width=True)
        st.caption("Projeção: dose pareada diária constante; Mg cai apenas pelo consumo.")

    st.markdown('</div>', unsafe_allow_html=True)

    # Histórico Reef (upload/append + guard)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Histórico Reef (CSV / Excel / Numbers)")
    if "reef_history" not in st.session_state:
        st.session_state.reef_history = pd.DataFrame(columns=[
            "timestamp","volume_L","KH_atual","Ca_atual","Mg_atual",
            "KH_ideal","Ca_ideal","Mg_ideal","KH_cons","Ca_cons","Mg_cons",
            "dose_pair_mL","KH_gain_dia","Ca_gain_dia","KH_liq_dia","Ca_liq_dia","obs"
        ])
    up=st.file_uploader("Carregar arquivo", type=["csv","xlsx","xls","numbers"], key="reef_uploader")
    if up is not None:
        sig=(up.name, getattr(up,"size",None))
        if st.session_state.get("reef_loaded_sig")!=sig:
            df_loaded=load_history_any(up)
            if df_loaded is not None:
                st.session_state.reef_history=df_loaded; st.session_state.reef_loaded_sig=sig
                st.success("Histórico carregado com sucesso.")
    obs=st.text_input("Observações (opcional)")
    if st.button("➕ Adicionar linha desta sessão"):
        row={"timestamp":dt.datetime.now().isoformat(timespec="seconds"),
             "volume_L":vol,"KH_atual":round(kh_now,2),"Ca_atual":round(ca_now,2),"Mg_atual":round(mg_now,2),
             "KH_ideal":round(kh_target,2),"Ca_ideal":round(ca_target,2),"Mg_ideal":round(mg_target,2),
             "KH_cons":round(kh_cons,2),"Ca_cons":round(ca_cons,2),"Mg_cons":round(mg_cons,2),
             "dose_pair_mL":round(ml_pair,2),"KH_gain_dia":round(kh_gain,2),"Ca_gain_dia":round(ca_gain,2),
             "KH_liq_dia":round(kh_net,2),"Ca_liq_dia":round(ca_net,2),"obs":obs or ""}
        st.session_state.reef_history = pd.concat([st.session_state.reef_history, pd.DataFrame([row])], ignore_index=True)
        st.success("Linha adicionada ao histórico local.")

    st.dataframe(st.session_state.reef_history, use_container_width=True)
    st.download_button("⬇️ Baixar histórico (CSV)",
                       data=st.session_state.reef_history.to_csv(index=False).encode(),
                       file_name="reef_history.csv", mime="text/csv")
    st.caption("Dica: faça upload deste mesmo arquivo na próxima sessão para continuar seu log.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Faixas Reef
    reef_df=pd.DataFrame({
        "Parâmetro":["KH (°dKH)","Ca (ppm)","Mg (ppm)"],
        "Atual":[round(kh_now,2),round(ca_now,2),round(mg_now,2)],
        "Faixa":["8–12","380–450","1250–1350"],
        "min":[8.0,380.0,1250.0],"max":[12.0,450.0,1350.0],
    })
    show=reef_df[["Parâmetro","Atual","Faixa"]].copy()
    def _style(df_show,limits=reef_df[["min","max"]]):
        s=pd.DataFrame('', index=df_show.index, columns=df_show.columns)
        for i in df_show.index:
            mn,mx=limits.loc[i,"min"],limits.loc[i,"max"]; val=df_show.loc[i,"Atual"]
            s.at[i,"Atual"]=('background-color:#065f46; color:#ecfeff; font-weight:600;'
                             if mn<=val<=mx else 'background-color:#7f1d1d; color:#fee2e2; font-weight:600;')
        return s
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Faixas recomendadas (Reef)")
    st.markdown(show.style.apply(_style, axis=None).to_html(), unsafe_allow_html=True)
    st.caption("Padrão: KH 8–12 • Ca 380–450 ppm • Mg 1250–1350 ppm.")
    st.markdown('<div class="muted">Versão 2.12 • Histórico diário por resample • Consumo observado consistente • UI refinada</div>', unsafe_allow_html=True)
