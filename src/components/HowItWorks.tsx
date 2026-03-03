import { Brain, Search, FileCheck, BarChart3, ArrowRight } from "lucide-react";

const steps = [
  {
    icon: Search,
    number: "01",
    title: "Clause Extraction & Categorization",
    description: "The Auditor parses raw contract text using NLP to identify key clauses — payment terms, IP rights, termination rules, arbitration, non-competes, and more.",
  },
  {
    icon: Brain,
    number: "02",
    title: "Advocate vs Skeptic Reasoning",
    description: "Two internal AI perspectives simulate a legal debate. This ensures balanced, bias-resistant analysis.",
  },
  {
    icon: BarChart3,
    number: "03",
    title: "Scoring, Verdict & Negotiation Strategy",
    description: "The Judge evaluates the debate, assigns fairness and risk scores, and delivers Overall contract rating. A final verdict you can act on confidently.",
  },
  {
    icon: FileCheck,
    number: "04",
    title: "Report Generation",
    description: "A complete transparency report is generated with fairness scores, clause-by-clause analysis, and negotiation strategies.",
  },
];

const HowItWorks = () => {
  return (
    <section className="py-24 px-6 relative">
      <div className="absolute inset-0 opacity-30" style={{
        background: "radial-gradient(ellipse at 70% 50%, hsl(183 100% 45% / 0.05) 0%, transparent 60%)"
      }} />
      <div className="max-w-7xl mx-auto relative z-10">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold mb-4" style={{ fontFamily: "Space Grotesk, sans-serif" }}>
            Meet the 3-Agent AI Council
          </h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            An intelligent contract auditing system where three AI agents — Auditor, Advocate, and Judge — collaborate to analyze gig contracts and protect worker fairness in seconds.
          </p>
        </div>

        <div className="relative">
          {/* Connector line */}
          <div className="hidden lg:block absolute top-16 left-[12.5%] right-[12.5%] h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map((step, i) => {
              const Icon = step.icon;
              return (
                <div key={step.number} className="relative group">
                  <div className="rounded-2xl border border-border/60 bg-gradient-card p-6 hover:border-primary/40 hover:bg-primary/5 transition-all duration-300">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 rounded-xl bg-primary/15 border border-primary/30 flex items-center justify-center group-hover:glow-cyan transition-all duration-300">
                        <Icon className="w-5 h-5 text-primary" />
                      </div>
                      <span className="text-3xl font-bold font-mono text-primary/20 group-hover:text-primary/40 transition-colors">{step.number}</span>
                    </div>
                    <h3 className="font-bold text-lg mb-2" style={{ fontFamily: "Space Grotesk, sans-serif" }}>{step.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">{step.description}</p>
                  </div>
                  {i < steps.length - 1 && (
                    <ArrowRight className="hidden lg:block absolute -right-3 top-14 w-6 h-6 text-primary/30 z-10" />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
