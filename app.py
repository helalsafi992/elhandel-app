import streamlit as st
import pandas as pd
import datetime as dt
import requests

# ---------- Opsætning ----------
ZONER = ["DK1", "DK2"]
zone = "DK1"
kwh_per_trade = 1000

# ---------- Hent senest tilgængelig dato ----------
def find_seneste_dato():
    i = 0
    while i < 10:
        dato = dt.date.today() - dt.timedelta(days=i)
        vind, forbrug, imp = hent_reelle_data(dato)
        priser = hent_spotpriser(dato, zone)
        if vind and forbrug and imp and not priser.empty:
            return dato
        i += 1
    return dt.date.today() - dt.timedelta(days=1)

# ---------- Hent spotpriser ----------
def hent_spotpriser(dato, zone="DK1"):
    url = f"https://stromligning.dk/api/v1/prices?start={dato}&end={dato}&zone={zone}"
    r = requests.get(url)
    if r.status_code == 200:
        df = pd.DataFrame(r.json())
        df["HourDK"] = pd.to_datetime(df["HourDK"])
        df["Hour"] = df["HourDK"].dt.hour
        return df
    return pd.DataFrame()

# ---------- Hent reelle data ----------
def hent_reelle_data(dato):
    try:
        d_str = dato.strftime('%Y-%m-%d')
        # Vind
        v = requests.get(f"https://api.energidataservice.dk/dataset/ActualWindProduction?start={d_str}T00:00&end={d_str}T23:59&filter={{\"PriceArea\":[\"{zone}\"]}}&limit=1000").json()
        vind = sum([x["OffshoreWindPower"] + x["OnshoreWindPower"] for x in v["records"]]) // len(v["records"])
        # Forbrug
        f = requests.get(f"https://api.energidataservice.dk/dataset/ConsumptionDE35?start={d_str}T00:00&end={d_str}T23:59&filter={{\"PriceArea\":[\"{zone}\"]}}&limit=1000").json()
        forbrug = sum([x["Consumption"] for x in f["records"]]) // len(f["records"])
        # Import
        n = requests.get(f"https://api.energidataservice.dk/dataset/NetExchange?start={d_str}T00:00&end={d_str}T23:59&filter={{\"PriceArea\":[\"{zone}\"]}}&limit=1000").json()
        imp = sum([x["Exchange"] for x in n["records"] if x["Exchange"] > 0]) // len(n["records"])
        return int(vind), int(forbrug), int(imp)
    except:
        return 0, 0, 0

# ---------- Beregn signal ----------
def beregn_signal(vind, forbrug, imp):
    residual = forbrug - vind
    return residual, residual > 2450 and imp < 200

# ---------- Køb-/salgstidspunkter ----------
def vælg_tidspunkter(df):
    købsvindue = df[df["Hour"].isin([0,1,2,3,4,5,12,13,14])]
    købstid = købsvindue.loc[købsvindue["SpotPriceDKK"].idxmin()]["Hour"]
    salgstid = df.loc[df["SpotPriceDKK"].idxmax()]["Hour"]
    spot_køb = købsvindue["SpotPriceDKK"].min()
    spot_salg = df["SpotPriceDKK"].max()
    return int(købstid), int(salgstid), spot_køb, spot_salg

# ---------- UI ----------
st.title("⚡ Live Elhandel – Automatisk signal")

# Hent nyeste valide data
dato = find_seneste_dato()
vind, forbrug, imp = hent_reelle_data(dato)
residual, signal = beregn_signal(vind, forbrug, imp)
spot_df = hent_spotpriser(dato, zone)

st.markdown(f"📅 **Signal beregnet for: {dato.strftime('%d. %B %Y')}**")
st.markdown(f"- Vindproduktion: **{vind} MW**")
st.markdown(f"- Forbrug: **{forbrug} MW**")
st.markdown(f"- Import: **{imp} MW**")
st.markdown(f"- Residual Load: **{residual} MW**")

# Resultat
if signal:
    st.success("✅ KØBSSIGNAL registreret")
    if not spot_df.empty:
        køb_tid, salg_tid, spot_køb, spot_salg = vælg_tidspunkter(spot_df)
        profit = spot_salg - spot_køb
        kr = profit * kwh_per_trade
        st.markdown(f"- Køb kl. **{køb_tid}:00**, sælg kl. **{salg_tid}:00**")
        st.markdown(f"- Forventet profit: **{profit:.2f} kr/kWh** ({kr:.0f} kr for 1000 kWh)")
    else:
        st.warning("⚠️ Spotpriser ikke fundet – signal vist uden prisberegning.")
else:
    st.warning("❌ Intet købssignal – betingelser ikke opfyldt.")
