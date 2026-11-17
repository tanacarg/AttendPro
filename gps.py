
import math


# GPS distance rules
OFFICE_ALLOWED_RADIUS_METERS = 100
SITE_ALERT_DISTANCE_METERS = 10_000

EARTH_RADIUS_METERS = 6_371_000


def validate_coordinates(latitude, longitude):
    """Validate GPS latitude and longitude."""

    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise ValueError("GPS coordinates must be valid numbers")

    if not -90 <= latitude <= 90:
        raise ValueError("Invalid latitude")

    if not -180 <= longitude <= 180:
        raise ValueError("Invalid longitude")


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two GPS coordinates
    using the Haversine formula.
    Returns distance in meters.
    """

    validate_coordinates(lat1, lon1)
    validate_coordinates(lat2, lon2)

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    delta_lat = lat2 - lat1
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    # Protect against floating-point rounding errors.
    a = max(0.0, min(1.0, a))

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return EARTH_RADIUS_METERS * c


def find_nearest_location(
    worker_latitude,
    worker_longitude,
    locations,
):
    """
    Find the nearest location from a list.

    Each location must contain:
    latitude, longitude and label.
    """

    validate_coordinates(
        worker_latitude,
        worker_longitude,
    )

    if not locations:
        raise ValueError("No GPS locations are registered")

    nearest_location = None
    nearest_distance = None

    for location in locations:
        latitude = float(location["latitude"])
        longitude = float(location["longitude"])

        distance = calculate_distance(
            worker_latitude,
            worker_longitude,
            latitude,
            longitude,
        )

        if (
            nearest_distance is None
            or distance < nearest_distance
        ):
            nearest_distance = distance
            nearest_location = location

    return {
        "nearest_location": nearest_location,
        "distance_meters": round(nearest_distance, 2),
        "distance_km": round(nearest_distance / 1000, 2),
    }


def check_office_distance(
    worker_latitude,
    worker_longitude,
    office_locations,
):
    """
    Office attendance rules:

    - A company may have multiple office branches.
    - Worker can attend at any active registered branch.
    - Attendance is allowed within 100 meters.
    - Attendance is blocked beyond 100 meters.
    """

    result = find_nearest_location(
        worker_latitude,
        worker_longitude,
        office_locations,
    )

    distance = result["distance_meters"]

    attendance_allowed = (
        distance <= OFFICE_ALLOWED_RADIUS_METERS
    )

    result.update({
        "attendance_type": "office",
        "gps_alert": not attendance_allowed,
        "attendance_allowed": attendance_allowed,
        "allowed_radius_meters": OFFICE_ALLOWED_RADIUS_METERS,
    })

    return result


def check_site_distance(
    worker_latitude,
    worker_longitude,
    project_locations,
):
    """
    Site attendance rules:

    - A project may have multiple GPS points.
    - Compare worker location with the nearest project point.
    - Above 10,000 meters creates an alert.
    - Attendance is never blocked because of this distance.
    """

    result = find_nearest_location(
        worker_latitude,
        worker_longitude,
        project_locations,
    )

    distance = result["distance_meters"]

    gps_alert = (
        distance > SITE_ALERT_DISTANCE_METERS
    )

    result.update({
        "attendance_type": "site",
        "gps_alert": gps_alert,
        "attendance_allowed": True,
        "alert_distance_meters": SITE_ALERT_DISTANCE_METERS,
    })

    return result


def check_project_distance(
    worker_latitude,
    worker_longitude,
    project_locations,
):
    """
    Backward-compatible function for existing code.
    Uses the Site GPS rule.
    """

    return check_site_distance(
        worker_latitude,
        worker_longitude,
        project_locations,
    )


def format_distance_result(result):
    distance_km = result["distance_km"]
    attendance_type = result["attendance_type"]

    if attendance_type == "office":
        if result["attendance_allowed"]:
            return (
                f"Office GPS verified. "
                f"Distance: {distance_km} KM."
            )

        return (
            f"Office attendance blocked. "
            f"Distance: {distance_km} KM. "
            f"Maximum allowed distance is 100 meters."
        )

    if result["gps_alert"]:
        return (
            f"SITE GPS ALERT: Worker is "
            f"{distance_km} KM from the nearest "
            f"project GPS point. Attendance is allowed."
        )

    return (
        f"Site GPS checked. "
        f"Distance from nearest project GPS point: "
        f"{distance_km} KM."
    )
