import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="NSW Fuel Price Cycle", layout="wide")

st.title("NSW Fuel Price Cycle Tracker")
st.write("Live analysis of NSW petrol price cycles using data from the FuelCheck API.")

# Load and clean the data
df = pd.read_csv("fuel_prices_history.csv")
df['pull_time'] = pd.to_datetime(df['pull_time'])
df = df.drop_duplicates(subset=['pull_time', 'stationcode', 'fueltype'])
df['day'] = df['pull_time'].dt.date

# Quick stats
col1, col2, col3 = st.columns(3)
col1.metric("Total price records", f"{len(df):,}")
col2.metric("Stations tracked", f"{df['stationcode'].nunique():,}")
col3.metric("Days of data", df['day'].nunique())

# Let the user pick a fuel type
fuel_types = sorted(df['fueltype'].unique())
default_index = fuel_types.index('E10') if 'E10' in fuel_types else 0
choice = st.selectbox("Choose a fuel type:", fuel_types, index=default_index)

# Build the daily series for the chosen fuel
subset = df[df['fueltype'] == choice]
daily = subset.groupby('day')['price'].mean().reset_index()
daily.columns = ['date', 'avg_price']
daily['date'] = pd.to_datetime(daily['date'])
daily = daily.sort_values('date').reset_index(drop=True)

# Fit a simple linear trend and forecast 7 days ahead
daily['day_num'] = range(len(daily))
coeffs = np.polyfit(daily['day_num'], daily['avg_price'], deg=1)
trend = np.poly1d(coeffs)

future_days = range(len(daily), len(daily) + 7)
future_dates = pd.date_range(daily['date'].iloc[-1], periods=8, freq='D')[1:]
future_prices = trend(list(future_days))

# Plot
st.subheader(f"{choice} Price Cycle and 7-Day Forecast")
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(daily['date'], daily['avg_price'], marker='o', label='Actual', color='#c0392b')
ax.plot(future_dates, future_prices, 'o--', label='7-day forecast', color='#27ae60')
ax.set_xlabel("Date")
ax.set_ylabel("Average price (cents/L)")
ax.legend()
ax.grid(True, alpha=0.3)
plt.xticks(rotation=45)
st.pyplot(fig)

st.caption("Note: a linear trend can't capture the price crash that ends each cycle — a seasonal model is the next step.")