"""
Backtest the E10 price forecast across the full data window.

Instead of testing on one held-out period, this slides a window through
every day in the dataset: pretend it's day N, fit using only days before N,
forecast 7 days ahead, check against what actually happened. Repeat for
every possible N. This proves the model works consistently, not just on
the one test window it happened to be validated against originally.

Run: python backtest.py
Needs: fuel.db in the same folder (from the SQLite work you already did)
"""

import sqlite3
import pandas as pd
import numpy as np

DB_PATH = "fuel.db"
FUEL_TYPE = "E10"
MIN_HISTORY_DAYS = 7       # need at least a week of history before forecasting
FORECAST_HORIZON = 7        # forecast 7 days ahead each time

def load_daily_avg(fueltype: str) -> pd.DataFrame:
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT DATE(pull_time) AS day, AVG(CAST(price AS REAL)) AS price
        FROM prices
        WHERE fueltype = ?
          AND price IS NOT NULL
          AND CAST(price AS REAL) > 0
        GROUP BY DATE(pull_time)
        ORDER BY day
        """,
        con, params=(fueltype,)
    )
    con.close()
    df["day"] = pd.to_datetime(df["day"])
    df = df.reset_index(drop=True)
    return df


def naive_baseline_forecast(history: pd.Series, horizon: int) -> np.ndarray:
    """Persistence baseline: tomorrow = today's last known price, repeated."""
    last_value = history.iloc[-1]
    return np.full(horizon, last_value)


def linear_trend_forecast(history: pd.Series, horizon: int) -> np.ndarray:
    """Fit a straight line to the history, extrapolate forward."""
    x = np.arange(len(history))
    coeffs = np.polyfit(x, history.values, deg=1)
    future_x = np.arange(len(history), len(history) + horizon)
    return np.polyval(coeffs, future_x)


def run_backtest(df: pd.DataFrame):
    results = []
    n = len(df)

    for split_point in range(MIN_HISTORY_DAYS, n - FORECAST_HORIZON):
        history = df["price"].iloc[:split_point]
        actual_future = df["price"].iloc[split_point:split_point + FORECAST_HORIZON].values

        baseline_pred = naive_baseline_forecast(history, FORECAST_HORIZON)
        trend_pred = linear_trend_forecast(history, FORECAST_HORIZON)

        baseline_mae = np.mean(np.abs(actual_future - baseline_pred))
        trend_mae = np.mean(np.abs(actual_future - trend_pred))

        results.append({
            "split_day": df["day"].iloc[split_point].date(),
            "history_days": split_point,
            "baseline_mae": baseline_mae,
            "trend_mae": trend_mae,
            "improvement_pct": (baseline_mae - trend_mae) / baseline_mae * 100
                                if baseline_mae > 0 else np.nan,
        })

    return pd.DataFrame(results)


def main():
    df = load_daily_avg(FUEL_TYPE)
    print(f"Loaded {len(df)} days of {FUEL_TYPE} data, "
          f"{df['day'].min().date()} to {df['day'].max().date()}")

    if len(df) < MIN_HISTORY_DAYS + FORECAST_HORIZON + 1:
        print(f"Not enough days yet for a meaningful backtest "
              f"(need at least {MIN_HISTORY_DAYS + FORECAST_HORIZON + 1}, have {len(df)}). "
              f"Let the collector run longer and try again.")
        return

    results = run_backtest(df)

    print(f"\nRan {len(results)} backtest folds across the full data window.\n")
    print(f"Naive baseline MAE (avg across all folds): {results['baseline_mae'].mean():.2f} c/L")
    print(f"Linear trend MAE  (avg across all folds): {results['trend_mae'].mean():.2f} c/L")
    print(f"Average improvement over baseline:         {results['improvement_pct'].mean():.1f}%")
    print(f"Folds where trend model beat baseline:     "
          f"{(results['trend_mae'] < results['baseline_mae']).sum()} / {len(results)}")

    results.to_csv("backtest_results.csv", index=False)
    print("\nFull per-day results saved to backtest_results.csv")


if __name__ == "__main__":
    main()
