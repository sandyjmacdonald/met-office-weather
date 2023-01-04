import json
import requests

from io import BytesIO

from flask import Flask, send_file

# Create the Flask app object
app = Flask(__name__)

# The Met Office have numerical codes for different weather types.
# This is a list of the weather types in the order that corresponds
# with those numerical codes.
weather_types = [
    "Clear Night",
    "Sunny Day",
    "Partly Cloudy (night)",
    "Partly Cloudy (day)",
    "Not used",
    "Mist",
    "Fog",
    "Cloudy",
    "Overcast",
    "Light Rain Shower (night)",
    "Light Rain Shower (day)",
    "Drizzle",
    "Light Rain",
    "Heavy Rain Shower (night)",
    "Heavy Rain Shower (day)",
    "Heavy Rain",
    "Sleet Shower (night)",
    "Sleet Shower (day)",
    "Sleet",
    "Hail Shower (night)",
    "Hail Shower (day)",
    "Hail",
    "Light Snow Shower (night)",
    "Light Snow Shower (day)",
    "Light Snow",
    "Heavy Show Shower (night)",
    "Heavy Snow Shower (day)",
    "Heavy Snow",
    "Thunder Shower (night)",
    "Thunder Shower (day)",
    "Thunder",
]


def get_met_office_data():
    """
    Gets the second-to-last set of data from the Met Office API via an HTTP request
    """
    url = "http://datapoint.metoffice.gov.uk/public/data/val/wxobs/all/json/capabilities?res=hourly&key=7ed9189d-6f69-47bc-92f7-d1374c7285d6"
    retries = 5

    while retries > 0:
        r = requests.get(url)
        if r.status_code == requests.codes.ok:
            res = r.json()
            retries = 0
        else:
            retries -= 1
            res = False

    if res:
        timestamp = res["Resource"]["TimeSteps"]["TS"][-2]
        new_url = f"http://datapoint.metoffice.gov.uk/public/data/val/wxobs/all/json/all?res=hourly&time={timestamp}&key=7ed9189d-6f69-47bc-92f7-d1374c7285d6"
        retries = 5

        while retries > 0:
            r = requests.get(new_url)
            if r.status_code == requests.codes.ok:
                res = r.json()
                retries = 0
            else:
                retries -= 1
                res = False

        return res
    else:
        return False


def reformat_met_office_data(weather_data):
    """
    Reformats the raw JSON response returned by the Met Office API.
    """
    colnames = "Latitude\tLongitude\tCountry\tLocation\tTemperature (C)\tWind Speed (mph)\tWind Direction\tWind Gust (mph)\tVisibility (m)\tPressure (hPa)\tPressure Tendency\tHumidity\tUV Index\tPrecipitation Probability (%)\tFeels-like Temperature\tWeather Type\tWeather Description\tElevation (m)"
    data = []
    countries = {}

    for location in weather_data["SiteRep"]["DV"]["Location"]:
        if location["country"] not in countries:
            countries[location["country"]] = {}
        countries[location["country"]][location["name"]] = location

    # These report_keys correspond to the different variables they provide,
    # T=temperature, P=pressure, H=humidity, etc.
    report_keys = ["T", "S", "D", "G", "V", "P", "Pt", "H", "U", "Pp", "F", "W"]

    for country in sorted(countries.keys()):
        for location in sorted(countries[country].keys()):
            site = countries[country][location]
            values = [site["lat"], site["lon"], country.title(), location.title()]
            if "Rep" in site["Period"]:
                report = site["Period"]["Rep"]
                if isinstance(report, dict):
                    for report_key in report_keys:
                        if report_key in report:
                            values.append(report[report_key])
                        else:
                            values.append("NA")
                    if "W" in report:
                        weather_type = weather_types[int(report["W"])]
                        values.append(weather_type)
                    else:
                        values.append("NA")
                else:
                    for i in range(len(report_keys) + 1):
                        values.append("NA")
            else:
                null_values = ["NA"] * (len(report_keys) + 1)
                values.extend(null_values)
            values.append(site["elevation"])
            data.append("\t".join(values))

    # Join up all of the lines with newline characters
    joined = "\n".join([colnames] + data)
    # Encode as binary to be able to send the data as a file object later
    joined = joined.encode()
    return joined


@app.route("/request/weather", methods=["GET", "POST"])
def request_weather():
    """
    Grabs weather data as JSON from the Met Office API, reformats into TSV,
    then send the file as an attachment with the correct mimetype.
    """
    weather_data = get_met_office_data()
    reformatted_weather_data = reformat_met_office_data(weather_data)
    # Convert to bytes object for downloading
    reformatted_weather_data = BytesIO(reformatted_weather_data)
    reformatted_weather_data.seek(0)
    filename = "met_office_weather_data.tsv"
    response = send_file(
        reformatted_weather_data,
        as_attachment=True,
        download_name=filename,
        mimetype="text/tsv",
    )
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-Type"] = "text/tsv"
    return response


@app.route("/")
def base_url():
    """
    Minimal page with link to download reformatted Met Office weather data
    """
    return '<a href="/request/weather">met_office_weather_data.tsv</a>'
