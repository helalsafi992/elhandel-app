import requests
import pandas as pd
from datetime import datetime, timedelta

# ---------- Position for DK1 (København) ----------
LAT = 55.6761
LON = 12.5683

# ---------- YR.NO Vindprognose ----------
def hent_yrno_wind_forecast():
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={LAT}&lon={LON}"
    headers = {"User-Agent": "ElhandelApp/1.0 kontakt@dinmail.dk"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()["properties"]["timeseries"]

        vinddata = {}
        for entry in data:
            tidspunkt = entry["time"]
            time = datetime.fromisoformat(tidspunkt.replace("Z", "")).hour
            dato = datetime.fromisoformat(tidspunkt.replace("Z", "")).date()
            hastighed = entry["data"]["instant"]["details"].get("wind_speed", None)
            if dato == datetime.utcnow().date() + timedelta(days=1):
                vinddata[time] = hastighed

        df = pd.Series(vinddata).sort_index().reindex(range(24), fill_value=None)
        return df.round(1), "live"

    except Exception as e:
        fallback = pd.Series([2.8]*24, index=range(24))
        return fallback, "fallback"

# ---------- Test (kør kun hvis standalone) ----------
if __name__ == "__main__":
    vind, kilde = hent_yrno_wind_forecast()
    print(f"Kilde: {kilde}")
    print(vind)
