"""Local SQLite full-text knowledge store for tourism RAG."""

import os
import re
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


_ROOT = Path(__file__).resolve().parents[1]
_STOP_WORDS = {
    "a", "an", "and", "are", "about", "at", "can", "do", "does", "for", "from",
    "how", "i", "in", "is", "it", "me", "of", "on", "or", "please", "tell",
    "the", "this", "to", "was", "what", "where", "why", "with", "you",
}
_DESTINATION_ALIASES = {
    "Sylhet": "সিলেট", "Sreemangal": "শ্রীমঙ্গল", "Jaflong": "জাফলং",
    "Tanguar Haor": "টাঙ্গুয়ার হাওর", "Cox's Bazar": "কক্সবাজার",
    "Saint Martin's Island": "সেন্ট মার্টিন দ্বীপ", "Bandarban": "বান্দরবান",
    "Sajek Valley": "সাজেক ভ্যালি", "Khagrachhari": "খাগড়াছড়ি",
    "Rangamati": "রাঙামাটি", "Kuakata": "কুয়াকাটা", "Chattogram": "চট্টগ্রাম",
    "Sundarbans": "সুন্দরবন", "Bagerhat": "বাগেরহাট", "Sonargaon": "সোনারগাঁও",
    "Paharpur": "পাহাড়পুর", "Mahasthangarh": "মহাস্থানগড়",
    "Rajshahi": "রাজশাহী", "Dhaka": "ঢাকা", "Kathmandu": "কাঠমান্ডু",
    "Thimphu": "থিম্পু", "Tokyo": "টোকিও", "Kolkata": "কলকাতা",
    "Bangkok": "ব্যাংকক",
}
_TAG_TRANSLATIONS = {
    "adventure": "অভিযান", "archaeology": "প্রত্নতত্ত্ব", "architecture": "স্থাপত্য",
    "beach": "সমুদ্র সৈকত", "culture": "সংস্কৃতি", "food": "খাবার",
    "forest": "বন", "history": "ইতিহাস", "lake": "হ্রদ", "mountain": "পাহাড়",
    "museum": "জাদুঘর", "nature": "প্রকৃতি", "photography": "ফটোগ্রাফি",
    "relax": "বিশ্রাম", "tea": "চা বাগান", "waterfall": "ঝরনা",
}


def destination_alias(name: str) -> str:
    """Return a known Bangla spelling for a catalog destination."""
    return _DESTINATION_ALIASES.get(name, "")


def knowledge_paths() -> tuple[Path, Path]:
    """Return the configured local database and editable document directory."""
    database_value = os.getenv("TRIPMATE_KNOWLEDGE_DB", "").strip()
    database_path = Path(database_value) if database_value else _ROOT / "data" / "tripmate_knowledge.sqlite3"
    if not database_path.is_absolute():
        database_path = _ROOT / database_path
    directory_value = os.getenv("TRIPMATE_KNOWLEDGE_DIR", "").strip()
    knowledge_dir = Path(directory_value) if directory_value else _ROOT / "data" / "knowledge"
    if not knowledge_dir.is_absolute():
        knowledge_dir = _ROOT / knowledge_dir
    return database_path, knowledge_dir


class LocalKnowledgeBase:
    """Persist local source documents and retrieve relevant chunks with SQLite FTS5."""

    def __init__(self, database_path: Path, knowledge_dir: Path):
        self.database_path = database_path
        self.knowledge_dir = knowledge_dir
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        connection = sqlite3.connect(self.database_path, timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_url TEXT
                )
            """)
            connection.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_search
                USING fts5(id UNINDEXED, title, content, tokenize='unicode61')
            """)

    def upsert_documents(self, documents: list[dict[str, Any]]) -> None:
        with self._connect() as connection:
            self._write_documents(connection, documents)

    @staticmethod
    def _write_documents(
        connection: sqlite3.Connection,
        documents: list[dict[str, Any]],
    ) -> None:
        for document in documents:
            document_id = str(document["id"])
            title = str(document["title"]).strip()
            content = str(document["content"]).strip()
            if not title or not content:
                continue
            connection.execute(
                "DELETE FROM knowledge_search WHERE id = ?",
                (document_id,),
            )
            connection.execute(
                """
                INSERT INTO knowledge_documents (id, title, content, source, source_url)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    source = excluded.source,
                    source_url = excluded.source_url
                """,
                (
                    document_id,
                    title,
                    content,
                    str(document.get("source", "TripMate local knowledge base")),
                    document.get("source_url"),
                ),
            )
            connection.execute(
                "INSERT INTO knowledge_search (id, title, content) VALUES (?, ?, ?)",
                (document_id, title, content),
            )

    def index_catalog(
        self,
        destinations: list[dict[str, Any]],
        route_catalog: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Index destination facts and route stops already curated in TripMate."""
        documents: list[dict[str, Any]] = []
        for destination in destinations:
            name = destination["name"]
            country = destination["country"]
            seen_attractions: set[str] = set()
            tags = [str(tag) for tag in destination.get("tags", [])]
            translated_tags = [
                _TAG_TRANSLATIONS[tag.casefold()]
                for tag in tags if tag.casefold() in _TAG_TRANSLATIONS
            ]
            alias = _DESTINATION_ALIASES.get(name, "")
            routes = route_catalog.get(name, [])
            route_details = [
                f"{route['area']}: {', '.join(route['places'])}"
                for route in routes
            ]
            content = (
                f"{name} {alias} is a TripMate catalog destination in {country}. "
                f"Catalog description: {destination['summary']} "
                f"Catalog themes: {', '.join(tags)} {', '.join(translated_tags)}. "
                f"Suggested itinerary areas and stops: {'; '.join(route_details)}. "
                "These are TripMate starter-catalog notes, not current opening hours, "
                "prices, access notices, or independently verified local advice."
            )
            documents.append({
                "id": f"catalog:destination:{name.casefold()}",
                "title": f"{name} ({alias}) — destination overview",
                "content": content,
                "source": "TripMate starter destination catalog",
            })
            for route in routes:
                for place in route["places"]:
                    if place.casefold() in seen_attractions:
                        continue
                    seen_attractions.add(place.casefold())
                    documents.append({
                        "id": f"catalog:attraction:{name.casefold()}:{place.casefold()}",
                        "title": f"{place} — suggested stop near {name}",
                        "content": (
                            f"{place} is listed as a suggested stop in TripMate's "
                            f"{name}, {country} itinerary, in the area {route['area']}. "
                            f"Other stops in this suggested route: "
                            f"{', '.join(route['places'])}. The local catalog does not "
                            "provide a verified history, opening hours, ticket price, "
                            "or current access information for this stop."
                        ),
                        "source": "TripMate starter itinerary catalog",
                    })
        self.upsert_documents(documents)

    def ingest_directory(self) -> int:
        """Index local Markdown/text notes with optional Source-URL metadata."""
        if not self.knowledge_dir.exists():
            return 0
        documents = []
        for path in sorted(self.knowledge_dir.rglob("*")):
            if not path.is_file() or path.suffix.casefold() not in {".md", ".txt"}:
                continue
            if path.name.casefold() == "readme.md":
                continue
            text = path.read_text(encoding="utf-8").strip()
            source_url = None
            lines = text.splitlines()
            if lines and lines[0].casefold().startswith("source-url:"):
                source_url = lines.pop(0).split(":", 1)[1].strip()
                text = "\n".join(lines).strip()
            heading = next(
                (line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")),
                path.stem.replace("_", " ").replace("-", " ").title(),
            )
            for index, chunk in enumerate(_split_chunks(text), start=1):
                documents.append({
                    "id": f"file:{path.relative_to(self.knowledge_dir).as_posix()}:{index}",
                    "title": heading,
                    "content": chunk,
                    "source": path.relative_to(self.knowledge_dir).as_posix(),
                    "source_url": source_url,
                })
        with self._connect() as connection:
            connection.execute("DELETE FROM knowledge_search WHERE id LIKE 'file:%'")
            connection.execute("DELETE FROM knowledge_documents WHERE id LIKE 'file:%'")
            self._write_documents(connection, documents)
        return len(documents)

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        terms = [
            term for term in dict.fromkeys(re.findall(r"[\w]+", query, flags=re.UNICODE))
            if len(term) > 1 and term.casefold() not in _STOP_WORDS
        ][:32]
        if not terms:
            return []
        match_expression = " OR ".join(f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT d.id, d.title, d.content, d.source, d.source_url,
                       bm25(knowledge_search) AS relevance
                FROM knowledge_search
                JOIN knowledge_documents AS d ON d.id = knowledge_search.id
                WHERE knowledge_search MATCH ?
                ORDER BY relevance
                LIMIT ?
                """,
                (match_expression, max(1, min(limit, 10))),
            ).fetchall()
        return [dict(row) for row in rows]

    def document_count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM knowledge_documents").fetchone()
        return int(row["count"])


def _split_chunks(text: str, max_characters: int = 1200) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > max_characters:
            chunks.append(current)
            current = ""
        if len(paragraph) > max_characters:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(
                paragraph[start:start + max_characters]
                for start in range(0, len(paragraph), max_characters)
            )
        else:
            current = f"{current}\n\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks
