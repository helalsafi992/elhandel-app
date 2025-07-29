import streamlit as st
import pandas as pd
import datetime as dt
import requests

# ---------- Konfiguration ----------
ZONE = "DK1"
KWH = 1000
KØB_TIMER = [0, 1, 2, 3, 4, 5, 12, 13, 14]
i_morgen = dt.date.today() + dt.timedelta(days=1)
dato_str = i_morgen.strftime('%Y-%m-%d')

# ---------- Vindforecast ----------
def hent_vindprognose(dato):
    try:
        url = f"https://api.energidataservice.dk/dataset/ForeCastWindProduction?start={dato}T00:00&end={dato}T23:59&limit=1000"
        res = requests.get(url).json()["records"]
        df = pd.DataFrame(res)
        df["Hour"] = pd.to_datetime(df["Minutes5UTC"]).dt.hour
        vind = df.groupby("Hour")[["Offshore", "Onshore"]].mean().sum(axis=1)
        return vind.round(0), "live"
    except:
        fallback = pd.Series([2000]*24, index=range(24))
        return fallback, "fallback"

# ---------- Forbrugsforecast ----------
def hent_forbrugsforecast(dato):
    try:
        url = f"https://api.energidataservice.dk/dataset/ConsumptionForecast?start={dato}T00:00&end={dato}T23:59&filter={{\"PriceArea\":[\"{ZONE}\"]}}"
        res = requests.get(url).json()["records"]
        df = pd.DataFrame(res)
        df["Hour"] = pd.to_datetime(df["HourUTC"]).dt.hour
        forbrug = df.groupby("Hour")["ForecastLoad"].mean()
        return forbrug.round(0), "live"
    except:
        base = 5100
        pattern = [0.85,0.80,0.75,0.73,0.75,0.78,0.85,0.95,1.00,1.05,1.10,1.12,
                   1.15,1.10,1.05,1.00,1.02,1.04,1.00,0.95,0.90,0.85,0.83,0.80]
        fallback = pd.Series([int(base * p) for p in pattern], index=range(24))
        return fallback, "fallback"

# ---------- Importestimat ----------
def hent_importforecast(dato):
    try:
        url = f"https://api.energidataservice.dk/dataset/NetExchange?start={dato}T00:00&end={dato}T23:59&filter={{\"PriceArea\":[\"{ZONE}\"]}}"
        res = requests.get(url).json()["records"]
        df = pd.DataFrame(res)
        df["Hour"] = pd.to_datetime(df["HourUTC"]).dt.hour
        df_pos = df[df["Exchange"] > 0]
        imp = df_pos.groupby("Hour")["Exchange"].mean().round(0)
        return imp, "live"
    except:
        fallback = pd.Series([150]*24, index=range(24))
        return fallback, "fallback"

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

# ---------- UI ----------
st.title("⚡ Day-Ahead Signal – 100 % datadrevet")
st.markdown(f"📅 **Signal for: {i_morgen.strftime('%A %d. %B %Y')}**")

vind, vind_kilde = hent_vindprognose(dato_str)
forbrug, forbrug_kilde = hent_forbrugsforecast(dato_str)
imp, imp_kilde = hent_importforecast(dato_str)
confidence = vurder_confidence([vind_kilde, forbrug_kilde, imp_kilde])

df = beregn_signal(vind, forbrug, imp)

st.markdown(f"**Datakilder:** Vind: *{vind_kilde}*, Forbrug: *{forbrug_kilde}*, Import: *{imp_kilde}*")
st.markdown(f"**Confidence:** {confidence}")
st.dataframe(df)

if df["Signal?"].any():
    køb_tid, sælg_tid = vælg_tidspunkter(df[df["Signal?"]])
    st.success("✅ Signal aktiv")
    st.markdown(f"- **Køb:** kl. **{køb_tid:02}:00**")
    st.markdown(f"- **Sælg:** kl. **{sælg_tid:02}:00**")
else:
    st.warning("❌ Ingen signal – krav ikke opfyldt i nogen time")
