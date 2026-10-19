SELECT 
    * EXCEPT "ts_count"
FROM (
    SELECT
        s."time",
        s."External_Temp",
        s."Salinity",
        s."Chlorophyll_RFU",
        s."BGA_PE_RFU",
        a."Latitude",
        a."Longitude",
        COUNT(*) OVER(PARTITION BY s."time") as ts_count
    FROM "SondeValues" s
    INNER JOIN "Ai1" a
        ON s."time" = a."time" AND s."station_name" ILIKE a."station_name"
    WHERE
        s."station_name" ILIKE 'blynken' AND
        s."time" >= '2026-06-01' AND
        s."time" < '2026-06-02'
) sub
WHERE ts_count = 1
ORDER BY "time" ASC