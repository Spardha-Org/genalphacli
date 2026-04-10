"use client";

import { useRef, useEffect } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { FlowCard } from "./flow-card";

const PARSE_LINES = [
  { text: "$ genalpha parse github.com/you/api", color: "var(--text)" },
  { text: "✓ Cloned repository", color: "var(--green)" },
  { text: "✓ Detected FastAPI framework", color: "var(--green)" },
  { text: "✓ OpenAPI spec: 12 routes", color: "var(--green)" },
  { text: "✓ AST extraction: 23 routes", color: "var(--green)" },
  { text: "✓ Merged: 23 unique routes in 39ms", color: "var(--accent)" },
];

const BUILD_LINES = [
  { text: "$ genalpha build --type cli --type mcp", color: "var(--text)" },
  { text: "" },
  { text: "✓ Generated CLI tool", color: "var(--green)" },
  { text: "  └ myapi list-users", color: "var(--blue)" },
  { text: "  └ myapi create-user --body", color: "var(--blue)" },
  { text: "  └ myapi --help (23 commands)", color: "var(--blue)" },
  { text: "" },
  { text: "✓ Generated MCP server", color: "var(--green)" },
  { text: "  └ @mcp.tool(\"list_users\")", color: "var(--violet)" },
  { text: "  └ @mcp.tool(\"create_user\")", color: "var(--violet)" },
  { text: "  └ Auto-registered with Claude", color: "var(--text-dim)" },
];

const USE_LINES = [
  { text: "# CLI", color: "var(--text-muted)" },
  { text: "$ cd dist/myapi && pip install .", color: "var(--text)" },
  { text: "$ myapi list-users --pretty", color: "var(--text)" },
  { text: '[{"id":1,"name":"Alice"},...]', color: "var(--green)" },
  { text: "" },
  { text: "# MCP (Claude Desktop)", color: "var(--text-muted)" },
  { text: 'User: "list all users"', color: "var(--violet)" },
  { text: "Claude: Calling list_users()", color: "var(--green)" },
  { text: '[{"id":1,"name":"Alice"},...]', color: "var(--green)" },
];

export function FlowSection() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ["start start", "end end"] });

  // Allow horizontal trackpad/wheel to drive vertical scroll within the horizontal phase only
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const handler = (e: WheelEvent) => {
      const rect = el.getBoundingClientRect();
      const sectionHeight = el.offsetHeight - window.innerHeight;
      const progress = sectionHeight > 0 ? Math.abs(rect.top) / sectionHeight : 0;
      const inHorizontalPhase = rect.top <= 0 && progress < 0.8;

      if (inHorizontalPhase && Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
        window.scrollBy({ top: e.deltaX, behavior: "instant" as ScrollBehavior });
        e.preventDefault();
      }
    };

    window.addEventListener("wheel", handler, { passive: false });
    return () => window.removeEventListener("wheel", handler);
  }, []);

  // Horizontal scroll stops when 3rd card reaches center, then section releases quickly
  // [0, 0.8] = horizontal scroll phase, [0.8, 1] = short release buffer
  const x = useTransform(scrollYProgress, [0, 0.8], ["0%", "-38%"]);

  return (
    <section ref={containerRef} id="flow" className="relative z-[1]" style={{ height: "250vh" }}>
      <div className="sticky top-0 h-screen flex items-center overflow-hidden">
        <motion.div className="flex items-center gap-0 pl-[60px]" style={{ x }}>

          {/* Intro text */}
          <div className="flex-shrink-0 w-[360px] pr-10">
            <div className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold tracking-[3px] uppercase text-[var(--accent)] mb-5">
              Pipeline
            </div>
            <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[36px] font-extrabold tracking-[-1.5px] leading-[1.05] mb-4">
              ONE PIPELINE.
              <br />
              <span className="text-[var(--accent)]">THREE OUTPUTS.</span>
            </h2>
            <p className="text-[var(--text-dim)] text-[14px] leading-[1.7]">
              Scroll to explore the full GenAlpha pipeline — from your repo to installable tools.
            </p>
          </div>

          {/* Arrow from intro to first card */}
          <div className="flex-shrink-0 w-20 flex items-center justify-center">
            <svg width="60" height="40" className="overflow-visible">
              <line x1="0" y1="20" x2="50" y2="20" stroke="var(--border)" strokeWidth="2" strokeDasharray="6 4" />
              <polygon points="50,14 60,20 50,26" fill="var(--accent)" />
            </svg>
          </div>

          {/* PARSE */}
          <FlowCard
            stepNumber="01"
            tag="Step 01 — Parse"
            tagColor="var(--green)"
            title="Clone + Detect + Extract"
            description="We clone your repo, detect the framework automatically, and extract every API route via two-layer static analysis."
            codeLines={PARSE_LINES}
          />

          {/* BUILD */}
          <FlowCard
            stepNumber="02"
            tag="Step 02 — Build"
            tagColor="var(--blue)"
            title="Generate CLI + MCP"
            description="Choose your output: a Typer CLI, a FastMCP server for AI agents, or both. Pip-installable packages, ready to ship."
            codeLines={BUILD_LINES}
          />

          {/* USE */}
          <FlowCard
            stepNumber="03"
            tag="Step 03 — Use"
            tagColor="var(--violet)"
            title="Ship Instantly"
            description="Install the CLI with pip. MCP auto-registers with Claude Desktop. Your API is accessible from terminal and AI agents."
            codeLines={USE_LINES}
            showArrow={false}
          />

          {/* End spacer */}
          <div className="flex-shrink-0 w-[200px]" />
        </motion.div>
      </div>
    </section>
  );
}
