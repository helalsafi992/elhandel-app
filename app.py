import streamlit as st
import pandas as pd
import datetime as dt
import requests
import os

# ----------- Konfiguration -----------
ZONER = ["DK1", "DK2"]
kwh_per_trade = 1000
csv_log = "elhandel_signal_log.csv"

# ----------- Hent spotpriser fra Strømligning -----------
def hent_spotpriser(dato, zone="DK1"):
    dato_str = dato.strftime('%Y-%m-%d')
    url = f"https://stromligning.dk/api/v1/prices?start={dato_str}&end={dato_str}&zone={zone}"
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        df = pd.DataFrame(data)
        df["HourDK"] = pd.to_datetime(df["HourDK"])
        df["Hour"] = df["HourDK"].dt.hour
        return df
    return pd.DataFrame()

# ----------- Beregn signal -----------
def beregn_signal(vind, forbrug, import_mw):
    residual = forbrug - vind
    signal = residual > 2450 and import_mw < 200
    return residual, signal

# ----------- Automatisk valg af tidspunkter -----------
def vælg_tidspunkter(df):
    købsvindue = df[df["Hour"].isin([0,1,2,3,4,5,12,13,14])]
    købstid = købsvindue.loc[købsvindue["SpotPriceDKK"].idxmin()]["Hour"]
    salgstid = df.loc[df["SpotPriceDKK"].idxmax()]["Hour"]
    spot_køb = købsvindue["SpotPriceDKK"].min()
    spot_salg = df["SpotPriceDKK"].max()
    return int(købstid), int(salgstid), spot_køb, spot_salg

# ----------- Gem log -----------
def log_signal(dato, vind, forbrug, import_mw, residual, signal, køb_tid, salg_tid, spot_køb, spot_salg, zone):
    forventet_profit = spot_salg - spot_køb
    reel_profit = forventet_profit * kwh_per_trade

    row = {
        "Dato": dato.strftime('%Y-%m-%d'),
        "Vind": vind,
        "Forbrug": forbrug,
        "Import": import_mw,
        "Residual Load": residual,
        "Signal": "Ja" if signal else "Nej",
        "Købstid": f"{køb_tid}:00",
        "Salgstid": f"{salg_tid}:00",
        "Spotpris køb": spot_køb,
        "Spotpris salg": spot_salg,
        "Profit (kr/kWh)": forventet_profit,
        "Reel Profit (kr)": reel_profit,
        "KWh handlet": kwh_per_trade
    }

    if os.path.exists(csv_log):
        df = pd.read_csv(csv_log)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_csv(csv_log, index=False)

# ----------- Streamlit UI -----------
st.title("🔋 Elhandel – Automatisk signal og historik")

# Inputs
today = dt.date.today()
vind = st.number_input("Vindproduktion (MW)", value=1600)
forbrug = st.number_input("Forbrug (MW)", value=5100)
import_mw = st.number_input("Import (MW)", value=150)
zone = st.selectbox("Priszone", ZONER, index=0)

# Beregn
if st.button("📡 Beregn og log automatisk signal"):
    residual, signal = beregn_signal(vind, forbrug, import_mw)
    st.subheader("📊 Beregning")
    st.write(f"Residual load: **{residual:.0f} MW**")
    st.write(f"Import: **{import_mw} MW**")

    if signal:
        st.success("✅ KØBSSIGNAL registreret")
        spot_df = hent_spotpriser(today, zone)
        if not spot_df.empty:
            køb_tid, salg_tid, spot_køb, spot_salg = vælg_tidspunkter(spot_df)
            st.markdown(f"- Automatisk valgt køb: **{køb_tid}:00** til **{salg_tid}:00**")
            st.markdown(f"- Forventet profit: **{spot_salg - spot_køb:.2f} kr/kWh**")
            log_signal(today, vind, forbrug, import_mw, residual, signal, køb_tid, salg_tid, spot_køb, spot_salg, zone)
            st.success("📁 Signal logget og gemt.")
        else:
            st.error("Kunne ikke hente spotpriser fra API.")
    else:
        st.warning("❌ Ingen signal – ingen handel anbefalet")

# Vis historik
if os.path.exists(csv_log):
    st.subheader("📈 Signalhistorik")
    df_hist = pd.read_csv(csv_log)
    st.dataframe(df_hist)
    st.download_button("📥 Download CSV", df_hist.to_csv(index=False), file_name=csv_log)
else:
    st.info("Ingen signaler logget endnu.")
