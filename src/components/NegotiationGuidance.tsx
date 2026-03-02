import { MessageSquare, TrendingUp, Scale, Shield, Copy, CheckCheck } from "lucide-react";
import { useState } from "react";

interface NegotiationTip {
  id: string;
  category: string;
  icon: typeof MessageSquare;
  title: string;
  script: string;
  leverage: string;
  outcome: string;
}

const tips: NegotiationTip[] = [
  {
    id: "1",
    category: "Payment Terms",
    icon: TrendingUp,
    title: "Counter the 90-Day Payment Delay",
    script: '"Industry standard for freelance contracts is Net-30. I'd be comfortable proceeding with Net-30 payment terms. For projects over $500, I require a 50% deposit upfront. This is standard practice and I'm happy to provide references from other clients who've agreed to these terms."',
    leverage: "Net-30 is the legal standard in most jurisdictions. Longer delays may violate wage payment laws.",
    outcome: "Payment within 30 days, 50% deposit on large projects",
  },
  {
    id: "2",
    category: "IP Rights",
    icon: Shield,
    title: "Limit Intellectual Property Transfer",
    script: '"I can assign IP for work specifically created under this contract, but I retain rights to pre-existing tools, frameworks, and any work created independently. I'd like to add: \'Contractor retains ownership of all pre-existing intellectual property and general know-how.\'"',
    leverage: "Blanket IP assignment of work done 'outside hours' is legally unenforceable in many states.",
    outcome: "IP limited to deliverables, not background knowledge",
  },
  {
    id: "3",
    category: "Non-Compete",
    icon: Scale,
    title: "Narrow the Non-Compete Scope",
    script: '"A 3-year, 500-mile non-compete is overly broad and likely unenforceable. I'd agree to a 6-month non-solicitation of your direct clients only. I need to remain able to work in my field to sustain my livelihood."',
    leverage: "Courts frequently void overly broad non-competes. Several states (CA, ND, OK) ban them entirely.",
    outcome: "6-month non-solicitation only, no geographic restriction",
  },
  {
    id: "4",
    category: "Arbitration",
    icon: MessageSquare,
    title: "Remove One-Sided Arbitration Costs",
    script: '"I'm open to arbitration but need costs shared equally, or capped at $500 for me. I'd also like to preserve the right to small claims court for disputes under $10,000. One-sided cost arrangements discourage legitimate claims."',
    leverage: "Forcing all arbitration costs on the weaker party may be deemed unconscionable by courts.",
    outcome: "Equal cost-sharing, small claims court preserved",
  },
];

const NegotiationGuidance = () => {
  const [copied, setCopied] = useState<string | null>(null);

  const copyScript = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="rounded-2xl border border-border/60 bg-gradient-card p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-primary/15 border border-primary/30 flex items-center justify-center">
          <MessageSquare className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h2 className="text-2xl font-bold" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>Negotiation Playbook</h2>
          <p className="text-sm text-muted-foreground">Evidence-based scripts for each flagged clause</p>
        </div>
      </div>

      <div className="space-y-4">
        {tips.map((tip) => {
          const Icon = tip.icon;
          return (
            <div key={tip.id} className="rounded-xl border border-border/50 bg-secondary/30 overflow-hidden">
              <div className="p-4">
                <div className="flex items-start gap-3 mb-3">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-4 h-4 text-primary" />
                  </div>
                  <div>
                    <span className="text-xs text-primary font-semibold font-mono uppercase tracking-wider">{tip.category}</span>
                    <h3 className="font-semibold text-foreground mt-0.5">{tip.title}</h3>
                  </div>
                </div>

                {/* Script */}
                <div className="relative bg-background/60 rounded-lg p-4 border border-border/40 mb-3">
                  <p className="text-sm text-foreground/80 leading-relaxed italic pr-8">{tip.script}</p>
                  <button
                    onClick={() => copyScript(tip.id, tip.script)}
                    className="absolute top-3 right-3 text-muted-foreground hover:text-primary transition-colors"
                    title="Copy script"
                  >
                    {copied === tip.id ? <CheckCheck className="w-4 h-4 text-success" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-warning/5 border border-warning/20">
                    <p className="text-xs font-semibold text-warning uppercase tracking-wider mb-1">Your Leverage</p>
                    <p className="text-xs text-foreground/70 leading-relaxed">{tip.leverage}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-success/5 border border-success/20">
                    <p className="text-xs font-semibold text-success uppercase tracking-wider mb-1">Target Outcome</p>
                    <p className="text-xs text-foreground/70 leading-relaxed">{tip.outcome}</p>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default NegotiationGuidance;
