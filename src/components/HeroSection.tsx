import { ArrowRight, CheckCircle, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import heroBg from "@/assets/hero-bg.jpg";

const stats = [
  { value: "94%", label: "Detection Accuracy" },
  { value: "2.3x", label: "Fairer Wages Negotiated" },
  { value: "50K+", label: "Contracts Analyzed" },
];

const HeroSection = ({ onAnalyze }: { onAnalyze: () => void }) => {
  return (
    <section className="relative min-h-screen flex items-center overflow-hidden pt-20">
      {/* Background image with overlay */}
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: `url(${heroBg})` }}
      />
      <div className="absolute inset-0 bg-background/85" />
      <div className="absolute inset-0" style={{ background: 'radial-gradient(ellipse at 30% 50%, hsl(183 100% 45% / 0.06) 0%, transparent 60%)' }} />

      {/* Grid overlay */}
      <div className="absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: 'linear-gradient(hsl(183 100% 45%) 1px, transparent 1px), linear-gradient(90deg, hsl(183 100% 45%) 1px, transparent 1px)',
        backgroundSize: '60px 60px'
      }} />

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-24">
        <div className="max-w-4xl">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-primary/30 bg-primary/10 text-primary text-sm font-medium mb-8 animate-fade-in-up">
            <Zap className="w-3.5 h-3.5" />
            AI-Powered Contract Intelligence
          </div>

          <h1 className="text-5xl md:text-7xl font-bold leading-tight mb-6 animate-fade-in-up" style={{ animationDelay: '0.1s', fontFamily: 'Space Grotesk, sans-serif' }}>
            Audit Gig Contracts.
            <br />
            <span className="text-gradient-primary">Expose Unfair</span>
            <br />
            Clauses Instantly.
          </h1>

          <p className="text-xl text-muted-foreground max-w-2xl mb-10 leading-relaxed animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
            Our NLP engine scans digital job contracts to detect wage discrepancies,
            hidden clauses, and exploitative terms — then guides you through evidence-based
            negotiation strategies.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 mb-16 animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
            <Button
              onClick={onAnalyze}
              className="bg-primary text-primary-foreground hover:bg-primary/90 glow-cyan text-base px-8 py-6 gap-2 font-semibold"
            >
              Analyze Your Contract
              <ArrowRight className="w-5 h-5" />
            </Button>

          </div>

          {/* Trust signals */}
          <div className="flex flex-wrap gap-4 mb-16 animate-fade-in-up" style={{ animationDelay: '0.4s' }}>
            {["No data stored", "GDPR compliant", "Free to analyze"].map((item) => (
              <div key={item} className="flex items-center gap-2 text-sm text-muted-foreground">
                <CheckCircle className="w-4 h-4 text-success" />
                {item}
              </div>
            ))}
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-8 max-w-lg animate-fade-in-up" style={{ animationDelay: '0.5s' }}>
            {stats.map((s) => (
              <div key={s.label}>
                <div className="text-3xl font-bold text-gradient-primary" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>{s.value}</div>
                <div className="text-sm text-muted-foreground mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
