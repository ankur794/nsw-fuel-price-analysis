# NSW Fuel Price Analysis

A data project that tracks petrol prices across New South Wales using the government's live FuelCheck API, uncovers the pricing cycle behind the daily fluctuations, forecasts where prices head next, and turns the whole thing into a live web app people can actually use.

**Live app:** https://nsw-fuel-price-analysis.streamlit.app

## Where the idea came from

I work at an Ampol service station. Standing at the counter, you notice things about fuel prices that most people don't. They aren't random. They grind upward for a week or two, hit a peak, then drop hard almost overnight, and the whole thing starts again. I wanted to find out whether the data actually backed up the pattern I'd been watching from behind the register, so I built a pipeline to test it.

## What it does

The project collects a full snapshot of every NSW station's fuel prices on a schedule and builds a price history over time. Once there's enough history, it cleans the data, charts the cycle across every fuel grade, forecasts the coming days, and presents it all through an interactive dashboard. Someone can open the app, see where prices sit in the cycle, find the cheapest fuel near them, and get a read on whether now is a good time to fill up.

## The data

- Source: NSW Government FuelCheck API (OAuth2)
- Coverage: roughly 3,300 stations statewide, 10 fuel types
- Records: hundreds of thousands of timestamped prices, growing as collection continues
- Two datasets: a price history for the analysis, and a station file with names, addresses and coordinates for the maps

Collection runs on its own. A scheduled job calls the collector every few hours, so the dataset keeps building without any manual work.

## What the data showed

The analysis confirmed a clear, market-wide cycle. Every fuel grade moved in step, which points to a broad market pattern rather than noise at individual stations. Regular unleaded swung around 27 cents per litre from the bottom of the cycle to the peak, and diesel moved the most. Premium grades held a roughly constant margin above regular the whole way through.

## Forecasting, tested honestly

Describing the cycle was only half the work. I wanted to predict short-term prices and, more importantly, prove any model actually added value rather than just looking convincing on a chart. The approach was to measure every model against a naive baseline: assume tomorrow's price equals today's. Anything that can't beat that isn't worth using.

| Model | Mean error on unseen days (c/L) |
|-------|--------------------------------|
| Naive baseline | 2.93 |
| Linear trend | 2.45 |
| Prophet (seasonal) | 8.04 |

The linear trend model beat the baseline. The seasonal Prophet model, tested properly on days it had never seen, did worse, and that is the finding worth reporting. On a short dataset Prophet overfits; it needs several full cycles before it can learn the pattern well enough to win. When I first measured Prophet on its own training data it scored a near-perfect 0.38, which is a reminder that a model must always be judged on data it hasn't seen. Reporting the honest 8.04 matters more than a number that only looks good.

The framework is in place, so as the dataset grows past a few full cycles the seasonal model should overtake the simpler ones on its own.

## The live app

The dashboard turns the analysis into something anyone can use. It is organised into tabs:

- **Price Cycle** — the cycle chart, the 7-day forecast, the model comparison, and a view of all fuel grades moving together
- **By Brand** — which brands run cheapest and priciest on average, with the gap between them
- **Live Map** — every station plotted on a dark interactive map, coloured by price, with brand, address, price and last-updated time on each point
- **Find Fuel** — enter a suburb or postcode, or use your location, to find the cheapest fuel nearby, sorted by price and distance

A "should I fill up now?" indicator sits at the top, reading where the current price sits between the cycle's low and high and giving a clear verdict.

## How it works

**`collect_prices.py`** authenticates against the FuelCheck OAuth endpoint, pulls current prices and station details for every station, and appends each snapshot to the price history with a timestamp. The analysis notebook loads that data, cleans it, builds the charts, and fits the forecasts. The dashboard reads the same data and presents it interactively.

API credentials are kept out of the code in a local environment file that isn't committed.

## Built with

Python, pandas, NumPy, matplotlib, Prophet, Streamlit, Plotly, and cron for scheduling.

## Running it yourself

1. Register for a free FuelCheck API key at the [NSW API portal](https://api.nsw.gov.au).
2. Add your key and secret to a `.env` file in the project root:
   ```
   API_KEY=your_key
   API_SECRET=your_secret
   ```
3. Install the dependencies:
   ```
   pip install requests pandas numpy matplotlib prophet streamlit plotly python-dotenv
   ```
4. Run `python collect_prices.py` to collect a snapshot, or schedule it with cron to build history automatically.
5. Run `streamlit run dashboard.py` to launch the app locally.

## Where it goes next

The clear next step is making the app pull live from the FuelCheck API on load, so the data stays current on its own without manual updates. Beyond that: brand logos on the map markers, and a richer seasonal model once enough full cycles have been collected.
s