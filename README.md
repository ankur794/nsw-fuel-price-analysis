# NSW Fuel Price Cycle Analysis

A data pipeline that tracks petrol prices across New South Wales using the government's live FuelCheck API, then digs out the pricing cycle underneath the day-to-day noise.

## Background

I spent over a year working the counter at an Ampol service station. One thing you pick up fast is that fuel prices don't move randomly — they grind upward for a week or two, hit a peak, then drop hard almost overnight, and the whole thing starts over. This project was me checking whether the data actually backs up the pattern I'd been watching from behind the register.

## What it does

It collects a full snapshot of every NSW station's fuel prices on a schedule, stamps each snapshot with a time, and builds a price history over time. Once there's enough history, it cleans the data and charts the cycle across every fuel grade.

Collection runs on its own. A cron job calls the collector every few hours, so the dataset keeps growing without me touching it.

## Data

- Source: NSW Government FuelCheck API (OAuth2)
- Coverage: ~3,300 stations statewide, 10 fuel types
- Window: 23 July – 11 August 2026
- ~317,000 timestamped price records after removing duplicate pulls

## Findings

Across the collection window the data showed a clean cycle — a steady climb to a peak around 5–6 August, then the start of a sharp fall.

A few things stood out:

- Every fuel grade moved together. E10, unleaded 91, premium 95/98 and diesel all traced the same climb-and-crash shape, which points to a market-wide cycle rather than station-level noise.
- Regular unleaded (E10) swung about 27 c/L from trough to peak.
- Diesel moved the most, climbing over 30 c/L.
- Premium grades held a roughly constant margin above regular the whole way through, instead of widening or narrowing across the cycle.

![E10 price cycle](e10_price_cycle.png)

![Price cycle by fuel type](price_by_fueltype.png)

## How it works

**`collect_prices.py`**
- Authenticates against the FuelCheck OAuth endpoint
- Pulls current prices for every station
- Appends each pull to `fuel_prices_history.csv` with a timestamp

The analysis notebook loads that CSV, drops duplicate pulls, groups by day and fuel type, and builds the charts above.

API credentials are kept out of the code in a local `.env` file, which isn't committed.

## Stack

Python, pandas, matplotlib, requests, cron.

## Running it yourself

1. Register for a free FuelCheck API key at the [NSW API portal](https://api.nsw.gov.au).
2. Add your key and secret to a `.env` file in the project root:
   ```
   API_KEY=your_key
   API_SECRET=your_secret
   ```
3. Install the dependencies:
   ```
   pip install requests pandas matplotlib python-dotenv
   ```
4. Run `python3 collect_prices.py` to collect a snapshot, or schedule it with cron to build history automatically.

## Next steps

This version documents the cycle. The next stage is forecasting — modelling when the next price spike is likely by region, and testing it properly against a naive baseline rather than eyeballing the chart.
