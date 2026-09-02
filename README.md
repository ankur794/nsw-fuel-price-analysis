# Fuel Price Analysis

Tracking petrol price cycles across New South Wales with live government data, from raw API through SQL analysis to two deployed dashboards.

**Live app:** https://nsw-fuel-price-analysis.streamlit.app
**Tableau dashboard:** https://public.tableau.com/views/NSWFuelProject/Dashboard1

---

## The idea

I work at an Ampol service station. Behind the counter you start to notice that fuel prices aren't random. They climb for a week or two, hit a peak, then crash almost overnight, and the cycle repeats. I wanted to know if the data actually proved the pattern I was watching every shift, so I built a pipeline to find out.

---

## What it does

An automated collector pulls live prices from every NSW station on a schedule and builds a price history over time. From that data, the project:

- maps out the full price cycle and forecasts where prices head next
- compares fuel grades and brands
- plots every station on a live map, coloured by price
- lets anyone find the cheapest fuel near them by suburb, postcode, or their actual location

Collection runs on its own every few hours, so the dataset keeps growing.

**Data:** NSW Government FuelCheck API, roughly 3,300 stations, 10 fuel types, 570,000+ timestamped records and counting.

---

## What the data showed

The cycle is real, and it's market-wide. Every fuel grade moves in step, which rules out random station-level noise.

![Price cycle](e10_price_cycle.png)

Regular unleaded swings around **27 c/L** from the bottom of the cycle to the peak, diesel moves the most, and premium grades hold a steady margin above regular the whole way through.

![All fuel grades](price_by_fueltype.png)

---

## Forecasting, backtested honestly

Spotting the cycle was only half of it. I wanted a model that actually adds value, not just a chart that looks right, so every result here is measured against a naive baseline: assume tomorrow's price equals today's. Anything that can't beat that consistently isn't worth using.

The first version of this project tested one model against one held-out window and reported a 16% improvement over baseline. That result was real, but it only proved the model worked on one slice of data. So I went back and backtested it properly: sliding a window through every day in the full dataset, refitting the model fresh each time, and checking the forecast against what actually happened next.

| Test | Result |
|------|--------|
| Original single-window test | Linear trend beat baseline by 16% |
| Full backtest, 13 folds across the entire dataset | Naive baseline beat linear trend in 12 of 13 folds |

The honest answer is the second one. A straight-line model can't see a sharp crash coming, so it consistently lags a step behind every sudden turn in the cycle, while a naive "tomorrow equals today" guess barely gets hurt by a single sharp move because it never tries to predict one. Tested properly across the whole window, short-term fuel prices behave more like a random walk with occasional sharp breaks than something a simple trend line can reliably predict.

I'm reporting this instead of the flattering first result because it's the true one, and because the failure itself is the more interesting finding: it says something specific about *why* naive persistence models are hard to beat in this kind of data, not just that one model happened to score well once.

![Model comparison](model_comparison.png)

---

## SQL

The full analysis also lives as SQL, run directly against a SQLite database of the same records, so the findings above aren't locked to one language or one notebook.

- Brand-level pricing built with JOINs and GROUP BY across prices and stations
- Cycle turning points detected automatically with a LAG() window function, comparing each day's movement to the day before to flag real peaks and crashes without any manual chart-reading
- A clean export view feeding the Tableau dashboard, with suburb, state, and postcode parsed out as separate fields

`analysis.sql` has the full set of queries, runnable directly against `fuel.db`.

---

## Two dashboards, two purposes

**Streamlit** is the interactive one. Filter by fuel type, explore the live map, find the cheapest station near you by suburb, postcode, or GPS location.

**Tableau** is the SQL-backed one, built to be readable at a glance: the price cycle, a ranked brand comparison, and a live map of every station coloured by price, zoomed to NSW. It's a snapshot rather than a live feed since it runs off an exported database extract, refreshed periodically rather than in real time.

The Streamlit app stays organised into four tabs:

- **Price Cycle**, the cycle, the 7-day forecast, and the honest model comparison
- **By Brand**, which brands run cheapest and priciest, and the gap between them
- **Live Map**, every station on a dark interactive map, coloured by price, with brand, address, price and last-updated time on each point
- **Find Fuel**, cheapest fuel near you by suburb, postcode, or GPS location, sorted by price and distance

A "should I fill up now?" indicator sits up top, reading where the current price sits in the cycle and giving a straight verdict.

---

## How it works

`collect_prices.py` authenticates with the FuelCheck OAuth endpoint, pulls current prices and station details for every station, and appends each snapshot to the price history with a timestamp, scheduled through cron. The notebook cleans the data, builds the charts, and fits the forecasts. `backtest.py` runs the full walk-forward backtest behind the forecasting results above. `analysis.sql` reproduces the core findings directly in SQL against a SQLite database built from the same collected data. The dashboard reads the same underlying data and serves it interactively. API keys are kept out of the code in a local `.env` file.

**Built with:** Python, pandas, NumPy, matplotlib, Prophet, Streamlit, Plotly, SQL (SQLite), Tableau, cron

---

## Run it yourself

1. Get a free FuelCheck API key at the [NSW API portal](https://api.nsw.gov.au).
2. Add your credentials to a `.env` file:
   ```
   API_KEY=your_key
   API_SECRET=your_secret
   ```
3. Install dependencies:
   ```
   pip install requests pandas numpy matplotlib prophet streamlit plotly python-dotenv
   ```
4. `python collect_prices.py` to collect data (or schedule it with cron).
5. `streamlit run dashboard.py` to launch the app.
6. `python backtest.py` to reproduce the backtest results.
7. `sqlite3 fuel.db < analysis.sql` to run the SQL analysis directly.

---

## Next steps

Making the app pull live from the FuelCheck API on load, so the data stays current with no manual updates, then testing whether a model built specifically to detect the crash point, rather than a general trend line, can do what linear and seasonal models both failed to.

---

*Built by Ankur Bajaj, Computer Science (Data Science) student at Deakin University, and someone who's watched these prices from behind the counter.*
