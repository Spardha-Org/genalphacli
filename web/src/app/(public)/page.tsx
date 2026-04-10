import { GridBackground } from "@/components/landing/grid-background";
import { LandingNav } from "@/components/landing/landing-nav";
import { HeroSection } from "@/components/landing/hero-section";
import { FlowSection } from "@/components/landing/flow-section";
import { ShowcaseSection } from "@/components/landing/showcase-section";
import { AiSection } from "@/components/landing/ai-section";
import { CtaSection } from "@/components/landing/cta-section";
import { SectionDivider } from "@/components/landing/section-divider";

export default function LandingPage() {
  return (
    <>
      <GridBackground />
      <LandingNav />

      {/* Section 1: Hero */}
      <HeroSection />

      <SectionDivider />

      {/* Section 2: Horizontal Parallax Flow */}
      <FlowSection />
      <SectionDivider />

      {/* Section 3: Feature Showcase */}
      <ShowcaseSection />
      <SectionDivider />

      {/* Section 4: AI Integrations */}
      <AiSection />
      <SectionDivider />

      {/* Section 5: CTA + ASCII Zoom */}
      <CtaSection />

      <footer className="border-t border-[var(--border)] px-[60px] py-6 text-center font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-[var(--text-muted)] tracking-wider relative z-[1]">
        Built by <a href="https://github.com/NandishNaik01" className="text-[var(--text-dim)] no-underline hover:text-[var(--accent)]">NandishNaik01</a> &middot;
        <a href="https://github.com/NandishNaik01/genalphacli" className="text-[var(--text-dim)] no-underline hover:text-[var(--accent)]"> GitHub</a> &middot; MIT
      </footer>
    </>
  );
}
