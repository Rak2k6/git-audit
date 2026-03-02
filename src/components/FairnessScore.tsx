import { useEffect, useRef, useState } from "react";

interface FairnessGaugeProps {
  score: number; // 0-100
  breakdown: { label: string; score: number; weight: number }[];
}

const getScoreColor = (score: number) => {
  if (score >= 70) return "hsl(142 70% 45%)";
  if (score >= 40) return "hsl(38 92% 55%)";
  return "hsl(0 75% 55%)";
};

const getScoreLabel = (score: number) => {
  if (score >= 80) return { text: "FAIR", sub: "Contract meets industry standards" };
  if (score >= 60) return { text: "MARGINAL", sub: "Several areas need attention" };
  if (score >= 40) return { text: "UNFAIR", sub: "Significant issues detected" };
  return { text: "PREDATORY", sub: "Multiple exploitative clauses found" };
};

const AnimatedBar = ({ score, color, delay }: { score: number; color: string; delay: number }) => {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setWidth(score), delay);
    return () => clearTimeout(t);
  }, [score, delay]);

  return (
    <div className="h-2 rounded-full bg-secondary overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700 ease-out"
        style={{ width: `${width}%`, backgroundColor: color }}
      />
    </div>
  );
};

const FairnessScore = ({ score, breakdown }: FairnessGaugeProps) => {
  const color = getScoreColor(score);
  const label = getScoreLabel(score);
  const [displayed, setDisplayed] = useState(0);
  const animRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let current = 0;
    const step = () => {
      current += 2;
      if (current >= score) {
        setDisplayed(score);
        return;
      }
      setDisplayed(current);
      animRef.current = setTimeout(step, 20);
    };
    animRef.current = setTimeout(step, 300);
    return () => { if (animRef.current) clearTimeout(animRef.current); };
  }, [score]);

  // SVG arc gauge
  const radius = 80;
  const cx = 100;
  const cy = 100;
  const startAngle = -220;
  const endAngle = 40;
  const totalAngle = endAngle - startAngle;
  const scoreAngle = startAngle + (totalAngle * score) / 100;

  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const arcPath = (from: number, to: number, r: number) => {
    const start = { x: cx + r * Math.cos(toRad(from)), y: cy + r * Math.sin(toRad(from)) };
    const end = { x: cx + r * Math.cos(toRad(to)), y: cy + r * Math.sin(toRad(to)) };
    const large = to - from > 180 ? 1 : 0;
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y}`;
  };

  return (
    <div className="rounded-2xl border border-border/60 bg-gradient-card p-6">
      <h2 className="text-2xl font-bold mb-6" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
        Fairness Score
      </h2>

      <div className="flex flex-col items-center mb-8">
        <svg viewBox="0 0 200 140" className="w-56 h-40">
          {/* Background arc */}
          <path d={arcPath(startAngle, endAngle, radius)} fill="none" stroke="hsl(var(--secondary))" strokeWidth="12" strokeLinecap="round" />
          {/* Score arc */}
          <path
            d={arcPath(startAngle, scoreAngle, radius)}
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 8px ${color})`, transition: 'all 1s ease-out' }}
          />
          {/* Score text */}
          <text x={cx} y={cy + 10} textAnchor="middle" fontSize="36" fontWeight="700" fill={color} fontFamily="Space Grotesk, sans-serif">
            {displayed}
          </text>
          <text x={cx} y={cy + 30} textAnchor="middle" fontSize="11" fill="hsl(var(--muted-foreground))" fontFamily="Inter, sans-serif">
            out of 100
          </text>
        </svg>

        <div className="text-center mt-1">
          <span className="text-lg font-bold font-mono tracking-widest" style={{ color }}>{label.text}</span>
          <p className="text-sm text-muted-foreground mt-1">{label.sub}</p>
        </div>
      </div>

      {/* Breakdown bars */}
      <div className="space-y-4">
        {breakdown.map((item, i) => (
          <div key={item.label}>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-sm text-foreground/80">{item.label}</span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground font-mono">{item.weight}% weight</span>
                <span className="text-sm font-semibold font-mono" style={{ color: getScoreColor(item.score) }}>{item.score}</span>
              </div>
            </div>
            <AnimatedBar score={item.score} color={getScoreColor(item.score)} delay={500 + i * 100} />
          </div>
        ))}
      </div>
    </div>
  );
};

export default FairnessScore;
