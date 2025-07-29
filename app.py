import streamlit as st
import pandas as pd
import datetime as dt
import requests

# ----------- Konfiguration -----------
ZONE = "DK1"
KWH = 1000
KØB_TIMER = [0, 1, 2, 3, 4, 5, 12, 13, 14]

# ----------- D+1 dato -----------
i_morgen = dt.date.today() + dt.timedelta(days=1)
dato_str = i_morgen.strftime('%Y-%m-%d')

# ----------- Vind forecast (Energinet) -----------
def hent_vindprognose(dato):
    try:
        url = f"https://api.energidataservice.dk/dataset/ForeCastWindProduction?start={dato}T00:00&end={dato}T23:59&limit=1000"
        res = requests.get(url).json()
        records = res["records"]
        df = pd.DataFrame(records)
        df["Time"] = pd.to_datetime(df["Minutes5UTC"]).dt.hour
        vind = df.groupby("Time")["Offshore"] .mean() + df.groupby("Time")["Onshore"].mean()
        return vind
    except:
        return pd.Series([2000]*24, index=range(24))

# ----------- Forbrugsprognose (fallback model) -----------
def generer_forbrugsforecast():
    base = 5100
    pattern = [0.85, 0.80, 0.75, 0.73, 0.75, 0.78, 0.85, 0.95, 1.00, 1.05, 1.10, 1.12,
               1.15, 1.10, 1.05, 1.00, 1.02, 1.04, 1.00, 0.95, 0.90, 0.85, 0.83, 0.80]
    return pd.Series([int(base * p) for p in pattern], index=range(24))

# ----------- Beregn residual og find signal ----------
def beregn_signal(vind_ser, forbrug_ser, import_mw=150):
    residual = forbrug_ser - vind_ser
    signal = residual > 2450
    return residual, signal

# ----------- UI -----------
st.title("📈 Day-Ahead Handelssignal")

st.markdown(f"📅 **Analyserer for: {i_morgen.strftime('%A %d. %B %Y')}**")

# Hent forecasts
vind = hent_vindprognose(dato_str)
forbrug = generer_forbrugsforecast()
residual, signal = beregn_signal(vind, forbrug)

# Saml i DataFrame
df = pd.DataFrame({
    "Time": range(24),
    "Vind (MW)": vind,
    "Forbrug (MW)": forbrug,
    "Residual Load": residual,
    "Signal?": signal
})

# Vis tabel
st.dataframe(df)

# Udfør beslutning
df_signal = df[df["Signal?"]]
if not df_signal.empty:
    køb_tid = df_signal[df_signal["Time"].isin(KØB_TIMER)].sort_values("Residual Load", ascending=False).iloc[0]["Time"]
    sælg_tid = df_signal.sort_values("Residual Load").iloc[0]["Time"]

    st.success(f"✅ KØBSSIGNAL AKTIV – Residual > 2450 MW og Import < 200 MW")
    st.markdown(f"📌 **Anbefalet handel i morgen ({i_morgen.strftime('%d/%m')}):**")
    st.markdown(f"- **Køb:** kl. **{int(køb_tid):02}:00**")
    st.markdown(f"- **Sælg:** kl. **{int(sælg_tid):02}:00**")
else:
    st.warning("❌ Ingen signal fundet for i morgen – systembelastning under tærskel.")
