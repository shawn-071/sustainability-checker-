"""
data_sources.py
---------------
Fetch climate data from NASA POWER and soil pH data from SoilGrids.

Both sources are free and require no API key.
"""

import json
import math
import sys

import requests


NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"
SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"

TIMEOUT = 10


def _validate_coordinates(lat: float, lon: float):
    """Validate latitude and longitude values."""

    lat = float(lat)
    lon = float(lon)

    if not -90 <= lat <= 90:
        raise ValueError("Latitude must be between -90 and 90.")

    if not -180 <= lon <= 180:
        raise ValueError("Longitude must be between -180 and 180.")

    return lat, lon


def _extract_annual(param_dict):
    """
    Extract an annual value from a NASA POWER parameter block.

    Handles the common annual keys and falls back to the average
    of numeric values if an explicit annual key is unavailable.
    """

    if not isinstance(param_dict, dict):
        return None

    for key in ("ANN", "13", "ANNUAL", "Annual"):
        value = param_dict.get(key)

        if isinstance(value, (int, float)):
            return float(value)

    values = [
        value
        for value in param_dict.values()
        if isinstance(value, (int, float))
    ]

    if not values:
        return None

    return sum(values) / len(values)


def fetch_climate(lat: float, lon: float) -> dict:
    """
    Fetch long-term climate data for a location.

    Returns:
        temp_c
        rain_mm_year
        humidity_pct
        error
    """

    out = {
        "temp_c": None,
        "rain_mm_year": None,
        "humidity_pct": None,
        "error": None,
    }

    try:
        lat, lon = _validate_coordinates(lat, lon)

        params = {
            "parameters": "T2M,PRECTOTCORR,RH2M",
            "community": "AG",
            "longitude": lon,
            "latitude": lat,
            "format": "JSON",
        }

        response = requests.get(
            NASA_POWER_URL,
            params=params,
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        param_block = (
            data
            .get("properties", {})
            .get("parameter", {})
        )

        if not param_block:
            raise ValueError(
                "NASA POWER returned no parameter data."
            )

        # Average temperature.
        out["temp_c"] = _extract_annual(
            param_block.get("T2M", {})
        )

        # NASA POWER precipitation is represented as an
        # average daily precipitation value in the climatology.
        rain_avg_daily = _extract_annual(
            param_block.get("PRECTOTCORR", {})
        )

        if rain_avg_daily is not None:
            out["rain_mm_year"] = rain_avg_daily * 365

        # Relative humidity.
        out["humidity_pct"] = _extract_annual(
            param_block.get("RH2M", {})
        )

    except requests.RequestException as exc:
        out["error"] = (
            f"NASA POWER request failed: {exc}"
        )

    except (ValueError, KeyError, TypeError) as exc:
        out["error"] = (
            f"NASA POWER data could not be read: {exc}"
        )

    except Exception as exc:
        out["error"] = (
            f"NASA POWER fetch failed: {exc}"
        )

    return out


def fetch_soil(lat: float, lon: float) -> dict:
    """
    Fetch soil pH for the top 0-5 cm of soil.

    Returns:
        ph
        error
    """

    out = {
        "ph": None,
        "error": None,
    }

    try:
        lat, lon = _validate_coordinates(lat, lon)

        params = {
            "lon": lon,
            "lat": lat,
            "property": "phh2o",
            "depth": "0-5cm",
            "value": "mean",
        }

        response = requests.get(
            SOILGRIDS_URL,
            params=params,
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        layers = (
            data
            .get("properties", {})
            .get("layers", [])
        )

        ph_layer = next(
            (
                layer
                for layer in layers
                if layer.get("name") == "phh2o"
            ),
            None,
        )

        if ph_layer is None:
            raise ValueError(
                "SoilGrids did not return a phh2o layer."
            )

        depths = ph_layer.get("depths", [])

        if not depths:
            raise ValueError(
                "SoilGrids did not return depth data."
            )

        depth_block = depths[0]

        values = depth_block.get("values", {})

        raw_value = values.get("mean")

        if raw_value is None:
            raise ValueError(
                "SoilGrids did not return a mean pH value."
            )

        unit_measure = ph_layer.get(
            "unit_measure",
            {},
        )

        d_factor = unit_measure.get(
            "d_factor",
            10,
        )

        out["ph"] = (
            float(raw_value) / float(d_factor)
            if d_factor
            else float(raw_value)
        )

    except requests.RequestException as exc:
        out["error"] = (
            f"SoilGrids request failed: {exc}"
        )

    except (ValueError, KeyError, TypeError, StopIteration) as exc:
        out["error"] = (
            f"SoilGrids data could not be read: {exc}"
        )

    except Exception as exc:
        out["error"] = (
            f"SoilGrids fetch failed: {exc}"
        )

    return out


def fetch_terrain(lat: float, lon: float) -> dict:
    """Return a 90 m DEM elevation and a rough nearby slope estimate."""
    out = {"elevation_m": None, "slope_pct": None, "terrain_error": None}
    try:
        lat, lon = _validate_coordinates(lat, lon)
        lat_step = 0.0008
        cos_lat = max(abs(math.cos(math.radians(lat))), 0.1)
        lon_step = min(0.0008 / cos_lat, 1.0)
        points = [
            (lat, lon),
            (min(90.0, lat + lat_step), lon),
            (max(-90.0, lat - lat_step), lon),
            (lat, ((lon + lon_step + 180) % 360) - 180),
            (lat, ((lon - lon_step + 180) % 360) - 180),
        ]
        response = requests.get(
            ELEVATION_URL,
            params={
                "latitude": ",".join(f"{point[0]:.6f}" for point in points),
                "longitude": ",".join(f"{point[1]:.6f}" for point in points),
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        elevations = response.json().get("elevation", [])
        if len(elevations) != 5 or any(value is None for value in elevations):
            raise ValueError("Elevation service returned incomplete terrain data.")

        out["elevation_m"] = float(elevations[0])
        north_south_m = max(1.0, (points[1][0] - points[2][0]) * 111_320)
        east_west_m = max(1.0, (2 * lon_step) * 111_320 * cos_lat)
        north_south_grade = (float(elevations[1]) - float(elevations[2])) / north_south_m
        east_west_grade = (float(elevations[3]) - float(elevations[4])) / east_west_m
        out["slope_pct"] = math.hypot(north_south_grade, east_west_grade) * 100
    except requests.RequestException as exc:
        out["terrain_error"] = f"Elevation lookup failed: {exc}"
    except (ValueError, KeyError, TypeError) as exc:
        out["terrain_error"] = f"Terrain data could not be read: {exc}"
    except Exception as exc:
        out["terrain_error"] = f"Terrain lookup failed: {exc}"
    return out


def fetch_all(lat: float, lon: float) -> dict:
    """Fetch both climate and soil data."""

    return {
        "climate": fetch_climate(lat, lon),
        "soil": fetch_soil(lat, lon),
        "terrain": fetch_terrain(lat, lon),
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Usage: python data_sources.py <latitude> <longitude>"
        )
        raise SystemExit(1)

    try:
        latitude = float(sys.argv[1])
        longitude = float(sys.argv[2])

        results = fetch_all(latitude, longitude)

        print(
            json.dumps(
                results,
                indent=2,
            )
        )

    except ValueError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)
