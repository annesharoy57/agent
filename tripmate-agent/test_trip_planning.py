import json
import os
import unittest
from datetime import date
from unittest.mock import patch
from urllib.error import URLError

from app.main import (
    ChatRequest,
    DESTINATIONS,
    TripRequest,
    choose_destination,
    build_itinerary,
    build_route_guidance,
    chat_with_tripmate,
    discover_destinations,
    get_weather,
    plan_trip,
    recommend_trips,
    finalize_transport_estimates,
)
from app.conversation import answer_travel_question, classify_travel_question
from app.research import (
    _openstreetmap_geocode,
    build_vehicle_route,
    calculate_road_route,
    destination_days,
)
from app.transport import estimate_transport_cost, select_vehicle_type


def trip_payload(**overrides):
    payload = {
        "budget": 20000,
        "currency": "BDT",
        "duration_days": 2,
        "departure_city": "Dhaka",
        "start_date": "2027-01-15",
        "travel_scope": "local",
    }
    payload.update(overrides)
    return payload


def road_route_payload():
    return {
        "provider": "OpenStreetMap / OpenRouteService",
        "profile": "driving-car",
        "status": "ready",
        "origin": {"lat": 23.8, "lon": 90.4, "label": "Dhaka"},
        "destination": {"lat": 24.9, "lon": 91.8, "label": "Sylhet"},
        "waypoints": [],
        "geometry": {"type": "LineString", "coordinates": [[90.4, 23.8], [91.8, 24.9]]},
        "segments": [{"from": "Dhaka", "to": "Sylhet", "distance_km": 244.5, "duration_minutes": 300}],
        "distance_km": 244.5,
        "duration_minutes": 300,
        "route_url": "https://www.openstreetmap.org/directions?route=23.8%2C90.4%3B24.9%2C91.8",
        "note": "Calculated driving route.",
    }


class TripPlanningTests(unittest.TestCase):
    def test_group_budget_is_member_contribution_times_member_count(self):
        request = TripRequest(**trip_payload(
            trip_type="group",
            travelers=4,
            contribution_per_person=5000,
        ))

        self.assertEqual(request.budget, 20000)
        self.assertEqual(request.travelers, 4)

    def test_legacy_multi_traveler_request_remains_a_group(self):
        request = TripRequest(**trip_payload(travelers=3))

        self.assertEqual(request.trip_type, "group")
        self.assertEqual(request.travelers, 3)
        self.assertEqual(request.contribution_per_person, request.budget / 3)

    def test_group_requires_at_least_two_members(self):
        with self.assertRaises(ValueError):
            TripRequest(**trip_payload(
                trip_type="group",
                travelers=1,
                contribution_per_person=5000,
            ))

    def test_route_guidance_uses_budget_transport_options_and_links(self):
        request = TripRequest(**trip_payload(travel_style="budget"))
        destination = next(place for place in DESTINATIONS if place["name"] == "Sylhet")

        with patch("app.main.calculate_road_route", return_value=road_route_payload()):
            route = build_route_guidance(request, destination, estimated_total=30000)

        self.assertIn("coach", route["recommended"].lower())
        self.assertIn("openstreetmap.org/directions", route["route_url"])
        self.assertEqual(route["road_route"]["distance_km"], 244.5)
        self.assertEqual(route["transport_estimate_vehicle"], route["best_vehicle"])
        self.assertEqual(route["transport_estimate"]["minimum"], 1470)
        self.assertEqual(route["transport_estimate"]["maximum"], 2930)
        self.assertEqual(route["estimate_currency"], "BDT")

    def test_bus_cost_range_scales_for_return_trip_and_passengers(self):
        fare = estimate_transport_cost("bus", 100, travelers=3, return_trip=True)

        self.assertEqual(fare["minimum"], 1800)
        self.assertEqual(fare["maximum"], 3600)
        self.assertEqual(fare["distance_km"], 200)
        self.assertEqual(fare["status"], "estimated_range")
        self.assertIn("not verified", fare["basis"])

    def test_local_fare_range_is_vehicle_cost_not_per_person(self):
        fare = estimate_transport_cost("cng", 10, travelers=4)

        self.assertEqual(fare["minimum"], 400)
        self.assertEqual(fare["maximum"], 800)
        self.assertEqual(select_vehicle_type("CNG auto-rickshaw", local=True), "cng")

    def test_unavailable_distance_never_returns_a_zero_fare(self):
        fare = estimate_transport_cost("rickshaw", None)

        self.assertIsNone(fare["minimum"])
        self.assertIsNone(fare["maximum"])
        self.assertEqual(fare["status"], "distance_unavailable")

    def test_transport_total_sums_intercity_and_daily_route_ranges(self):
        request = TripRequest(**trip_payload())
        destination = next(place for place in DESTINATIONS if place["name"] == "Sylhet")
        main_route = road_route_payload()
        daily_route = {
            **road_route_payload(),
            "segments": [
                {"from": "Sylhet", "to": "Jaflong", "distance_km": 5, "duration_minutes": 15},
                {"from": "Jaflong", "to": "Sylhet", "distance_km": 5, "duration_minutes": 15},
            ],
        }
        daily_plan = [{
            "day": 1,
            "stops": [{"name": "Jaflong"}],
            "transport": {"vehicle": "Local CNG auto-rickshaw"},
        }]
        with patch("app.main.calculate_road_route", side_effect=[main_route, daily_route]):
            route = build_route_guidance(request, destination, estimated_total=30000)
            finalize_transport_estimates(route, daily_plan, destination, request.travelers)

        self.assertEqual(len(route["transport_segments"]), 3)
        self.assertEqual(route["transport_segments"][1]["from"], "Sylhet")
        self.assertEqual(route["total_transport_estimate"]["status"], "estimated_range")
        self.assertEqual(
            route["total_transport_estimate"]["minimum"],
            route["transport_estimate"]["minimum"] + 200,
        )

    def test_empty_daily_routes_do_not_count_as_complete_transport_estimates(self):
        request = TripRequest(**trip_payload(destination="Sylhet"))
        destination = next(place for place in DESTINATIONS if place["name"] == "Sylhet")
        empty_plan = [{
            "day": 1,
            "stops": [{"name": "Choose a new attraction or take a rest day"}],
            "transport": {"vehicle": "Local CNG"},
        }]

        with patch("app.main.calculate_road_route", return_value=road_route_payload()):
            route = build_route_guidance(request, destination, estimated_total=30000)
            finalize_transport_estimates(route, empty_plan, destination, request.travelers)

        self.assertEqual(route["local_transport_estimate"]["status"], "unavailable")
        self.assertEqual(route["total_transport_estimate"]["status"], "partial")

    def test_custom_destinations_do_not_inherit_dhaka_coordinates(self):
        request = TripRequest(**trip_payload(destination="Atlantis"))

        destination = choose_destination(request)

        self.assertIsNone(destination["lat"])
        self.assertIsNone(destination["lon"])
        self.assertEqual(destination["scope"], "unknown")
        with patch("app.main.calculate_road_route") as route_lookup:
            route = build_route_guidance(request, destination, estimated_total=10000)

        route_lookup.assert_not_called()
        self.assertEqual(route["road_route"]["status"], "destination_not_confirmed")
        self.assertEqual(route["transport_estimate"]["status"], "distance_unavailable")

    def test_weather_module_skips_destinations_without_coordinates(self):
        with patch("app.weather.fetch_json") as fetch:
            forecast = get_weather(
                {"name": "Custom place", "lat": None, "lon": None},
                date.today(),
                1,
            )

        self.assertIsNone(forecast)
        fetch.assert_not_called()

    def test_chat_keeps_answer_and_returns_budget_warning_separately(self):
        request = ChatRequest(
            message="Recommend a beach destination.",
            trip=TripRequest(**trip_payload(budget=100)),
        )
        options = {
            "within_budget": [],
            "stretch": [{
                "name": "Sylhet", "estimated_total": 1000, "currency": "BDT",
                "within_budget": False,
            }],
        }
        with (
            patch("app.main.discover_destinations", return_value=options),
            patch("app.main.generate_reply", return_value={
                "reply": "Here is the answer to your question.",
                "sources": [], "status": "local_model",
            }) as local_agent,
        ):
            result = chat_with_tripmate(request)

        local_agent.assert_not_called()
        self.assertIn("beach", result["reply"].lower())
        self.assertNotEqual(result["reply"], result["budget_warning"])
        self.assertIn("budget is too low", result["budget_warning"])

    def test_unrelated_chat_does_not_run_destination_discovery(self):
        request = ChatRequest(
            message="What is a passport?",
            trip=TripRequest(**trip_payload(destination="Sylhet")),
        )
        with (
            patch("app.main.discover_destinations") as discovery,
            patch("app.main.generate_reply", return_value={
                "reply": "A passport is an official travel document.",
                "sources": [], "status": "local_model",
            }),
        ):
            result = chat_with_tripmate(request)

        discovery.assert_not_called()
        self.assertEqual(result["reply"], "A passport is an official travel document.")
        self.assertEqual(result["trip"]["destination"], "Sylhet")

    def test_named_destination_question_gets_a_concise_sourced_answer_without_model(self):
        request = ChatRequest(
            message="Tell me more about Cox's Bazar.",
            trip=TripRequest(**trip_payload(destination="Cox's Bazar")),
        )
        option = {
            "name": "Cox's Bazar",
            "summary": "A popular coastal town with a long beach and seafood.",
            "image_url": "https://example.org/cox.jpg",
            "source": {"name": "Tourism Board", "url": "https://example.org/cox"},
        }
        with (
            patch("app.main.discover_destinations", return_value={
                "within_budget": [option], "stretch": [],
            }),
            patch("app.main.generate_reply") as local_agent,
        ):
            result = chat_with_tripmate(request)

        local_agent.assert_not_called()
        self.assertIn("popular coastal town", result["reply"])
        self.assertLessEqual(len(result["reply"].split()), 60)
        self.assertEqual(result["agent_status"], "tripmate_tools")
        self.assertEqual(result["answer_sources"], [option["source"]])
        self.assertEqual(result["answer_media"][0]["image_url"], option["image_url"])

    def test_budget_question_uses_current_plan_estimate_without_model(self):
        request = ChatRequest(
            message="Can you explain whether the budget is enough and what I should prioritize?",
            trip=TripRequest(**trip_payload(
                budget=30000,
                destination="Cox's Bazar",
            )),
            plan_estimate={
                "destination": "Cox's Bazar",
                "budget": 30000,
                "currency": "BDT",
                "estimated_total": 12845,
                "budget_difference": 17155,
                "within_budget": True,
                "breakdown": {
                    "transport": 3520,
                    "accommodation": 2450,
                    "food": 2100,
                    "activities": 1400,
                    "local_travel": 3025,
                    "contingency": 350,
                },
            },
        )

        with patch("app.main.generate_reply") as local_agent:
            result = chat_with_tripmate(request)

        local_agent.assert_not_called()
        self.assertIn("BDT 12,845", result["reply"])
        self.assertIn("BDT 17,155", result["reply"])
        self.assertIn("transport (BDT 3,520)", result["reply"])
        self.assertEqual(result["agent_status"], "tripmate_tools")

    def test_combined_cost_question_answers_all_requested_categories_for_two(self):
        request = ChatRequest(
            message="Can you estimate the total transportation, food, and entry costs for both of us",
            trip=TripRequest(**trip_payload(destination="Sonargaon")),
            plan_estimate={
                "destination": "Sonargaon", "budget": 20000, "currency": "BDT",
                "estimated_total": 6000, "budget_difference": 14000,
                "within_budget": True,
                "breakdown": {
                    "transport": 1200, "accommodation": 0, "food": 800,
                    "activities": 500, "local_travel": 200, "contingency": 300,
                },
            },
        )
        with (
            patch("app.main.discover_destinations") as discovery,
            patch("app.main.wikipedia_research") as wiki,
            patch("app.main.generate_reply") as local_agent,
        ):
            result = chat_with_tripmate(request)

        self.assertEqual(classify_travel_question(request.message), "cost_estimate")
        self.assertIn("Transportation", result["reply"])
        self.assertIn("Food", result["reply"])
        self.assertIn("Attractions and activities", result["reply"])
        self.assertIn("BDT 5,400", result["reply"])
        self.assertEqual(result["answer_media"], [])
        self.assertEqual(result["answer_sources"], [])
        discovery.assert_not_called()
        wiki.assert_not_called()
        local_agent.assert_not_called()

    def test_cost_question_with_food_is_not_misclassified_as_food(self):
        self.assertEqual(
            classify_travel_question("Estimate transportation, food, and entry costs"),
            "cost_estimate",
        )

    def test_cost_question_estimates_from_catalog_when_plan_estimate_missing(self):
        request = ChatRequest(
            message="Can you estimate transportation, food, and entry costs for both of us?",
            trip=TripRequest(**trip_payload(destination="Sonargaon")),
        )
        with (
            patch("app.main.wikipedia_research") as wiki,
            patch("app.main.generate_reply") as local_agent,
        ):
            result = chat_with_tripmate(request)

        self.assertIn("Estimated costs for 2 people", result["reply"])
        self.assertIn("Estimated total: BDT 5,800–8,600", result["reply"])
        self.assertIn("not verified live prices", result["reply"])
        self.assertEqual(result["answer_media"], [])
        wiki.assert_not_called()
        local_agent.assert_not_called()

    def test_foreign_currency_budget_and_estimates_use_the_same_rate(self):
        request = TripRequest(**trip_payload(
            budget=100,
            currency="USD",
        ))
        sylhet = next(place for place in DESTINATIONS if place["name"] == "Sylhet")
        with (
            patch("app.main.get_currency_rate", return_value={
                "rate": 100.0, "date": "2026-11-12", "source": "ExchangeRate-API Open Access",
            }),
            patch("app.main.wikipedia_research", return_value=None),
        ):
            groups = discover_destinations(request, [sylhet])

        self.assertTrue(groups["within_budget"][0]["within_budget"])
        self.assertEqual(groups["within_budget"][0]["currency"], "USD")
        self.assertEqual(groups["within_budget"][0]["estimated_total"], 74)

    def test_itinerary_converts_bdt_cost_estimates_before_foreign_budget_check(self):
        request = TripRequest(**trip_payload(
            budget=100,
            currency="USD",
            destination="Sylhet",
        ))
        destination = next(place for place in DESTINATIONS if place["name"] == "Sylhet")
        route = {
            "recommended": "Intercity coach",
            "transport_estimate_vehicle": "Intercity coach",
            "legs": [],
            "transport_segments": [],
            "transport_estimate": {
                "status": "estimated_range", "minimum": 2000, "maximum": 3000,
            },
            "local_transport_estimate": {"status": "unavailable"},
            "total_transport_estimate": {
                "status": "partial", "minimum": 2000, "maximum": 3000,
                "note": "Planning estimate.",
            },
        }
        with patch("app.main.get_currency_rate", return_value={
            "rate": 100.0, "date": "2026-11-12", "source": "ExchangeRate-API Open Access",
        }):
            itinerary, details = build_itinerary(
                request, destination, None, None, route_guidance=route,
            )

        self.assertEqual(details["estimated_total"], 81.0)
        self.assertTrue(details["within_budget"])
        self.assertIn("1 USD = 100.0000 BDT", itinerary)
        self.assertIn("Transport to/from destination (budget estimate): USD 25", itinerary)

    def test_chat_preferences_append_feedback_and_accept_bangla_interests(self):
        request = ChatRequest(
            message="I prefer beaches.",
            trip=TripRequest(**trip_payload(
                destination="Sylhet",
                interests=["nature"],
                feedback="Prefer quiet places",
            )),
        )
        with (
            patch("app.main.discover_destinations", return_value={
                "within_budget": [], "stretch": [],
            }),
            patch("app.main.generate_reply", return_value={
                "reply": "I updated the destination ideas.",
                "sources": [], "status": "local_model",
            }),
        ):
            result = chat_with_tripmate(request)

        self.assertEqual(result["trip"]["destination"], "Sylhet")
        self.assertEqual(result["trip"]["feedback"], "Prefer quiet places; I prefer beaches.")
        self.assertEqual(result["trip"]["interests"], ["nature", "beach"])
        self.assertEqual(classify_travel_question("সিলেটে কী খাবার পাওয়া যায়?"), "food")
        self.assertIsNone(classify_travel_question("আমার বাসা কোথায়?"))

    def test_short_follow_up_reuses_the_previous_travel_intent(self):
        request = ChatRequest(
            message="How much?",
            trip=TripRequest(**trip_payload(destination="Sylhet")),
            history=[{"role": "user", "content": "How do I get there by bus?"}],
        )
        with (
            patch("app.main.discover_destinations") as discovery,
            patch("app.main.wikipedia_research", return_value=None),
            patch("app.conversation.calculate_road_route", return_value={
                "status": "unavailable", "distance_km": None, "origin": None,
                "route_url": None,
            }),
            patch("app.main.get_knowledge_base"),
            patch("app.main.generate_reply", return_value={
                "reply": "Check current operator fares and schedules.",
                "sources": [], "status": "local_model",
            }) as local_agent,
        ):
            result = chat_with_tripmate(request)

        discovery.assert_not_called()
        local_agent.assert_not_called()
        self.assertEqual(result["agent_status"], "tripmate_tools")
        self.assertIn("could not calculate a road distance", result["reply"])

    def test_sundarbans_route_identifies_coach_and_licensed_boat_legs(self):
        route = build_vehicle_route("Dhaka", "Sundarbans")

        self.assertIn("coach", route["best_vehicle"].lower())
        self.assertIn("boat", route["best_vehicle"].lower())
        self.assertEqual(len(route["legs"]), 2)
        self.assertIn("Licensed tour boat", route["legs"][1]["vehicle"])

    def test_hill_destination_route_identifies_shared_local_vehicle(self):
        route = build_vehicle_route("Dhaka", "Sajek Valley")

        self.assertIn("coach", route["legs"][0]["vehicle"].lower())
        self.assertIn("Chander Gari", route["legs"][1]["vehicle"])
        self.assertTrue(route["alternatives"])

    def test_international_route_recommends_flight(self):
        route = build_vehicle_route("Dhaka", "Kathmandu", international=True)

        self.assertIn("Flight", route["best_vehicle"])
        self.assertIn("International flight", route["legs"][1]["vehicle"])

    def test_low_budget_itinerary_asks_to_increase_budget(self):
        request = TripRequest(**trip_payload(budget=1000, destination="Sylhet"))
        destination = next(place for place in DESTINATIONS if place["name"] == "Sylhet")

        with patch("app.main.calculate_road_route", return_value=road_route_payload()):
            itinerary, details = build_itinerary(request, destination, None, None)

        self.assertFalse(details["within_budget"])
        self.assertIn("Your budget is too low for this trip. Please increase your budget", itinerary)

    def test_itinerary_lists_vehicle_choices_for_each_route_leg(self):
        request = TripRequest(**trip_payload(budget=100000, destination="Sundarbans"))
        destination = next(place for place in DESTINATIONS if place["name"] == "Sundarbans")

        with patch("app.main.calculate_road_route", return_value=road_route_payload()):
            itinerary, _ = build_itinerary(request, destination, None, None)

        self.assertIn("Suggested vehicles by route leg", itinerary)
        self.assertIn("Intercity coach or train", itinerary)
        self.assertIn("Licensed tour boat", itinerary)

    def test_cox_bazar_day_plan_identifies_local_vehicles_by_area(self):
        days, _ = destination_days(
            "Cox's Bazar", days=2, budget=30000, currency="BDT",
            fetch_images=False,
        )

        self.assertIn("CNG auto-rickshaw", days[0]["transport"]["vehicle"])
        self.assertIn("return pickup", days[1]["transport"]["guidance"])

    def test_daily_itinerary_includes_local_transport_for_sightseeing_day(self):
        request = TripRequest(**trip_payload(
            budget=50000,
            destination="Cox's Bazar",
        ))
        destination = next(place for place in DESTINATIONS if place["name"] == "Cox's Bazar")
        daily_plan, _ = destination_days(
            "Cox's Bazar", days=2, budget=request.budget, currency="BDT",
            fetch_images=False,
        )

        with patch("app.main.calculate_road_route", return_value=road_route_payload()):
            itinerary, _ = build_itinerary(request, destination, None, None, daily_plan)

        self.assertIn("How to get around today:", itinerary)
        self.assertIn("CNG auto-rickshaw", itinerary)
        self.assertIn("shared or reserved cng auto-rickshaw/jeep", itinerary.lower())

    def test_plan_response_includes_route_links_and_low_budget_warning(self):
        request = TripRequest(**trip_payload(budget=1000, destination="Sylhet"))
        with (
            patch("app.main.wikipedia_research", return_value=None),
            patch("app.main.get_weather", return_value=None),
            patch("app.main.destination_days", return_value=([], [])),
            patch("app.main.calculate_road_route", return_value=road_route_payload()),
        ):
            result = plan_trip(request)

        self.assertIn("route_url", result["route_guidance"])
        self.assertTrue(result["budget_warning"].startswith("Your budget is too low"))
        self.assertEqual(result["details"]["travelers"], 1)

    @patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": "test-key"})
    @patch("app.research._openstreetmap_geocode", return_value=(23.8, 90.4))
    @patch("app.research.urlopen")
    def test_openrouteservice_route_returns_distance_time_and_geojson(self, mocked_urlopen, _):
        response_data = {
            "features": [{
                "properties": {
                    "summary": {"distance": 244500, "duration": 18000},
                    "segments": [{"distance": 244500, "duration": 18000}],
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[90.4, 23.8], [91.8, 24.9]],
                },
            }],
        }
        mocked_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
            response_data
        ).encode("utf-8")

        route = calculate_road_route("Dhaka", "Sylhet", 24.9, 91.8)

        self.assertEqual(route["status"], "ready")
        self.assertEqual(route["distance_km"], 244.5)
        self.assertEqual(route["duration_minutes"], 300)
        self.assertEqual(route["geometry"]["type"], "LineString")
        self.assertIn("openstreetmap.org/directions", route["route_url"])
        self.assertEqual(mocked_urlopen.call_args.args[0].method, "POST")
        self.assertEqual(
            mocked_urlopen.call_args.args[0].get_header("Authorization"), "test-key",
        )

    @patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": ""})
    @patch("app.research._openstreetmap_geocode", return_value=(23.8, 90.4))
    @patch("app.research.urlopen")
    def test_osrm_fallback_calculates_route_without_api_key(self, mocked_urlopen, _):
        mocked_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps({
            "routes": [{
                "distance": 244500,
                "duration": 18000,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[90.4, 23.8], [91.8, 24.9]],
                },
                "legs": [{"distance": 244500, "duration": 18000}],
            }],
        }).encode("utf-8")

        route = calculate_road_route("Dhaka", "Sylhet", 24.9, 91.8)

        self.assertEqual(route["status"], "ready")
        self.assertTrue(route["provider"].endswith("OSRM"))
        self.assertIsNotNone(route["origin"])
        self.assertIsNotNone(route["destination"])
        self.assertEqual(route["distance_km"], 244.5)
        self.assertEqual(route["duration_minutes"], 300)
        self.assertIsNotNone(route["geometry"])
        self.assertIsNotNone(route["route_url"])
        self.assertIn("router.project-osrm.org", mocked_urlopen.call_args.args[0].full_url)

    @patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": ""})
    @patch("app.research._openstreetmap_geocode", side_effect=[
        (23.8, 90.4), (24.0, 91.0), None,
    ])
    @patch("app.research.urlopen")
    def test_missing_waypoint_keeps_verified_route_and_marks_it_partial(
        self, mocked_urlopen, _,
    ):
        mocked_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps({
            "routes": [{
                "distance": 100000,
                "duration": 7200,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[90.4, 23.8], [91.0, 24.0], [91.8, 24.9]],
                },
                "legs": [
                    {"distance": 50000, "duration": 3600},
                    {"distance": 50000, "duration": 3600},
                ],
            }],
        }).encode("utf-8")

        route = calculate_road_route(
            "Dhaka",
            "Sylhet",
            24.9,
            91.8,
            waypoints=["Verified stop", "Unverified stop"],
            country_code="bd",
            country_name="Bangladesh",
        )

        self.assertEqual(route["status"], "partial")
        self.assertEqual(route["unmapped_waypoints"], ["Unverified stop"])
        self.assertEqual(route["segments"][0]["to"], "Verified stop")
        self.assertEqual(route["segments"][1]["from"], "Verified stop")
        self.assertIsNotNone(route["origin"])
        self.assertIsNotNone(route["destination"])

    @patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": ""})
    @patch("app.research._openstreetmap_geocode", return_value=(23.8, 90.4))
    @patch("app.research.urlopen", side_effect=URLError("offline"))
    def test_map_pins_remain_when_public_router_is_unavailable(self, _, __):
        route = calculate_road_route("Dhaka", "Sylhet", 24.9, 91.8)

        self.assertEqual(route["status"], "unavailable")
        self.assertIsNotNone(route["origin"])
        self.assertIsNotNone(route["destination"])
        self.assertIsNone(route["geometry"])

    @patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": ""})
    @patch("app.research._openstreetmap_geocode", side_effect=[(23.8, 90.4), (25.8, 88.9)])
    @patch("app.research.urlopen", side_effect=URLError("offline"))
    def test_custom_destination_geocode_is_not_scoped_to_departure_city(
        self, _, geocode,
    ):
        route = calculate_road_route("Dhaka", "Railway Station", None, None)

        self.assertEqual(route["status"], "unavailable")
        self.assertEqual(
            [call.args[0] for call in geocode.call_args_list],
            ["Dhaka", "Railway Station"],
        )

    def test_missing_nominatim_result_uses_photon_only_for_matching_nearby_country(self):
        _openstreetmap_geocode.cache_clear()
        photon_results = {
            "features": [
                {
                    "geometry": {"coordinates": [77.2, 28.6]},
                    "properties": {"country": "India", "name": "Inani"},
                },
                {
                    "geometry": {"coordinates": [92.085879, 21.1506551]},
                    "properties": {"country": "Bangladesh", "name": "Inani National Park"},
                },
                {
                    "geometry": {"coordinates": [92.086, 21.1507]},
                    "properties": {"country": "Bangladesh", "name": "Inani Beach"},
                },
            ],
        }
        with patch(
            "app.research.fetch_json",
            side_effect=[None, photon_results],
        ) as fetch:
            coordinates = _openstreetmap_geocode(
                "Inani Beach, Cox's Bazar",
                country_code="bd",
                country_name="Bangladesh",
                focus=None,
            )

        self.assertEqual(coordinates, (21.1507, 92.086))
        self.assertIn("countrycodes=bd", fetch.call_args_list[0].args[0])
        self.assertIn("photon.komoot.io", fetch.call_args_list[1].args[0])

    def test_geocoding_does_not_substitute_a_nearby_differently_named_place(self):
        _openstreetmap_geocode.cache_clear()
        with patch(
            "app.research.fetch_json",
            side_effect=[
                [{"lat": "21.1506551", "lon": "92.085879", "name": "Inani National Park"}],
                {"features": [{
                    "geometry": {"coordinates": [92.085879, 21.1506551]},
                    "properties": {
                        "country": "Bangladesh",
                        "name": "Inani National Park",
                    },
                }]},
            ],
        ):
            coordinates = _openstreetmap_geocode(
                "Inani Beach, Cox's Bazar",
                country_code="bd",
                country_name="Bangladesh",
                focus=(21.4272, 92.0058),
            )

        self.assertIsNone(coordinates)

    def test_geocoding_rejects_a_matching_name_far_from_the_destination_area(self):
        _openstreetmap_geocode.cache_clear()
        far_result = {
            "lat": "21.1449423",
            "lon": "92.0776515",
            "name": "Cox's Bazar Beach",
        }
        with patch(
            "app.research.fetch_json",
            side_effect=[
                [far_result],
                {"features": [{
                    "geometry": {"coordinates": [92.0776515, 21.1449423]},
                    "properties": {
                        "country": "Bangladesh",
                        "name": "Cox's Bazar Beach",
                    },
                }]},
            ],
        ):
            coordinates = _openstreetmap_geocode(
                "Cox's Bazar Beach, Cox's Bazar",
                country_code="bd",
                country_name="Bangladesh",
                focus=(21.4272, 92.0058),
            )

        self.assertIsNone(coordinates)

    @patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": "test-key"})
    @patch("app.research._openstreetmap_geocode", return_value=(23.8, 90.4))
    @patch("app.research.urlopen")
    def test_invalid_openrouteservice_segment_data_is_not_treated_as_a_route(
        self, mocked_urlopen, _,
    ):
        mocked_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps({
            "features": [{
                "properties": {
                    "summary": {"distance": 1000, "duration": 100},
                    "segments": [{}],
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[90.4, 23.8], [91.0, 24.0]],
                },
            }],
        }).encode("utf-8")

        route = calculate_road_route("Dhaka", "Sylhet", 24.9, 91.8)

        self.assertEqual(route["status"], "unavailable")
        self.assertIsNone(route["distance_km"])
        self.assertIn("could not be displayed", route["note"])

    def test_recommendations_warn_when_no_destination_fits(self):
        request = TripRequest(**trip_payload(budget=1))
        with patch("app.main.wikipedia_research", return_value=None):
            result = recommend_trips(request)

        self.assertTrue(result["budget_warning"].startswith("Your budget is too low"))
        self.assertEqual(result["message"], result["budget_warning"])
        self.assertFalse(result["recommendations"]["within_budget"])

    def test_chat_transport_answer_is_concise_and_uses_local_fare_ranges(self):
        destination = next(place for place in DESTINATIONS if place["name"] == "Sylhet")

        with patch("app.conversation.calculate_road_route", return_value={
            "status": "ready", "distance_km": 244.5,
            "origin": {"lat": 23.8, "lon": 90.4},
            "route_url": "https://www.openstreetmap.org/directions",
        }):
            answer, sources = answer_travel_question(
                "transport", destination, trip_payload(), [], [],
            )

        self.assertLessEqual(len(answer.split()), 60)
        self.assertIn("planning range", answer)
        self.assertIn("coach", answer.lower())
        self.assertFalse(any("google.com" in source["url"] for source in sources))

    def test_chat_can_estimate_a_user_named_local_route_without_google_redirect(self):
        destination = next(place for place in DESTINATIONS if place["name"] == "Sylhet")
        with patch("app.conversation.calculate_road_route", return_value={
            "status": "ready", "distance_km": 10.0,
            "origin": {"lat": 25.8, "lon": 88.9},
            "route_url": "https://www.openstreetmap.org/directions",
        }) as route_calculator:
            answer, sources = answer_travel_question(
                "transport", destination, trip_payload(), [], [],
                message="What is the fare from Saidpur to Railway Station by CNG?",
            )

        self.assertIn("Saidpur to Railway Station", answer)
        self.assertIn("one-way fare range: BDT 200–400", answer)
        self.assertEqual(route_calculator.call_args.args[:2], ("Saidpur", "Railway Station"))
        self.assertFalse(any("google.com" in source["url"] for source in sources))
        self.assertEqual(
            classify_travel_question("Saidpur to Railway Station by CNG"),
            "transport",
        )

if __name__ == "__main__":
    unittest.main()
