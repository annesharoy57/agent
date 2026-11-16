"""Bangladesh transport planning fare ranges and distance-based estimates."""

from math import ceil
from typing import Any


FARE_RANGES: dict[str, dict[str, Any]] = {
    "bus": {
        "label": "Intercity coach / bus",
        "minimum_per_km": 3.0,
        "maximum_per_km": 6.0,
        "minimum_fare": 150.0,
        "maximum_minimum_fare": 250.0,
        "per_traveler": True,
        "vehicle_capacity": 1,
    },
    "train": {
        "label": "Train",
        "minimum_per_km": 1.5,
        "maximum_per_km": 4.0,
        "minimum_fare": 30.0,
        "maximum_minimum_fare": 60.0,
        "per_traveler": True,
        "vehicle_capacity": 1,
    },
    "cng": {
        "label": "CNG auto-rickshaw",
        "minimum_per_km": 20.0,
        "maximum_per_km": 40.0,
        "minimum_fare": 50.0,
        "maximum_minimum_fare": 100.0,
        "per_traveler": False,
        "vehicle_capacity": 3,
    },
    "auto_rickshaw": {
        "label": "Auto-rickshaw",
        "minimum_per_km": 20.0,
        "maximum_per_km": 45.0,
        "minimum_fare": 40.0,
        "maximum_minimum_fare": 80.0,
        "per_traveler": False,
        "vehicle_capacity": 3,
    },
    "rickshaw": {
        "label": "Cycle rickshaw",
        "minimum_per_km": 25.0,
        "maximum_per_km": 60.0,
        "minimum_fare": 30.0,
        "maximum_minimum_fare": 60.0,
        "per_traveler": False,
        "vehicle_capacity": 2,
    },
    "ride_sharing": {
        "label": "Ride-sharing car",
        "minimum_per_km": 25.0,
        "maximum_per_km": 55.0,
        "minimum_fare": 60.0,
        "maximum_minimum_fare": 120.0,
        "per_traveler": False,
        "vehicle_capacity": 4,
    },
}

FARE_DATA_NOTE = (
    "Planning ranges in BDT/km, not verified operator quotes. Bus and train ranges "
    "approximate per-traveler fares; CNG, auto-rickshaw, rickshaw, and ride-sharing "
    "ranges approximate a vehicle fare; groups above estimated vehicle capacity need "
    "multiple vehicles. Actual fares vary by operator, route, class, "
    "time, traffic, negotiation, and service charges. Where used, OpenRouteService "
    "driving distance is only a proxy for bus/train fare distance; it is not a rail route."
)


def estimate_transport_cost(
    vehicle_type: str, distance_km: float | None, travelers: int = 1,
    *, return_trip: bool = False,
) -> dict[str, Any]:
    """Estimate a BDT fare range; return an explicit unavailable result without distance."""
    fare = FARE_RANGES[vehicle_type]
    if distance_km is None or distance_km <= 0:
        return {
            "vehicle_type": vehicle_type,
            "vehicle": fare["label"],
            "currency": "BDT",
            "minimum": None,
            "maximum": None,
            "distance_km": distance_km,
            "return_trip": return_trip,
            "status": "distance_unavailable",
            "basis": FARE_DATA_NOTE,
        }

    multiplier = 2 if return_trip else 1
    fare_distance = float(distance_km) * multiplier
    scale = (
        max(1, travelers)
        if fare["per_traveler"]
        else ceil(max(1, travelers) / fare["vehicle_capacity"])
    )
    minimum = max(float(fare["minimum_fare"]), fare_distance * fare["minimum_per_km"]) * scale
    maximum = max(
        float(fare["maximum_minimum_fare"]),
        fare_distance * fare["maximum_per_km"],
    ) * scale
    return {
        "vehicle_type": vehicle_type,
        "vehicle": fare["label"],
        "currency": "BDT",
        "minimum": round(minimum / 10) * 10,
        "maximum": round(maximum / 10) * 10,
        "distance_km": round(fare_distance, 1),
        "return_trip": return_trip,
        "status": "estimated_range",
        "basis": FARE_DATA_NOTE,
    }


def select_vehicle_type(vehicle_guidance: str, *, local: bool = False) -> str:
    """Select the fare model matching TripMate's vehicle guidance."""
    text = vehicle_guidance.casefold()
    if local:
        if "cng" in text:
            return "cng"
        if "rickshaw" in text and "auto-rickshaw" not in text:
            return "rickshaw"
        if "ride-hailing" in text or "ride-sharing" in text or "car" in text:
            return "ride_sharing"
        return "auto_rickshaw"
    if "train" in text and "coach" not in text and "bus" not in text:
        return "train"
    return "bus"
