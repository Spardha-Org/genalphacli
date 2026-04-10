"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";

interface FlowCardProps {
  stepNumber: string;
  tag: string;
  tagColor: string;
  title: string;
  description: string;
  codeLines: { text: string; color?: string }[];
  showArrow?: boolean;
}

export function FlowCard({ stepNumber, tag, tagColor, title, description, codeLines, showArrow = true }: FlowCardProps) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <div className="relative flex items-center">
      <motion.div
        ref={ref}
        className="flex-shrink-0 w-[440px] bg-[var(--surface)] border border-[var(--border)] rounded-lg p-9 relative transition-all duration-400 hover:bg-[var(--elevated)] hover:-translate-y-2 hover:border-[var(--accent)] hover:shadow-[0_0_40px_var(--accent-glow)]"
      >
        {/* Step tag */}
        <div
          className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold tracking-[3px] uppercase mb-4"
          style={{ color: tagColor }}
        >
          {tag}
        </div>

        {/* Title */}
        <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-[22px] font-extrabold tracking-[-1px] mb-3">
          {title}
        </h3>

        {/* Description */}
        <p className="text-[var(--text-dim)] text-[13px] leading-[1.7] mb-4">
          {description}
        </p>

        {/* Code block with staggered line reveal */}
        <div className="bg-[var(--elevated)] border border-[var(--border)] rounded p-4 font-[family-name:var(--font-jetbrains-mono)] text-[10px] leading-[1.7] text-left overflow-hidden">
          {codeLines.map((line, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -10 }}
              animate={isInView ? { opacity: 1, x: 0 } : {}}
              transition={{ delay: 0.3 + i * 0.12, duration: 0.4, ease: "easeOut" }}
              style={{ color: line.color || "var(--text-dim)" }}
            >
              {line.text || "\u00A0"}
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Connector arrow */}
      {showArrow && (
        <div className="flex-shrink-0 w-20 flex items-center justify-center">
          <svg width="60" height="40" className="overflow-visible">
            <line
              x1="0" y1="20" x2="50" y2="20"
              stroke="var(--border)"
              strokeWidth="2"
              strokeDasharray="6 4"
              className="animate-[flow-dash_1s_linear_infinite]"
            />
            <polygon points="50,14 60,20 50,26" fill="var(--accent)" />
          </svg>
        </div>
      )}
    </div>
  );
}
