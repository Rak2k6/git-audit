import { useState, useRef } from "react";
import { Upload, FileText, ArrowRight, Loader2, AlertTriangle, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";

const SAMPLE_CONTRACT = `FREELANCE SERVICE AGREEMENT

This agreement is entered into between GigCorp Inc. ("Company") and the Contractor.

1. PAYMENT TERMS: Contractor shall be paid $12/hour for all services rendered. Payment will be processed within 90 days of invoice submission. Company reserves the right to withhold payment indefinitely pending "quality review."

2. INTELLECTUAL PROPERTY: All work product, ideas, inventions, and materials created by Contractor, including any work created outside of working hours that may be related to Company's business, shall be the exclusive property of GigCorp Inc.

3. NON-COMPETE CLAUSE: Contractor agrees not to engage in any competing business activities for a period of 3 years within a 500-mile radius following termination.

4. ARBITRATION: Any disputes shall be resolved through binding arbitration. Contractor waives all rights to class action lawsuits. Arbitration costs shall be borne entirely by the Contractor.

5. TERMINATION: Company may terminate this agreement at any time without notice or compensation. Contractor must provide 90 days written notice of termination.

6. RATE MODIFICATION: Company reserves the unilateral right to modify compensation rates with 24-hour notice.

7. EXPENSES: Contractor is responsible for all equipment, software, and operational expenses. No reimbursements will be provided.`;

interface ContractAnalyzerProps {
  onAnalysis: (text: string) => void;
  isAnalyzing: boolean;
}

const ContractAnalyzer = ({ onAnalysis, isAnalyzing }: ContractAnalyzerProps) => {
  const [text, setText] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => setText(e.target?.result as string);
    reader.readAsText(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const loadSample = () => setText(SAMPLE_CONTRACT);

  return (
    <section id="analyzer" className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold mb-4" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Paste or Upload Your Contract
          </h2>
          <p className="text-muted-foreground text-lg">
            Supports plain text, .txt, and .pdf files. Analysis takes under 10 seconds.
          </p>
        </div>

        <div className="rounded-2xl border border-border/60 bg-gradient-card overflow-hidden">
          {/* Drag & drop zone */}
          <div
            className={`border-b border-border/60 p-6 flex items-center gap-4 cursor-pointer transition-colors duration-200 ${dragOver ? 'bg-primary/10' : 'hover:bg-secondary/50'}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
          >
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${dragOver ? 'bg-primary/30 border-primary' : 'bg-secondary border-border/60'} border`}>
              <Upload className={`w-5 h-5 ${dragOver ? 'text-primary' : 'text-muted-foreground'}`} />
            </div>
            <div>
              <p className="font-medium text-sm">Drop file here or click to upload</p>
              <p className="text-xs text-muted-foreground mt-0.5">TXT, PDF up to 10MB</p>
            </div>
            <input ref={fileRef} type="file" accept=".txt,.pdf" className="hidden" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
          </div>

          {/* Text area */}
          <div className="relative">
            <div className="absolute top-4 left-4 flex items-center gap-2 text-xs text-muted-foreground font-mono">
              <FileText className="w-3.5 h-3.5" />
              CONTRACT TEXT
            </div>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste your contract text here..."
              className="w-full h-72 bg-transparent pt-10 px-4 pb-4 text-sm text-foreground placeholder:text-muted-foreground/40 resize-none outline-none font-mono leading-relaxed"
            />
            {/* Scanline animation when analyzing */}
            {isAnalyzing && (
              <div className="absolute inset-0 pointer-events-none scanline" />
            )}
          </div>

          {/* Footer controls */}
          <div className="border-t border-border/60 p-4 flex items-center justify-between gap-4">
            <button
              onClick={loadSample}
              className="text-sm text-primary hover:text-primary/80 underline underline-offset-4 flex items-center gap-1.5 transition-colors"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Load sample contract
            </button>

            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground font-mono">{text.length} chars</span>
              <Button
                onClick={() => onAnalysis(text)}
                disabled={text.length < 50 || isAnalyzing}
                className="bg-primary text-primary-foreground hover:bg-primary/90 glow-cyan gap-2 font-semibold px-6"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    Run AI Analysis
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ContractAnalyzer;
