"""Public destination research helpers used by the planning agent."""

import json
import math
import os
import re
import threading
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from functools import lru_cache
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen


class _ResearchHTMLParser(HTMLParser):
    """Extract readable page text while ignoring non-content elements."""

    _ignored_tags = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._in_title = False
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._ignored_tags:
            self._ignored_depth += 1
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in self._ignored_tags and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        if not self._ignored_depth:
            self.text_parts.append(text)


class _SearchHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._active: dict[str, str] | None = None
        self._active_depth = 0
        self._snippet: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == "a" and "result__a" in classes and attributes.get("href"):
            href = attributes["href"] or ""
            parsed = urlparse(href)
            if parsed.netloc.endswith("duckduckgo.com"):
                href = parse_qs(parsed.query).get("uddg", [href])[0]
            self._active = {"url": href, "title": ""}
            self._active_depth = 1
        elif self._active is not None:
            self._active_depth += 1
        if "result__snippet" in classes:
            self._snippet = {"text": ""}

    def handle_endtag(self, tag: str) -> None:
        if self._active is not None:
            self._active_depth -= 1
            if self._active_depth <= 0:
                if self._active.get("title"):
                    self.results.append(self._active)
                self._active = None
        if tag in {"div", "a"} and self._snippet is not None:
            self._snippet = None

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        if self._active is not None:
            self._active["title"] = f"{self._active['title']} {text}".strip()
        if self._snippet is not None:
            self._snippet["text"] = f"{self._snippet['text']} {text}".strip()
            if self.results:
                self.results[-1]["snippet"] = self._snippet["text"]


def web_search(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Search the public web with DuckDuckGo's HTML endpoint."""
    query = query.strip()
    if not query:
        return []
    request = Request(
        "https://html.duckduckgo.com/html/?" + urlencode({"q": query}),
        headers={"User-Agent": "TripMateAI/1.0 (travel research)", "Accept": "text/html"},
    )
    try:
        with urlopen(request, timeout=8.0) as response:
            html = response.read(1_000_000).decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise RuntimeError(f"Web search is currently unavailable: {error}") from error

    parser = _SearchHTMLParser()
    parser.feed(html)
    results = []
    seen_urls: set[str] = set()
    for result in parser.results:
        parsed = urlparse(result.get("url", ""))
        if parsed.scheme != "https" or not parsed.netloc or parsed.netloc.endswith("duckduckgo.com"):
            continue
        if result["url"] in seen_urls:
            continue
        seen_urls.add(result["url"])
        results.append({
            "title": result["title"][:300],
            "url": result["url"],
            "snippet": result.get("snippet", "")[:1000],
        })
        if len(results) >= max(1, min(limit, 5)):
            break
    return results


def extract_webpage(url: str) -> dict[str, str]:
    """Fetch and extract a bounded HTTPS page selected from web search results."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Only public HTTPS webpages can be extracted.")
    request = Request(
        url,
        headers={"User-Agent": "TripMateAI/1.0 (travel research)", "Accept": "text/html"},
    )
    try:
        with urlopen(request, timeout=8.0) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type.casefold():
                raise ValueError("The selected source is not an HTML webpage.")
            html = response.read(1_000_000).decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise RuntimeError(f"Webpage extraction is currently unavailable: {error}") from error

    parser = _ResearchHTMLParser()
    parser.feed(html)
    text = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    if not text:
        raise RuntimeError("The selected webpage did not contain readable text.")
    return {
        "title": " ".join(parser.title_parts)[:300] or parsed.netloc,
        "url": url,
        "content": text[:8000],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_json(url: str, timeout: float = 4.0) -> dict[str, Any] | list[Any] | None:
    request = Request(url, headers={"User-Agent": "TripMateAI/1.0 (travel planning demo)"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None


_nominatim_lock = threading.Lock()
_last_nominatim_request = 0.0
_MAX_WAYPOINT_DISTANCE_KM = 25.0
_exchange_rate_lock = threading.Lock()
_exchange_rate_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def currency_to_bdt_rate(currency: str) -> dict[str, Any]:
    """Return a recent ExchangeRate-API Open Access conversion rate into BDT."""
    currency = currency.strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("Currency must be a three-letter ISO code.")
    if currency == "BDT":
        return {"rate": 1.0, "date": None, "source": "TripMate estimate currency"}

    now = time.monotonic()
    with _exchange_rate_lock:
        cached = _exchange_rate_cache.get(currency)
        if cached and now - cached[0] < 21600:
            return dict(cached[1])
        data = fetch_json(
            f"https://open.er-api.com/v6/latest/{quote(currency)}",
            timeout=5.0,
        )
        try:
            if data["result"] != "success":  # type: ignore[index]
                raise ValueError("Exchange-rate provider returned an error.")
            rate = float(data["rates"]["BDT"])  # type: ignore[index]
            rate_date = str(data["time_last_update_utc"])  # type: ignore[index]
        except (KeyError, TypeError, ValueError):
            raise RuntimeError(
                f"A current {currency}-to-BDT exchange rate is unavailable."
            ) from None
        if rate <= 0:
            raise RuntimeError(f"The {currency}-to-BDT exchange rate was invalid.")
        result = {
            "rate": rate,
            "date": rate_date,
            "source": "ExchangeRate-API Open Access",
        }
        _exchange_rate_cache[currency] = (now, result)
        return dict(result)


def _distance_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    latitude1, longitude1 = map(math.radians, first)
    latitude2, longitude2 = map(math.radians, second)
    latitude_delta = latitude2 - latitude1
    longitude_delta = longitude2 - longitude1
    value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude1) * math.cos(latitude2)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(value))


def _geocode_name_matches(location: str, candidate: str) -> bool:
    requested_name = location.split(",", 1)[0]

    def tokens(value: str) -> set[str]:
        normalized = re.sub(r"['’]s\b", "", value.casefold())
        normalized = re.sub(r"['’]", "", normalized)
        return set(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))

    requested_tokens = tokens(requested_name)
    return bool(requested_tokens) and requested_tokens.issubset(tokens(candidate))


@lru_cache(maxsize=128)
def _openstreetmap_geocode(
    location: str, country_code: str | None = None,
    country_name: str | None = None,
    focus: tuple[float, float] | None = None,
) -> tuple[float, float] | None:
    global _last_nominatim_request
    query = location
    if country_name and country_name.casefold() not in location.casefold():
        query = f"{location}, {country_name}"
    parameters: dict[str, Any] = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
    }
    if country_code:
        parameters["countrycodes"] = country_code
    if focus:
        latitude, longitude = focus
        parameters["viewbox"] = (
            f"{longitude - 1.5},{latitude + 1.5},"
            f"{longitude + 1.5},{latitude - 1.5}"
        )
    with _nominatim_lock:
        delay = 1.0 - (time.monotonic() - _last_nominatim_request)
        if delay > 0:
            time.sleep(delay)
        data = fetch_json(
            "https://nominatim.openstreetmap.org/search?"
            + urlencode({
                **parameters,
                **({"email": os.environ["NOMINATIM_EMAIL"]} if os.getenv("NOMINATIM_EMAIL") else {}),
            }),
            timeout=8.0,
        )
        _last_nominatim_request = time.monotonic()
    if isinstance(data, list) and data and isinstance(data[0], dict):
        try:
            candidate_name = str(
                data[0].get("name") or data[0].get("display_name") or ""
            )
            if not _geocode_name_matches(location, candidate_name):
                raise ValueError("The geocoder result did not match the requested place.")
            coordinates = float(data[0]["lat"]), float(data[0]["lon"])
            if not focus or _distance_km(coordinates, focus) <= _MAX_WAYPOINT_DISTANCE_KM:
                return coordinates
        except (KeyError, TypeError, ValueError):
            pass

    return _photon_geocode(query, country_name, focus) if country_name else None


def _photon_geocode(
    query: str, country_name: str | None,
    focus: tuple[float, float] | None,
) -> tuple[float, float] | None:
    parameters = {"q": query, "limit": 5, "lang": "en"}
    if focus:
        parameters.update({
            "lat": str(focus[0]),
            "lon": str(focus[1]),
            "zoom": "10",
        })
    data = fetch_json(
        "https://photon.komoot.io/api/?" + urlencode(parameters),
        timeout=8.0,
    )
    if not isinstance(data, dict) or not isinstance(data.get("features"), list):
        return None
    for feature in data["features"]:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(properties, dict) or not isinstance(geometry, dict):
            continue
        if (
            not country_name
            or str(properties.get("country", "")).casefold() != country_name.casefold()
        ):
            continue
        if not _geocode_name_matches(query, str(properties.get("name") or "")):
            continue
        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            continue
        try:
            point = float(coordinates[1]), float(coordinates[0])
        except (TypeError, ValueError):
            continue
        if focus and _distance_km(point, focus) > _MAX_WAYPOINT_DISTANCE_KM:
            continue
        return point
    return None


def calculate_road_route(
    origin: str, destination: str, destination_lat: float | None,
    destination_lon: float | None, waypoints: list[str] | None = None,
    country_code: str | None = None, country_name: str | None = None,
) -> dict[str, Any]:
    """Geocode with OSM and calculate a driving route with ORS when configured."""
    result: dict[str, Any] = {
        "provider": "OpenStreetMap / OpenRouteService",
        "profile": "driving-car",
        "status": "unavailable",
        "origin": None,
        "destination": None,
        "waypoints": [],
        "geometry": None,
        "segments": [],
        "distance_km": None,
        "duration_minutes": None,
        "route_url": None,
    }
    start = _openstreetmap_geocode(
        origin, country_code=country_code, country_name=country_name,
    )
    if start is None:
        result["status"] = "origin_not_found"
        result["note"] = f"OpenStreetMap could not locate the departure city “{origin}”."
        return result

    if destination_lat is None or destination_lon is None:
        # Do not bias the destination search toward the departure city; that can
        # resolve a nearby place with the same name instead of the requested one.
        end = _openstreetmap_geocode(
            destination, country_code=country_code, country_name=country_name,
        )
        if end is None:
            result["status"] = "destination_not_found"
            result["note"] = f"OpenStreetMap could not locate “{destination}”."
            return result
    else:
        end = (float(destination_lat), float(destination_lon))
    result["origin"] = {"lat": start[0], "lon": start[1], "label": origin}
    result["destination"] = {"lat": end[0], "lon": end[1], "label": destination}
    points = [start]
    geocoded_waypoints = []
    unmapped_waypoints = []
    for waypoint in waypoints or []:
        location = f"{waypoint}, {destination}"
        coordinates = _openstreetmap_geocode(
            location,
            country_code=country_code,
            country_name=country_name,
            focus=end,
        )
        if coordinates is None:
            unmapped_waypoints.append(waypoint)
            continue
        points.append(coordinates)
        geocoded_waypoints.append({
            "lat": coordinates[0],
            "lon": coordinates[1],
            "label": waypoint,
        })
    points.append(end)
    result["waypoints"] = geocoded_waypoints
    result["unmapped_waypoints"] = unmapped_waypoints
    result["route_url"] = "https://www.openstreetmap.org/directions?" + urlencode({
        "engine": "fossgis_osrm_car",
        "route": ";".join(f"{latitude},{longitude}" for latitude, longitude in points),
    })

    api_key = os.getenv("OPENROUTESERVICE_API_KEY", "").strip()
    if api_key:
        router = "OpenRouteService"
        request = Request(
            "https://api.openrouteservice.org/v2/directions/driving-car/geojson",
            data=json.dumps({
                "coordinates": [[longitude, latitude] for latitude, longitude in points],
            }).encode("utf-8"),
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json",
                "Accept": "application/geo+json",
            },
            method="POST",
        )
    else:
        router = "OSRM"
        coordinates = ";".join(
            f"{longitude},{latitude}" for latitude, longitude in points
        )
        request = Request(
            f"https://router.project-osrm.org/route/v1/driving/{coordinates}?"
            "overview=full&geometries=geojson&steps=false",
            headers={"User-Agent": "TripMateAI/1.0 (travel planning)"},
        )
    result["provider"] = f"OpenStreetMap / {router}"
    try:
        with urlopen(request, timeout=12.0) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        result["note"] = f"{router} could not calculate this road route (HTTP {error.code})."
        return result
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        result["note"] = f"{router} is temporarily unavailable; the OSM map pins are still shown."
        return result

    try:
        if api_key:
            feature = data["features"][0]
            summary = feature["properties"]["summary"]
            geometry = feature["geometry"]
            distance = float(summary["distance"])
            duration = float(summary["duration"])
            route_segments = feature["properties"]["segments"]
        else:
            route = data["routes"][0]
            geometry = route["geometry"]
            distance = float(route["distance"])
            duration = float(route["duration"])
            route_segments = route["legs"]
        coordinates = geometry["coordinates"]
        if (
            geometry.get("type") != "LineString"
            or not isinstance(coordinates, list)
            or len(coordinates) < 2
            or not isinstance(route_segments, list)
            or len(route_segments) != len(points) - 1
        ):
            raise ValueError("Invalid route geometry")
        segment_results = []
        waypoint_names = [point["label"] for point in geocoded_waypoints]
        for index, segment in enumerate(route_segments):
            segment_distance = float(segment["distance"])
            segment_duration = float(segment["duration"])
            segment_results.append({
                "from": origin if index == 0 else waypoint_names[index - 1],
                "to": (
                    waypoint_names[index]
                    if index < len(waypoint_names)
                    else destination
                ),
                "distance_km": round(segment_distance / 1000, 1),
                "duration_minutes": round(segment_duration / 60),
            })
    except (KeyError, IndexError, TypeError, ValueError):
        result["note"] = "OpenRouteService returned route data that could not be displayed."
        return result

    result.update({
        "status": "partial" if unmapped_waypoints else "ready",
        "geometry": geometry,
        "segments": segment_results,
        "distance_km": round(distance / 1000, 1),
        "duration_minutes": round(duration / 60),
        "note": (
            (
                "Could not verify map locations for "
                + ", ".join(unmapped_waypoints)
                + "; those stops are omitted from this route. "
            )
            if unmapped_waypoints else ""
        ) + (
            f"Driving distance and time are calculated by {router} from OpenStreetMap data. "
            "This is a road route, not a live traffic report or a bus/train/ferry itinerary."
        ),
    })
    return result


@lru_cache(maxsize=128)
def wikipedia_research(destination: str) -> dict[str, Any] | None:
    """Retrieve a short public summary and thumbnail, when available."""
    search_url = "https://en.wikipedia.org/w/api.php?" + urlencode({
        "action": "query", "list": "search", "srsearch": destination,
        "format": "json", "srlimit": 1,
    })
    search_data = fetch_json(search_url)
    try:
        title = search_data["query"]["search"][0]["title"]  # type: ignore[index]
    except (TypeError, KeyError, IndexError):
        return None
    summary_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(title.replace(" ", "_"))
    summary_data = fetch_json(summary_url)
    if not isinstance(summary_data, dict) or not summary_data.get("extract"):
        return None
    return {
        "title": summary_data.get("title", title),
        "summary": summary_data["extract"],
        "url": summary_data.get("content_urls", {}).get("desktop", {}).get("page", "https://en.wikipedia.org/"),
        "image_url": summary_data.get("thumbnail", {}).get("source"),
        "source": "Wikipedia",
    }


@lru_cache(maxsize=256)
def wikipedia_page_research(title: str) -> dict[str, Any] | None:
    """Fetch one known attraction page directly to avoid an extra search request."""
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(title.replace(" ", "_"))
    data = fetch_json(url)
    if not isinstance(data, dict) or not data.get("extract"):
        return None
    return {
        "title": data.get("title", title),
        "summary": data["extract"],
        "url": data.get("content_urls", {}).get("desktop", {}).get("page", "https://en.wikipedia.org/"),
        "image_url": data.get("thumbnail", {}).get("source"),
        "source": "Wikipedia",
    }


# Starter route catalog for the university project's Bangladesh-first scope.
# Routes are grouped by neighborhood to reduce unnecessary cross-city driving.
DESTINATION_DAY_ROUTES = {
  "Dhaka": [
    {"area": "Old Dhaka: Lalbagh", "places": ["Lalbagh Fort", "Dhakeshwari Temple", "Star Mosque"]},
    {"area": "Old Dhaka: riverfront", "places": ["Ahsan Manzil", "Sadarghat", "Armenian Church, Dhaka"]},
    {"area": "Shahbag and Ramna", "places": ["Bangladesh National Museum", "Suhrawardy Udyan", "Ramna Park"]},
    {"area": "University area", "places": ["Curzon Hall", "University of Dhaka", "TSC, University of Dhaka"]},
    {"area": "Sher-e-Bangla Nagar", "places": ["Jatiya Sangsad Bhaban", "Chandrima Uddan"]},
    {"area": "Dhanmondi", "places": ["Liberation War Museum", "Dhanmondi Lake", "New Market, Dhaka"]},
    {"area": "Hatirjheel and Gulshan", "places": ["Hatirjheel", "Gulshan Lake Park"]},
  ],
  "Chattogram": [
    {"area": "City heritage", "places": ["Chattogram War Cemetery", "Ethnological Museum, Chittagong"]},
    {"area": "Foy's Lake and hills", "places": ["Foy's Lake", "Chattogram Zoo"]},
    {"area": "Coastal day", "places": ["Patenga Beach", "Karnaphuli River"]},
    {"area": "Sitakunda day trip", "places": ["Sitakunda Botanical Garden and Eco-Park", "Chandranath Temple"]},
  ],
  "Cox's Bazar": [
    {"area": "Cox's Bazar town", "places": ["Cox's Bazar Beach", "Burmese Market, Cox's Bazar"]},
    {"area": "South coast", "places": ["Himchari National Park", "Inani Beach"]},
    {"area": "Island day trip", "places": ["Maheshkhali Island", "Adinath Temple"]},
    {"area": "Saint Martin overnight route (check current boat service and island access before booking)", "places": ["Saint Martin's Island", "Cheradwip"]},
  ],
  "Saint Martin's Island": [
    {"area": "Island coast", "places": ["Saint Martin's Island", "Cheradwip"]},
    {"area": "Island village and beach", "places": ["Saint Martin's Island", "Coconut Grove, Saint Martin's Island"]},
  ],
  "Sylhet": [
    {"area": "Sylhet city", "places": ["Shrine of Shah Jalal", "Ali Amjad's Clock"]},
    {"area": "Jaflong and river scenery", "places": ["Jaflong", "Lalakhal"]},
    {"area": "Wetland and forest", "places": ["Ratargul Swamp Forest", "Bisanakandi"]},
  ],
  "Sreemangal": [
    {"area": "Tea gardens", "places": ["Sreemangal", "Baikka Beel"]},
    {"area": "Forest and lake", "places": ["Lawachara National Park", "Madhabpur Lake"]},
  ],
  "Bandarban": [
    {"area": "Bandarban town and viewpoints", "places": ["Nilachal, Bandarban", "Buddha Dhatu Jadi"]},
    {"area": "Hill viewpoints", "places": ["Nilgiri, Bandarban", "Meghla Tourist Spot"]},
  ],
  "Rangamati": [
    {"area": "Rangamati town and lake", "places": ["Kaptai Lake", "Rangamati Hanging Bridge"]},
    {"area": "Lake boat route", "places": ["Shuvolong Waterfall", "Kaptai National Park"]},
  ],
  "Sajek Valley": [
    {"area": "Sajek hill route", "places": ["Sajek Valley", "Konglak Hill"]},
    {"area": "Ruilui village", "places": ["Ruilui Para", "Sajek Valley"]},
  ],
  "Kuakata": [
    {"area": "Kuakata coast", "places": ["Kuakata Beach", "Kuakata Buddhist Temple"]},
    {"area": "Coastal day trip", "places": ["Fatrar Char", "Rakhine Palli, Kuakata"]},
  ],
  "Sonargaon": [
    {"area": "Historic Sonargaon", "places": ["Panam City", "Folk Art and Craft Museum"]},
    {"area": "Old Bengal heritage", "places": ["Goaldi Mosque", "Sonargaon"]},
  ],
  "Jaflong": [
    {"area": "Jaflong and river", "places": ["Jaflong", "Lalakhal"]},
    {"area": "Sylhet nature day", "places": ["Ratargul Swamp Forest", "Bisanakandi"]},
  ],
  "Tanguar Haor": [
    {"area": "Sunamganj and haor", "places": ["Tanguar Haor", "Jadukata River"]},
    {"area": "Wetland boat route", "places": ["Tanguar Haor", "Niladri Lake"]},
  ],
  "Sundarbans": [
    {"area": "Mongla gateway and forest boat route", "places": ["Sundarbans", "Karamjal Wildlife Breeding Centre"]},
    {"area": "Guided mangrove route", "places": ["Harbaria Ecotourism Center", "Sundarbans"]},
  ],
  "Bagerhat": [
    {"area": "Historic mosque city", "places": ["Sixty Dome Mosque", "Tomb of Khan Jahan Ali"]},
    {"area": "Bagerhat heritage", "places": ["Bagerhat Museum", "Singair Mosque"]},
  ],
  "Paharpur": [
    {"area": "Paharpur archaeological site", "places": ["Somapura Mahavihara", "Paharpur Museum"]},
  ],
  "Mahasthangarh": [
    {"area": "Mahasthangarh archaeological area", "places": ["Mahasthangarh", "Govinda Bhita"]},
  ],
  "Khagrachhari": [
    {"area": "Khagrachhari town and hills", "places": ["Alutila Cave", "Risang Waterfall"]},
    {"area": "Hill and lake route", "places": ["Alutila Tourist Center", "Madhupur Lake, Khagrachhari"]},
  ],
  "Rajshahi": [
    {"area": "Rajshahi city", "places": ["Varendra Research Museum", "Padma Garden"]},
    {"area": "Heritage day trip", "places": ["Bagha Mosque", "Puthia Temple Complex"]},
  ],
}


def build_vehicle_route(
    origin: str, destination: str, *, international: bool = False,
) -> dict[str, Any]:
    """Suggest practical vehicle types and route legs without claiming live service."""
    name = destination.strip()
    origin = origin.strip() or "your departure city"
    if international:
        return {
            "best_vehicle": "Flight from your nearest suitable airport",
            "legs": [
                {
                    "from": origin,
                    "to": "the departure airport",
                    "vehicle": "Local bus, train, taxi, or ride-hailing to the airport",
                    "note": "Compare transfer time and fare for your departure time.",
                },
                {
                    "from": "the departure airport",
                    "to": name,
                    "vehicle": "International flight",
                    "note": "Check current fares, baggage, transit/visa requirements, and entry rules.",
                },
                {
                    "from": "the arrival airport",
                    "to": name,
                    "vehicle": "Airport shuttle, public transport, taxi, or ride-hailing",
                    "note": "Choose after checking local availability and cost.",
                },
            ],
            "alternatives": ["Compare connecting flights and total airport-transfer costs"],
        }

    if name in {"Saint Martin's Island"}:
        legs = [
            {
                "from": origin,
                "to": "the currently operating mainland departure gateway",
                "vehicle": "Intercity coach; compare train or domestic flight connections if available",
                "note": "Confirm the current departure port and seasonal service before booking.",
            },
            {
                "from": "the authorized departure port",
                "to": name,
                "vehicle": "Authorized passenger vessel or ferry",
                "note": "Travel only when passenger service is operating and island access is officially permitted.",
            },
        ]
        return {"best_vehicle": "Intercity coach plus an authorized passenger vessel", "legs": legs,
                "alternatives": ["Train or domestic flight to the mainland gateway, if available", "Private road transfer to the authorized port"]}

    if name == "Sundarbans":
        legs = [
            {
                "from": origin,
                "to": "Khulna or Mongla, the relevant tour-operator gateway",
                "vehicle": "Intercity coach or train",
                "note": "The best gateway depends on the licensed tour and boat departure point.",
            },
            {
                "from": "the tour operator's embarkation point",
                "to": "the permitted Sundarbans itinerary",
                "vehicle": "Licensed tour boat",
                "note": "Use a registered operator; confirm permits, itinerary, and current access.",
            },
        ]
        return {"best_vehicle": "Intercity coach or train, then a licensed tour boat", "legs": legs,
                "alternatives": ["Private road transfer to the operator's gateway"]}

    if name == "Tanguar Haor":
        legs = [
            {
                "from": origin,
                "to": "Sunamganj",
                "vehicle": "Intercity coach; check whether a suitable train connection is available",
                "note": "Confirm the current route and departure times.",
            },
            {
                "from": "Sunamganj",
                "to": "the boat departure point",
                "vehicle": "Local CNG auto-rickshaw or reserved local vehicle",
                "note": "Agree the fare and boat departure point locally before setting out.",
            },
            {
                "from": "the authorized boat departure point",
                "to": name,
                "vehicle": "Locally operated boat with an agreed operator",
                "note": "Check weather, water conditions, and local guidance before travel.",
            },
        ]
        return {"best_vehicle": "Intercity coach, local CNG, then a locally operated boat", "legs": legs,
                "alternatives": ["Private transfer to Sunamganj; compare total group cost"]}

    hill_destinations = {"Bandarban", "Sajek Valley", "Khagrachhari", "Rangamati"}
    if name in hill_destinations:
        district = "Rangamati" if name == "Sajek Valley" else name
        local_vehicle = "Shared local jeep or Chander Gari with a local driver"
        legs = [
            {
                "from": origin,
                "to": f"{district} town or the relevant hill-district gateway",
                "vehicle": "Intercity coach; compare rail only if a suitable service is available",
                "note": "Check current routes, road conditions, and any local travel requirements.",
            },
            {
                "from": f"{district} town or the authorized pickup point",
                "to": name,
                "vehicle": local_vehicle,
                "note": "Use an experienced local driver and confirm current access rules; shared transport may cost less per person.",
            },
        ]
        return {"best_vehicle": "Intercity coach, then a shared local jeep/Chander Gari", "legs": legs,
                "alternatives": ["Reserved jeep/Chander Gari for a group; compare the full vehicle fare", "Local CNG for short town trips where suitable"]}

    if name == "Cox's Bazar":
        legs = [
            {
                "from": origin,
                "to": name,
                "vehicle": "Intercity coach (budget option); compare a flight if a service operates on your dates",
                "note": "Check current schedules and total fare, including airport transfers.",
            },
            {
                "from": "Cox's Bazar town",
                "to": "nearby beaches and attractions",
                "vehicle": "CNG auto-rickshaw or locally available shared/reserved transfer",
                "note": "Agree the fare before departure and check current access to each stop.",
            },
        ]
        return {"best_vehicle": "Intercity coach, then local CNG or shared transfer", "legs": legs,
                "alternatives": ["Flight if available and within budget", "Reserved local vehicle for a group; compare per-person cost"]}

    if name in {"Sylhet", "Sreemangal", "Jaflong"}:
        local_vehicle = "Local CNG auto-rickshaw or shared/reserved vehicle"
        if name == "Jaflong":
            local_vehicle = "Shared local vehicle or reserved CNG/jeep for the trip from Sylhet"
        legs = [
            {
                "from": origin,
                "to": "Sylhet" if name == "Jaflong" else name,
                "vehicle": "Intercity coach or train; compare current schedules and fares",
                "note": "A direct service may not run at your preferred time; confirm before booking.",
            },
            {
                "from": "Sylhet" if name == "Jaflong" else name,
                "to": name if name == "Jaflong" else "nearby attractions",
                "vehicle": local_vehicle,
                "note": "For out-of-town stops, confirm the return pickup and total fare with the driver.",
            },
        ]
        return {"best_vehicle": "Intercity coach or train, then a local CNG/shared transfer", "legs": legs,
                "alternatives": ["Reserved car for a group; compare its total fare against shared transport"]}

    if name == "Kuakata":
        legs = [
            {
                "from": origin,
                "to": name,
                "vehicle": "Intercity coach",
                "note": "Check the current direct route or any transfer required for your travel dates.",
            },
            {
                "from": name,
                "to": "nearby coastal stops",
                "vehicle": "Local e-rickshaw, auto-rickshaw, or locally arranged vehicle",
                "note": "Availability varies by stop; confirm the return arrangement and fare.",
            },
        ]
        return {"best_vehicle": "Intercity coach, then a local e-rickshaw or auto-rickshaw", "legs": legs,
                "alternatives": ["Reserved local vehicle for a group; compare the full fare"]}

    if destination and name.casefold() == origin.casefold():
        return {
            "best_vehicle": "Local bus or CNG auto-rickshaw for longer hops; walk for nearby stops",
            "legs": [{
                "from": origin,
                "to": "nearby attractions",
                "vehicle": "Local bus, CNG auto-rickshaw, or walking depending on distance",
                "note": "Check traffic, walking distance, and current local fares.",
            }],
            "alternatives": ["Ride-hailing or a reserved car if it suits your group and budget"],
        }

    legs = [
        {
            "from": origin,
            "to": name,
            "vehicle": "Intercity coach; use a train only if a suitable service operates on this route",
            "note": "Check direct service, schedules, and current fares before choosing.",
        },
        {
            "from": name,
            "to": "local attractions",
            "vehicle": "Local CNG auto-rickshaw, bus, or walking depending on distance",
            "note": "Choose the locally suitable option and confirm fares before riding.",
        },
    ]
    return {"best_vehicle": "Intercity coach, then local CNG or bus for nearby stops", "legs": legs,
            "alternatives": ["Train if a suitable service is available", "Shared or reserved vehicle for a group; compare total cost"]}


def build_daily_vehicle_guidance(destination: str, area: str) -> dict[str, str]:
    """Recommend practical local vehicles for the day's sightseeing area."""
    name = destination.strip()
    area_name = area.strip()
    area_lower = area_name.casefold()

    if name == "Cox's Bazar" and "south coast" in area_lower:
        return {
            "vehicle": "Shared or reserved CNG auto-rickshaw/jeep",
            "guidance": "Use a local vehicle between Himchari and Inani; agree the full fare and return pickup before leaving.",
        }
    if name == "Cox's Bazar" and "island" in area_lower:
        return {
            "vehicle": "Local CNG/auto-rickshaw to the authorized jetty, then an authorized passenger boat",
            "guidance": "Confirm current boat service, departure point, and island access before setting out.",
        }
    if name == "Cox's Bazar":
        return {
            "vehicle": "Walk for nearby beach stops; use a local CNG auto-rickshaw for the market or farther stops",
            "guidance": "Check walking distance and agree a local fare before riding.",
        }
    if name == "Sundarbans":
        return {
            "vehicle": "Transfer to the operator's embarkation point, then a licensed tour boat",
            "guidance": "Follow a licensed operator's permitted itinerary and confirm current access and pickup details.",
        }
    if name == "Saint Martin's Island":
        return {
            "vehicle": "Walk for nearby island stops; use an authorized boat only for water crossings",
            "guidance": "Check current vessel operations and local access rules before travel.",
        }
    if name == "Tanguar Haor" or "wetland" in area_lower or "haor" in area_lower:
        return {
            "vehicle": "Local CNG/auto-rickshaw to the boat point, then a locally operated boat",
            "guidance": "Confirm the boat operator, weather, water conditions, and return arrangement locally.",
        }
    if "boat route" in area_lower or "lake boat" in area_lower or "waterfall" in area_lower and name == "Rangamati":
        return {
            "vehicle": "Local CNG/auto-rickshaw to the launch point, then a locally operated lake boat",
            "guidance": "Confirm the launch point, boat fare, and return time before departure.",
        }
    if name in {"Bandarban", "Sajek Valley", "Khagrachhari", "Rangamati"}:
        return {
            "vehicle": "Shared local jeep/Chander Gari for hill routes; local CNG for short town trips",
            "guidance": "Use an experienced local driver and confirm current road access and local requirements.",
        }
    if name in {"Jaflong", "Sylhet", "Sreemangal"} and any(
        word in area_lower for word in ("jaflong", "river", "forest", "wetland", "tea gardens")
    ):
        return {
            "vehicle": "Shared or reserved local CNG/vehicle; use a local boat only where the route requires one",
            "guidance": "Agree the return pickup and total fare for out-of-town stops before leaving.",
        }
    if "day trip" in area_lower or "heritage day" in area_lower or "outside" in area_lower:
        return {
            "vehicle": "Intercity/local bus where available, or a shared/reserved CNG or car",
            "guidance": "Check whether public transport serves every stop; agree the return plan and fare.",
        }
    return {
        "vehicle": "Walk between nearby stops; use a local bus, rickshaw, or CNG auto-rickshaw for longer hops",
        "guidance": "Choose based on distance and local availability; check the fare before riding.",
    }


def destination_days(destination: str, days: int, budget: float, currency: str, visited_places: list[str] | None = None, fetch_images: bool = True) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Create neighborhood-based sightseeing routes and budget-aware hotel searches."""
    normalized_destination = "Chattogram" if destination.casefold() in {"chittagong", "chittagong city"} else destination
    routes = next((value for name, value in DESTINATION_DAY_ROUTES.items() if name.casefold() == normalized_destination.casefold()), None)
    if routes is None:
        return [], []

    daily_routes = []
    visited = {place.strip().casefold() for place in (visited_places or []) if place.strip()}
    remaining_routes = []
    for route in routes:
        fresh_places = [
            place for place in route["places"]
            if not any(
                visited_place == place.casefold() or
                (len(visited_place) >= 5 and visited_place in place.casefold())
                for visited_place in visited
            )
        ]
        if fresh_places:
            remaining_routes.append({"area": route["area"], "places": fresh_places})
    image_routes = remaining_routes[:min(days, len(remaining_routes))]
    for day_number, route in enumerate(image_routes, 1):
        attractions = []
        for index, place_name in enumerate(route["places"]):
            # Fetch an image for the lead stop on each route; keep the request bounded.
            research = wikipedia_page_research(place_name) if index == 0 and fetch_images else None
            attractions.append({
                "name": place_name,
                "area": route["area"],
                "summary": research["summary"] if research else "Add this nearby stop to the same neighborhood visit; confirm current opening times before you go.",
                "image_url": research.get("image_url") if research else None,
                "source": {"name": research["source"], "url": research["url"]} if research else None,
            })
        daily_routes.append({
            "day": day_number,
            "area": route["area"],
            "stops": attractions,
            "transport": build_daily_vehicle_guidance(normalized_destination, route["area"]),
        })

    for day_number in range(len(daily_routes) + 1, days + 1):
        flexible_area = f"Flexible {destination} day"
        daily_routes.append({
            "day": day_number, "area": f"Flexible {destination} day",
            "stops": [{
                "name": "Choose a new attraction or take a rest day",
                "area": f"Choose the closest neighborhood to your hotel in {destination}",
                "summary": "Keep this day flexible for rest, weather, traffic, shopping, a new neighborhood, or a place you want to revisit.",
                "image_url": None, "source": None,
            }],
            "transport": build_daily_vehicle_guidance(normalized_destination, flexible_area),
        })

    # Allocate a planning target from the user's total budget. These are not hotel quotes.
    nightly_target = round(max(0, budget * 0.35 / max(days, 1)))
    areas_by_destination = {
        "Dhaka": [("Central and Shahbag", "guest houses and budget hotels near Shahbag Dhaka"), ("Old Dhaka edge", "budget hotels near Lalbagh Fort Dhaka"), ("Dhanmondi", "budget hotels in Dhanmondi Dhaka")],
        "Chattogram": [("Central Chattogram", "budget hotels in central Chattogram"), ("GEC Circle", "budget hotels near GEC Circle Chattogram"), ("Patenga", "hotels near Patenga Beach Chattogram")],
        "Cox's Bazar": [("Beach area", "budget hotels near Cox's Bazar Beach"), ("Kolatoli", "budget hotels in Kolatoli Cox's Bazar"), ("Himchari route", "guesthouses near Himchari Cox's Bazar")],
        "Saint Martin's Island": [("Island village", "guesthouses on Saint Martin's Island Bangladesh")],
    }
    destination = normalized_destination
    areas = areas_by_destination.get(destination, [("Near your route", f"budget hotels in {destination}")])
    hotels = [{
        "area": area,
        "nightly_budget": nightly_target,
        "currency": currency.upper(),
        "search_url": "https://www.google.com/maps/search/?api=1&query=" + quote(query),
        "note": "Compare current room prices, guest reviews, location, and cancellation terms. No live room rate is available here.",
    } for area, query in areas]
    return daily_routes, hotels
