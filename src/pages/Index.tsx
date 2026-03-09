import { useState, useRef } from "react";
import NavBar from "@/components/NavBar";
import HeroSection from "@/components/HeroSection";
import ContractAnalyzer from "@/components/ContractAnalyzer";
import ClauseDetector, { DetectedClause } from "@/components/ClauseDetector";
import FairnessScore from "@/components/FairnessScore";
import NegotiationGuidance from "@/components/NegotiationGuidance";
import TransparencyReport from "@/components/TransparencyReport";
import HowItWorks from "@/components/HowItWorks";

// ── Backend URL ─────────────────────────────────────────────────────────────
// In development this points to the local FastAPI server.
// For production, replace with your deployed API URL or set via env var.
const API_BASE = import.meta.env.VITE_API_URL ?? "https://gig-audit-council.onrender.com";

// ── API response types (mirror backend Pydantic models) ─────────────────────
interface CategoryScores {
  payment: number;
  termination: number;
  non_compete: number;
  ip: number;
  dispute: number;
  compensation: number;
}

interface ApiRiskyClause {
  category: string;
  risk_level: "low" | "medium" | "high" | "critical";
  explanation: string;
  suggestion: string;
}

interface AnalyzeApiResponse {
  overall_score: number;
  category_scores: CategoryScores;
  verdict: "approved" | "needs_renegotiation" | "unfair";
  risky_clauses: ApiRiskyClause[];
}

// ── Shape the API response into the UI types ─────────────────────────────────
interface UIResult {
  score: number;
  breakdown: { label: string; score: number; weight: number }[];
  clauses: DetectedClause[];
  verdict: string;
}

const CATEGORY_META: Record<
  keyof CategoryScores,
  { label: string; weight: number }
> = {
  payment: { label: "Payment Fairness", weight: 25 },
  termination: { label: "Termination Equity", weight: 15 },
  non_compete: { label: "Non-Compete Scope", weight: 15 },
  ip: { label: "IP & Ownership Terms", weight: 20 },
  dispute: { label: "Dispute Resolution", weight: 15 },
  compensation: { label: "Compensation Terms", weight: 10 },
};

function mapApiToUI(api: AnalyzeApiResponse): UIResult {
  // Breakdown bars
  const breakdown = (Object.keys(CATEGORY_META) as (keyof CategoryScores)[]).map(
    (key) => ({
      label: CATEGORY_META[key].label,
      score: api.category_scores[key],
      weight: CATEGORY_META[key].weight,
    })
  );

  // Convert back-end risky_clauses → DetectedClause[] for existing UI components
  const clauses: DetectedClause[] = api.risky_clauses.length > 0
    ? api.risky_clauses.map((c, i) => ({
      id: String(i + 1),
      title: `${c.category.charAt(0).toUpperCase() + c.category.slice(1).replace("_", " ")} Issue`,
      excerpt: c.explanation.slice(0, 120) + (c.explanation.length > 120 ? "…" : ""),
      risk: c.risk_level,
      category: c.category.replace("_", " "),
      explanation: c.explanation,
      recommendation: c.suggestion,
    }))
    : [
      {
        id: "0",
        title: "General Contract Review",
        excerpt: "No specific high-risk patterns detected.",
        risk: "low",
        category: "General",
        explanation: "The AI Council did not detect common exploitative clauses. Always consult a lawyer for high-value agreements.",
        recommendation: "Consider having a labour attorney review before signing.",
      },
    ];

  return { score: api.overall_score, breakdown, clauses, verdict: api.verdict };
}

// ── Main page ────────────────────────────────────────────────────────────────
const Index = () => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<UIResult | null>(null);
  const [contractLength, setContractLength] = useState(0);
  const [apiError, setApiError] = useState<string | null>(null);

  const analyzerRef = useRef<HTMLDivElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  const scrollToAnalyzer = () =>
    analyzerRef.current?.scrollIntoView({ behavior: "smooth" });

  const handleAnalysis = async (text: string) => {
    setIsAnalyzing(true);
    setApiError(null);
    setContractLength(text.length);

    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contract_text: text }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail ?? `Server error ${res.status}`);
      }

      const data: AnalyzeApiResponse = await res.json();
      const uiResult = mapApiToUI(data);
      setResult(uiResult);

      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "An unexpected error occurred.";
      setApiError(message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <NavBar />
      <HeroSection onAnalyze={scrollToAnalyzer} />
      <HowItWorks />

      <div ref={analyzerRef}>
        <ContractAnalyzer onAnalysis={handleAnalysis} isAnalyzing={isAnalyzing} />
      </div>

      {/* API error banner */}
      {apiError && (
        <div className="max-w-4xl mx-auto px-6 -mt-10 mb-6">
          <div className="rounded-xl bg-destructive/10 border border-destructive/30 p-4 text-sm text-destructive font-mono">
            ⚠ Analysis failed: {apiError}
            <br />
            <span className="text-muted-foreground text-xs">
              Make sure the backend is running on {API_BASE} and GROQ_API_KEY is set.
            </span>
          </div>
        </div>
      )}

      {result && (
        <div ref={resultsRef} className="max-w-7xl mx-auto px-6 pb-24 animate-fade-in-up">
          <div className="mb-10 text-center">
            <h2
              className="text-3xl font-bold mb-2"
              style={{ fontFamily: "Space Grotesk, sans-serif" }}
            >
              Analysis Complete
            </h2>
            <p className="text-muted-foreground">
              Your contract has been analysed by the AI Council. Review results below.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <div className="lg:col-span-1">
              <FairnessScore score={result.score} breakdown={result.breakdown} />
            </div>
            <div className="lg:col-span-2">
              <ClauseDetector clauses={result.clauses} />
            </div>
          </div>

          <div className="mb-8">
            <TransparencyReport
              score={result.score}
              clauseCount={result.clauses.length}
              criticalCount={result.clauses.filter((c) => c.risk === "critical").length}
              highCount={result.clauses.filter((c) => c.risk === "high").length}
              contractLength={contractLength}
              clauses={result.clauses}
            />
          </div>

          <NegotiationGuidance />
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-border/60 py-12 px-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span
              className="font-bold text-lg"
              style={{ fontFamily: "Space Grotesk, sans-serif" }}
            >
              <span className="text-gradient-primary">Gig</span>
              <span className="text-foreground">Audit</span>
            </span>
            <span className="text-muted-foreground text-sm">
              AI-powered contract intelligence
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            Not legal advice. For educational purposes only. Consult a labour
            attorney for binding decisions.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Index;
