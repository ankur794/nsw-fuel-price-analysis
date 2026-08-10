import requests
import base64
import json
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# Step 1: Get access token
auth_url = "https://api.onegov.nsw.gov.au/oauth/client_credential/accesstoken?grant_type=client_credentials"
credentials = f"{API_KEY}:{API_SECRET}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()
auth_headers = {"Authorization": f"Basic {encoded_credentials}"}

auth_response = requests.get(auth_url, headers=auth_headers)
access_token = auth_response.json()["access_token"]
print("Got access token:", access_token)

# Step 2: Use the token to call the fuel prices endpoint
prices_url = "https://api.onegov.nsw.gov.au/FuelPriceCheck/v2/fuel/prices"
price_headers = {
    "Authorization": f"Bearer {access_token}",
    "apikey": API_KEY,
    "transactionid": "test123",
    "requesttimestamp": "23/07/2026 03:30:00 PM",
}

price_response = requests.get(prices_url, headers=price_headers)
print("Price status:", price_response.status_code)
print(price_response.text[:500])