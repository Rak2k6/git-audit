"""
main.py
-------
FastAPI entry point for the Fair Gig Guardian backend.

Run locally:
    cd backend
    uvicorn main:app --reload --port 8000

Environment:
    GROQ_API_KEY=<your_key>   (required)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from backend.council_service import run_council

# ── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Fair Gig Guardian API",
    description="3-Agent AI Council for contract fairness analysis",
    version="1.0.0",
)

# Allow the React dev server (any localhost port) and production origin.
# Adjust origins in production to your actual domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "https://gig-audit-council.onrender.com/",  # Vite default
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
    overall_score:    int
    category_scores:  CategoryScores
    verdict:          str
    risky_clauses:    list[RiskyClause]


# ── Routes ───────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def health_check():
    """Quick liveness probe."""
    return {"status": "ok", "service": "Fair Gig Guardian API"}


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
def analyze_contract(body: AnalyzeRequest) -> AnalyzeResponse:
    """
    Run the 3-Agent AI Council on the provided contract text.

    - **contract_text**: The raw text of the gig contract (≥ 50 chars).

    Returns a structured fairness analysis with scores, verdict, and
    per-clause negotiation guidance.
    """
    try:
        result = run_council(body.contract_text)
    except EnvironmentError as exc:
        # GROQ_API_KEY missing
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        print(f"[main] Unexpected error: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Analysis failed. Please try again or contact support.",
        )

    # Validate and return — Pydantic will raise 422 on bad shapes
    return AnalyzeResponse(**result)
