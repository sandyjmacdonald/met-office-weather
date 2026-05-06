# Open-Meteo Current UK Weather Data

**Note that this app no longer gets weather data directly from the Met Office, more info. below**

A small Flask app that returns current UK weather as a downloadable TSV.
Deploys to Vercel as a Python serverless function.

Powered by [Open-Meteo](https://open-meteo.com), which aggregates open data
from national weather services -- including UK Met Office UKMO Global 10km
and UKV 2km models for the UK and Ireland.

## Why not the Met Office API directly?

The original DataPoint API was retired on 1 December 2025. Its successor
(Weather DataHub) requires a free account, gives you 360 calls/day, and
forces you to make one HTTP request per station. For an "all UK in one
TSV" use case, Open-Meteo is a much better fit:

| | DataPoint (retired) | DataHub | Open-Meteo |
|---|---|---|---|
| API key needed | yes | yes | **no** |
| Stations per call | all | one | up to 1000 |
| Free tier | yes | 360/day | 10,000/day |
| Underlying data | Met Office | Met Office | Includes UKMO |

The trade-off: Open-Meteo returns *modelled current values* rather than raw
station observations. For most apps and dashboards this is fine and
arguably more useful (data for any lat/lon, not just stations).

## Setup

No setup beyond deploying. There's no API key to configure.

1. Push this repo to GitHub.
2. Import it in Vercel. Vercel auto-detects Flask in `api/index.py` -- no
   `vercel.json` is needed.
3. Done.

## Local development

```bash
pip install -r requirements.txt
python api/index.py
# visit http://localhost:5000
```

## Customising

- **Add or remove locations**: edit the `LOCATIONS` list at the top of
  `api/index.py`. Open-Meteo accepts up to 1000 in one call.
- **Change the variables**: edit `CURRENT_VARS` and `COLUMNS`. Full list:
  https://open-meteo.com/en/docs

## Attribution

Weather data by Open-Meteo.com, incorporating UK Met Office UKMO model
data. Data licensed under CC BY 4.0.

Open-Meteo's free tier is for non-commercial use. If you put this behind
a paywall or run ads against it, sign up for a paid plan:
https://open-meteo.com/en/pricing
