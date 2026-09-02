.headers on
.mode csv
.once tableau_fuel_v3.csv

SELECT
    DATE(p.pull_time) AS day,
    p.pull_time,
    p.fueltype,
    ROUND(CAST(p.price AS REAL), 2) AS price,
    s.brand,
    s.name AS station_name,
    s.address,
    TRIM(
      SUBSTR(
        TRIM(SUBSTR(s.address, INSTR(s.address, ',') + 1)),
        1,
        LENGTH(TRIM(SUBSTR(s.address, INSTR(s.address, ',') + 1))) - 9
      )
    ) AS suburb,
    'NSW' AS state,
    SUBSTR(TRIM(s.address), -4, 4) AS postcode
FROM prices p
JOIN stations s ON s.stationcode = p.stationcode
WHERE p.price IS NOT NULL
  AND CAST(p.price AS REAL) > 0;
