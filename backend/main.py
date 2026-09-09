"""
main.py
-------
FastAPI entry point for the Fair Gig Guardian backend.

Run locally:
    cd backend
    uvicorn main:app --reload --port 8000

Environment:
    GROQ_API_KEY=<your_key>   (required)
    REDIS_URL=redis://...     (optional — caching disabled if absent)

Changes from v1.0:
    - analyze_contract() is now async to support the Map-Reduce pipeline's
      asyncio.gather() concurrency in services/pipeline.py.
    - Added structured logging configuration.
    - All Pydantic models and the /analyze response shape are UNCHANGED —
      the React frontend requires zero modifications.
"""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from backend.council_service import run_council

# ── Logging setup ─────────────────────────────────────────────────────────────
# Configure structured logging at startup.  In production, swap the format
# for a JSON formatter and ship logs to your aggregation platform.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Fair Gig Guardian API",
    description=(
        "3-Agent AI Council for contract fairness analysis. "
        "Supports adaptive Map-Reduce pipeline for long contracts."
    ),
    version="2.0.0",
)

# Allow the React dev server (any localhost port) and production origin.
# Adjust origins in production to your actual domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "https://gig-audit-council.onrender.com",  # Vite default
        "https://gig-audit.vercel.app",
        "http://localhost:8080",   # Vite alternate port
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────
# These models are UNCHANGED from v1.0.  The frontend sees the same API surface.

class AnalyzeRequest(BaseModel):
    contract_text: str

    @field_validator("contract_text")
    @classmethod
    def must_have_content(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 50:
            raise ValueError("contract_text must be at least 50 characters.")
        return v


class CategoryScores(BaseModel):
    payment:      int
    termination:  int
    non_compete:  int
    ip:           int
    dispute:      int
    compensation: int


class RiskyClause(BaseModel):
    category:    str
    risk_level:  str
    explanation: str
    suggestion:  str


class AnalyzeResponse(BaseModel):
    overall_score:   int
    category_scores: CategoryScores
    verdict:         str
    risky_clauses:   list[RiskyClause]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    """Quick liveness probe."""
    return {"status": "ok", "service": "Fair Gig Guardian API", "version": "2.0.0"}


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_contract(body: AnalyzeRequest) -> AnalyzeResponse:
    """
    Run the GigAudit AI Council on the provided contract text.

    - **contract_text**: The raw text of the gig contract (≥ 50 chars).

    For short contracts (≤ 6 000 tokens) the pipeline runs a single Auditor
    call.  For longer contracts it automatically switches to the Map-Reduce
    chunked pipeline with parallel Auditor agents and semantic deduplication.

    Returns a structured fairness analysis with scores, verdict, and
    per-clause negotiation guidance.  The response shape is identical to v1.0.
    """
    logger.info(
        "[main] /analyze request received — contract length: %d chars.",
        len(body.contract_text),
    )
    try:
        result = await run_council(body.contract_text)
    except EnvironmentError as exc:
        # GROQ_API_KEY missing
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        logger.exception("[main] Unexpected error during analysis: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Analysis failed. Please try again or contact support.",
        )

    # Validate and return — Pydantic will raise 422 on bad shapes
    return AnalyzeResponse(**result)
