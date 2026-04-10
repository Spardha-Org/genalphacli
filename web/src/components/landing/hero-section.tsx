"use client";

import dynamic from "next/dynamic";
import { motion } from "framer-motion";

// Lazy load xterm.js — heavy dependency, SSR incompatible
const HeroTerminal = dynamic(
  () => import("./hero-terminal").then((m) => ({ default: m.HeroTerminal })),
  {
    ssr: false,
    loading: () => (
      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg overflow-hidden min-h-[400px] flex items-center justify-center">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-[var(--text-muted)]">
          // loading terminal...
        </span>
      </div>
    ),
  }
);

const stagger = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: 0.2 + i * 0.1, duration: 0.7, ease: "easeOut" as const },
  }),
};

export function HeroSection() {
  return (
    <section
      className="min-h-screen grid grid-cols-1 lg:grid-cols-[1fr_1.1fr] items-center gap-12 px-6 lg:px-[60px] pt-[100px] relative z-[1]"
      style={{ marginBottom: "-200px" }}
    >
      {/* Left: Text */}
      <div>
        <motion.div
          className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-muted)] mb-8 leading-[2.2]"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
        >
          <div>
            // PARALLEL_ENGINES&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
            <span className="text-[var(--green)]">ONLINE</span>
          </div>
          <div>
            // PARSER_LAYERS&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
            <span className="text-[var(--accent)]">ACTIVE</span>
          </div>
          <div>
            // READINESS_STATUS&nbsp;&nbsp;&nbsp;&nbsp;
            <span className="text-[var(--green)]">READY</span>
          </div>
        </motion.div>

        <motion.h1
          className="font-[family-name:var(--font-jetbrains-mono)] text-[clamp(32px,4.5vw,56px)] font-extrabold leading-[0.95] tracking-[-2px] mb-6"
          custom={1}
          initial="hidden"
          animate="visible"
          variants={stagger}
        >
          <span className="text-[var(--text-muted)] font-light">SEE YOUR API.</span>
          <br />
          <span className="bg-gradient-to-br from-[var(--accent)] to-[var(--cyan)] bg-clip-text text-transparent">
            BUILD WHAT&apos;S NEXT.
          </span>
        </motion.h1>

        <motion.p
          className="text-[var(--text-dim)] text-[15px] max-w-[420px] leading-[1.7] mb-7"
          custom={2}
          initial="hidden"
          animate="visible"
          variants={stagger}
        >
          Paste a GitHub repo. We parse every route via static analysis. You get
          a CLI and an MCP server for AI agents — automatically.
        </motion.p>

        <motion.div
          className="flex gap-3"
          custom={3}
          initial="hidden"
          animate="visible"
          variants={stagger}
        >
          <a
            href="/login"
            className="group font-[family-name:var(--font-jetbrains-mono)] text-xs font-semibold tracking-[2px] uppercase bg-[var(--accent)] text-[var(--bg)] px-7 py-3.5 no-underline border border-[var(--accent)] flex items-center gap-2.5 transition-all hover:shadow-[0_0_40px_var(--accent-glow)] hover:-translate-y-0.5 relative overflow-hidden"
          >
            <span>&#9654;</span> Launch App
            <span className="absolute top-0 left-[-100%] w-full h-full bg-gradient-to-r from-transparent via-white/10 to-transparent group-hover:left-[100%] transition-[left] duration-500" />
          </a>
          <a
            href="https://github.com/NandishNaik01/genalphacli"
            className="font-[family-name:var(--font-jetbrains-mono)] text-xs font-medium tracking-[2px] uppercase text-[var(--text-dim)] px-7 py-3.5 no-underline border border-[var(--border)] flex items-center gap-2.5 transition-all hover:border-[var(--accent)] hover:text-[var(--accent)]"
            target="_blank"
            rel="noopener noreferrer"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
            </svg>
            View Source
          </a>
        </motion.div>
      </div>

      {/* Right: Interactive Terminal */}
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        <HeroTerminal />
      </motion.div>
    </section>
  );
}
