# TripMate local AI agent and routing setup

TripMate answers tourism questions with its own Python service, a local
SQLite/FTS5 knowledge base, and a CPU-running Qwen GGUF model through
llama.cpp. Inference does not use Gemini, ChatGPT, or another hosted AI API.
Trip-planning, route, fare, and budget calculations remain deterministic Python
tools; they are not delegated to the language model. For open-ended questions,
Qwen selects from a bounded set of validated research tools: local knowledge
search, DuckDuckGo web search, and extraction of pages returned by that search.
Python executes the requested tools and supplies their results back to Qwen for
up to two sequential tool calls before answer generation.
Common budget questions use the active itinerary's exact estimate and cost
breakdown, so that answer does not wait on local model inference.

## Set up the local model

Use 64-bit Python 3.14 on Windows (tested with the prebuilt CPU wheel), then
from this directory create the environment and install the requirements:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Download the Apache-2.0 Qwen3 1.7B Q8 GGUF model (about 1.8 GB):

```powershell
.\download-model.ps1
```

If your PowerShell execution policy blocks local scripts, create `models` and
run the download directly in that PowerShell session instead:

```powershell
New-Item -ItemType Directory -Force .\models | Out-Null
Invoke-WebRequest -Uri 'https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q8_0.gguf?download=true' -OutFile '.\models\Qwen3-1.7B-Q8_0.gguf'
```

The default model path is `models/Qwen3-1.7B-Q8_0.gguf`. Set
`TRIPMATE_MODEL_PATH` in `.env` to override it. The model runs on CPU by
default; `TRIPMATE_MODEL_THREADS` and `TRIPMATE_CONTEXT_TOKENS` control its
thread and context limits. The first generated answer may take time while
llama.cpp loads the model. Check `/health` for the runtime, model, and local
knowledge-base status.

Start the agent from this directory so Laravel can reach its default local
endpoint at `http://127.0.0.1:8001`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

## Local tourism knowledge

On first use, TripMate indexes its built-in destination and suggested-route
catalog in `data/tripmate_knowledge.sqlite3`. Add curated, sourced `.md` or
`.txt` notes under `data/knowledge/` to extend it. For externally sourced
notes, put a secure source link on the first line:

```text
Source-URL: https://example.org/trusted-tourism-source
# Destination or attraction

Describe its location, significance, visitor activities, and any limits on
what is known. Avoid embedding changing prices or access notices as timeless
facts.
```

The index is created lazily and cached by the running service. Markdown and text
notes are re-indexed automatically when their file changes; Python code changes
are picked up by Uvicorn's development reload. Documents without a source URL
are still retrieved locally but are not presented as external links. If local
retrieval finds no relevant note, the research planner can search the web and extract
pages instead of stopping immediately. Search results and page text are
retrieved at request time, but are not independently fact-checked; the model is
instructed to use only retrieved evidence and to abstain when it is insufficient.
Starter sourced notes cover the Sundarbans,
Bagerhat, and Paharpur using UNESCO World Heritage descriptions; other places
start with TripMate's own short catalog and route notes. Extend or correct the
curated notes to improve coverage; the model weights and generated SQLite
index are ignored by Git.

Generated replies are checked against retrieved terms; if the model adds
unsupported content words, TripMate abstains and keeps the source links rather
than displaying raw knowledge excerpts. This is a conservative lexical
safeguard, not a formal proof that every sentence is entailed by its sources.
Keep the notes trusted and verify important travel decisions with current
official sources.

Non-BDT budgets are converted to BDT for destination ranking and budget checks,
then estimates are converted back using ExchangeRate-API Open Access data
(cached for up to six hours). If a rate cannot be retrieved, the agent returns
an explicit service error instead of comparing amounts in different currencies.
Transport fare ranges remain labeled in BDT because their underlying planning
assumptions are BDT-based; they are not current operator quotes.

The model's license, runtime, and knowledge base are self-managed locally.
Some existing TripMate features still use public non-AI services for optional
research, weather, geocoding, and routing; those are described below.

TripMate displays OpenStreetMap tiles and geocodes places with OpenStreetMap
Nominatim, with a country-checked Photon fallback for missing locations.
Candidates must match the requested place name and be within 25 km of the
destination area; a distant or differently named feature is left unmapped
rather than mislabeled.
Driving distance and duration are calculated
with OpenRouteService using OpenStreetMap data. If no OpenRouteService key is
configured, TripMate tries the public OSRM router for driving routes instead.
Both providers return road routes only, not live traffic or public-transport
routes; availability and usage limits depend on the provider.

To use OpenRouteService as the preferred driving router:

1. Create a key in your OpenRouteService account.
2. Add `OPENROUTESERVICE_API_KEY=your-key` to `tripmate-agent/.env`.
   Keep `.env` local; do not commit or share the key.
3. Restart the Python agent.

Copy `.env.example` as a starting point. Without the key, TripMate falls back
to the public OSRM service. If neither router is reachable, it still shows
OpenStreetMap pins but does not invent a distance-based fare range.

OpenRouteService's `driving-car` profile describes a road route only. It does
not calculate bus, train, ferry, flight, fare, or live-traffic data.

`app/transport.py` contains local BDT/km planning ranges for intercity bus,
train, CNG, auto-rickshaw, cycle rickshaw, and ride-sharing. The ranges are
transparent planning assumptions, not verified or live operator fares. They
are multiplied by OpenRouteService route distances and shown by route segment;
per-passenger fares scale with traveler count, while hired local vehicle fares
are estimated per vehicle. Any ferry/boat leg or segment without a calculated
route is excluded from the subtotal and marked as partial/unavailable.

Transportation questions are answered by TripMate's Python agent, including
one-way user-specified origin/destination questions. They do not redirect to
Google fare searches. Always confirm current operator fares, schedules, access
restrictions, and road conditions before travel.
