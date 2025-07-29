import streamlit as st
import pandas as pd
import datetime as dt
import requests

# ---------- Konfiguration ----------
zone = "DK1"

# ---------- Hent senest gyldig dato med data ----------
def find_seneste_dato(max_dage=10):
    for i in range(max_dage):
        dato = dt.date.today() - dt.timedelta(days=i)
        vind, forbrug, imp = hent_reelle_data(dato)
        if vind > 0 and forbrug > 0 and imp >= 0:
            return dato
    return None

# ---------- Hent reelle værdier ----------
def hent_reelle_data(dato):
    vind = 0
    forbrug = 0
    imp = 0
    try:
        d_str = dato.strftime('%Y-%m-%d')
        # Vind
        v_url = f"https://api.energidataservice.dk/dataset/ActualWindProduction?start={d_str}T00:00&end={d_str}T23:59&filter={{\"PriceArea\":[\"{zone}\"]}}&limit=1000"
        v_res = requests.get(v_url).json()
        vind = sum([x["OffshoreWindPower"] + x["OnshoreWindPower"] for x in v_res["records"]]) // len(v_res["records"])
        # Forbrug
        f_url = f"https://api.energidataservice.dk/dataset/ConsumptionDE35?start={d_str}T00:00&end={d_str}T23:59&filter={{\"PriceArea\":[\"{zone}\"]}}&limit=1000"
        f_res = requests.get(f_url).json()
        forbrug = sum([x["Consumption"] for x in f_res["records"]]) // len(f_res["records"])
        # Import
        n_url = f"https://api.energidataservice.dk/dataset/NetExchange?start={d_str}T00:00&end={d_str}T23:59&filter={{\"PriceArea\":[\"{zone}\"]}}&limit=1000"
        n_res = requests.get(n_url).json()
        imp = sum([x["Exchange"] for x in n_res["records"] if x["Exchange"] > 0]) // len(n_res["records"])
    except:
        pass
    return int(vind), int(forbrug), int(imp)

# ---------- Beregn signal ----------
def beregn_signal(vind, forbrug, imp):
    residual = forbrug - vind
    return residual, residual > 2450 and imp < 200

# ---------- UI ----------
st.title("⚡ Live Elhandel – Signal uden spotpriser")

dato = find_seneste_dato()

if dato:
    vind, forbrug, imp = hent_reelle_data(dato)
    residual, signal = beregn_signal(vind, forbrug, imp)

    st.markdown(f"📅 **Signal beregnet for: {dato.strftime('%d. %B %Y')}**")
    st.markdown(f"- Vindproduktion: **{vind} MW**")
    st.markdown(f"- Forbrug: **{forbrug} MW**")
    st.markdown(f"- Import: **{imp} MW**")
    st.markdown(f"- Residual Load: **{residual} MW**")

    if signal:
        st.success("✅ KØBSSIGNAL registreret (baseret på logik)")
    else:
        st.warning("❌ Intet købssignal – betingelser ikke opfyldt.")
else:
    st.error("🚫 Ingen gyldig dag med data kunne findes.")
