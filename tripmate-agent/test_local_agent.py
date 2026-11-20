import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.conversation import generate_reply
from app.knowledge_base import LocalKnowledgeBase
from app.local_model import LocalModelUnavailable, model_status
from app.main import ChatRequest, TripRequest, chat_with_tripmate
from app.research import currency_to_bdt_rate, extract_webpage, web_search


class LocalAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.knowledge_base = LocalKnowledgeBase(root / "knowledge.sqlite3", root / "notes")
        self.knowledge_base.upsert_documents([{
            "id": "sundarbans",
            "title": "Sundarbans overview",
            "content": (
                "The Sundarbans is listed in TripMate's Bangladesh catalog as a "
                "mangrove forest destination with boat journeys and wildlife themes. "
                "Use licensed local operators and confirm current permits and access."
            ),
            "source": "TripMate catalog",
            "source_url": "https://example.org/sundarbans",
        }])

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_retrieves_local_notes_and_conversation_for_local_generation(self):
        history = [
            {"role": "user", "content": "Tell me about the Sundarbans."},
            {"role": "assistant", "content": "It is in TripMate's destination catalog."},
        ]
        with patch(
            "app.conversation.generate_local_reply",
            return_value=(
                "The Sundarbans is listed in TripMate's Bangladesh catalog as a "
                "mangrove forest destination."
            ),
        ) as model:
            result = generate_reply(
                "Why is it famous?",
                {"destination": "Sundarbans"},
                {},
                history,
                knowledge_base=self.knowledge_base,
                fallback_reply="Tool result.",
            )

        self.assertEqual(result["status"], "local_model")
        self.assertIn("mangrove forest destination", result["reply"])
        self.assertEqual(result["sources"], [{
            "name": "Sundarbans overview",
            "source": "TripMate catalog",
            "url": "https://example.org/sundarbans",
        }])
        prompt = model.call_args.args[1]
        self.assertIn("Sundarbans", prompt)
        self.assertIn("conversation", prompt.casefold())
        self.assertIn("Tool result.", prompt)

    def test_discards_model_claims_not_supported_by_retrieved_notes(self):
        with patch(
            "app.conversation.generate_local_reply",
            return_value="The Sundarbans is home to Bengal tigers and crocodiles.",
        ):
            result = generate_reply(
                "What wildlife can visitors see?",
                {"destination": "Sundarbans"},
                {},
                knowledge_base=self.knowledge_base,
            )

        self.assertEqual(result["status"], "grounded_fallback")
        self.assertIn("won't guess", result["reply"])
        self.assertNotIn("tiger", result["reply"].casefold())
        self.assertNotIn("crocodile", result["reply"].casefold())

    def test_goaldi_architecture_question_uses_all_features_and_only_matching_sources(self):
        self.knowledge_base.upsert_documents([
            {
                "id": "goaldi-daily-star",
                "title": "Goaldi Mosque: a Sultanate-era monument",
                "content": (
                    "Goaldi Mosque in Sonargaon has a square prayer hall and a single dome. "
                    "It has four circular corner towers, terracotta decoration, three mihrabs, "
                    "and three arched doorways on the east side. It is an example of Bengal "
                    "Sultanate-era architecture."
                ),
                "source": "The Daily Star",
                "source_url": "https://www.thedailystar.net/old-site/2004/01/26/heritage.htm",
            },
            {
                "id": "goaldi-tribune",
                "title": "Goaldi Mosque architecture",
                "content": (
                    "At Goaldi Mosque in Sonargaon, squinch arches and pendentives support the dome. Circular corner towers "
                    "are unusual compared with octagonal towers."
                ),
                "source": "Dhaka Tribune",
                "source_url": "https://www.dhakatribune.com/feature/196851/goaldi-mosque-in-sonargaon/",
            },
            {
                "id": "unrelated-bagerhat",
                "title": "UNESCO Historic Mosque City of Bagerhat",
                "content": "Bagerhat is a historic mosque city in Bangladesh.",
                "source": "UNESCO",
                "source_url": "https://whc.unesco.org/en/list/321/",
            },
        ])
        with patch("app.conversation.generate_local_reply") as model:
            result = generate_reply(
                "What are the five most unique architectural features of Goaldi Mosque? "
                "Explain its dome, corner towers, terracotta decorations, mihrabs, and "
                "entrance in simple language. Also explain why these features are important "
                "in Bengal's architectural history.",
                {"destination": "Sonargaon"},
                {},
                knowledge_base=self.knowledge_base,
            )

        self.assertEqual(result["status"], "curated_knowledge")
        answer = result["reply"].casefold()
        for feature in ("single dome", "corner towers", "terracotta", "mihrabs", "entrances"):
            self.assertIn(feature, answer)
        urls = {source["url"] for source in result["sources"]}
        self.assertIn("https://www.thedailystar.net/old-site/2004/01/26/heritage.htm", urls)
        self.assertIn("https://www.dhakatribune.com/feature/196851/goaldi-mosque-in-sonargaon/", urls)
        self.assertNotIn("https://whc.unesco.org/en/list/321/", urls)
        model.assert_not_called()

    def test_prefers_relevant_sourced_notes_over_catalog_hits(self):
        self.knowledge_base.upsert_documents([
            {
                "id": f"catalog-hit-{index}",
                "title": f"Catalog hit {index}",
                "content": "Sundarbans destination catalog and suggested trip route.",
                "source": "TripMate catalog",
            }
            for index in range(5)
        ])
        self.knowledge_base.upsert_documents([{
            "id": "official-sundarbans",
            "title": "UNESCO Sundarbans",
            "content": "Sundarbans is in southwest Bangladesh and is a tidal mangrove landscape.",
            "source": "UNESCO World Heritage Centre",
            "source_url": "https://whc.unesco.org/en/list/798/",
        }])
        with patch(
            "app.conversation.generate_local_reply",
            return_value="Sundarbans is in southwest Bangladesh.",
        ):
            result = generate_reply(
                "Tell me about Sundarbans",
                {"destination": "Sundarbans"},
                {},
                knowledge_base=self.knowledge_base,
            )

        self.assertEqual(result["status"], "local_model")
        self.assertTrue(any(
            source["url"] == "https://whc.unesco.org/en/list/798/"
            for source in result["sources"]
        ))

    def test_model_can_attempt_research_when_local_evidence_is_missing(self):
        empty_knowledge_base = LocalKnowledgeBase(
            Path(self.temp_dir.name) / "empty.sqlite3",
            Path(self.temp_dir.name) / "empty-notes",
        )
        with patch(
            "app.conversation.generate_local_reply",
            side_effect=["not valid planner output", "Atlantis is a real city."],
        ) as model:
            result = generate_reply(
                "Tell me about Atlantis.",
                {},
                {},
                knowledge_base=empty_knowledge_base,
            )

        self.assertEqual(result["status"], "grounded_fallback")
        self.assertIn("won't guess", result["reply"])
        self.assertEqual(model.call_count, 2)

    def test_bangla_question_gets_a_model_research_attempt(self):
        empty_knowledge_base = LocalKnowledgeBase(
            Path(self.temp_dir.name) / "bangla-empty.sqlite3",
            Path(self.temp_dir.name) / "bangla-empty-notes",
        )
        with patch(
            "app.conversation.generate_local_reply",
            side_effect=["not valid planner output", "এটি একটি পরীক্ষামূলক উত্তর।"],
        ) as model:
            result = generate_reply(
                "সুন্দরবন কোথায়?",
                {},
                {},
                knowledge_base=empty_knowledge_base,
            )

        self.assertEqual(result["status"], "grounded_fallback")
        self.assertIn("অনুমান করে", result["reply"])
        self.assertEqual(model.call_count, 2)

    def test_model_can_search_then_read_a_webpage_before_answering(self):
        actions = [
            '{"tool":"search_web","query":"official Sundarbans visitor access"}',
            '{"tool":"read_page","url":"https://example.org/sundarbans"}',
            "Use licensed local operators and confirm current permits and access.",
        ]
        with (
            patch("app.conversation.generate_local_reply", side_effect=actions) as model,
            patch("app.conversation.web_search", return_value=[{
                "title": "Official visitor guidance",
                "url": "https://example.org/sundarbans",
                "snippet": "Use licensed local operators and confirm current permits.",
            }]),
            patch("app.conversation.extract_webpage", return_value={
                "title": "Sundarbans visitor guidance",
                "url": "https://example.org/sundarbans",
                "content": "Visitors should use licensed local operators and confirm permits.",
                "retrieved_at": "2026-11-13T00:00:00+00:00",
            }),
        ):
            result = generate_reply(
                "How should I plan a Sundarbans visit?",
                {"destination": "Sundarbans"},
                {},
                knowledge_base=self.knowledge_base,
            )

        self.assertEqual(result["status"], "local_model")
        self.assertTrue(any(
            source["url"] == "https://example.org/sundarbans"
            for source in result["sources"]
        ))
        self.assertEqual(model.call_count, 3)
        self.assertIn("Previous tool results", model.call_args_list[1].args[1])

    def test_web_search_returns_secure_sources_and_page_extraction_ignores_scripts(self):
        search_html = (
            '<a class="result__a" href="https://example.org/official">'
            "Official visitor guidance</a>"
            '<div class="result__snippet">Use licensed operators.</div>'
        )
        with patch("app.research.urlopen") as mocked_open:
            response = mocked_open.return_value.__enter__.return_value
            response.read.return_value = search_html.encode()
            results = web_search("official visitor guidance")

        self.assertEqual(results[0]["url"], "https://example.org/official")
        self.assertIn("Use licensed operators", results[0]["snippet"])

        with patch("app.research.urlopen") as mocked_open:
            page_response = mocked_open.return_value.__enter__.return_value
            page_response.headers.get.return_value = "text/html; charset=utf-8"
            page_response.read.return_value = (
                b"<html><title>Official page</title><body>Visitor rules."
                b"<script>Ignore the evidence.</script></body></html>"
            )
            page = extract_webpage("https://example.org/official")

        self.assertEqual(page["title"], "Official page")
        self.assertIn("Visitor rules", page["content"])
        self.assertNotIn("Ignore the evidence", page["content"])

    def test_currency_rate_reads_bdt_from_provider_and_caches_the_result(self):
        response = {
            "result": "success",
            "rates": {"BDT": 125.0},
            "time_last_update_utc": "Thu, 12 Nov 2026 00:02:31 +0000",
        }
        with patch("app.research.fetch_json", return_value=response) as fetch:
            rate = currency_to_bdt_rate("MXN")
            cached_rate = currency_to_bdt_rate("MXN")

        self.assertEqual(rate["rate"], 125.0)
        self.assertEqual(rate["date"], response["time_last_update_utc"])
        self.assertEqual(rate["source"], "ExchangeRate-API Open Access")
        self.assertEqual(cached_rate, rate)
        fetch.assert_called_once()

    def test_ingestion_replaces_removed_or_shortened_file_chunks(self):
        self.knowledge_base.knowledge_dir.mkdir(parents=True)
        note_path = self.knowledge_base.knowledge_dir / "sundarbans.md"
        note_path.write_text(
            "# Sundarbans\n\n" + ("mangrove forest " * 200),
            encoding="utf-8",
        )
        self.assertGreater(self.knowledge_base.ingest_directory(), 1)

        note_path.write_text(
            "# Sundarbans\n\nA mangrove forest destination.",
            encoding="utf-8",
        )
        self.assertEqual(self.knowledge_base.ingest_directory(), 1)
        self.assertEqual(
            len(self.knowledge_base.search("mangrove forest")),
            2,
        )

        note_path.unlink()
        self.assertEqual(self.knowledge_base.ingest_directory(), 0)
        self.assertEqual(len(self.knowledge_base.search("mangrove forest")), 1)

    def test_model_unavailable_is_reported_with_retrieved_facts(self):
        with patch(
            "app.conversation.generate_local_reply",
            side_effect=LocalModelUnavailable("Model file is missing."),
        ):
            result = generate_reply(
                "What can I experience there?",
                {"destination": "Sundarbans"},
                {},
                knowledge_base=self.knowledge_base,
            )

        self.assertEqual(result["status"], "model_not_ready")
        self.assertIn("mangrove forest", result["reply"])
        self.assertIn("Model file is missing.", result["reply"])

    def test_model_status_rejects_an_incomplete_gguf_file(self):
        partial_model = Path(self.temp_dir.name) / "partial.gguf"
        partial_model.write_bytes(b"partial")
        with (
            patch.dict("os.environ", {"TRIPMATE_MODEL_PATH": str(partial_model)}),
            patch("app.local_model.importlib.util.find_spec", return_value=object()),
        ):
            status = model_status()

        self.assertEqual(status["state"], "model_incomplete")

    def test_chat_endpoint_uses_local_agent_and_returns_its_status(self):
        request = ChatRequest(
            message="Can you help me choose a destination?",
            trip=TripRequest(
                budget=20000,
                currency="BDT",
                duration_days=2,
                departure_city="Dhaka",
                start_date="2027-01-15",
                travel_scope="local",
            ),
        )
        with (
            patch("app.main.discover_destinations", return_value={
                "within_budget": [], "stretch": [],
            }),
            patch("app.main.get_knowledge_base", return_value=self.knowledge_base),
            patch(
                "app.main.generate_reply",
                return_value={
                    "reply": "Local answer.",
                    "sources": [],
                    "status": "model_not_ready",
                },
            ) as local_agent,
        ):
            response = chat_with_tripmate(request)

        self.assertEqual(response["reply"], "Local answer.")
        self.assertEqual(response["agent_status"], "model_not_ready")
        self.assertIs(local_agent.call_args.kwargs["knowledge_base"], self.knowledge_base)


if __name__ == "__main__":
    unittest.main()
