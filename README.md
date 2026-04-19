# RouteScout

A natural-language hiking trip planner for Yosemite National Park. Describe the trip you want — *"3-day loop that camps at lakes, around 10 miles a day"* — and get back a day-by-day itinerary with a routed map, an elevation profile, and a written plan.

## How it works

An LLM parses the prompt into a structured trip spec (duration, target mileage, feature preferences, difficulty). The planner then searches over a trail graph built from OpenStreetMap data, scoring multi-day paths by how closely they match the requested features and mileage. A narrative generator writes the final day-by-day description from the resolved route.

- **Trail graph** — OSMnx + NetworkX, bounded to Yosemite. Elevation from SRTM. Difficulty weighted by OSM `sac_scale` tags.
- **Prompt parsing** — Gemini 2.5 Flash with structured JSON output.
- **Routing** — A\* for single-day segments, beam search across feature-weighted multi-day paths.
- **Narrative generation** — Gemini writes the trip description from the resolved itinerary.

## Tech

Python 3.12 · FastAPI · OSMnx · NetworkX · Gemini · React · Vite · TypeScript · Leaflet · recharts
