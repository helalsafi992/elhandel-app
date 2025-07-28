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
def hent_spotpris(dato, time, zone="DK1"):
    dato_str = dato.strftime('%Y-%m-%d')
    url = f"https://stromligning.dk/api/v1/prices?start={dato_str}&end={dato_str}&zone={zone}"
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        for row in data:
            if row["HourDK"].startswith(f"{dato_str}T{time:02d}"):
                return row["SpotPriceDKK"]
    return None

# ----------- Beregn signal -----------
def beregn_signal(vind, forbrug, import_mw):
    residual = forbrug - vind
    signal = residual > 2450 and import_mw < 200
    return residual, signal

# ----------- Gem log -----------
def log_dagens_signal(dato, vind, forbrug, import_mw, residual, signal, køb_tid, salg_tid, zone):
    spot_køb = hent_spotpris(dato, køb_tid, zone)
    spot_salg = hent_spotpris(dato, salg_tid, zone)
    forventet_profit = None
    reel_profit = None
    afvigelse = None

    if spot_køb and spot_salg:
        forventet_profit = spot_salg - spot_køb
        reel_profit = forventet_profit * kwh_per_trade
        afvigelse = forventet_profit  # her kan du forbedre med forecast vs real

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
        "Afvigelse": afvigelse,
        "KWh handlet": kwh_per_trade
    }

    if os.path.exists(csv_log):
        df = pd.read_csv(csv_log)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_csv(csv_log, index=False)

# ----------- Streamlit UI -----------
st.title("🔋 Elhandel – Dagligt signal med historik")

today = dt.date.today()

vind = st.number_input("Vindproduktion (MW)", value=1600)
forbrug = st.number_input("Forbrug (MW)", value=5100)
import_mw = st.number_input("Import (MW)", value=150)
zone = st.selectbox("Priszone", ZONER, index=0)
køb_tid = st.selectbox("Købstidspunkt", [0, 1, 2, 3, 4, 5, 12, 13, 14], index=3)
salg_tid = st.selectbox("Salgstidspunkt", [16, 17, 18, 19, 20], index=3)

if st.button("📥 Beregn og log signal"):
    residual, signal = beregn_signal(vind, forbrug, import_mw)
    st.subheader("📊 Beregning")
    st.write(f"Residual load: **{residual:.0f} MW**")
    st.write(f"Import: **{import_mw} MW**")

    if signal:
        st.success("✅ KØBSSIGNAL registreret")
        st.markdown(f"- Køb kl. **{køb_tid}:00**, sælg kl. **{salg_tid}:00**")
    else:
        st.warning("❌ Ingen signal – ingen handel anbefalet")

    log_dagens_signal(today, vind, forbrug, import_mw, residual, signal, køb_tid, salg_tid, zone)
    st.success("🔁 Signal logget")

# ----------- Vis historik -----------
if os.path.exists(csv_log):
    st.subheader("📈 Signalhistorik")
    df_hist = pd.read_csv(csv_log)
    st.dataframe(df_hist)
    st.download_button("📥 Download CSV", df_hist.to_csv(index=False), file_name=csv_log)
else:
    st.info("Ingen signaler logget endnu.")
