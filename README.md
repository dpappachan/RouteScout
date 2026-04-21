# RouteScout

A natural-language hiking trip planner for the Sierra Nevada. You type something like *"3-day loop from Tuolumne camping at lakes, 9 miles a day"* and get back a routed map, a day-by-day breakdown, an elevation profile, the wilderness regulations you'll actually need, and a written trip plan.

![Trail graph](data/sierra_graph.png)

## How it works

There are three steps and they happen in this order:

1. **Parse the prompt.** A Gemini 2.5 Flash-Lite call maps the request to a structured trip spec — start trailhead, days, miles per day, what to camp near, named must-visits. The output is constrained to a Pydantic schema server-side, so the LLM can't drift the shape. Vague prompts (`easy`, `weekend`, `day hike`) get sensible defaults.

2. **Plan the route.** This is the part with the actual algorithms in it. A\* with a great-circle heuristic picks the shortest path within a single day. Beam search across overnight camps stitches multiple days together. Camps aren't a hand-picked list — they're every graph node with a max local edge grade < 10% (flat enough for a tent) within 700 m of a curated water feature (water for cooking). The optimizer tracks visited edges and penalizes reused trails so it prefers actual loops over figure-8s. If feature-preference scoring pushes the top-K beam toward dead-ends, it widens to 24 → 36 candidates before declaring infeasibility.

3. **Write it up.** A second Gemini call generates the trip narrative. It only sees the resolved itinerary (camps, distances, features), so it can't invent things that aren't actually on your route.

## Coverage

Yosemite NP plus the contiguous wilderness areas backpackers actually go through:

- **Yosemite National Park** (NPS)
- **Ansel Adams Wilderness** (Inyo NF) — JMT corridor, Thousand Island Lake, Banner Peak
- **Hoover Wilderness** (Humboldt-Toiyabe NF) — Twin Lakes, Matterhorn Peak
- **Emigrant Wilderness** (Stanislaus NF) — Sonora Pass, Kennedy Meadows

About 2,200 trail nodes, 5,200 edges, 343 named features (175 lakes, 72 peaks, 33 viewpoints, 24 waterfalls, 21 passes, 18 meadows). Each wilderness has a different managing agency with a different permit process, so the regulations layer is per-region — you get the right permit info attached to your trip automatically. Half Dome cables, Donohue Pass cross-jurisdiction, Tioga / Glacier Point / Sonora Pass road closures all detected based on the route and start trailhead.

## Stack

Python 3.12, FastAPI, OSMnx, NetworkX, scikit-learn (for snap-to-graph), Gemini 2.5 Flash-Lite. React 19 + Vite + Tailwind on the frontend with Leaflet for the map and recharts for the elevation chart. OpenTopoMap tiles. Hosted on Render (backend, Docker) + Vercel (frontend).

## Running it locally

```bash
# Backend (Python 3.12)
cd backend && python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your GEMINI_API_KEY
uvicorn backend.api.main:app --reload

# Frontend (Node ≥ 20.19, in another terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:5173.

The trail graph, features, trailheads, and camp candidates are precomputed and committed into `data/`, so first request is fast. To rebuild from scratch (takes a few minutes for the OSM download + elevation API calls):

```bash
python -m backend.graph.build --rebuild
python -m backend.graph.features
python -m backend.graph.trailheads
python -m backend.graph.camps
```

## Tests

```bash
cd backend && pytest tests
```

26 tests covering the optimizer (per-day target scaling, edge dedupe, day-hike branch, unknown-start error), pathfinder (haversine, A\*, length sum, ascent-only gain), parser tolerant lookup (case, parens, suffix add/remove, "X or Y" disjunction), and trip spec invariants. Runs in about a second; no network or LLM calls.

## What's still rough

- **OSM coverage outside Yosemite is patchy.** Some Hoover and Emigrant trailheads can't snap to the hiking-only graph and got dropped. Mt Dana, Lukens Lake, and Mariposa Grove are in the source JSON but didn't make it through.
- **Naismith time estimates ignore trail surface.** A talus scramble and a smooth fire road of the same distance get the same hours.
- **Some "loops" are really out-and-backs in disguise.** The edge-reuse penalty discourages it but can't always avoid it when only one trail leaves the trailhead.
