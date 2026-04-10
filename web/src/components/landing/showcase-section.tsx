"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { ConversionSvg } from "./conversion-svg";

const features = [
  { label: "OpenAPI spec detection + Python AST extraction", color: "var(--green)" },
  { label: "Cross-file include_router prefix resolution", color: "var(--blue)" },
  { label: "Dependency injection param filtering", color: "var(--violet)" },
  { label: "Full Pydantic model schema extraction", color: "var(--amber)" },
  { label: "Response format detection from decorators", color: "var(--accent)" },
  { label: "GitHub OAuth for private repo access", color: "var(--rose)" },
];

export function ShowcaseSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section
      id="features"
      ref={ref}
      className="min-h-screen grid grid-cols-1 lg:grid-cols-2 items-center gap-16 px-6 lg:px-[60px] py-10 relative z-[1]"
    >
      {/* Left: Text */}
      <div className="max-w-[480px]">
        <motion.div
          className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold tracking-[3px] uppercase text-[var(--accent)] mb-5"
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
        >
          Under The Hood
        </motion.div>

        <motion.h2
          className="font-[family-name:var(--font-jetbrains-mono)] text-[clamp(28px,4vw,48px)] font-extrabold tracking-[-2px] leading-[1] mb-5"
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.1 }}
        >
          NOT JUST A
          <br />
          <span className="bg-gradient-to-br from-[var(--accent)] to-[var(--cyan)] bg-clip-text text-transparent">
            CODE GENERATOR.
          </span>
        </motion.h2>

        <motion.p
          className="text-[var(--text-dim)] text-[14px] leading-[1.7] mb-6"
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.2 }}
        >
          GenAlpha understands your API at a deep level. Two-layer static
          analysis, cross-file router resolution, Pydantic model extraction,
          and intelligent parameter classification.
        </motion.p>

        <ul className="list-none mt-6">
          {features.map((feat, i) => (
            <motion.li
              key={i}
              className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-[var(--text-dim)] py-2.5 border-b border-[var(--border)] flex items-center gap-3 transition-colors hover:text-[var(--text)]"
              initial={{ opacity: 0, x: -20 }}
              animate={isInView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.3 + i * 0.08 }}
            >
              <span
                className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                style={{ background: feat.color }}
              />
              {feat.label}
            </motion.li>
          ))}
        </ul>
      </div>

      {/* Right: Animated SVG conversion scene */}
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.9, delay: 0.3 }}
      >
        <ConversionSvg />
      </motion.div>
    </section>
  );
}
