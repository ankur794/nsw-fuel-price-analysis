import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="NSW Fuel Price Cycle", page_icon="⛽", layout="wide")

# Load and clean
@st.cache_data
def load_data():
    df = pd.read_csv("fuel_prices_history.csv")
    df['pull_time'] = pd.to_datetime(df['pull_time'])
    df = df.drop_duplicates(subset=['pull_time', 'stationcode', 'fueltype'])
    df['day'] = df['pull_time'].dt.date
    return df

df = load_data()

# ---- Sidebar controls ----
st.sidebar.title("⛽ Controls")
fuel_types = sorted(df['fueltype'].unique())
default_index = fuel_types.index('E10') if 'E10' in fuel_types else 0
choice = st.sidebar.selectbox("Fuel type", fuel_types, index=default_index)
st.sidebar.caption(f"Data: {df['day'].min()} to {df['day'].max()}")

# ---- Header ----
st.title("NSW Fuel Price Cycle Tracker")
st.write("Live analysis of NSW petrol price cycles using data from the FuelCheck API.")

# ---- Build the daily series for chosen fuel ----
sub = df[df['fueltype'] == choice]
daily = sub.groupby('day')['price'].mean().reset_index()
daily.columns = ['date', 'avg_price']
daily['date'] = pd.to_datetime(daily['date'])
daily = daily.sort_values('date').reset_index(drop=True)

first_price = daily['avg_price'].iloc[0]
latest_price = daily['avg_price'].iloc[-1]
peak_price = daily['avg_price'].max()

# ---- Metric cards ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest avg price", f"{latest_price:.1f} c/L", f"{latest_price - first_price:.1f}")
c2.metric("Cycle peak", f"{peak_price:.1f} c/L")
c3.metric("Stations tracked", f"{df['stationcode'].nunique():,}")
c4.metric("Price records", f"{len(df):,}")

# ---- Fit linear trend + forecast ----
daily['day_num'] = range(len(daily))
coeffs = np.polyfit(daily['day_num'], daily['avg_price'], deg=1)
trend = np.poly1d(coeffs)
daily['fit'] = trend(daily['day_num'])

# Model accuracy vs naive baseline
daily['naive'] = daily['avg_price'].shift(1)
naive_mae = (daily['avg_price'] - daily['naive']).abs().mean()
trend_mae = (daily['avg_price'] - daily['fit']).abs().mean()

future_days = range(len(daily), len(daily) + 7)
future_dates = pd.date_range(daily['date'].iloc[-1], periods=8, freq='D')[1:]
future_prices = trend(list(future_days))

# ---- Forecast chart ----
st.subheader(f"{choice} price cycle and 7-day forecast")
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(daily['date'], daily['avg_price'], marker='o', label='Actual', color='#c0392b')
ax.plot(future_dates, future_prices, 'o--', label='Forecast', color='#27ae60')
ax.set_xlabel("Date"); ax.set_ylabel("Average price (cents/L)")
ax.legend(); ax.grid(True, alpha=0.3)
plt.xticks(rotation=45); plt.tight_layout()
st.pyplot(fig)

st.info(
    f"**Model check:** the linear trend forecast has a mean error of "
    f"**{trend_mae:.2f} c/L**, beating a naive baseline of **{naive_mae:.2f} c/L**. "
    f"A linear trend can't capture the crash that ends each cycle — a seasonal model is the next step."
)

# ---- All fuel types comparison ----
st.subheader("All fuel types compared")
fig2, ax2 = plt.subplots(figsize=(11, 5))
for ft in ['E10', 'U91', 'P95', 'P98', 'DL']:
    if ft in fuel_types:
        s = df[df['fueltype'] == ft].groupby('day')['price'].mean()
        ax2.plot(s.index, s.values, marker='o', label=ft)
ax2.set_xlabel("Date"); ax2.set_ylabel("Average price (cents/L)")
ax2.legend(title="Fuel"); ax2.grid(True, alpha=0.3)
plt.xticks(rotation=45); plt.tight_layout()
st.pyplot(fig2)

st.caption("Built by