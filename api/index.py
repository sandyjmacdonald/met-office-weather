"""
UK weather data -> TSV downloader, powered by Open-Meteo.

Open-Meteo is a free, no-API-key weather service that aggregates open data
from national weather services (including the UK Met Office UKMO Global 10km
and UKV 2km models for the UK). One HTTP call returns data for up to 1000
locations, which fits comfortably inside Vercel's serverless timeout.

Note: this returns the *current hour's modelled values* for each location.
True land-station observations (proper successor to DataPoint's wxobs feed)
are only available via the Met Office DataHub now, which charges per call
and per station -- impractical for a free public Vercel app. For most
practical purposes (apps, dashboards, weather widgets), Open-Meteo's
"current" values are accurate enough and *much* easier to work with.

Non-commercial use only. If you add ads or a paid tier, sign up for a paid
Open-Meteo plan: https://open-meteo.com/en/pricing
"""

from io import BytesIO

import requests
from flask import Flask, Response, send_file

app = Flask(__name__)

# --- Config -----------------------------------------------------------------

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# UK locations to fetch -- ~95 cities and towns chosen for geographic spread
# rather than population alone, so remote/rural areas get coverage too.
# Open-Meteo accepts up to 1000 locations per call, so feel free to extend.
LOCATIONS = [
    # --- England: South East ---
    ("London",            51.5074,  -0.1278, "England"),
    ("Heathrow",          51.4700,  -0.4543, "England"),
    ("Reading",           51.4543,  -0.9781, "England"),
    ("Oxford",            51.7520,  -1.2577, "England"),
    ("Brighton",          50.8225,  -0.1372, "England"),
    ("Southampton",       50.9097,  -1.4044, "England"),
    ("Portsmouth",        50.8198,  -1.0880, "England"),
    ("Dover",             51.1279,   1.3134, "England"),
    ("Canterbury",        51.2802,   1.0789, "England"),
    ("Maidstone",         51.2720,   0.5290, "England"),
    ("Guildford",         51.2362,  -0.5704, "England"),
    ("Milton Keynes",     52.0406,  -0.7594, "England"),

    # --- England: South West ---
    ("Bristol",           51.4545,  -2.5879, "England"),
    ("Bath",              51.3811,  -2.3590, "England"),
    ("Plymouth",          50.3755,  -4.1427, "England"),
    ("Exeter",            50.7184,  -3.5339, "England"),
    ("Truro",             50.2632,  -5.0510, "England"),
    ("Penzance",          50.1186,  -5.5373, "England"),
    ("Bournemouth",       50.7192,  -1.8808, "England"),
    ("Salisbury",         51.0688,  -1.7945, "England"),
    ("Taunton",           51.0148,  -3.1064, "England"),
    ("Gloucester",        51.8642,  -2.2380, "England"),

    # --- England: East ---
    ("Cambridge",         52.2053,   0.1218, "England"),
    ("Norwich",           52.6309,   1.2974, "England"),
    ("Ipswich",           52.0567,   1.1482, "England"),
    ("Peterborough",      52.5695,  -0.2405, "England"),
    ("Lowestoft",         52.4751,   1.7505, "England"),
    ("Kings Lynn",        52.7517,   0.3960, "England"),
    ("Luton",             51.8787,  -0.4200, "England"),

    # --- England: Midlands ---
    ("Birmingham",        52.4862,  -1.8904, "England"),
    ("Coventry",          52.4068,  -1.5197, "England"),
    ("Leicester",         52.6369,  -1.1398, "England"),
    ("Nottingham",        52.9548,  -1.1581, "England"),
    ("Derby",             52.9225,  -1.4746, "England"),
    ("Stoke-on-Trent",    53.0027,  -2.1794, "England"),
    ("Worcester",         52.1920,  -2.2200, "England"),
    ("Shrewsbury",        52.7077,  -2.7530, "England"),
    ("Lincoln",           53.2307,  -0.5406, "England"),
    ("Northampton",       52.2405,  -0.9027, "England"),

    # --- England: North West ---
    ("Manchester",        53.4808,  -2.2426, "England"),
    ("Liverpool",         53.4084,  -2.9916, "England"),
    ("Preston",           53.7632,  -2.7031, "England"),
    ("Lancaster",         54.0466,  -2.8007, "England"),
    ("Blackpool",         53.8175,  -3.0357, "England"),
    ("Carlisle",          54.8925,  -2.9329, "England"),
    ("Kendal",            54.3281,  -2.7464, "England"),
    ("Keswick",           54.6014,  -3.1347, "England"),  # Lake District

    # --- England: Yorkshire & Humber ---
    ("Leeds",             53.8008,  -1.5491, "England"),
    ("Sheffield",         53.3811,  -1.4701, "England"),
    ("York",              53.9600,  -1.0873, "England"),
    ("Hull",              53.7457,  -0.3367, "England"),
    ("Bradford",          53.7960,  -1.7594, "England"),
    ("Scarborough",       54.2773,  -0.4017, "England"),
    ("Whitby",            54.4858,  -0.6206, "England"),

    # --- England: North East ---
    ("Newcastle",         54.9783,  -1.6178, "England"),
    ("Sunderland",        54.9069,  -1.3838, "England"),
    ("Middlesbrough",     54.5742,  -1.2349, "England"),
    ("Durham",            54.7761,  -1.5733, "England"),
    ("Berwick-upon-Tweed", 55.7700, -2.0050, "England"),

    # --- Wales ---
    ("Cardiff",           51.4816,  -3.1791, "Wales"),
    ("Swansea",           51.6214,  -3.9436, "Wales"),
    ("Newport",           51.5842,  -2.9977, "Wales"),
    ("Wrexham",           53.0430,  -2.9927, "Wales"),
    ("Aberystwyth",       52.4140,  -4.0810, "Wales"),
    ("Bangor",            53.2280,  -4.1289, "Wales"),
    ("Holyhead",          53.3093,  -4.6336, "Wales"),
    ("Pembroke",          51.6739,  -4.9091, "Wales"),
    ("Brecon",            51.9476,  -3.3905, "Wales"),
    ("Caernarfon",        53.1390,  -4.2750, "Wales"),

    # --- Scotland: Central Belt & South ---
    ("Edinburgh",         55.9533,  -3.1883, "Scotland"),
    ("Glasgow",           55.8642,  -4.2518, "Scotland"),
    ("Stirling",          56.1165,  -3.9369, "Scotland"),
    ("Dundee",            56.4620,  -2.9707, "Scotland"),
    ("Perth",             56.3950,  -3.4308, "Scotland"),
    ("Dumfries",          55.0700,  -3.6053, "Scotland"),
    ("Ayr",               55.4586,  -4.6292, "Scotland"),
    ("Kilmarnock",        55.6111,  -4.4956, "Scotland"),
    ("St Andrews",        56.3398,  -2.7967, "Scotland"),

    # --- Scotland: Highlands & Islands ---
    ("Aberdeen",          57.1497,  -2.0943, "Scotland"),
    ("Inverness",         57.4778,  -4.2247, "Scotland"),
    ("Fort William",      56.8198,  -5.1052, "Scotland"),
    ("Oban",              56.4154,  -5.4719, "Scotland"),
    ("Wick",              58.4391,  -3.0938, "Scotland"),
    ("Thurso",            58.5936,  -3.5221, "Scotland"),
    ("Stornoway",         58.2090,  -6.3890, "Scotland"),  # Outer Hebrides
    ("Portree",           57.4128,  -6.1953, "Scotland"),  # Skye
    ("Kirkwall",          58.9809,  -2.9605, "Scotland"),  # Orkney
    ("Lerwick",           60.1547,  -1.1494, "Scotland"),  # Shetland
    ("Tiree",             56.5050,  -6.8700, "Scotland"),  # Inner Hebrides

    # --- Northern Ireland ---
    ("Belfast",           54.5973,  -5.9301, "Northern Ireland"),
    ("Londonderry",       54.9966,  -7.3086, "Northern Ireland"),
    ("Lisburn",           54.5162,  -6.0581, "Northern Ireland"),
    ("Newry",             54.1751,  -6.3402, "Northern Ireland"),
    ("Armagh",            54.3503,  -6.6528, "Northern Ireland"),
    ("Enniskillen",       54.3438,  -7.6320, "Northern Ireland"),
    ("Ballymena",         54.8642,  -6.2787, "Northern Ireland"),
    ("Coleraine",         55.1326,  -6.6685, "Northern Ireland"),

    # --- Crown Dependencies (often included with UK weather) ---
    ("Douglas",           54.1509,  -4.4810, "Isle of Man"),
]

# Variables to request from Open-Meteo's `current=` endpoint.
# See: https://open-meteo.com/en/docs
CURRENT_VARS = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "is_day",
    "precipitation",
    "weather_code",
    "cloud_cover",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]

# Output TSV columns, in order.
COLUMNS = [
    "Location", "Country", "Latitude", "Longitude", "Time",
    "Temperature (C)", "Feels-like Temperature (C)", "Humidity (%)",
    "Precipitation (mm)", "Cloud Cover (%)", "Pressure (hPa)",
    "Wind Speed (mph)", "Wind Direction", "Wind Gust (mph)",
    "Weather Code", "Weather Description", "Day/Night",
]

# WMO weather interpretation codes used by Open-Meteo.
# https://open-meteo.com/en/docs (see "WMO Weather interpretation codes")
WMO_CODES = {
    0:  "Clear sky",
    1:  "Mainly clear", 2:  "Partly cloudy", 3:  "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}

# Compass direction labels for wind direction (in degrees, meteorological).
COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


# --- Helpers ----------------------------------------------------------------

def deg_to_compass(deg):
    """Convert wind bearing in degrees to a 16-point compass label."""
    if deg is None or deg == "":
        return ""
    try:
        idx = int((float(deg) / 22.5) + 0.5) % 16
        return COMPASS[idx]
    except (TypeError, ValueError):
        return ""


def fetch_all_locations(timeout=8):
    """Fetch current weather for every location in one Open-Meteo request.

    Returns a list of (location_tuple, current_dict) pairs, in the original
    order. Raises requests.RequestException or returns [] on failure.
    """
    lats = ",".join(f"{lat:.4f}" for _, lat, _, _ in LOCATIONS)
    lons = ",".join(f"{lon:.4f}" for _, _, lon, _ in LOCATIONS)

    params = {
        "latitude": lats,
        "longitude": lons,
        "current": ",".join(CURRENT_VARS),
        "wind_speed_unit": "mph",
        "timezone": "Europe/London",
    }
    r = requests.get(OPEN_METEO_URL, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()

    # When you pass multiple coordinates, Open-Meteo returns a JSON array.
    # When you pass exactly one, it returns a single object. Normalise.
    if isinstance(data, dict):
        data = [data]

    return list(zip(LOCATIONS, data))


def row_for_location(location, payload):
    """Build a TSV row dict for a single location's API payload."""
    name, lat, lon, country = location
    current = payload.get("current") or {}

    code = current.get("weather_code")
    description = WMO_CODES.get(code, "") if isinstance(code, int) else ""

    is_day = current.get("is_day")
    day_night = "Day" if is_day == 1 else "Night" if is_day == 0 else ""

    return {
        "Location": name,
        "Country": country,
        "Latitude": lat,
        "Longitude": lon,
        "Time": current.get("time", ""),
        "Temperature (C)": current.get("temperature_2m", ""),
        "Feels-like Temperature (C)": current.get("apparent_temperature", ""),
        "Humidity (%)": current.get("relative_humidity_2m", ""),
        "Precipitation (mm)": current.get("precipitation", ""),
        "Cloud Cover (%)": current.get("cloud_cover", ""),
        "Pressure (hPa)": current.get("surface_pressure", ""),
        "Wind Speed (mph)": current.get("wind_speed_10m", ""),
        "Wind Direction": deg_to_compass(current.get("wind_direction_10m")),
        "Wind Gust (mph)": current.get("wind_gusts_10m", ""),
        "Weather Code": code if code is not None else "",
        "Weather Description": description,
        "Day/Night": day_night,
    }


def build_tsv(rows):
    lines = ["\t".join(COLUMNS)]
    for row in rows:
        lines.append("\t".join(str(row.get(col, "")) for col in COLUMNS))
    return "\n".join(lines).encode("utf-8")


# --- Routes -----------------------------------------------------------------

@app.route("/")
def index():
    return (
        '<!doctype html>'
        '<html><head><title>UK weather data</title></head><body>'
        '<h1>UK weather data</h1>'
        '<p><a href="/request/weather">Download uk_weather_data.tsv</a></p>'
        '<p><small>Weather data by Open-Meteo.com, '
        'incorporating UK Met Office UKMO model data. '
        'Licensed under CC BY 4.0.</small></p>'
        '</body></html>'
    )


@app.route("/request/weather", methods=["GET", "POST"])
def request_weather():
    try:
        results = fetch_all_locations()
    except requests.RequestException as exc:
        return Response(
            f"Failed to reach Open-Meteo: {exc}",
            status=502,
            mimetype="text/plain",
        )

    rows = [row_for_location(loc, payload) for loc, payload in results]
    rows.sort(key=lambda r: (r["Country"], r["Location"]))

    tsv_bytes = build_tsv(rows)
    buf = BytesIO(tsv_bytes)
    buf.seek(0)
    filename = "uk_weather_data.tsv"
    response = send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="text/tab-separated-values",
    )
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


# Local dev: `python api/index.py`
if __name__ == "__main__":
    app.run(debug=True, port=5000)
