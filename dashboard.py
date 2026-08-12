import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="NSW Fuel Price Analysis", page_icon="⛽", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("fuel_prices_history.csv")
    df['pull_time'] = pd.to_datetime(df['pull_time'])
    df = df.drop_duplicates(subset=['pull_time', 'stationcode', 'fueltype'])
    df['day'] = df['pull_time'].dt.date
    return df

@st.cache_data
def load_stations():
    try:
        return pd.read_csv("stations.csv")
    except FileNotFoundError:
        return None

def time_ago(lastupdated_str):
    try:
        then = datetime.strptime(lastupdated_str, "%d/%m/%Y %H:%M:%S")
        diff = datetime.now() - then
        hrs = diff.total_seconds() / 3600
        if hrs < 1:
            return f"{int(diff.total_seconds()/60)} min ago"
        if hrs < 24:
            return f"{int(hrs)} hr ago"
        return f"{int(hrs/24)} days ago"
    except Exception:
        return "unknown"

df = load_data()
stations = load_stations()

# ---------- Sidebar ----------
st.sidebar.title("⛽ Controls")
fuel_types = sorted(df['fueltype'].unique())
default_index = fuel_types.index('E10') if 'E10' in fuel_types else 0
choice = st.sidebar.selectbox("Fuel type", fuel_types, index=default_index)
st.sidebar.caption(f"Data window: {df['day'].min()} to {df['day'].max()}")
st.sidebar.caption("Data source: NSW FuelCheck API")

# ---------- Header ----------
st.title("⛽ NSW Fuel Price Cycle Analysis")
st.write(
    "An end-to-end analysis of New South Wales petrol price cycles, built on live data "
    "from the government's FuelCheck API: from data collection through forecasting to a "
    "station-level price finder."
)

# Shared latest priced + located data
latest_pull = df['pull_time'].max()
latest = df[(df['pull_time'] == latest_pull) & (df['fueltype'] == choice)].copy()
if stations is not None:
    priced = latest.merge(stations, on='stationcode', how='inner').dropna(subset=['latitude', 'longitude', 'price'])
    priced['updated'] = priced['lastupdated'].apply(time_ago)
else:
    priced = None

# Daily series for the chosen fuel
sub = df[df['fueltype'] == choice]
daily = sub.groupby('day')['price'].mean().reset_index()
daily.columns = ['date', 'avg_price']
daily['date'] = pd.to_datetime(daily['date'])
daily = daily.sort_values('date').reset_index(drop=True)

first_price = daily['avg_price'].iloc[0]
latest_price = daily['avg_price'].iloc[-1]
peak_price = daily['avg_price'].max()

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Latest avg {choice}", f"{latest_price:.1f} c/L", f"{latest_price - first_price:.1f}")
c2.metric("Cycle peak", f"{peak_price:.1f} c/L")
c3.metric("Stations tracked", f"{df['stationcode'].nunique():,}")
c4.metric("Price records", f"{len(df):,}")

# ---------- Tabs ----------
tab1, tab2, tab3 = st.tabs(["📈 Price Cycle", "🗺️ Live Map", "🔍 Find Fuel"])

# ===== TAB 1: PRICE CYCLE =====
with tab1:
    st.subheader(f"{choice} price cycle and 7-day forecast")

    daily['day_num'] = range(len(daily))
    coeffs = np.polyfit(daily['day_num'], daily['avg_price'], deg=1)
    trend = np.poly1d(coeffs)
    daily['fit'] = trend(daily['day_num'])
    daily['naive'] = daily['avg_price'].shift(1)
    naive_mae = (daily['avg_price'] - daily['naive']).abs().mean()
    trend_mae = (daily['avg_price'] - daily['fit']).abs().mean()

    future_days = range(len(daily), len(daily) + 7)
    future_dates = pd.date_range(daily['date'].iloc[-1], periods=8, freq='D')[1:]
    future_prices = trend(list(future_days))

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(daily['date'], daily['avg_price'], marker='o', label='Actual', color='#c0392b')
    ax.plot(future_dates, future_prices, 'o--', label='Forecast', color='#27ae60')
    ax.set_xlabel("Date")
    ax.set_ylabel("Average price (cents/L)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)

    st.info(
        f"**Model check:** the linear trend forecast has a mean error of "
        f"**{trend_mae:.2f} c/L**, beating a naive baseline of **{naive_mae:.2f} c/L**. "
        f"A linear trend can't capture the crash that ends each cycle; a seasonal model "
        f"needs several full cycles before it overtakes the simple model."
    )

    st.subheader("All fuel grades move together")
    fig2, ax2 = plt.subplots(figsize=(11, 5))
    for ft in ['E10', 'U91', 'P95', 'P98', 'DL']:
        if ft in fuel_types:
            s = df[df['fueltype'] == ft].groupby('day')['price'].mean()
            ax2.plot(s.index, s.values, marker='o', label=ft)
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Average price (cents/L)")
    ax2.legend(title="Fuel")
    ax2.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig2)
    st.caption("Every fuel grade traces the same climb-peak-crash cycle, pointing to a market-wide pattern rather than station-level noise.")

# ===== TAB 2: LIVE MAP =====
with tab2:
    st.subheader(f"{choice} prices across NSW right now")
    if priced is not None:
        try:
            import plotly.express as px
            fig_px = px.scatter_map(
                priced, lat="latitude", lon="longitude", color="price",
                hover_name="name",
                hover_data={"brand": True, "address": True, "price": True,
                            "updated": True, "latitude": False, "longitude": False},
                color_continuous_scale="RdYlGn_r", zoom=5, height=650,
            )
            fig_px.update_traces(marker={"size": 8})
            fig_px.update_layout(map_style="carto-darkmatter", margin={"r": 0, "t": 0, "l": 0, "b": 0})
            st.plotly_chart(fig_px, use_container_width=True)
            st.caption("Green is cheaper, red is pricier. Hover or click any station for brand, address, price, and when it was last updated.")
        except Exception as e:
            st.info(f"Map could not be drawn: {e}")
    else:
        st.info("Station location data not available yet.")

# ===== TAB 3: FIND FUEL =====
with tab3:
    st.subheader(f"Find the cheapest {choice} near you")
    if priced is not None:
        query = st.text_input("Enter your suburb or postcode (e.g. Parramatta or 2150):").strip().upper()
        if query:
            area = priced[priced['address'].str.upper().str.contains(query, na=False)].copy()
            if len(area) > 0:
                area = area.sort_values('price').reset_index(drop=True)
                cheapest_row = area.iloc[0]
                st.success(f"Cheapest {choice} in '{query}': **{cheapest_row['name']}** at "
                           f"**{cheapest_row['price']} c/L** — {cheapest_row['address']} "
                           f"(updated {cheapest_row['updated']})")
                try:
                    import plotly.express as px
                    center_lat = area['latitude'].mean()
                    center_lon = area['longitude'].mean()
                    fig_area = px.scatter_map(
                        area, lat="latitude", lon="longitude", color="price",
                        hover_name="name",
                        hover_data={"brand": True, "address": True, "price": True,
                                    "updated": True, "latitude": False, "longitude": False},
                        color_continuous_scale="RdYlGn_r", zoom=11, height=500,
                    )
                    fig_area.update_traces(marker={"size": 14})
                    fig_area.update_layout(map_style="carto-darkmatter",
                                           map_center={"lat": center_lat, "lon": center_lon},
                                           margin={"r": 0, "t": 0, "l": 0, "b": 0})
                    st.plotly_chart(fig_area, use_container_width=True)
                except Exception as e:
                    st.info(f"Map could not be drawn: {e}")
                st.dataframe(
                    area[['name', 'address', 'price', 'updated']].rename(
                        columns={'name': 'Station', 'address': 'Address',
                                 'price': 'Price (c/L)', 'updated': 'Updated'}),
                    hide_index=True, use_container_width=True)
            else:
                st.warning(f"No stations found matching '{query}'. Try a nearby suburb or postcode.")
        else:
            st.caption("Type your suburb or postcode above; the map zooms in and shows the cheapest fuel there.")
    else:
        st.info("Station location data not available yet.")

st.divider()
st.caption("Built by Ankur Bajaj | Data from NSW FuelCheck API | Python, pandas, matplotlib, Streamlit, Plotly")