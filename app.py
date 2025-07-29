import streamlit as st
import pandas as pd
import datetime as dt
from forecast_model import hent_vindprognose, hent_forbrugsforecast, hent_importforecast

# ---------- Konfiguration ----------
ZONE = "DK1"
KWH = 1000
KØB_TIMER = [0, 1, 2, 3, 4, 5, 12, 13, 14]

# ---------- Dato ----------
i_morgen = dt.date.today() + dt.timedelta(days=1)
dato_str = i_morgen.strftime('%Y-%m-%d')

# ---------- Residual og signal ----------
def beregn_signal(vind, forbrug, imp):
    df = pd.DataFrame({
        "Vind": vind,
        "Forbrug": forbrug,
        "Import": imp
    })
    df["Residual Load"] = df["Forbrug"] - df["Vind"]
    df["Signal?"] = (df["Residual Load"] > 2450) & (df["Import"] < 200)
    return df

# ---------- Confidence score ----------
def vurder_confidence(kilder):
    if all(k == "live" for k in kilder):
        return "🟢 Høj (live data)"
    elif kilder.count("fallback") == 1:
        return "🟡 Mellem (1 fallback)"
    else:
        return "🔴 Lav (flere fallback)"

# ---------- Køb-/salgstider ----------
def vælg_tidspunkter(df_signal):
    køb = df_signal[df_signal.index.isin(KØB_TIMER)].sort_values("Residual Load", ascending=False)
    køb_tid = køb.index[0] if not køb.empty else df_signal.index[0]
    sælg_tid = df_signal.sort_values("Residual Load").index[0]
    return køb_tid, sælg_tid

# ---------- App UI ----------
st.set_page_config(page_title="Elhandel Forecast", page_icon="⚡")
st.title("⚡ Day-Ahead Signal – 100 % datadrevet")
st.markdown(f"📅 **Signal for: {i_morgen.strftime('%A %d. %B %Y')}**")

# Datahentning
vind, vind_kilde = hent_vindprognose(dato_str)
forbrug, forbrug_kilde = hent_forbrugsforecast(dato_str)
imp, imp_kilde = hent_importforecast(dato_str)
confidence = vurder_confidence([vind_kilde, forbrug_kilde, imp_kilde])

# Beregn signal
df = beregn_signal(vind, forbrug, imp)

# Output
st.markdown(f"**Datakilder:** Vind: *{vind_kilde}*, Forbrug: *{forbrug_kilde}*, Import: *{imp_kilde}*")
st.markdown(f"**Confidence:** {confidence}")
st.dataframe(df)

# Signal
if df["Signal?"].any():
    køb_tid, sælg_tid = vælg_tidspunkter(df[df["Signal?"]])
    st.success("✅ Signal aktiv")
    st.markdown(f"- **Køb:** kl. **{køb_tid:02}:00**")
    st.markdown(f"- **Sælg:** kl. **{sælg_tid:02}:00**")
else:
    st.warning("❌ Ingen signal – krav ikke opfyldt i nogen time")
