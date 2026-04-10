import { GridBackground } from "@/components/landing/grid-background";
import { LandingNav } from "@/components/landing/landing-nav";
import { HeroSection } from "@/components/landing/hero-section";
import { FlowSection } from "@/components/landing/flow-section";
import { ShowcaseSection } from "@/components/landing/showcase-section";
import { SectionDivider } from "@/components/landing/section-divider";

export default function LandingPage() {
  return (
    <>
      <GridBackground />
      <LandingNav />

      {/* Section 1: Hero */}
      <HeroSection />

      <SectionDivider />

      {/* Sections 2-5: placeholders for Phases 3-6 */}
      <FlowSection />
      <SectionDivider />
      <ShowcaseSection />
      <SectionDivider />
      <section className="min-h-screen flex items-center justify-center relative z-[1] px-[60px] py-10">
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-[var(--text-muted)] text-sm">// AI integrations (Phase 5)</p>
      </section>
      <SectionDivider />
      <section className="min-h-screen flex items-center justify-center relative z-[1] px-[60px] py-10">
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-[var(--text-muted)] text-sm">// CTA + ASCII zoom (Phase 6)</p>
      </section>

      <footer className="border-t border-[var(--border)] px-[60px] py-6 text-center font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-[var(--text-muted)] tracking-wider relative z-[1]">
        Built by <a href="https://github.com/NandishNaik01" className="text-[var(--text-dim)] no-underline hover:text-[var(--accent)]">NandishNaik01</a> &middot;
        <a href="https://github.com/NandishNaik01/genalphacli" className="text-[var(--text-dim)] no-underline hover:text-[var(--accent)]"> GitHub</a> &middot; MIT
      </footer>
    </>
  );
}
