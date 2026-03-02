import { useState, useRef } from "react";
import NavBar from "@/components/NavBar";
import HeroSection from "@/components/HeroSection";
import ContractAnalyzer from "@/components/ContractAnalyzer";
import ClauseDetector, { DetectedClause } from "@/components/ClauseDetector";
import FairnessScore from "@/components/FairnessScore";
import NegotiationGuidance from "@/components/NegotiationGuidance";
import TransparencyReport from "@/components/TransparencyReport";
import HowItWorks from "@/components/HowItWorks";

// Mock AI analysis function
const analyzeContract = (text: string) => {
  const lower = text.toLowerCase();
  const clauses: DetectedClause[] = [];

  if (lower.includes("90 days") || lower.includes("90-day") || lower.includes("indefinitely")) {
    clauses.push({
      id: "1",
      title: "Excessive Payment Delay",
      excerpt: "Payment will be processed within 90 days of invoice. Company may withhold payment indefinitely...",
      risk: "critical",
      category: "Payment Terms",
      explanation: "A 90-day payment delay significantly exceeds the industry standard of Net-30. The phrase 'withhold indefinitely' removes any guaranteed payment obligation, effectively giving the company an opt-out. This may violate state wage payment laws.",
      recommendation: "Demand Net-30 payment terms and remove any language allowing indefinite withholding. Require a specific cure period (e.g., 10 business days) if disputes arise.",
    });
  }

  if (lower.includes("outside of working hours") || lower.includes("exclusive property") || lower.includes("all work product")) {
    clauses.push({
      id: "2",
      title: "Overbroad Intellectual Property Assignment",
      excerpt: "All work product, ideas, inventions created outside of working hours that may be related...",
      risk: "critical",
      category: "Intellectual Property",
      explanation: "Claiming ownership of work created 'outside of working hours' that is merely 'related to' the company's business is a dramatic overreach. This could strip you of personal projects, side work, and innovations you developed entirely on your own time.",
      recommendation: "Limit IP assignment strictly to deliverables produced under this contract. Add explicit carve-outs for pre-existing work and anything created without company resources.",
    });
  }

  if (lower.includes("non-compete") || lower.includes("3 years") || lower.includes("500-mile")) {
    clauses.push({
      id: "3",
      title: "Unenforceable Non-Compete Clause",
      excerpt: "Contractor agrees not to engage in any competing activities for 3 years within a 500-mile radius...",
      risk: "high",
      category: "Non-Compete",
      explanation: "A 3-year, 500-mile non-compete is almost certainly unenforceable in most jurisdictions due to its extreme breadth. However, it may still chill your ability to find work due to fear of litigation, even if you would ultimately prevail.",
      recommendation: "Negotiate this down to a narrowly scoped non-solicitation clause (no poaching of specific named clients) for no more than 6 months.",
    });
  }

  if (lower.includes("arbitration") || lower.includes("waives all rights") || lower.includes("borne entirely")) {
    clauses.push({
      id: "4",
      title: "One-Sided Arbitration Clause",
      excerpt: "Contractor waives all rights to class action. Arbitration costs shall be borne entirely by the Contractor.",
      risk: "high",
      category: "Dispute Resolution",
      explanation: "Mandatory arbitration with full cost burden on the contractor effectively eliminates your ability to pursue legitimate claims. Combined with a class action waiver, this is a common tactic to prevent accountability for systemic wage theft.",
      recommendation: "Require cost-splitting or cost caps, preserve small claims court access, and remove class action waiver language.",
    });
  }

  if (lower.includes("unilateral") || lower.includes("24-hour notice") || lower.includes("modify compensation")) {
    clauses.push({
      id: "5",
      title: "Unilateral Rate Modification",
      excerpt: "Company reserves the unilateral right to modify compensation rates with 24-hour notice.",
      risk: "high",
      category: "Compensation",
      explanation: "Allowing rate changes with only 24-hour notice gives you no ability to plan financially or exit the contract before losing income. This violates basic principles of contract mutuality.",
      recommendation: "Require 30-day written notice for any rate changes, with your right to terminate without penalty if you don't accept the new rate.",
    });
  }

  if (lower.includes("90 days written notice") || lower.includes("without notice or compensation")) {
    clauses.push({
      id: "6",
      title: "Asymmetric Termination Terms",
      excerpt: "Company may terminate at any time without notice. Contractor must provide 90 days written notice...",
      risk: "medium",
      category: "Termination",
      explanation: "Termination rights being completely one-sided is a significant imbalance. The company can walk away instantly while binding you for 90 days creates a power imbalance that can be exploited.",
      recommendation: "Negotiate equal notice periods (14-30 days for both parties) or at minimum a kill fee if the company terminates early.",
    });
  }

  if (clauses.length === 0) {
    clauses.push({
      id: "0",
      title: "General Contract Review",
      excerpt: "Review complete. No specific high-risk patterns detected in standard scan.",
      risk: "low",
      category: "General",
      explanation: "Our standard pattern library did not detect common exploitative clauses in this text. However, this does not guarantee the contract is fully fair — consulting a lawyer is recommended for high-value agreements.",
      recommendation: "Consider having a labor attorney review the full contract before signing, especially clauses around scope creep and deliverable definitions.",
    });
  }

  const critCount = clauses.filter(c => c.risk === "critical").length;
  const highCount = clauses.filter(c => c.risk === "high").length;
  const score = Math.max(10, 100 - critCount * 22 - highCount * 14 - clauses.filter(c => c.risk === "medium").length * 8);

  const breakdown = [
    { label: "Payment Fairness", score: critCount >= 1 ? 15 : 78, weight: 30 },
    { label: "IP & Ownership Terms", score: clauses.some(c => c.id === "2") ? 12 : 82, weight: 20 },
    { label: "Non-Compete Scope", score: clauses.some(c => c.id === "3") ? 20 : 88, weight: 15 },
    { label: "Dispute Resolution", score: clauses.some(c => c.id === "4") ? 18 : 75, weight: 20 },
    { label: "Termination Equity", score: clauses.some(c => c.id === "6") ? 35 : 80, weight: 15 },
  ];

  return { clauses, score, breakdown };
};

const Index = () => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<ReturnType<typeof analyzeContract> | null>(null);
  const [contractLength, setContractLength] = useState(0);
  const analyzerRef = useRef<HTMLDivElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  const scrollToAnalyzer = () => {
    analyzerRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleAnalysis = (text: string) => {
    setIsAnalyzing(true);
    setContractLength(text.length);
    // Simulate AI processing delay
    setTimeout(() => {
      const analysis = analyzeContract(text);
      setResult(analysis);
      setIsAnalyzing(false);
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }, 2500);
  };

  return (
    <div className="min-h-screen bg-background">
      <NavBar />
      <HeroSection onAnalyze={scrollToAnalyzer} />
      <HowItWorks />

      <div ref={analyzerRef}>
        <ContractAnalyzer onAnalysis={handleAnalysis} isAnalyzing={isAnalyzing} />
      </div>

      {result && (
        <div ref={resultsRef} className="max-w-7xl mx-auto px-6 pb-24 animate-fade-in-up">
          <div className="mb-10 text-center">
            <h2 className="text-3xl font-bold mb-2" style={{ fontFamily: "Space Grotesk, sans-serif" }}>
              Analysis Complete
            </h2>
            <p className="text-muted-foreground">Your contract has been analyzed. Review results below.</p>
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
              criticalCount={result.clauses.filter(c => c.risk === "critical").length}
              highCount={result.clauses.filter(c => c.risk === "high").length}
              contractLength={contractLength}
            />
          </div>

          <NegotiationGuidance />
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-border/60 py-12 px-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-lg" style={{ fontFamily: "Space Grotesk, sans-serif" }}>
              <span className="text-gradient-primary">Gig</span>
              <span className="text-foreground">Audit</span>
            </span>
            <span className="text-muted-foreground text-sm">AI-powered contract intelligence</span>
          </div>
          <p className="text-sm text-muted-foreground">
            Not legal advice. For educational purposes only. Consult a labor attorney for binding decisions.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Index;
