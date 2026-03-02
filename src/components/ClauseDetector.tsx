import { AlertTriangle, AlertCircle, Info, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { useState } from "react";

export type RiskLevel = "critical" | "high" | "medium" | "low";

export interface DetectedClause {
  id: string;
  title: string;
  excerpt: string;
  risk: RiskLevel;
  category: string;
  explanation: string;
  recommendation: string;
}

const riskConfig: Record<RiskLevel, { icon: typeof AlertTriangle; color: string; bg: string; border: string; label: string }> = {
  critical: { icon: AlertCircle, color: "text-destructive", bg: "bg-destructive/10", border: "border-destructive/30", label: "CRITICAL" },
  high: { icon: AlertTriangle, color: "text-warning", bg: "bg-warning/10", border: "border-warning/30", label: "HIGH" },
  medium: { icon: AlertTriangle, color: "text-yellow-400", bg: "bg-yellow-400/10", border: "border-yellow-400/30", label: "MEDIUM" },
  low: { icon: Info, color: "text-primary", bg: "bg-primary/10", border: "border-primary/30", label: "LOW" },
};

const ClauseCard = ({ clause }: { clause: DetectedClause }) => {
  const [expanded, setExpanded] = useState(false);
  const cfg = riskConfig[clause.risk];
  const Icon = cfg.icon;

  return (
    <div className={`rounded-xl border ${cfg.border} ${cfg.bg} overflow-hidden transition-all duration-300`}>
      <button
        className="w-full p-4 text-left flex items-start gap-3"
        onClick={() => setExpanded(!expanded)}
      >
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${cfg.bg} border ${cfg.border}`}>
          <Icon className={`w-4 h-4 ${cfg.color}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1">
            <span className={`text-xs font-bold font-mono tracking-widest ${cfg.color}`}>{cfg.label}</span>
            <span className="text-xs text-muted-foreground px-2 py-0.5 rounded-full bg-secondary border border-border/40">{clause.category}</span>
          </div>
          <h3 className="font-semibold text-foreground">{clause.title}</h3>
          <p className="text-sm text-muted-foreground mt-1 line-clamp-2 font-mono">"{clause.excerpt}"</p>
        </div>
        <div className="ml-2 flex-shrink-0 text-muted-foreground">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 ml-11 border-t border-border/30 pt-4">
          <div className="mb-4">
            <p className="text-xs text-muted-foreground font-semibold uppercase tracking-wider mb-2">Why This Is Problematic</p>
            <p className="text-sm text-foreground/80 leading-relaxed">{clause.explanation}</p>
          </div>
          <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
            <p className="text-xs text-primary font-semibold uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
              <ExternalLink className="w-3 h-3" />
              Recommended Action
            </p>
            <p className="text-sm text-foreground/80 leading-relaxed">{clause.recommendation}</p>
          </div>
        </div>
      )}
    </div>
  );
};

const ClauseDetector = ({ clauses }: { clauses: DetectedClause[] }) => {
  const counts = {
    critical: clauses.filter(c => c.risk === "critical").length,
    high: clauses.filter(c => c.risk === "high").length,
    medium: clauses.filter(c => c.risk === "medium").length,
    low: clauses.filter(c => c.risk === "low").length,
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          Detected Issues
          <span className="ml-3 text-sm font-normal text-muted-foreground">({clauses.length} found)</span>
        </h2>
        <div className="flex gap-2">
          {Object.entries(counts).map(([risk, count]) => count > 0 && (
            <span
              key={risk}
              className={`text-xs font-bold font-mono px-2 py-1 rounded-full ${riskConfig[risk as RiskLevel].bg} ${riskConfig[risk as RiskLevel].color} border ${riskConfig[risk as RiskLevel].border}`}
            >
              {count} {risk.toUpperCase()}
            </span>
          ))}
        </div>
      </div>
      <div className="space-y-3">
        {clauses.map(c => <ClauseCard key={c.id} clause={c} />)}
      </div>
    </div>
  );
};

export default ClauseDetector;
