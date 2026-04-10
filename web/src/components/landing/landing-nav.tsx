"use client";

import Link from "next/link";

export function LandingNav() {
  return (
    <nav
      className="fixed top-0 left-0 right-0 z-[100] flex items-center justify-between px-10 py-3.5"
      style={{
        background: "rgba(5, 5, 7, 0.5)",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <Link
        href="/"
        className="font-[family-name:var(--font-jetbrains-mono)] font-extrabold text-lg tracking-wide uppercase text-[var(--text)] no-underline"
      >
        <span className="text-[var(--accent)]">//</span> GenAlpha
      </Link>

      <div className="flex items-center gap-6">
        <a
          href="#flow"
          className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-dim)] no-underline tracking-wider uppercase hover:text-[var(--accent)] transition-colors"
        >
          Pipeline
        </a>
        <a
          href="#features"
          className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-dim)] no-underline tracking-wider uppercase hover:text-[var(--accent)] transition-colors"
        >
          Capabilities
        </a>
        <a
          href="https://github.com/NandishNaik01/genalphacli"
          className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-dim)] no-underline tracking-wider uppercase hover:text-[var(--accent)] transition-colors"
          target="_blank"
          rel="noopener noreferrer"
        >
          GitHub
        </a>
        <Link
          href="/login"
          className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] font-semibold tracking-wider uppercase bg-[var(--accent)] text-[var(--bg)] px-5 py-2 rounded-sm no-underline border border-[var(--accent)] hover:bg-transparent hover:text-[var(--accent)] transition-all"
        >
          Launch App
        </Link>
      </div>
    </nav>
  );
}
