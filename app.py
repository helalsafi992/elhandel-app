import streamlit as st
import pandas as pd
import datetime as dt
import requests

st.set_page_config(page_title="🔌 Day-Ahead Debug", layout="wide")

st.title("🔌 Day-Ahead – Forecast Test & Debug")

tomorrow = (dt.datetime.utcnow() + dt.timedelta(days=1)).strftime("%Y-%m-%d")
st.markdown(f"📅 Testdato: **{tomorrow}**")

# URL'er
url_wind = f"https://api.energidataservice.dk/dataset/ForeCastWindProduction?start={tomorrow}T00:00&end={tomorrow}T23:59&limit=1000"
url_load = f"https://api.energidataservice.dk/dataset/ConsumptionForecast?start={tomorrow}T00:00&end={tomorrow}T23:59&filter={{\"PriceArea\":[\"DK1\"]}}"
url_import = f"https://api.energidataservice.dk/dataset/NetExchange?start={tomorrow}T00:00&end={tomorrow}T23:59&filter={{\"PriceArea\":[\"DK1\"]}}"

# Funktion til at hente og vise data
@st.cache_data(ttl=600)
def hent_forecast_data():
    resultater = {}
    for navn, url in zip(["Vind", "Forbrug", "Import"], [url_wind, url_load, url_import]):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                records = r.json().get("records", [])
                resultater[navn] = {
                    "status": "✅ OK",
                    "antal": len(records),
                    "eksempel": records[:2] if records else "(ingen data)"
                }
            else:
                resultater[navn] = {"status": f"❌ Fejl {r.status_code}", "antal": 0, "eksempel": ""}
        except Exception as e:
            resultater[navn] = {"status": f"⚠️ Exception", "antal": 0, "eksempel": str(e)}
    return resultater

# Visning
if st.button("🚀 Test API-kald for i morgen"):
    data = hent_forecast_data()
    for navn, info in data.items():
        st.subheader(f"🔍 {navn}-forecast")
        st.markdown(f"Status: {info['status']}")
        st.markdown(f"Antal records: `{info['antal']}`")
        st.markdown("Eksempel:")
        st.json(info['eksempel'])
