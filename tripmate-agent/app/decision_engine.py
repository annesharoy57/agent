"""Deterministic destination ranking for TripMate's first agent workflow."""

from typing import Any


def estimate_trip_cost(destination: dict[str, Any], days: int, travelers: int, style: str) -> float:
    daily = float(destination["daily_cost"])
    style = style.lower()
    if any(word in style for word in ("budget", "cheap", "economy")):
        daily *= 0.75
    elif any(word in style for word in ("comfort", "luxury", "premium")):
        daily *= 1.6
    return (float(destination["travel_cost"]) + daily * days) * travelers


def rank_destinations(
    destinations: list[dict[str, Any]], *, budget: float, days: int, travelers: int,
    style: str, interests: list[str], departure_city: str, scope: str, limit: int = 3,
    feedback: str = "", excluded_destinations: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Rank known candidates using explicit fit factors and return explainable scores."""
    scope = scope.lower().strip()
    normalized_interests = {value.lower().strip() for value in interests if value.strip()}
    excluded = {name.strip().casefold() for name in (excluded_destinations or [])}
    candidates = [d for d in destinations if d["name"].casefold() not in excluded and
                  (scope not in {"local", "domestic", "international"} or
                   d.get("scope") == ("local" if scope in {"local", "domestic"} else "international"))]
    feedback_text = feedback.casefold()
    cheaper_requested = any(term in feedback_text for term in ("cheaper", "lower cost", "less expensive", "low cost", "save money"))
    aliases = {
        "nature": ("nature", "green", "forest", "quiet", "peaceful", "less crowded", "calm"),
        "mountain": ("mountain", "hill", "hills", "hiking", "trekking"),
        "beach": ("beach", "sea", "ocean", "coast"),
        "culture": ("culture", "cultural", "tradition"),
        "history": ("history", "historic", "museum"),
        "food": ("food", "foodie", "local cuisine"),
        "photography": ("photo", "photography", "scenic", "scenery"),
        "relax": ("relax", "peaceful", "quiet", "calm", "less crowded", "not crowded"),
        "lake": ("lake", "lakes"),
        "tea": ("tea", "tea garden", "tea gardens"),
    }
    for tag, words in aliases.items():
        if any(word in feedback_text for word in words):
            normalized_interests.add(tag)
    negative_phrases = ("don't like", "do not like", "avoid", "no ", "not interested in", "less ")
    negative_tags = set()
    for tag, words in aliases.items():
        if any(f"{phrase}{word}" in feedback_text for phrase in negative_phrases for word in words):
            negative_tags.add(tag)
    ranked = []
    for destination in candidates:
        tags = {tag.lower() for tag in destination.get("tags", [])}
        matched = sorted(i for i in normalized_interests if any(i == tag or i in tag or tag in i for tag in tags))
        estimated = estimate_trip_cost(destination, days, travelers, style)
        affordability = max(-5.0, min(5.0, 5.0 * (budget - estimated) / max(budget, 1)))
        interest_score = min(6.0, len(matched) * 2.0)
        interest_score -= 3.0 * len(tags.intersection(negative_tags))
        if cheaper_requested:
            interest_score -= min(3.0, estimated / max(budget, 1))
        departure_match = 1.0 if departure_city.lower().strip() in destination["name"].lower() else 0.0
        score = interest_score + affordability + departure_match
        ranked.append({
            "destination": destination,
            "estimated_total": round(estimated),
            "within_budget": estimated <= budget,
            "matched_interests": matched,
            "score": round(score, 2), "negative_matches": sorted(tags.intersection(negative_tags)),
        })
    has_affordable = any(item["within_budget"] for item in ranked)
    ranked.sort(key=lambda item: (item["within_budget"] if has_affordable else False,
                                 item["score"], -item["estimated_total"]), reverse=True)

    return ranked[:limit]


def split_recommendations(ranked: list[dict[str, Any]], affordable_count: int = 4, stretch_count: int = 2) -> dict[str, list[dict[str, Any]]]:
    """Return several budget fits and a separate, clearly labeled stretch group."""
    affordable = [item for item in ranked if item["within_budget"]][:affordable_count]
    stretch = [item for item in ranked if not item["within_budget"]][:stretch_count]
    return {"within_budget": affordable, "stretch": stretch}
