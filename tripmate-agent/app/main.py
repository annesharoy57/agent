import re
import threading
from datetime import date, timedelta
from typing import Any, Literal
from urllib.parse import urlencode

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from app.decision_engine import estimate_trip_cost, rank_destinations, split_recommendations
from app.conversation import (
    answer_travel_question, classify_travel_question, generate_reply,
    is_destination_information_question,
)
from app.knowledge_base import LocalKnowledgeBase, destination_alias, knowledge_paths
from app.local_model import model_status
from app.research import (
    DESTINATION_DAY_ROUTES, build_vehicle_route, calculate_road_route,
    currency_to_bdt_rate, destination_days, wikipedia_page_research,
    wikipedia_research,
)
from app.transport import estimate_transport_cost, select_vehicle_type
from app.weather import get_destination_forecast as get_weather

load_dotenv()

app = FastAPI(
    title="TripMate AI Agent",
    description="A self-hosted tourism assistant using llama.cpp, local RAG, and Python trip-planning tools.",
    version="1.0.0",
)

# Bangladesh starter catalog. Costs are planning estimates in BDT, not live quotes.
DESTINATIONS: list[dict[str, Any]] = [
    {"name": "Sylhet", "country": "Bangladesh", "scope": "local", "tags": ["nature", "tea", "waterfall", "relax", "adventure"], "daily_cost": 2800, "travel_cost": 1800, "lat": 24.8949, "lon": 91.8687, "summary": "Tea gardens, green hills, rivers, and nature trips."},
    {"name": "Sreemangal", "country": "Bangladesh", "scope": "local", "tags": ["nature", "tea", "relax", "photography"], "daily_cost": 2500, "travel_cost": 1500, "lat": 24.3065, "lon": 91.7296, "summary": "Tea estates, forest trails, and peaceful countryside."},
    {"name": "Jaflong", "country": "Bangladesh", "scope": "local", "tags": ["nature", "river", "mountain", "photography"], "daily_cost": 2600, "travel_cost": 2500, "lat": 25.1632, "lon": 92.0175, "summary": "River scenery and green hills near the Indian border."},
    {"name": "Tanguar Haor", "country": "Bangladesh", "scope": "local", "tags": ["nature", "wetland", "boat", "photography", "birdwatching"], "daily_cost": 3000, "travel_cost": 4500, "lat": 25.0870, "lon": 91.0740, "summary": "A large wetland landscape known for seasonal boat trips and birdlife."},
    {"name": "Cox's Bazar", "country": "Bangladesh", "scope": "local", "tags": ["beach", "sea", "relax", "photography", "food"], "daily_cost": 3500, "travel_cost": 2500, "lat": 21.4272, "lon": 92.0058, "summary": "A long sandy beach, sea views, and seafood."},
    {"name": "Saint Martin's Island", "country": "Bangladesh", "scope": "local", "tags": ["island", "beach", "sea", "snorkeling", "nature"], "daily_cost": 4500, "travel_cost": 9000, "lat": 20.6270, "lon": 92.3220, "summary": "A small island destination with beaches and marine scenery; verify current vessel access and travel rules."},
    {"name": "Bandarban", "country": "Bangladesh", "scope": "local", "tags": ["mountain", "nature", "adventure", "hiking", "photography", "waterfall"], "daily_cost": 3200, "travel_cost": 3500, "lat": 22.1953, "lon": 92.2184, "summary": "Hills, viewpoints, and guided nature excursions."},
    {"name": "Sajek Valley", "country": "Bangladesh", "scope": "local", "tags": ["mountain", "nature", "adventure", "photography", "hiking"], "daily_cost": 3800, "travel_cost": 7000, "lat": 23.3810, "lon": 92.2930, "summary": "Hilltop scenery and cloud views in the Rangamati hill district."},
    {"name": "Khagrachhari", "country": "Bangladesh", "scope": "local", "tags": ["mountain", "nature", "adventure", "cave", "waterfall"], "daily_cost": 3000, "travel_cost": 4500, "lat": 23.1193, "lon": 91.9847, "summary": "Hill landscapes, caves, and waterfalls."},
    {"name": "Rangamati", "country": "Bangladesh", "scope": "local", "tags": ["lake", "nature", "relax", "photography", "culture"], "daily_cost": 2800, "travel_cost": 2200, "lat": 22.6533, "lon": 92.1750, "summary": "Kaptai Lake, green hills, and cultural experiences."},
    {"name": "Kuakata", "country": "Bangladesh", "scope": "local", "tags": ["beach", "sea", "relax", "photography"], "daily_cost": 3000, "travel_cost": 2200, "lat": 21.8167, "lon": 90.1167, "summary": "Coastal scenery and sunrise/sunset views."},
    {"name": "Chattogram", "country": "Bangladesh", "scope": "local", "tags": ["city", "beach", "history", "food", "lake", "culture"], "daily_cost": 3000, "travel_cost": 2500, "lat": 22.3569, "lon": 91.7832, "summary": "A port city with hill, lake, beach, and historic attractions."},
    {"name": "Sundarbans", "country": "Bangladesh", "scope": "local", "tags": ["forest", "nature", "wildlife", "boat", "adventure"], "daily_cost": 5500, "travel_cost": 7000, "lat": 21.9497, "lon": 89.1833, "summary": "Mangrove forest journeys by boat with licensed local operators."},
    {"name": "Bagerhat", "country": "Bangladesh", "scope": "local", "tags": ["history", "heritage", "mosque", "culture", "architecture"], "daily_cost": 2600, "travel_cost": 4500, "lat": 22.6572, "lon": 89.7895, "summary": "Historic mosque-city heritage and archaeological sites."},
    {"name": "Sonargaon", "country": "Bangladesh", "scope": "local", "tags": ["history", "heritage", "culture", "museum", "architecture"], "daily_cost": 2000, "travel_cost": 1200, "lat": 23.6500, "lon": 90.6000, "summary": "Historic Bengal capital sites, old buildings, and folk art."},
    {"name": "Paharpur", "country": "Bangladesh", "scope": "local", "tags": ["history", "heritage", "archaeology", "culture"], "daily_cost": 2500, "travel_cost": 5000, "lat": 25.0311, "lon": 88.9775, "summary": "A major archaeological monastery site in northern Bangladesh."},
    {"name": "Mahasthangarh", "country": "Bangladesh", "scope": "local", "tags": ["history", "heritage", "archaeology", "culture"], "daily_cost": 2500, "travel_cost": 3800, "lat": 24.9617, "lon": 89.3400, "summary": "Ancient archaeological remains near Bogura."},
    {"name": "Rajshahi", "country": "Bangladesh", "scope": "local", "tags": ["history", "culture", "food", "museum", "heritage"], "daily_cost": 2600, "travel_cost": 3500, "lat": 24.3636, "lon": 88.6241, "summary": "A riverside city with museums, heritage sites, and local food."},
    {"name": "Dhaka", "country": "Bangladesh", "scope": "local", "tags": ["history", "culture", "food", "museum", "architecture"], "daily_cost": 2200, "travel_cost": 500, "lat": 23.8103, "lon": 90.4125, "summary": "Museums, historic sites, food, and city culture."},
    {"name": "Kathmandu", "country": "Nepal", "scope": "international", "tags": ["mountain", "history", "culture", "hiking", "photography"], "daily_cost": 4500, "travel_cost": 18000, "lat": 27.7172, "lon": 85.3240, "summary": "Historic squares, temples, and Himalayan culture."},
    {"name": "Thimphu", "country": "Bhutan", "scope": "international", "tags": ["mountain", "nature", "culture", "temple", "photography"], "daily_cost": 7500, "travel_cost": 35000, "lat": 27.4728, "lon": 89.6390, "summary": "A Himalayan capital with monasteries, markets, and mountain scenery."},
    {"name": "Tokyo", "country": "Japan", "scope": "international", "tags": ["city", "culture", "food", "history", "shopping", "photography"], "daily_cost": 12000, "travel_cost": 80000, "lat": 35.6762, "lon": 139.6503, "summary": "A large city with historic temples, neighborhoods, food, and modern attractions."},
    {"name": "Kolkata", "country": "India", "scope": "international", "tags": ["history", "culture", "food", "museum", "architecture"], "daily_cost": 4000, "travel_cost": 10000, "lat": 22.5726, "lon": 88.3639, "summary": "Museums, colonial-era architecture, markets, and food."},
    {"name": "Bangkok", "country": "Thailand", "scope": "international", "tags": ["food", "culture", "shopping", "temple", "city"], "daily_cost": 6500, "travel_cost": 30000, "lat": 13.7563, "lon": 100.5018, "summary": "Temples, markets, street food, and city experiences."},
]


_knowledge_base_lock = threading.Lock()
_knowledge_base_instance: LocalKnowledgeBase | None = None
_knowledge_file_signature: tuple[tuple[str, int, int], ...] | None = None


def get_knowledge_base() -> LocalKnowledgeBase:
    global _knowledge_base_instance, _knowledge_file_signature
    with _knowledge_base_lock:
        database_path, knowledge_dir = knowledge_paths()
        if _knowledge_base_instance is None:
            _knowledge_base_instance = LocalKnowledgeBase(database_path, knowledge_dir)
            _knowledge_base_instance.index_catalog(DESTINATIONS, DESTINATION_DAY_ROUTES)
        signature = tuple(
            (path.relative_to(knowledge_dir).as_posix(), path.stat().st_mtime_ns, path.stat().st_size)
            for path in sorted(knowledge_dir.rglob("*"))
            if path.is_file() and path.suffix.casefold() in {".md", ".txt"}
            and path.name.casefold() != "readme.md"
        ) if knowledge_dir.exists() else ()
        if signature != _knowledge_file_signature:
            _knowledge_base_instance.ingest_directory()
            _knowledge_file_signature = signature
        return _knowledge_base_instance


class TripRequest(BaseModel):
    budget: float = Field(gt=0, description="Total trip budget")
    currency: str = "BDT"
    duration_days: int = Field(ge=1, le=30)
    departure_city: str = Field(min_length=1, max_length=100)
    start_date: str = Field(description="Trip start date in YYYY-MM-DD format")
    travel_scope: str = "anywhere"
    interests: list[str] = Field(default_factory=list)
    destination: str | None = None
    travelers: int = Field(default=1, ge=1, le=100)
    trip_type: Literal["single", "group"] = "single"
    contribution_per_person: float | None = Field(default=None, gt=0)
    travel_style: str = "balanced"
    additional_preferences: str = ""
    feedback: str = ""
    excluded_destinations: list[str] = Field(default_factory=list)
    first_visit: bool | None = None
    visited_places: list[str] = Field(default_factory=list)

    @field_validator("start_date")
    @classmethod
    def validate_start_date(cls, value: str) -> str:
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("start_date must use YYYY-MM-DD format") from exc
        return value

    @model_validator(mode="after")
    def normalize_party_budget(self) -> "TripRequest":
        if "trip_type" not in self.model_fields_set and self.travelers > 1:
            self.trip_type = "group"
            self.contribution_per_person = self.budget / self.travelers
        if self.trip_type == "single":
            self.travelers = 1
            self.contribution_per_person = self.budget
        else:
            if self.travelers < 2:
                raise ValueError("A group tour must include at least two members.")
            if self.contribution_per_person is None:
                raise ValueError("Enter each group member's contribution.")
            self.budget = self.contribution_per_person * self.travelers
        return self


class PlanBudgetBreakdown(BaseModel):
    transport: float = Field(ge=0)
    accommodation: float = Field(ge=0)
    food: float = Field(ge=0)
    activities: float = Field(ge=0)
    local_travel: float = Field(ge=0)
    contingency: float = Field(ge=0)


class PlanEstimate(BaseModel):
    destination: str = Field(min_length=1, max_length=150)
    budget: float = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    estimated_total: float = Field(ge=0)
    budget_difference: float
    within_budget: bool
    breakdown: PlanBudgetBreakdown


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    trip: TripRequest
    history: list[dict[str, str]] = Field(default_factory=list)
    plan_estimate: PlanEstimate | None = None


def normalize_scope(scope: str) -> str:
    value = scope.lower().strip()
    if any(word in value for word in ("international", "abroad", "foreign", "outside bangladesh")):
        return "international"
    if any(word in value for word in ("local", "domestic", "bangladesh", "inside")):
        return "local"
    return "anywhere"


def choose_destination(request: TripRequest) -> dict[str, Any]:
    if request.destination and request.destination.strip():
        wanted = request.destination.strip().lower()
        if wanted in {"chittagong", "chittagong city"}:
            wanted = "chattogram"
        known = next((d for d in DESTINATIONS if wanted in d["name"].lower() or d["name"].lower() in wanted), None)
        if known:
            return known
        # Unknown destinations can still be researched; use a neutral cost estimate.
        return {
            "name": request.destination.strip(), "country": "Not confirmed", "scope": "unknown",
            "tags": [], "daily_cost": 3500, "travel_cost": 3000,
            "lat": None, "lon": None,
            "summary": "A destination supplied by the traveler; confirm local details before travelling.",
            "custom_destination": True,
        }

    ranked = rank_destinations(
        DESTINATIONS,
        budget=request.budget * get_currency_rate(request.currency)["rate"],
        days=request.duration_days,
        travelers=request.travelers, style=request.travel_style,
        interests=request.interests, departure_city=request.departure_city,
        scope=normalize_scope(request.travel_scope), limit=1, feedback=request.feedback,
        excluded_destinations=request.excluded_destinations,
    )
    return ranked[0]["destination"]


def money(value: float, currency: str) -> str:
    return f"{currency} {value:,.0f}"


def get_currency_rate(currency: str) -> dict[str, Any]:
    try:
        return currency_to_bdt_rate(currency)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=f"Currency conversion is unavailable: {error}",
        ) from error


def build_route_guidance(
    request: TripRequest, destination: dict[str, Any], estimated_total: float,
) -> dict[str, Any]:
    origin = request.departure_city.strip()
    name = destination["name"]
    is_international = destination.get("scope") == "international"
    destination_unconfirmed = destination.get("scope") == "unknown"
    if destination_unconfirmed:
        vehicle_route = {
            "best_vehicle": "Not determined until the destination is verified",
            "legs": [{
                "from": origin,
                "to": name,
                "vehicle": "Not determined",
                "note": "Confirm the destination country and available route before choosing transport.",
            }],
            "alternatives": [],
        }
        road_route = {
            "provider": "OpenStreetMap / OpenRouteService",
            "profile": "driving-car",
            "status": "destination_not_confirmed",
            "origin": None,
            "destination": None,
            "geometry": None,
            "segments": [],
            "distance_km": None,
            "duration_minutes": None,
            "route_url": None,
            "note": "The custom destination country and coordinates are not confirmed; no route or fare was estimated.",
        }
    elif is_international:
        vehicle_route = build_vehicle_route(origin, name, international=True)
        road_route = {
            "provider": "OpenStreetMap / OpenRouteService",
            "profile": "driving-car",
            "status": "not_applicable",
            "origin": None,
            "destination": None,
            "geometry": None,
            "segments": [],
            "distance_km": None,
            "duration_minutes": None,
            "route_url": None,
            "note": "Driving distance is not applicable to this international flight itinerary.",
        }
    else:
        vehicle_route = build_vehicle_route(origin, name)
        route_country = destination.get("country")
        road_route = calculate_road_route(
            origin, name, destination.get("lat"), destination.get("lon"),
            country_code="bd" if route_country == "Bangladesh" else None,
            country_name=route_country if route_country != "Not confirmed" else None,
        )
    main_transport_vehicle = select_vehicle_type(vehicle_route["best_vehicle"])
    main_cost = estimate_transport_cost(
        main_transport_vehicle,
        road_route["distance_km"],
        request.travelers,
        return_trip=True,
    )
    route_segments = []
    if road_route["segments"]:
        segment = road_route["segments"][0]
        route_segments.append({
            **segment,
            "vehicle": vehicle_route["best_vehicle"],
            "fare_vehicle": main_cost["vehicle"],
            "fare": main_cost,
            "route_type": "intercity",
            "geometry": road_route["geometry"],
        })

    if destination_unconfirmed:
        recommended = (
            "Verify the destination's country and location first. Then confirm the route, "
            "transport mode, and current fares with reliable local operators."
        )
        modes = [{
            "name": "Transport not determined",
            "guidance": "No route or fare is estimated until the destination is confirmed.",
        }]
    elif is_international:
        recommended = "Compare flights from your nearest airport; include baggage, airport transfers, and entry requirements in the cost."
        modes = [{
            "name": "Flight",
            "guidance": "Compare current airline fares and schedules for your dates; this is a long-distance international route.",
        }]
    elif (
        request.travel_style == "budget"
        or estimated_total > request.budget * get_currency_rate(request.currency)["rate"] * 0.9
    ):
        recommended = f"Budget pick: {vehicle_route['best_vehicle']}. Prefer shared public transport where available and confirm the complete route and fare."
        modes = [
            {"name": vehicle_route["best_vehicle"], "guidance": "Recommended starting choice for this route; verify service and price for your dates."},
            *[{"name": alternative, "guidance": "Compare its total fare and availability before choosing."} for alternative in vehicle_route["alternatives"]],
        ]
    else:
        recommended = f"Suggested vehicles: {vehicle_route['best_vehicle']}. Compare the route and current fares before booking."
        modes = [
            {"name": vehicle_route["best_vehicle"], "guidance": "Recommended starting choice for this route; verify service and price for your dates."},
            *[{"name": alternative, "guidance": "Compare its total fare and availability before choosing."} for alternative in vehicle_route["alternatives"]],
        ]

    return {
        "origin": origin,
        "destination": name,
        "recommended": recommended,
        "best_vehicle": vehicle_route["best_vehicle"],
        "legs": vehicle_route["legs"],
        "modes": modes,
        "transport_estimate_vehicle": vehicle_route["best_vehicle"],
        "estimate_currency": "BDT",
        "travelers": request.travelers,
        "road_route": road_route,
        "transport_segments": route_segments,
        "transport_estimate": {
            "minimum": main_cost["minimum"],
            "maximum": main_cost["maximum"],
            "currency": "BDT",
            "status": main_cost["status"],
            "basis": main_cost["basis"],
        },
        "route_url": road_route["route_url"] or (
            "https://www.openstreetmap.org/search?" + urlencode({"query": name})
        ),
        "route_label": "View OpenStreetMap route" if road_route["route_url"] else "Find destination on OpenStreetMap",
        "note": (
            f"Return transport for the suggested vehicle combination "
            f"({vehicle_route['best_vehicle']}) is an estimated fare range, not a live quote. "
            "The route fare is estimated from road distance and the selected local fare range. "
            "Boat and other non-road legs are not included. Confirm current prices, "
            "timetables, and service availability for your travel dates. "
            + road_route["note"]
        ),
    }


def finalize_transport_estimates(
    route_guidance: dict[str, Any], daily_plan: list[dict[str, Any]],
    destination: dict[str, Any], travelers: int,
) -> None:
    local_segments, local_complete = add_local_transport_estimates(
        daily_plan, destination, travelers,
    )
    route_guidance["transport_segments"].extend(local_segments)
    local_fares = [
        segment["fare"] for segment in local_segments
        if segment["fare"]["status"] == "estimated_range"
    ]
    local_estimate = {
        "minimum": sum(fare["minimum"] for fare in local_fares),
        "maximum": sum(fare["maximum"] for fare in local_fares),
        "currency": "BDT",
        "fare_data_status": "unverified_planning_ranges",
        "status": "estimated_range" if local_complete and local_segments else (
            "partial" if local_fares else "unavailable"
        ),
    }
    route_guidance["local_transport_estimate"] = local_estimate

    all_fares = [
        segment["fare"] for segment in route_guidance["transport_segments"]
        if segment["fare"]["status"] == "estimated_range"
    ]
    vehicle_text = route_guidance["best_vehicle"].casefold()
    has_unpriced_vehicle = any(term in vehicle_text for term in ("boat", "ferry", "flight"))
    main_complete = (
        route_guidance["transport_estimate"]["status"] == "estimated_range"
        and not has_unpriced_vehicle
    )
    complete = main_complete and local_complete
    route_guidance["total_transport_estimate"] = {
        "minimum": sum(fare["minimum"] for fare in all_fares),
        "maximum": sum(fare["maximum"] for fare in all_fares),
        "currency": "BDT",
        "fare_data_status": "unverified_planning_ranges",
        "status": "estimated_range" if complete else (
            "partial" if all_fares else "unavailable"
        ),
        "note": (
            "Total covers the estimated intercity return journey and routed local sightseeing segments. "
            "Ranges are planning estimates, not verified or live fares."
            if complete else
            "Partial estimate: one or more journey segments could not be routed, priced, or cover non-road transport. "
            "Unpriced segments are not included in this subtotal."
        ),
    }


def add_local_transport_estimates(
    daily_plan: list[dict[str, Any]], destination: dict[str, Any],
    travelers: int,
) -> tuple[list[dict[str, Any]], bool]:
    """Route each day's attraction loop and estimate each road segment."""
    all_segments: list[dict[str, Any]] = []
    complete = bool(daily_plan)
    for day in daily_plan:
        stop_names = [
            stop["name"] for stop in day.get("stops", [])
            if stop.get("name") and stop["name"] != "Choose a new attraction or take a rest day"
        ]
        if not stop_names:
            day["transport_segments"] = []
            complete = False
            continue

        route = calculate_road_route(
            destination["name"],
            destination["name"],
            destination.get("lat"),
            destination.get("lon"),
            waypoints=stop_names,
            country_code="bd" if destination.get("country") == "Bangladesh" else None,
            country_name=destination.get("country"),
        )
        day["road_route"] = route
        local_guidance = day.get("transport", {}).get("vehicle", "Local auto-rickshaw")
        vehicle_type = select_vehicle_type(local_guidance, local=True)
        day_segments = []
        for leg_index, leg in enumerate(route["segments"]):
            fare = estimate_transport_cost(
                vehicle_type, leg["distance_km"], travelers,
            )
            segment = {
                **leg,
                "vehicle": local_guidance,
                "fare_vehicle": fare["vehicle"],
                "fare": fare,
                "route_type": "local",
                "geometry": route["geometry"],
                "route_waypoints": route["waypoints"] if leg_index == 0 else [],
                "day": day.get("day"),
            }
            day_segments.append(segment)
            all_segments.append(segment)
            if fare["status"] != "estimated_range":
                complete = False
        if route["status"] != "ready":
            complete = False
            if not day_segments:
                day_segments.append({
                    "from": destination["name"],
                    "to": stop_names[0],
                    "vehicle": local_guidance,
                    "fare_vehicle": estimate_transport_cost(vehicle_type, None)["vehicle"],
                    "fare": estimate_transport_cost(
                        vehicle_type, None, travelers,
                    ),
                    "distance_km": None,
                    "duration_minutes": None,
                    "geometry": None,
                    "route_type": "local",
                    "day": day.get("day"),
                    "note": route["note"],
                })
                all_segments.extend(day_segments)
        day["transport_segments"] = day_segments
    return all_segments, complete


def build_itinerary(
    request: TripRequest, destination: dict[str, Any],
    research: dict[str, Any] | None, weather: dict[str, Any] | None,
    daily_plan: list[dict[str, Any]] | None = None,
    route_guidance: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    days = request.duration_days
    people = request.travelers
    currency = request.currency.upper().strip() or "BDT"
    currency_rate = get_currency_rate(currency)
    rate = float(currency_rate["rate"])
    budget_bdt = request.budget * rate
    style = request.travel_style.lower()
    daily_base = float(destination["daily_cost"])
    if any(word in style for word in ("budget", "cheap", "economy")):
        daily_base *= 0.75
    elif any(word in style for word in ("comfort", "luxury", "premium")):
        daily_base *= 1.6

    transport = float(destination["travel_cost"]) * people
    accommodation = daily_base * 0.35 * days * people
    food = daily_base * 0.30 * days * people
    food_per_person_day = food / (days * people)
    activities = daily_base * 0.20 * days * people
    local_travel = daily_base * 0.10 * days * people
    transport_estimate = (route_guidance or {}).get("transport_estimate", {})
    local_estimate = (route_guidance or {}).get("local_transport_estimate", {})
    if transport_estimate.get("status") == "estimated_range":
        transport = (
            transport_estimate["minimum"] + transport_estimate["maximum"]
        ) / 2
    if local_estimate.get("status") == "estimated_range":
        local_travel = (
            local_estimate["minimum"] + local_estimate["maximum"]
        ) / 2
    contingency = daily_base * 0.05 * days * people
    estimated_total_bdt = transport + accommodation + food + activities + local_travel + contingency
    budget_ok = estimated_total_bdt <= budget_bdt
    transport /= rate
    accommodation /= rate
    food /= rate
    food_per_person_day /= rate
    activities /= rate
    local_travel /= rate
    contingency /= rate
    estimated_total = estimated_total_bdt / rate

    interests = [x.strip() for x in request.interests if x.strip()]
    tags = {tag.lower() for tag in destination.get("tags", [])}
    suggestions: list[str] = []
    for interest in interests:
        if interest.lower() in tags or any(interest.lower() in tag or tag in interest.lower() for tag in tags):
            suggestions.append(f"Choose a {interest.lower()}-focused activity available in {destination['name']}.")
    if not suggestions:
        suggestions = [
            f"Explore a well-known attraction in {destination['name']}.",
            "Try a local meal and leave time for rest.",
        ]

    start = date.fromisoformat(request.start_date)
    vehicle_guidance = route_guidance or build_route_guidance(
        request, destination, estimated_total_bdt,
    )
    lines = [
        f"# Your TripMate plan: {destination['name']}",
        "",
        "## Your trip at a glance",
        f"- Departure city: {request.departure_city}",
        f"- Destination: {destination['name']} ({destination['country']})",
        f"- Dates: {start.isoformat()} to {(start + timedelta(days=days - 1)).isoformat()} ({days} day(s))",
        f"- Tour type: {'Group tour' if request.trip_type == 'group' else 'Single tour'}",
        f"- Travelers: {people}",
        f"- Budget: {money(request.budget, currency)} total",
        f"- Travel style: {request.travel_style}",
        f"- Interests: {', '.join(interests) if interests else 'General sightseeing and relaxation'}",
        "",
        "## Why this destination?",
        destination["summary"],
    ]
    if research:
        lines.extend(["", "## Internet research", research["summary"], f"Source: {research['url']} (Wikipedia)"])
    else:
        lines.extend(["", "## Internet research", "Live destination research could not be retrieved during this request. The plan below uses TripMate's starter destination data; check local details before travelling."])

    main_estimate = vehicle_guidance.get("transport_estimate", {})
    local_estimate = vehicle_guidance.get("local_transport_estimate", {})
    total_transport = vehicle_guidance.get("total_transport_estimate", {})
    lines.extend([
        "",
        "## Getting there",
        f"**{request.departure_city} -> {destination['name']}**",
        f"- Suggested travel: {vehicle_guidance['best_vehicle']}",
    ])
    if main_estimate.get("status") == "estimated_range":
        lines.append(
            f"- Intercity return: BDT {main_estimate['minimum']:,.0f}-{main_estimate['maximum']:,.0f}"
        )
    else:
        lines.append("- Intercity fare: confirm a current route and fare with the operator")
    if local_estimate.get("status") != "unavailable":
        lines.append(
            f"- Local sightseeing transport: BDT {local_estimate['minimum']:,.0f}-{local_estimate['maximum']:,.0f}"
        )
    if total_transport.get("status") in {"estimated_range", "partial"}:
        partial_label = " (partial estimate)" if total_transport["status"] == "partial" else ""
        lines.append(
            f"- **Estimated transport total{partial_label}: BDT "
            f"{total_transport['minimum']:,.0f}-{total_transport['maximum']:,.0f}**"
        )
    lines.append("- Fare ranges are planning estimates, not live quotes. Unpriced legs are excluded.")
    if request.trip_type == "group":
        lines.append(
            f"- Group contribution: {money(float(request.contribution_per_person or 0), currency)} per member × {people} members."
        )

    lines.extend(["", "## Day-by-day itinerary"])
    for index in range(days):
        current_day = start + timedelta(days=index)
        lines.extend(["", f"### Day {index + 1} — {current_day.isoformat()}"])
        route = daily_plan[index] if daily_plan and index < len(daily_plan) else None
        if route:
            lines.append(f"- Suggested area: {route['area']}")
            daily_transport = route.get("transport")
            if daily_transport:
                lines.append(f"- How to get around today: {daily_transport['vehicle']}. {daily_transport['guidance']}")
            for stop in route["stops"]:
                lines.append(f"- Visit: {stop['name']}")
            for segment in route.get("transport_segments", []):
                fare = segment["fare"]
                cost = (
                    f"BDT {fare['minimum']:,.0f}–{fare['maximum']:,.0f}"
                    if fare["status"] == "estimated_range"
                    else "fare range unavailable"
                )
                lines.append(
                    f"- Route: {segment['from']} to {segment['to']} — "
                    f"{segment['distance_km'] if segment['distance_km'] is not None else 'distance unavailable'}"
                    f"{' km' if segment['distance_km'] is not None else ''}, "
                    f"{segment['duration_minutes'] if segment['duration_minutes'] is not None else 'time unavailable'}"
                    f"{' min' if segment['duration_minutes'] is not None else ''}, "
                    f"{segment['fare_vehicle']}: {cost}."
                )
            lines.append("- Check current opening hours and travel conditions before setting out.")
        elif index == 0:
            lines.append(f"- Morning: Travel from {request.departure_city} toward {destination['name']}; confirm transport schedules before departure.")
            lines.append("- Afternoon: Check in or leave luggage, then visit a nearby attraction.")
            lines.append("- Evening: Have a local dinner and take a relaxed walk in a suitable public area.")
        elif index == days - 1:
            lines.append("- Morning: Visit one main attraction or enjoy a short activity based on your interests.")
            lines.append("- Afternoon: Have lunch, collect belongings, and begin the return journey if appropriate.")
            lines.append("- Evening: Return home or use this time for travel, depending on your transport schedule.")
        else:
            lines.append(f"- Morning: Start with a major attraction or a {interests[0].lower() + '-focused activity' if interests else 'guided local sightseeing activity'}.")
            lines.append("- Afternoon: Explore a second nearby attraction; group locations geographically to reduce travel time.")
            lines.append("- Evening: Try local food and keep some free time for rest or an optional activity.")
        if index < len(suggestions):
            lines.append(f"- Personalization: {suggestions[index]}")

    lines.extend([
        "", "## Estimated budget breakdown",
        f"- Transport to/from destination (budget estimate): {money(transport, currency)}",
        f"- Accommodation: {money(accommodation, currency)}",
        f"- Food planning estimate: {money(food, currency)} (about {money(food_per_person_day, currency)} per traveler per day; not a live menu price)",
        f"- Activities: {money(activities, currency)}",
        f"- Local travel: {money(local_travel, currency)}",
        f"- Contingency: {money(contingency, currency)}",
        f"- **Estimated total: {money(estimated_total, currency)}**",
        f"- **Remaining budget: {money(request.budget - estimated_total, currency) if budget_ok else 'Over budget by ' + money(estimated_total - request.budget, currency)}**",
    ])
    if currency != "BDT":
        lines.append(
            f"- Catalog budget conversion: 1 {currency} = {rate:,.4f} BDT "
            f"(ExchangeRate-API rate updated {currency_rate['date']}); transport fare details remain in BDT."
        )
    if not budget_ok:
        lines.extend([
            "",
            f"Your budget is too low for this trip. Please increase your budget by at least {money(estimated_total - request.budget, currency)} based on this estimate.",
            "You can also choose a closer destination or fewer days and compare current lower-cost transport and food options.",
        ])
    else:
        lines.extend(["", "The rough estimate is within your stated budget. Keep a reserve and confirm actual transport and accommodation prices before booking."])

    if weather:
        lines.extend(["", "## Weather forecast (live source)", f"Forecast source: {weather['source']}. This forecast may change."])
        for i, day_text in enumerate(weather.get("forecast_days", [])):
            try:
                high = weather["max_temp_c"][i]
                low = weather["min_temp_c"][i]
                rain = weather["precipitation_probability_percent"][i]
                lines.append(f"- {day_text}: high {high}°C, low {low}°C, precipitation chance {rain}%.")
            except (IndexError, TypeError):
                continue
    else:
        lines.extend(["", "## Weather note", "A forecast was not available for the requested dates. Check a current forecast closer to departure."])

    lines.extend([
        "", "## Practical tips",
        "- Confirm transport times, accommodation rates, attraction opening hours, and any entry requirements before paying.",
        "- Carry identification, keep emergency contacts handy, and check local safety advice.",
        "- The budget is a planning estimate, not a live quote or booking confirmation.",
        "- Food and transport amounts are approximate catalog assumptions; compare current local prices and fares before travelling.",
    ])
    if request.additional_preferences.strip():
        lines.extend(["", "## Additional preference", request.additional_preferences.strip()])

    details = {
        "destination": destination["name"], "country": destination["country"],
        "estimated_total": round(estimated_total, 2), "currency": currency,
        "budget_breakdown": {
            "transport": round(transport, 2),
            "accommodation": round(accommodation, 2),
            "food": round(food, 2),
            "activities": round(activities, 2),
            "local_travel": round(local_travel, 2),
            "contingency": round(contingency, 2),
        },
        "food_per_person_per_day": round(food_per_person_day, 2),
        "within_budget": budget_ok, "budget_difference": round(request.budget - estimated_total, 2),
        "research_source": research["url"] if research else None,
        "weather_source": weather["source"] if weather else None,
        "trip_type": request.trip_type,
        "travelers": people,
        "contribution_per_person": round(float(request.contribution_per_person or request.budget), 2),
        "currency_conversion": currency_rate,
    }
    return "\n".join(lines), details


@app.get("/")
def home():
    return {
        "message": "TripMate travel agent is running.",
        "ai_model": model_status(),
        "knowledge_base": "local SQLite FTS5",
        "planning_engine": "TripMate Python tools and local RAG",
        "internet_research": [
            "DuckDuckGo web search and HTTPS webpage extraction",
            "Wikipedia public API",
            "Open-Meteo forecast API",
            "ExchangeRate-API Open Access",
        ],
    }


@app.get("/health")
def health():
    knowledge_base = get_knowledge_base()
    return {
        "status": "healthy",
        "ai_model": model_status(),
        "knowledge_base": {
            "engine": "SQLite FTS5",
            "documents": knowledge_base.document_count(),
        },
    }


@app.get("/destinations")
def list_destinations():
    return [{"name": d["name"], "country": d["country"], "scope": d["scope"], "tags": d["tags"]} for d in DESTINATIONS]


def discover_destinations(request: TripRequest, candidate_pool: list[dict[str, Any]] | None = None) -> dict[str, list[dict[str, Any]]]:
    pool = candidate_pool if candidate_pool is not None else DESTINATIONS
    rate = get_currency_rate(request.currency)["rate"]
    ranked = rank_destinations(
        pool, budget=request.budget * rate, days=request.duration_days,
        travelers=request.travelers, style=request.travel_style,
        interests=request.interests, departure_city=request.departure_city,
        scope="anywhere" if candidate_pool is not None else normalize_scope(request.travel_scope), limit=len(pool),
        feedback=request.feedback, excluded_destinations=request.excluded_destinations,
    )
    groups = split_recommendations(ranked, affordable_count=3, stretch_count=2)
    cards: dict[str, list[dict[str, Any]]] = {"within_budget": [], "stretch": []}
    for group_name, items in groups.items():
        for item in items:
            place = item["destination"]
            research = wikipedia_research(place["name"])
            cards[group_name].append({
                "name": place["name"], "country": place["country"],
                "summary": research["summary"] if research else place["summary"],
                "image_url": research.get("image_url") if research else None,
                "source": {"name": research["source"], "url": research["url"]} if research else None,
                "estimated_total": round(item["estimated_total"] / rate),
                "currency": request.currency.upper(),
                "within_budget": item["within_budget"], "matched_interests": item["matched_interests"],
                "reason": f"Estimated cost is {'within' if item['within_budget'] else 'above'} your budget.",
            })
    return cards


@app.post("/recommendations")
def recommend_trips(request: TripRequest):
    groups = discover_destinations(request)
    no_fits = not groups["within_budget"]
    budget_warning = (
        "Your budget is too low for the trips currently available. Please increase your budget or reduce the trip duration."
        if no_fits else None
    )
    return {
        "message": budget_warning or "Choose an option to see its detailed itinerary.",
        "budget_warning": budget_warning,
        "trip": request.model_dump(),
        "recommendations": groups,
        "live_data_used": any(item["source"] for values in groups.values() for item in values),
        "note": ("No destination estimate fits this budget; the displayed places are stretch options. " if no_fits else "") + "Costs are planning estimates, not live travel quotes. Stretch options are shown separately so you can compare a higher budget choice.",
    }


def _suggested_questions_for_chat(
    message: str, reply: str, history: list[dict[str, str]] | None = None,
) -> list[str]:
    """Suggest next questions from the active attraction or subject."""
    context = " ".join([
        message,
        reply,
        *[
            str(item.get("content", "")) for item in (history or [])[-6:]
            if isinstance(item.get("content"), str)
        ],
    ]).casefold()
    if "goaldi" in context:
        return [
            "Who built Goaldi Mosque and what does its inscription say?",
            "What is special about Goaldi Mosque’s dome and corner towers?",
            "What are the three mihrabs in Goaldi Mosque?",
            "When was Goaldi Mosque restored, and what was repaired?",
            "How can I visit Goaldi Mosque from Dhaka?",
        ]
    if any(term in context for term in ("mosque", "temple", "palace", "fort", "museum", "monument")):
        return [
            "Who built this historic attraction and when?",
            "What architectural details should I look for?",
            "What is known about its restoration and preservation?",
            "What other heritage sites are nearby?",
            "How can I get there from Dhaka?",
        ]
    if any(term in context for term in ("architecture", "architectural", "history", "heritage", "historic")):
        return [
            "Who built this attraction and when?",
            "Which architectural details are most distinctive?",
            "What role did it play in local history?",
            "What other heritage places are nearby?",
            "How can I plan a visit?",
        ]
    return [
        "What are the top attractions there?",
        "How can I get there from Dhaka?",
        "What is the best time to visit?",
        "What local food should I try?",
    ]


@app.post("/chat")
def chat_with_tripmate(request: ChatRequest):
    message = request.message.strip()
    trip = request.trip.model_copy(deep=True)
    message_lower = message.casefold().replace("’", "'")
    question_type = classify_travel_question(message)
    information_question = (
        question_type is None and is_destination_information_question(message)
    )
    if question_type is None and not information_question:
        previous_question = next(
            (
                item.get("content", "")
                for item in reversed(request.history)
                if item.get("role") == "user" and isinstance(item.get("content"), str)
            ),
            "",
        )
        follow_up = bool(re.search(
            r"\b(?:there|that|it|what about|how about|how much|and the|also|how is)\b",
            message_lower,
        )) or any(
            marker in message_lower
            for marker in ("ওখানে", "সেখানে", "সেটা", "এটা", "আর", "তাহলে", "কত")
        )
        if follow_up and previous_question:
            question_type = classify_travel_question(previous_question)
    explicit_places = [
        place for place in DESTINATIONS
        if place["name"].casefold() in message_lower
        or (
            destination_alias(place["name"])
            and destination_alias(place["name"]) in message_lower
        )
    ]
    country_aliases = {
        "nepal": "Nepal", "bhutan": "Bhutan", "japan": "Japan", "india": "India",
        "thailand": "Thailand", "bangladesh": "Bangladesh",
    }
    requested_country = next((country for alias, country in country_aliases.items() if alias in message_lower), None)
    if not explicit_places and requested_country and not information_question:
        explicit_places = [place for place in DESTINATIONS if place["country"].casefold() == requested_country.casefold()]
    mentions_past_visit = any(phrase in message_lower for phrase in ("visited", "been to", "already been", "i saw", "i have seen", "already saw"))
    if mentions_past_visit:
        mentioned_places = {
            place
            for routes in DESTINATION_DAY_ROUTES.values()
            for route in routes
            for place in route["places"]
            if place.casefold() in message_lower
        }
        trip.visited_places = list(dict.fromkeys([*trip.visited_places, *sorted(mentioned_places)]))
    keyword_groups = {
        "mountain": ("mountain", "mountains", "hill", "hills", "trek", "hiking", "পাহাড়", "পাহাড়", "হাইকিং"),
        "beach": ("beach", "beaches", "sea", "seas", "ocean", "island", "islands", "coast", "সমুদ্র", "সৈকত", "দ্বীপ", "উপকূল"),
        "nature": ("nature", "forest", "wildlife", "green", "waterfall", "প্রকৃতি", "বন", "বন্যপ্রাণী", "ঝরনা"),
        "history": ("history", "historic", "heritage", "archaeology", "ইতিহাস", "ঐতিহাসিক", "ঐতিহ্য"),
        "culture": ("culture", "cultural", "museum", "সংস্কৃতি", "জাদুঘর"),
        "photography": ("photo", "photography", "scenic", "scenery", "ছবি", "ফটোগ্রাফি", "দৃশ্য"),
        "tea": ("tea", "tea garden", "চা", "চা বাগান"),
        "food": ("food", "foodie", "cuisine", "খাবার", "রান্না"),
        "lake": ("lake", "lakes", "boat", "হ্রদ", "লেক", "নৌকা"),
    }
    preference_intent = bool(re.search(
        r"\b(?:i (?:want|like|love|prefer)|looking for|interested in|show me|find(?: me)?|"
        r"recommend|search for|cheaper|lower cost|less expensive|low cost|budget)\b|চাই|পছন্দ|খুঁজছি|দেখাও|সাজেস্ট",
        message_lower,
    ))
    additions = [
        tag for tag, terms in keyword_groups.items()
        if preference_intent and any(
            (re.search(rf"\b{re.escape(term)}\b", message_lower) if term.isascii() else term in message_lower)
            for term in terms
        )
    ]
    trip.interests = list(dict.fromkeys([*trip.interests, *additions]))
    if preference_intent:
        trip.feedback = "; ".join(filter(None, (trip.feedback.strip(), message.strip())))[:300]
    should_discover = bool(
        not information_question
        and (preference_intent or explicit_places or requested_country or mentions_past_visit)
    )
    groups = {"within_budget": [], "stretch": []}
    if should_discover and not question_type:
        groups = discover_destinations(
            trip, explicit_places if explicit_places else None,
        )
    matches = [item["name"] for group in groups.values() for item in group]
    named_destination = next(
        (
            place for place in sorted(DESTINATIONS, key=lambda item: len(item["name"]), reverse=True)
            if place["name"].casefold() in message_lower
            or (
                destination_alias(place["name"])
                and destination_alias(place["name"]) in message_lower
            )
        ),
        None,
    )
    if named_destination is None and any(alias in message_lower for alias in ("chittagong", "chittagong city")):
        named_destination = next((place for place in DESTINATIONS if place["name"] == "Chattogram"), None)
    if named_destination is None and explicit_places and len(explicit_places) == 1:
        named_destination = explicit_places[0]
    focus = named_destination
    if focus is None and trip.destination:
        focus = next((place for place in DESTINATIONS if place["name"].casefold() == trip.destination.casefold()), None)
    if focus is None and question_type == "transport":
        route_match = re.search(
            r"\bfrom\s+.+?\s+to\s+(.+?)(?:\s+(?:by|using)\s+"
            r"(?:bus|train|cng|auto[- ]?rickshaw|rickshaw|ride[- ]?sharing))?[?.!]*$",
            message,
            re.IGNORECASE,
        )
        if route_match:
            focus = {
                "name": route_match.group(1).strip(" ,?.!"),
                "scope": "local",
            }
    answer_media: list[dict[str, str]] = []
    answer_sources: list[dict[str, str]] = []
    if question_type and focus:
        trip.destination = focus["name"]
        hotel_options = []
        if question_type == "hotel":
            _, hotel_options = destination_days(
                focus["name"], trip.duration_days, trip.budget, trip.currency,
                trip.visited_places, fetch_images=False,
            )
        routes = DESTINATION_DAY_ROUTES.get(focus["name"], [])
        reply, answer_sources = answer_travel_question(
            question_type, focus, trip.model_dump(), routes, hotel_options,
            message=message,
            plan_estimate=(
                request.plan_estimate.model_dump()
                if request.plan_estimate
                and request.plan_estimate.destination.casefold() == focus["name"].casefold()
                and request.plan_estimate.currency.casefold() == trip.currency.casefold()
                and abs(request.plan_estimate.budget - trip.budget) < 0.01
                else None
            ),
        )
        if question_type == "rain":
            live_weather = get_weather(
                focus, date.fromisoformat(trip.start_date), trip.duration_days
            )
            if live_weather:
                rain_values = live_weather.get("precipitation_probability_percent", [])
                if rain_values:
                    max_rain = max(value for value in rain_values if isinstance(value, (int, float))) if any(isinstance(value, (int, float)) for value in rain_values) else None
                    if max_rain is not None:
                        reply += f" The available Open-Meteo forecast for your dates shows a maximum daily precipitation probability of {max_rain}% across {len(rain_values)} forecast day(s); forecasts can change."
                        answer_sources.append({"name": "Open-Meteo forecast", "url": "https://open-meteo.com/"})
        research = None if question_type in {"budget", "cost_estimate"} else wikipedia_research(focus["name"])
        photo = None
        if question_type == "activities" and routes and routes[0]["places"]:
            photo = wikipedia_page_research(routes[0]["places"][0])
        photo = photo or research
        if photo and photo.get("image_url"):
            answer_media.append({
                "image_url": photo["image_url"],
                "alt": f"{photo['title']} in {focus['name']}",
                "source_name": photo["source"],
                "source_url": photo["url"],
            })
            answer_sources.append({"name": photo["source"], "url": photo["url"]})
    elif question_type:
        reply = "Which destination are you asking about? Use “Ask about this place” on a destination card, or mention its name in your question. The cards include destination pictures."
    elif requested_country and explicit_places and not information_question:
        options = [item for group in groups.values() for item in group]
        if options:
            selected = options[0]
            gap = selected["estimated_total"] - trip.budget
            reply = (
                f"Yes—{requested_country} is in TripMate’s limited international catalog through "
                f"{selected['name']}. For {trip.duration_days} days, the rough estimate is "
                f"{selected['currency']} {selected['estimated_total']:,} for your group, "
                f"about {selected['currency']} {gap:,} above your {selected['currency']} {trip.budget:,.0f} budget. "
                "I’ve shown it in the stretch options. This is a planning estimate, not a current fare or booking quote."
            ) if not selected["within_budget"] else (
                f"Yes—{requested_country} is in TripMate’s limited international catalog through {selected['name']}. "
                f"The rough estimate is {selected['currency']} {selected['estimated_total']:,}, within your stated budget. "
                "I’ve shown it as an option; confirm current travel costs and entry requirements before booking."
            )
        else:
            reply = f"{requested_country} is not in the current destination catalog yet. Try Nepal, Bhutan, Japan, India, or Thailand."
    elif additions:
        reply = f"I’ll look for Bangladesh destinations related to {', '.join(additions)} and compare them with your budget. Choose a result to see its day-by-day plan."
    elif mentions_past_visit and trip.visited_places:
        reply = f"I’ve marked {', '.join(sorted(mentioned_places))} as already visited. Choose a destination and I’ll avoid those stops in the itinerary."
    elif information_question:
        reply = ""
    elif explicit_places and matches:
        selected = next(
            (
                option
                for group in groups.values()
                for option in group
                if option["name"] == explicit_places[0]["name"]
            ),
            None,
        )
        if selected:
            summary_words = selected["summary"].split()
            summary = " ".join(summary_words[:45])
            if len(summary_words) > 45:
                summary = summary.rstrip(".,;:") + "…"
            reply = (
                f"{selected['name']}: {summary} "
                "Ask me about attractions, hotels, routes, or a day-by-day plan."
            )
            if selected.get("source"):
                answer_sources.append(selected["source"])
            if selected.get("image_url"):
                answer_media.append({
                    "image_url": selected["image_url"],
                    "alt": f"Photo of {selected['name']}",
                    "source_name": selected.get("source", {}).get("name", "Source"),
                    "source_url": selected.get("source", {}).get("url", ""),
                })
        else:
            reply = f"I couldn’t retrieve a reliable overview of {explicit_places[0]['name']} just now. Ask me about a specific attraction or trip detail."
    elif matches:
        reply = "I’ve refreshed the destination ideas using your message and trip details. Tell me what kind of place you want, or choose a destination to build its itinerary."
    else:
        reply = "I couldn’t find a matching destination in the current Bangladesh catalog. Try a preference such as mountains, beaches, nature, history, or tea gardens."
    deterministic_reply = bool(
        question_type or additions or mentions_past_visit
        or (not information_question and requested_country and explicit_places)
        or (not information_question and explicit_places and matches)
    )
    if deterministic_reply:
        local_result = {"reply": reply, "sources": [], "status": "tripmate_tools"}
    else:
        local_result = generate_reply(
            message,
            trip.model_dump(),
            groups,
            request.history,
            knowledge_base=get_knowledge_base(),
            fallback_reply=None if information_question else reply,
        )
    reply = local_result["reply"]
    answer_sources.extend(local_result["sources"])
    agent_status = local_result["status"]
    budget_warning = None
    if not groups["within_budget"]:
        closest = min(
            (item for item in groups["stretch"]),
            key=lambda item: item["estimated_total"],
            default=None,
        )
        if closest:
            increase = max(0, closest["estimated_total"] - trip.budget)
            budget_warning = (
                f"Your budget is too low for the available trip options. Please increase your budget by at least "
                f"{trip.currency.upper()} {increase:,.0f}, or choose fewer days or a closer destination."
            )
    return {
        "reply": reply,
        "budget_warning": budget_warning,
        "trip": trip.model_dump(),
        "recommendations": groups,
        "answer_media": answer_media,
        "answer_sources": answer_sources,
        "suggested_questions": _suggested_questions_for_chat(
            message, reply, request.history,
        ),
        "agent_status": agent_status,
    }


@app.post("/plan")
def plan_trip(request: TripRequest):
    try:
        rate = get_currency_rate(request.currency)["rate"]
        budget_bdt = request.budget * rate
        ranked = []
        if not (request.destination and request.destination.strip()):
            ranked = rank_destinations(
                DESTINATIONS, budget=budget_bdt, days=request.duration_days,
                travelers=request.travelers, style=request.travel_style,
                interests=request.interests, departure_city=request.departure_city,
                scope=normalize_scope(request.travel_scope), limit=3,
                feedback=request.feedback, excluded_destinations=request.excluded_destinations,
            )
            if not ranked:
                raise HTTPException(status_code=422, detail="No more matching destinations are available. Change your preferences or clear the exclusions to try again.")
        destination = ranked[0]["destination"] if ranked else choose_destination(request)
        if not ranked:
            estimate = estimate_trip_cost(destination, request.duration_days, request.travelers, request.travel_style)
            ranked = [{
                "destination": destination, "estimated_total": round(estimate),
                "within_budget": estimate <= budget_bdt, "matched_interests": [],
            }]
        start = date.fromisoformat(request.start_date)
        # Independent public APIs: failures are handled gracefully and do not block planning.
        research = wikipedia_research(destination["name"])
        recommendations = []
        for item in ranked:
            place = item["destination"]
            details = research if place["name"] == destination["name"] else wikipedia_research(place["name"])
            tags = ", ".join(item["matched_interests"]) or "general sightseeing"
            recommendations.append({
                "name": place["name"], "country": place["country"],
                "summary": details["summary"] if details else place["summary"],
                "image_url": details.get("image_url") if details else None,
                "source": {"name": details["source"], "url": details["url"]} if details else None,
                "estimated_total": round(item["estimated_total"] / rate),
                "currency": request.currency.upper(),
                "within_budget": item["within_budget"], "matched_interests": item["matched_interests"],
                "reason": f"Fits your interest in {tags}; estimated cost is {'within' if item['within_budget'] else 'above'} your budget.",
            })
        weather = get_weather(destination, start, request.duration_days)
        daily_plan, hotel_options = destination_days(
            destination["name"], request.duration_days, request.budget, request.currency,
            request.visited_places,
        )
        estimated_total = estimate_trip_cost(
            destination, request.duration_days, request.travelers, request.travel_style,
        )
        route_guidance = build_route_guidance(request, destination, estimated_total)
        finalize_transport_estimates(
            route_guidance, daily_plan, destination, request.travelers,
        )
        itinerary, details = build_itinerary(
            request, destination, research, weather, daily_plan, route_guidance,
        )
        for option in recommendations:
            if option["name"] == destination["name"]:
                option["estimated_total"] = round(details["estimated_total"])
                option["within_budget"] = details["within_budget"]
                break
        details["hotel_nightly_budget_target"] = round(request.budget * 0.35 / request.duration_days) if hotel_options else None
        sources = [
            {"name": item["source"]["name"], "url": item["source"]["url"], "type": "destination summary"}
            for item in recommendations if item["source"]
        ]
        if research and not any(source["url"] == research["url"] for source in sources):
            sources.append({"name": "Wikipedia", "url": research["url"], "type": "destination summary"})
        if weather:
            sources.append({"name": "Open-Meteo", "url": "https://open-meteo.com/", "type": "weather forecast"})
        road_route = route_guidance["road_route"]
        if road_route["origin"]:
            sources.append({
                "name": "OpenStreetMap",
                "url": "https://www.openstreetmap.org/copyright",
                "type": "map data",
            })
        if road_route["status"] == "ready":
            sources.append({
                "name": road_route["provider"].split("/")[-1].strip(),
                "url": (
                    "https://project-osrm.org/"
                    if road_route["provider"].endswith("OSRM")
                    else "https://openrouteservice.org/"
                ),
                "type": "driving route",
            })
        for day in daily_plan:
            for stop in day["stops"]:
                if stop["source"] and not any(source["url"] == stop["source"]["url"] for source in sources):
                    sources.append({"name": stop["source"]["name"], "url": stop["source"]["url"], "type": "attraction summary and image"})
        budget_warning = None
        if not details["within_budget"]:
            budget_warning = (
                f"Your budget is too low for this trip. Please increase your budget by at least "
                f"{request.currency.upper()} {details['budget_difference'] * -1:,.0f}, based on TripMate's estimate."
            )
        return {
            "message": budget_warning or "TripMate created your travel plan using its own Python planning engine.",
            "budget_warning": budget_warning,
            "model": None,
            "trip": request.model_dump(),
            "itinerary": itinerary,
            "recommendations": recommendations,
            "daily_plan": daily_plan,
            "hotel_options": hotel_options,
            "route_guidance": route_guidance,
            "live_data_used": bool(sources),
            "sources": sources,
            "details": details,
            "note": ("Your budget is too low for the displayed trip estimate; please increase it or choose fewer days/a closer destination. " if recommendations and not any(option["within_budget"] for option in recommendations) else "") + "TripMate ranks destinations with Python decision rules and enriches options with public research when available. When configured, OpenRouteService calculates a driving route using OpenStreetMap data; it does not calculate public-transit or flight routes. Transport, food, and accommodation amounts are planning estimates, not live quotes. Confirm current prices and access rules before booking.",
        }
    except HTTPException:
        raise
    except Exception as error:
        # Keep internals in server logs; return a clear error to the client.
        print(f"Trip planning failed: {type(error).__name__}: {error}")
        raise HTTPException(status_code=500, detail="TripMate could not complete the plan. Please check the request and try again.") from error
