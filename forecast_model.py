import pandas as pd
import datetime as dt
import requests

ZONE = "DK1"

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
