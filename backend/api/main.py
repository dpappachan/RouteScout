"""FastAPI entry point — POST /plan is the main route.

Run locally:
    uvicorn backend.api.main:app --reload
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings
from .models import ErrorResponse, HealthResponse, PlanRequest, PlanResponse
from .service import PlannerError, plan_from_prompt
from .state import STATE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
log = logging.getLogger("routescout.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup: preloading graph and features")
    STATE.load()
    log.info(
        "ready: %d graph nodes, %d edges, %d features",
        STATE.graph.number_of_nodes(), STATE.graph.number_of_edges(), len(STATE.features),
    )
    yield
    log.info("shutdown")


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="RouteScout",
    description="Natural-language hiking route planner for Yosemite.",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=ErrorResponse(error="rate_limited", detail=str(exc.detail)).model_dump(),
    )


@app.exception_handler(PlannerError)
async def planner_error_handler(request: Request, exc: PlannerError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(error="no_plan", detail=str(exc)).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    log.exception("unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(error="internal", detail="An unexpected error occurred.").model_dump(),
    )


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        graph_nodes=STATE.graph.number_of_nodes(),
        graph_edges=STATE.graph.number_of_edges(),
        features=len(STATE.features),
        plans_served_today=STATE.plans_today(),
    )


@app.post("/plan", response_model=PlanResponse, responses={
    status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": ErrorResponse},
    status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse},
    status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
})
@limiter.limit(settings().plan_rate_limit)
def post_plan(request: Request, body: PlanRequest):
    today_count = STATE.bump_daily_counter()
    cap = settings().daily_plan_cap
    if today_count > cap:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Daily plan cap of {cap} reached; try again tomorrow.",
        )

    return plan_from_prompt(body.prompt, beam_width=settings().beam_width)
