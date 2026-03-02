import { Shield, Zap, Menu, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

const NavBar = () => {
  const [open, setOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border/60 backdrop-blur-md bg-background/80">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary/20 border border-primary/40 flex items-center justify-center animate-pulse-glow">
            <Shield className="w-4 h-4 text-primary" />
          </div>
          <span className="font-bold text-xl tracking-tight" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            <span className="text-gradient-primary">Gig</span>
            <span className="text-foreground">Audit</span>
          </span>
        </div>
        <button className="md:hidden text-muted-foreground" onClick={() => setOpen(!open)}>
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>
      {open && (
        <div className="md:hidden border-t border-border/60 bg-background/95 px-6 py-4 flex flex-col gap-4">
          {["Features", "How it Works", "Pricing"].map((item) => (
            <a key={item} href="#" className="text-sm text-muted-foreground hover:text-primary">{item}</a>
          ))}
          <Button className="bg-primary text-primary-foreground w-full gap-2">
            <Zap className="w-4 h-4" /> Analyze Contract
          </Button>
        </div>
      )}
    </nav>
  );
};

export default NavBar;
