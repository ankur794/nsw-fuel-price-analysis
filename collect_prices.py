import requests
import base64
import csv
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

def get_access_token():
    auth_url = "https://api.onegov.nsw.gov.au/oauth/client_credential/accesstoken?grant_type=client_credentials"
    credentials = f"{API_KEY}:{API_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()
    r = requests.get(auth_url, headers={"Authorization": f"Basic {encoded}"})
    return r.json()["access_token"]

def fetch_prices(token):
    url = "https://api.onegov.nsw.gov.au/FuelPriceCheck/v2/fuel/prices"
    now = datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": API_KEY,
        "transactionid": "collect001",
        "requesttimestamp": now,
    }
    return requests.get(url, headers=headers).json()

def save_prices(data):
    filename = "fuel_prices_history.csv"
    exists = os.path.isfile(filename)
    pull_time = datetime.now().isoformat()
    with open(filename, "a", newline="") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["pull_time", "stationcode", "fueltype", "price", "lastupdated"])
        for e in data.get("prices", []):
            w.writerow([pull_time, e.get("stationcode"), e.get("fueltype"),
                        e.get("price"), e.get("lastupdated")])
    print(f"Saved {len(data.get('prices', []))} prices")

def save_stations(data):
    # Station names + coordinates. Overwrite each time (station list rarely changes).
    filename = "stations.csv"
    with open(filename, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stationcode", "name", "address", "latitude", "longitude", "brand"])
        for s in data.get("stations", []):
            loc = s.get("location", {})
            w.writerow([s.get("code"), s.get("name"), s.get("address"),
                        loc.get("latitude"), loc.get("longitude"), s.get("brand")])
    print(f"Saved {len(data.get('stations', []))} stations")

if __name__ == "__main__":
    token = get_access_token()
    data = fetch_prices(token)
    save_prices(data)
    save_stations(data)