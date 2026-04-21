# Backend container — multi-stage to keep the runtime image small.
# OSMnx + geopandas pull in heavy native deps (GDAL, GEOS, PROJ, Spatialindex);
# we install them into a build stage and only ship the resolved venv to the
# runtime stage.

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Native deps OSMnx / geopandas / rasterio need at install time.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgeos-dev \
    libproj-dev \
    libspatialindex-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt ./
RUN python -m venv /venv && \
    /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install -r requirements.txt


# ──────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/venv/bin:$PATH"

# Runtime native libs (smaller subset — no -dev packages needed).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-c1v5 \
    libproj25 \
    libspatialindex6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /venv /venv

WORKDIR /app

# App code
COPY . /app/backend
# Pre-built data caches (graph, features, trailheads, camps) — much faster
# than rebuilding on every container start, and the data is static enough
# that committing the snapshot is fine.
COPY data /app/data

EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
