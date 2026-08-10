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
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    auth_headers = {"Authorization": f"Basic {encoded_credentials}"}
    response = requests.get(auth_url, headers=auth_headers)
    return response.json()["access_token"]

def fetch_prices(access_token):
    prices_url = "https://api.onegov.nsw.gov.au/FuelPriceCheck/v2/fuel/prices"
    now = datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "apikey": API_KEY,
        "transactionid": "collect001",
        "requesttimestamp": now,
    }
    response = requests.get(prices_url, headers=headers)
    return response.json()

def save_to_csv(data):
    filename = "fuel_prices_history.csv"
    file_exists = os.path.isfile(filename)
    pull_time = datetime.now().isoformat()

    with open(filename, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["pull_time", "stationcode", "fueltype", "price", "lastupdated"])
        for entry in data.get("prices", []):
            writer.writerow([
                pull_time,
                entry.get("stationcode"),
                entry.get("fueltype"),
                entry.get("price"),
                entry.get("lastupdated"),
            ])

    print(f"Saved {len(data.get('prices', []))} price entries to {filename}")

if __name__ == "__main__":
    token = get_access_token()
    data = fetch_prices(token)
    save_to_csv(data)