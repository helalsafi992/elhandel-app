import streamlit as st
import pandas as pd
import datetime as dt
import requests

# ----------- Konfiguration -----------
ZONER = ["DK1", "DK2"]
zone = "DK1"
kwh_per_trade = 1000

# ----------- Hent senest gyldig dato med data -----------
def find_seneste_dato(max_dage=10):
    for i in range(max_dage):
        dato = dt.date.today() - dt.timedelta(days=i)
        vind, forbrug, imp = hent_reelle_data(dato)
        priser = hent_spotpriser(dato, zone)
        if vind > 0 and forbrug > 0 and imp >= 0 and not priser.empty:
            return dato
    return None

# ----------- Hent spotpriser -----------
def hent_spotpriser(dato, zone="DK1"):
    try:
        url = f"https://stromligning.dk/api/v1/prices?start={dato}&end={dato}&zone={zone}"
        r = requests.get(url)
        if r.status_code == 200:
            df = pd.DataFrame(r.json())
            df["HourDK"] = pd.to_datetime(df["HourDK"])
            df["Hour"] = df["HourDK"].dt.hour
            return df
    except:
        pass
    return pd.DataFrame()

# ----------- Hent reelle værdier -----------
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

# ----------- Beregn signal -----------
def beregn_signal(vind, forbrug, imp):
    residual = forbrug - vind
    return residual, residual > 2450 and imp < 200

# ----------- Find bedste køb/salg ----------
def vælg_tidspunkter(df):
    købsvindue = df[df["Hour"].isin([0,1,2,3,4,5,12,13,14])]
    købstid = købsvindue.loc[købsvindue["SpotPriceDKK"].idxmin()]["Hour"]
    salgstid = df.loc[df["SpotPriceDKK"].idxmax()]["Hour"]
    spot_køb = købsvindue["SpotPriceDKK"].min()
    spot_salg = df["SpotPriceDKK"].max()
    return int(købstid), int(salgstid), spot_køb, spot_salg

# ----------- UI -----------
st.title("⚡ Live Elhandel – Automatisk signal")

# Start
dato = find_seneste_dato()

if dato:
    vind, forbrug, imp = hent_reelle_data(dato)
    spot_df = hent_spotpriser(dato, zone)
    residual, signal = beregn_signal(vind, forbrug, imp)

    st.markdown(f"📅 **Signal beregnet for: {dato.strftime('%d. %B %Y')}**")
    st.markdown(f"- Vindproduktion: **{vind} MW**")
    st.markdown(f"- Forbrug: **{forbrug} MW**")
    st.markdown(f"- Import: **{imp} MW**")
    st.markdown(f"- Residual Load: **{residual} MW**")

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

else:
    st.error("🚫 Ingen gyldig dag med både reelle data og spotpriser kunne findes.")
    st.info("Tjek internet, API eller prøv igen senere.")
