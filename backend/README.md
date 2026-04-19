# backend

FastAPI service. Parses prompts, plans itineraries over the Yosemite trail graph, returns GeoJSON + narrative.

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add GEMINI_API_KEY
```
