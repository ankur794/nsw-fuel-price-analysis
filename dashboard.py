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

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # km
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))

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
trough_price = daily['avg_price'].min()

# ---------- "Should I buy now?" indicator ----------
if peak_price > trough_price:
    position = (latest_price - trough_price) / (peak_price - trough_price)
else:
    position = 0.5

recent_change = daily['avg_price'].iloc[-1] - daily['avg_price'].iloc[-2] if len(daily) > 1 else 0

if position <= 0.33:
    verdict = "🟢 GOOD TIME TO FILL UP"
    reason = "Prices are near the bottom of the cycle."
elif position >= 0.66:
    verdict = "🔴 WAIT IF YOU CAN"
    reason = "Prices are near the top of the cycle — a drop usually follows soon."
else:
    if recent_change > 0:
        verdict = "🟠 PRICES RISING — FILL UP SOON"
        reason = "Prices are mid-cycle and climbing toward the peak."
    else:
        verdict = "🟢 PRICES EASING — OKAY TO BUY"
        reason = "Prices are mid-cycle and coming down."

st.markdown(f"### {verdict}")
st.caption(f"{reason}  (Current {choice}: {latest_price:.1f} c/L — cycle low {trough_price:.1f}, high {peak_price:.1f})")
st.progress(min(max(position, 0.0), 1.0))

st.divider()

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Latest avg {choice}", f"{latest_price:.1f} c/L", f"{latest_price - first_price:.1f}")
c2.metric("Cycle peak", f"{peak_price:.1f} c/L")
c3.metric("Stations tracked", f"{df['stationcode'].nunique():,}")
c4.metric("Price records", f"{len(df):,}")

# ---------- Tabs ----------
tab1, tab2, tab3, tab4 = st.tabs(["📈 Price Cycle", "🏷️ By Brand", "🗺️ Live Map", "🔍 Find Fuel"])

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

# ===== TAB 2: BY BRAND =====
with tab2:
    st.subheader(f"Which brands are cheapest for {choice}?")
    if priced is not None and 'brand' in priced.columns:
        brand_avg = (priced.groupby('brand')['price']
                     .agg(['mean', 'count'])
                     .reset_index()
                     .rename(columns={'mean': 'avg_price', 'count': 'stations'}))
        brand_avg = brand_avg[brand_avg['stations'] >= 3].sort_values('avg_price')

        if len(brand_avg) > 0:
            cheapest_brand = brand_avg.iloc[0]
            priciest_brand = brand_avg.iloc[-1]
            st.success(
                f"Cheapest brand on average: **{cheapest_brand['brand']}** at "
                f"**{cheapest_brand['avg_price']:.1f} c/L**  •  Priciest: "
                f"**{priciest_brand['brand']}** at **{priciest_brand['avg_price']:.1f} c/L**  "
                f"— a gap of **{priciest_brand['avg_price'] - cheapest_brand['avg_price']:.1f} c/L**."
            )

            top = brand_avg.head(15)
            fig_b, ax_b = plt.subplots(figsize=(11, max(4, len(top) * 0.4)))
            colors = plt.cm.RdYlGn_r(
                (top['avg_price'] - top['avg_price'].min()) /
                (top['avg_price'].max() - top['avg_price'].min() + 1e-9)
            )
            ax_b.barh(top['brand'], top['avg_price'], color=colors)
            ax_b.invert_yaxis()
            ax_b.set_xlabel("Average price (cents/L)")
            ax_b.set_title(f"Average {choice} price by brand (cheapest at top)")
            ax_b.grid(True, axis='x', alpha=0.3)
            for i, v in enumerate(top['avg_price']):
                ax_b.text(v + 0.1, i, f"{v:.1f}", va='center', fontsize=9)
            plt.tight_layout()
            st.pyplot(fig_b)

            st.dataframe(
                brand_avg.rename(columns={'brand': 'Brand', 'avg_price': 'Avg price (c/L)', 'stations': 'Stations'}),
                hide_index=True, use_container_width=True)
            st.caption("Averaged across all stations of each brand with current prices (brands with at least 3 stations shown).")
        else:
            st.info("Not enough brand data to compare yet.")
    else:
        st.info("Brand data not available yet.")

# ===== TAB 3: LIVE MAP =====
with tab3:
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

# ===== TAB 4: FIND FUEL =====
with tab4:
    st.subheader(f"Find the cheapest {choice} near you")
    if priced is not None:
        # --- Option A: use my location ---
        st.markdown("**Option A — use my location**")
        user_lat = user_lon = None
        try:
            from streamlit_geolocation import streamlit_geolocation
            loc = streamlit_geolocation()
            if loc and loc.get("latitude") and loc.get("longitude"):
                user_lat = loc["latitude"]
                user_lon = loc["longitude"]
        except Exception:
            st.caption("Location button unavailable — use suburb search below instead.")

        if user_lat and user_lon:
            near = priced.copy()
            near['distance_km'] = haversine(user_lat, user_lon, near['latitude'], near['longitude'])
            near = near[near['distance_km'] <= 15].sort_values('price')
            if len(near) > 0:
                best = near.iloc[0]
                st.success(f"Cheapest {choice} within 15 km: **{best['name']}** at "
                           f"**{best['price']} c/L**, {best['distance_km']:.1f} km away — {best['address']}")
                try:
                    import plotly.express as px
                    fig_near = px.scatter_map(
                        near, lat="latitude", lon="longitude", color="price",
                        hover_name="name",
                        hover_data={"brand": True, "address": True, "price": True,
                                    "distance_km": ":.1f", "updated": True,
                                    "latitude": False, "longitude": False},
                        color_continuous_scale="RdYlGn_r", zoom=11, height=500,
                    )
                    fig_near.update_traces(marker={"size": 13})
                    fig_near.update_layout(map_style="carto-darkmatter",
                                           map_center={"lat": user_lat, "lon": user_lon},
                                           margin={"r": 0, "t": 0, "l": 0, "b": 0})
                    st.plotly_chart(fig_near, use_container_width=True)
                except Exception as e:
                    st.info(f"Map could not be drawn: {e}")
                st.dataframe(
                    near[['name', 'address', 'price', 'distance_km', 'updated']].head(15).rename(
                        columns={'name': 'Station', 'address': 'Address', 'price': 'Price (c/L)',
                                 'distance_km': 'Distance (km)', 'updated': 'Updated'}),
                    hide_index=True, use_container_width=True,
                    column_config={"Distance (km)": st.column_config.NumberColumn(format="%.1f")})
            else:
                st.warning("No stations found within 15 km of your location.")

        st.divider()

        # --- Option B: search by suburb/postcode ---
        st.markdown("**Option B — search a suburb or postcode**")
        query = st.text_input("Suburb or postcode (e.g. Parramatta or 2150):").strip().upper()
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
        st.info("Station location data not available yet.")

st.divider()
st.caption("Built by Ankur Bajaj | Data from NSW FuelCheck API | Python, pandas, matplotlib, Streamlit, Plotly")