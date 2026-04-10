import { GridBackground } from "@/components/landing/grid-background";
import { LandingNav } from "@/components/landing/landing-nav";
import { SectionDivider } from "@/components/landing/section-divider";

export default function LandingPage() {
  return (
    <>
      <GridBackground />
      <LandingNav />

      {/* Section 1: Hero */}
      <section className="min-h-screen grid grid-cols-[1fr_1.1fr] items-center gap-12 px-[60px] pt-[100px] relative z-[1]" style={{ marginBottom: "-200px" }}>
        <div>
          <div className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-muted)] mb-8 leading-[2.2]">
            <div>// PARALLEL_ENGINES&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-[var(--green)]">ONLINE</span></div>
            <div>// PARSER_LAYERS&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-[var(--accent)]">ACTIVE</span></div>
            <div>// READINESS_STATUS&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-[var(--green)]">READY</span></div>
          </div>
          <h1 className="font-[family-name:var(--font-jetbrains-mono)] text-[clamp(32px,4.5vw,56px)] font-extrabold leading-[0.95] tracking-[-2px] mb-6">
            <span className="text-[var(--text-muted)] font-light">SEE YOUR API.</span>
            <br />
            <span className="bg-gradient-to-br from-[var(--accent)] to-[var(--cyan)] bg-clip-text text-transparent">
              BUILD WHAT&apos;S NEXT.
            </span>
          </h1>
          <p className="text-[var(--text-dim)] text-[15px] max-w-[420px] leading-[1.7] mb-7">
            Paste a GitHub repo. We parse every route via static analysis. You get a CLI and an MCP server for AI agents — automatically.
          </p>
          <div className="flex gap-3">
            <a href="/login" className="font-[family-name:var(--font-jetbrains-mono)] text-xs font-semibold tracking-[2px] uppercase bg-[var(--accent)] text-[var(--bg)] px-7 py-3.5 no-underline border border-[var(--accent)] flex items-center gap-2.5 transition-all hover:shadow-[0_0_40px_var(--accent-glow)] hover:-translate-y-0.5">
              <span>&#9654;</span> Launch App
            </a>
            <a href="https://github.com/NandishNaik01/genalphacli" className="font-[family-name:var(--font-jetbrains-mono)] text-xs font-medium tracking-[2px] uppercase text-[var(--text-dim)] px-7 py-3.5 no-underline border border-[var(--border)] flex items-center gap-2.5 transition-all hover:border-[var(--accent)] hover:text-[var(--accent)]" target="_blank" rel="noopener noreferrer">
              View Source
            </a>
          </div>
        </div>

        {/* Terminal placeholder — xterm.js in Phase 2 */}
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg overflow-hidden shadow-[0_40px_100px_rgba(0,0,0,0.6)]">
          <div className="flex items-center gap-2 px-4 py-3 bg-[var(--elevated)] border-b border-[var(--border)]">
            <div className="w-3 h-3 rounded-full bg-[#ef4444] opacity-70" />
            <div className="w-3 h-3 rounded-full bg-[#eab308] opacity-70" />
            <div className="w-3 h-3 rounded-full bg-[#22c55e] opacity-70" />
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-[var(--text-muted)] ml-auto tracking-wider">nandish@genalpha ~/projects</span>
          </div>
          <div className="p-5 font-[family-name:var(--font-jetbrains-mono)] text-xs min-h-[340px] text-[var(--text-muted)]">
            // terminal loading...
          </div>
        </div>
      </section>

      <SectionDivider />

      {/* Sections 2-5: placeholders for Phases 3-6 */}
      <section id="flow" className="min-h-screen flex items-center justify-center relative z-[1] px-[60px] py-10">
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-[var(--text-muted)] text-sm">// horizontal parallax flow (Phase 3)</p>
      </section>
      <SectionDivider />
      <section id="features" className="min-h-screen flex items-center justify-center relative z-[1] px-[60px] py-10">
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-[var(--text-muted)] text-sm">// feature showcase (Phase 4)</p>
      </section>
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
