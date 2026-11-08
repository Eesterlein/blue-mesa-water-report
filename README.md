# Blue Mesa Water Report

A one-page dashboard showing how much water is in Blue Mesa Reservoir (Gunnison County, Colorado) and how much the dam has released, using every daily reading since December 1968.

**[View the live dashboard →](https://eesterlein.github.io/blue-mesa-water-report/)**

You can also open `index.html` in a browser to view it locally. It needs no server.

## What it shows

- **Right now:** how full the lake is compared with its fullest and lowest days on record, shown as a gauge.
- **Key figures:** water in the lake against one year ago, the lake level against full pool, and water released so far this year against normal.
- **Has the lake ever been this low?** The full storage history, with today's level, the record high and the record low marked.
- **How does this year compare with every other year?** Every year's water level from January to December, overlaid, with this year and the closest year highlighted.
- **Which years released the most and least water?** Yearly release totals against the long-term average.
- **When the water goes out:** the average release rate by month, compared with this year and last year.
- **Every year on record:** a sortable table.

## Data

U.S. Bureau of Reclamation, Upper Colorado Region hydrologic data for Blue Mesa Reservoir (site 913):

| File | Contents | Source |
|---|---|---|
| `data/release_cfs.csv` | Daily total release, cubic feet per second | [913/csv/42.csv](https://www.usbr.gov/uc/water/hydrodata/reservoir_data/913/csv/42.csv) |
| `data/storage_af.csv` | Daily storage, acre-feet | [913/csv/17.csv](https://www.usbr.gov/uc/water/hydrodata/reservoir_data/913/csv/17.csv) |
| `data/elevation_ft.csv` | Daily lake elevation, feet | [913/csv/49.csv](https://www.usbr.gov/uc/water/hydrodata/reservoir_data/913/csv/49.csv) |
| `data/blue_mesa_daily.csv` | The three above merged by date (built) | |
| `data/summary.json` | The headline figures shown on the page (built) | |

## Updating

```sh
python3 scripts/build.py            # download the latest data from Reclamation and rebuild index.html
python3 scripts/build.py --offline  # rebuild from the CSVs already in data/
```

The script uses only the Python standard library. The page layout lives in `scripts/template.html`, and the build step embeds the data into it.

## Method notes

- One cubic foot per second flowing for a full day is 1.98347 acre-feet. Daily release rates are summed this way into yearly totals.
- Years are calendar years. A "normal year" is the average of every full calendar year on record. "Normal for this date" compares January 1 through the latest reading's date in every year.
- Full pool is 7,519.4 feet. "Fullest" and "lowest" are the highest and lowest daily storage readings on record.
- Blue Mesa is the first of three Aspinall Unit dams. Its releases flow into Morrow Point and Crystal, so flows through the Black Canyon are measured below Crystal Dam, not here.
