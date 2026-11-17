
import math

GPS_ALERT_DISTANCE_METERS = 10_000


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two GPS coordinates
    using the Haversine formula.
    Returns distance in meters.
    """

    earth_radius = 6_371_000

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius * c


def validate_coordinates(latitude, longitude):
    if not -90 <= latitude <= 90:
        raise ValueError("Invalid latitude")

    if not -180 <= longitude <= 180:
        raise ValueError("Invalid longitude")


def check_project_distance(
    worker_latitude,
    worker_longitude,
    project_locations
):
    """
    project_locations format:
    [
        {"latitude": 9.03, "longitude": 38.74, "label": "Start"},
        {"latitude": 9.04, "longitude": 38.75, "label": "Middle"}
    ]
    """

    validate_coordinates(worker_latitude, worker_longitude)

    if not project_locations:
        raise ValueError("Project GPS locations are not registered")

    nearest_location = None
    nearest_distance = None

    for location in project_locations:
        latitude = float(location["latitude"])
        longitude = float(location["longitude"])

        validate_coordinates(latitude, longitude)

        distance = calculate_distance(
            worker_latitude,
            worker_longitude,
            latitude,
            longitude
        )

        if nearest_distance is None or distance < nearest_distance:
            nearest_distance = distance
            nearest_location = location

    return {
        "distance_meters": round(nearest_distance, 2),
        "distance_km": round(nearest_distance / 1000, 2),
        "nearest_location": nearest_location,
        "gps_alert": nearest_distance > GPS_ALERT_DISTANCE_METERS,
        "attendance_allowed": True
    }


def format_distance_result(result):
    distance_km = result["distance_km"]

    if result["gps_alert"]:
        return (
            f"GPS ALERT: Worker is {distance_km} KM "
            "from the nearest project GPS point."
        )

    return (
        f"Distance from nearest project GPS point: "
        f"{distance_km} KM."
    )
