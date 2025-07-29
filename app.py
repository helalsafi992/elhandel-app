import streamlit as st
import pandas as pd
import datetime as dt
import requests
import os

# ----------- Konfiguration -----------
ZONER = ["DK1", "DK2"]
kwh_per_trade = 1000
csv_log = "elhandel_signal_log.csv"

# ----------- Hent spotpriser -----------
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

# ----------- Automatisk reelle værdier -----------
def hent_reelle_data(dato):
    vind = 1600
    forbrug = 5100
    import_mw = 150
    try:
        d_str = dato.strftime('%Y-%m-%d')
        # Vind
        vind_url = f"https://api.energidataservice.dk/dataset/ActualWindProduction?start={d_str}T00:00&end={d_str}T23:59&filter={{\"PriceArea\":[\"DK1\"]}}&limit=1000"
        v_res = requests.get(vind_url).json()
        vind = sum([x["OffshoreWindPower"] + x["OnshoreWindPower"] for x in v_res["records"]]) // len(v_res["records"])
        # Forbrug
        load_url = f"https://api.energidataservice.dk/dataset/ConsumptionDE35?start={d_str}T00:00&end={d_str}T23:59&filter={{\"PriceArea\":[\"DK1\"]}}&limit=1000"
        l_res = requests.get(load_url).json()
        forbrug = sum([x["Consumption"] for x in l_res["records"]]) // len(l_res["records"])
        # Import
        net_url = f"https://api.energidataservice.dk/dataset/NetExchange?start={d_str}T00:00&end={d_str}T23:59&filter={{\"PriceArea\":[\"DK1\"]}}&limit=1000"
        n_res = requests.get(net_url).json()
        import_mw = sum([x["Exchange"] for x in n_res["records"] if x["Exchange"] > 0]) // len(n_res["records"])
    except:
        pass
    return int(vind), int(forbrug), int(import_mw)

# ----------- Beregn signal -----------
def beregn_signal(vind, forbrug, import_mw):
    residual = forbrug - vind
    signal = residual > 2450 and import_mw < 200
    return residual, signal

# ----------- Vælg tidspunkter automatisk -----------
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
        "KWh handlet": kwh_per_trade,
        "Zone": zone
    }
    if os.path.exists(csv_log):
        df = pd.read_csv(csv_log)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])
    df.to_csv(csv_log, index=False)

# ----------- UI -----------
st.title("⚡ Elhandel – Automatisk signal og historik")

# 📆 Dato
dato = st.date_input("📅 Vælg dato for signal", dt.date.today())
zone = st.selectbox("Priszone", ZONER, index=0)

# 📥 Hent reelle værdier og vis som inputfelter
vind_val, forbrug_val, import_val = hent_reelle_data(dato)
vind = st.number_input("Vindproduktion (MW)", value=vind_val)
forbrug = st.number_input("Forbrug (MW)", value=forbrug_val)
import_mw = st.number_input("Import (MW)", value=import_val)

# 📡 Beregn
if st.button("📡 Beregn og log signal"):
    residual, signal = beregn_signal(vind, forbrug, import_mw)
    st.subheader("📊 Beregning")
    st.write(f"Residual load: **{residual} MW**")

    if signal:
        st.success("✅ KØBSSIGNAL registreret")
        spot_df = hent_spotpriser(dato, zone)
        if not spot_df.empty:
            køb_tid, salg_tid, spot_køb, spot_salg = vælg_tidspunkter(spot_df)
            st.markdown(f"- Automatisk køb: **{køb_tid}:00** → salg: **{salg_tid}:00**")
            st.markdown(f"- Forventet profit: **{spot_salg - spot_køb:.2f} kr/kWh**")
            log_signal(dato, vind, forbrug, import_mw, residual, signal, køb_tid, salg_tid, spot_køb, spot_salg, zone)
            st.success("📁 Signal gemt")
        else:
            st.error("⚠️ Spotpriser kunne ikke hentes.")
    else:
        st.warning("❌ Ingen signal – ingen handel")

# 📈 Historik
if os.path.exists(csv_log):
    st.subheader("📈 Signalhistorik")
    df_hist = pd.read_csv(csv_log)
    st.dataframe(df_hist)
    st.download_button("📥 Download CSV", df_hist.to_csv(index=False), file_name=csv_log)
else:
    st.info("Ingen signaler logget endnu.")
