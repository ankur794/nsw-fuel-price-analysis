-- NSW Fuel Price Analysis — SQL version
-- Same insights as the pandas analysis, expressed in SQL for the database side.

-- 1. Basic join: attach station name, brand, address to prices
SELECT p.stationcode, s.name, s.brand, s.address, p.fueltype, p.price, p.lastupdated
FROM prices p
JOIN stations s ON p.stationcode = s.stationcode
LIMIT 10;

-- 2. Average price by brand for E10 (only brands with 3+ stations)
SELECT s.brand,
       ROUND(AVG(p.price), 2) AS avg_price,
       COUNT(DISTINCT p.stationcode) AS stations
FROM prices p
JOIN stations s ON p.stationcode = s.stationcode
WHERE p.fueltype = 'E10'
GROUP BY s.brand
HAVING COUNT(DISTINCT p.stationcode) >= 3
ORDER BY avg_price ASC
LIMIT 15;

-- 3. Daily average E10 price across NSW (the price cycle)
SELECT DATE(pull_time) AS day,
       ROUND(AVG(price), 2) AS avg_price
FROM prices
WHERE fueltype = 'E10'
GROUP BY DATE(pull_time)
ORDER BY day;

-- 4. Day-over-day price change using a window function (LAG)
-- This finds the turning points in the cycle: where price stops rising and starts falling.
WITH daily AS (
    SELECT DATE(pull_time) AS day,
           ROUND(AVG(price), 2) AS avg_price
    FROM prices
    WHERE fueltype = 'E10'
    GROUP BY DATE(pull_time)
)
SELECT day,
       avg_price,
       avg_price - LAG(avg_price) OVER (ORDER BY day) AS change_from_prev_day,
       CASE
           WHEN avg_price - LAG(avg_price) OVER (ORDER BY day) > 0 THEN 'rising'
           WHEN avg_price - LAG(avg_price) OVER (ORDER BY day) < 0 THEN 'falling'
           ELSE 'flat'
       END AS direction
FROM daily
ORDER BY day;

-- 5. Cheapest 10 stations for E10 right now (latest pull only)
WITH latest AS (
    SELECT MAX(pull_time) AS latest_pull FROM prices
)
SELECT s.name, s.brand, s.address, p.price
FROM prices p
JOIN stations s ON p.stationcode = s.stationcode
JOIN latest ON p.pull_time = latest.latest_pull
WHERE p.fueltype = 'E10'
ORDER BY p.price ASC
LIMIT 10;