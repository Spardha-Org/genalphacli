"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { AiLogo } from "./ai-logo";

// Inline SVG logos
function ClaudeLogo() {
  return <svg className="w-10 h-10" viewBox="0 0 46 32" fill="none"><path d="M28.724.006 16.202 22.33l-4.136-7.39L22.282.006h6.442ZM17.14.006.002 30.644h6.604L17.462 12.77l3.202 5.725L12.19 30.644h6.604l4.474-7.923 3.202 5.726-3.07 5.44h6.604L45.998.006h-6.604L28.536 18.804l-3.2-5.726L36.19.006H29.59l-6.256 11.08L20.13.006H17.14Z" fill="#D97757"/></svg>;
}
function OpenAILogo() {
  return <svg className="w-10 h-10" viewBox="0 0 24 24" fill="#fff"><path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.998 5.998 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073ZM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494ZM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646ZM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872Zm16.597 3.855-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667Zm2.01-3.023-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66ZM8.324 12.952l-2.019-1.164a.08.08 0 0 1-.038-.057V6.148a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.72 5.534a.795.795 0 0 0-.393.681l-.003 6.737Zm1.096-2.365L12 8.96l2.58 1.488v2.976l-2.58 1.488-2.58-1.488Z"/></svg>;
}
function GeminiLogo() {
  return <svg className="w-10 h-10" viewBox="0 0 24 24"><defs><linearGradient id="gem-grad" x1="0" y1="0" x2="24" y2="24"><stop offset="0%" stopColor="#4285F4"/><stop offset="50%" stopColor="#9B72CB"/><stop offset="100%" stopColor="#D96570"/></linearGradient></defs><path d="M12 0C12 6.627 6.627 12 0 12c6.627 0 12 5.373 12 12 0-6.627 5.373-12 12-12-6.627 0-12-5.373-12-12Z" fill="url(#gem-grad)"/></svg>;
}
function CursorLogo() {
  return <svg className="w-10 h-10" viewBox="0 0 24 24" fill="none"><rect width="18" height="18" x="3" y="3" rx="3" stroke="#fff" strokeWidth="1.5"/><path d="M8 8l4 4-4 4" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/><line x1="14" y1="16" x2="18" y2="16" stroke="#fff" strokeWidth="1.5" strokeLinecap="round"/></svg>;
}
function CopilotLogo() {
  return <svg className="w-10 h-10" viewBox="0 0 24 24" fill="#fff"><path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0 1 12 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.163 22 16.418 22 12c0-5.523-4.477-10-10-10Z"/></svg>;
}
function AnthropicLogo() {
  return <svg className="w-10 h-10" viewBox="0 0 24 24" fill="#D97757"><path d="M13.827 3.52h3.603L24 20.48h-3.603l-6.57-16.96zm-7.258 0h3.767L16.906 20.48h-3.674l-1.478-3.906H5.246l-1.458 3.906H0L6.569 3.52zm.725 4.986L4.97 14.118h5.648L8.294 8.506h-1z"/></svg>;
}
function GenAlphaIcon() {
  return <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#14b8a6" strokeWidth="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>;
}

export function AiSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section ref={ref} className="grid grid-cols-1 lg:grid-cols-2 items-center gap-16 px-6 lg:px-[60px] py-16 mt-42 -mb-28 relative z-[1]">

      {/* Left: Floating logos with thread connections */}
      <motion.div
        className="relative h-[480px]"
        initial={{ opacity: 0 }}
        animate={isInView ? { opacity: 1 } : {}}
        transition={{ duration: 0.8 }}
      >
        {/* Thread SVG */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-[1]" viewBox="0 0 500 480">
          {[
            "M90,60 L250,200", "M380,50 L250,200", "M440,200 L250,200",
            "M40,280 L250,200", "M120,400 L250,200", "M350,420 L250,200",
          ].map((d, i) => (
            <g key={i}>
              <path d={d} stroke="rgba(255,255,255,0.06)" strokeWidth="1" fill="none" />
              <circle r="2" fill="#fff" opacity=".3">
                <animateMotion dur={`${3.5 + i * 0.5}s`} repeatCount="indefinite" path={d} begin={`${i * 0.4}s`} />
              </circle>
            </g>
          ))}
        </svg>

        {/* Claude */}
        <AiLogo label="Claude" top="20px" left="60px"><ClaudeLogo /></AiLogo>
        {/* OpenAI */}
        <AiLogo label="OpenAI" top="10px" right="80px"><OpenAILogo /></AiLogo>
        {/* Gemini */}
        <AiLogo label="Gemini" top="180px" right="20px"><GeminiLogo /></AiLogo>
        {/* GenAlpha (center, bigger) */}
        <AiLogo label="GenAlpha" top="140px" left="50%" size={96} isCenter><GenAlphaIcon /></AiLogo>
        {/* Cursor */}
        <AiLogo label="Cursor" bottom="50px" left="10px"><CursorLogo /></AiLogo>
        {/* Copilot */}
        <AiLogo label="Copilot" bottom="40px" left="48%"><CopilotLogo /></AiLogo>
        {/* Anthropic */}
        <AiLogo label="Anthropic" bottom="50px" right="60px"><AnthropicLogo /></AiLogo>
      </motion.div>

      {/* Right: Text (mirror of hero — right aligned) */}
      <div className="lg:text-right">
        <motion.div
          className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold tracking-[3px] uppercase text-[var(--accent)] mb-5"
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.2 }}
        >
          Integrations
        </motion.div>

        <motion.h2
          className="font-[family-name:var(--font-jetbrains-mono)] text-[clamp(28px,4vw,52px)] font-extrabold tracking-[-2px] leading-[1.05] mb-5"
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.3 }}
        >
          STITCH CLI + MCP
          <br />
          TO{" "}
          <span className="bg-gradient-to-br from-[var(--accent)] to-[var(--cyan)] bg-clip-text text-transparent">
            ANY AI.
          </span>
        </motion.h2>

        <motion.p
          className="text-[var(--text-dim)] text-[15px] leading-[1.7] mb-5 lg:ml-auto max-w-[440px]"
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.4 }}
        >
          Skip the GUI. Your generated MCP server plugs directly into Claude,
          Cursor, Codex, and any AI agent that speaks MCP. Your CLI works from
          any terminal, script, or CI pipeline.
        </motion.p>

        <motion.p
          className="text-[var(--text-muted)] text-[13px] font-[family-name:var(--font-jetbrains-mono)] mb-7"
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.5 }}
        >
           One parse. Every AI agent. No GUI needed.
        </motion.p>

        <motion.div
          className="flex gap-3 lg:justify-end"
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.6 }}
        >
          <a
            href="/login"
            className="font-[family-name:var(--font-jetbrains-mono)] text-xs font-semibold tracking-[2px] uppercase bg-[var(--accent)] text-[var(--bg)] px-7 py-3.5 no-underline border border-[var(--accent)] flex items-center gap-2.5 transition-all hover:shadow-[0_0_40px_var(--accent-glow)] hover:-translate-y-0.5"
          >
            <span>&#9654;</span> Launch App
          </a>
        </motion.div>
      </div>
    </section>
  );
}
