"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { ASCII_ART } from "./ascii-banner";

export function CtaSection() {
  const ref = useRef(null);
  const asciiRef = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });
  const asciiInView = useInView(asciiRef, { once: true, amount: 0.3 });

  return (
    <section ref={ref} className="py-40 px-6 lg:px-[60px] text-center relative z-[1] flex flex-col items-center justify-center" style={{ minHeight: "120vh" }}>
      {/* Glow */}
      <div
        className="absolute w-[600px] h-[300px] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none"
        style={{ background: "radial-gradient(ellipse, var(--accent-glow), transparent 70%)" }}
      />

      <motion.div
        className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold tracking-[3px] uppercase text-[var(--accent)] mb-5"
        initial={{ opacity: 0, y: 30 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.7 }}
      >
        Initialize
      </motion.div>

      <motion.h2
        className="font-[family-name:var(--font-jetbrains-mono)] text-[clamp(28px,4vw,52px)] font-extrabold tracking-[-2px] mb-4 relative"
        initial={{ opacity: 0, y: 30 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.7, delay: 0.1 }}
      >
        STOP WRITING BOILERPLATE.
        <br />
        <span className="text-[var(--accent)]">START SHIPPING.</span>
      </motion.h2>

      <motion.p
        className="text-[var(--text-dim)] text-[15px] mb-10 relative"
        initial={{ opacity: 0, y: 30 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.7, delay: 0.2 }}
      >
        Open source. Free. Parse your first repo in 30 seconds.
      </motion.p>

      <motion.div
        className="flex gap-3 justify-center relative mb-16"
        initial={{ opacity: 0, y: 30 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.7, delay: 0.3 }}
      >
        <a
          href="/login"
          className="font-[family-name:var(--font-jetbrains-mono)] text-xs font-semibold tracking-[2px] uppercase bg-[var(--accent)] text-[var(--bg)] px-7 py-3.5 no-underline border border-[var(--accent)] flex items-center gap-2.5 transition-all hover:shadow-[0_0_40px_var(--accent-glow)] hover:-translate-y-0.5"
        >
          <span>&#9654;</span> Launch App
        </a>
        <a
          href="https://github.com/NandishNaik01/genalphacli"
          className="font-[family-name:var(--font-jetbrains-mono)] text-xs font-medium tracking-[2px] uppercase text-[var(--text-dim)] px-7 py-3.5 no-underline border border-[var(--border)] flex items-center gap-2.5 transition-all hover:border-[var(--accent)] hover:text-[var(--accent)]"
          target="_blank"
          rel="noopener noreferrer"
        >
          View Source
        </a>
      </motion.div>

      {/* ASCII banner — reveals line by line */}
      <div ref={asciiRef} className="text-center mt-8">
        {asciiInView && ASCII_ART.map((line, i) => (
          <motion.div
            key={i}
            className="font-[family-name:var(--font-jetbrains-mono)] text-[clamp(6px,1.2vw,11px)] text-[var(--accent)] whitespace-pre leading-[1.15]"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.12, duration: 0.4 }}
          >
            {line}
          </motion.div>
        ))}
        {asciiInView && (
          <motion.div
            className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-muted)] mt-3 tracking-[2px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: ASCII_ART.length * 0.12 + 0.3, duration: 0.5 }}
          >
            // v0.1.0 — Turn any API into a CLI & MCP Server
          </motion.div>
        )}
      </div>
    </section>
  );
}
