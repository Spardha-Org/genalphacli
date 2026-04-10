"use client";

import { useRef, useEffect, useState } from "react";
import { motion } from "framer-motion";

interface AiLogoProps {
  children: React.ReactNode;
  label: string;
  top?: string;
  left?: string;
  right?: string;
  bottom?: string;
  size?: number;
  isCenter?: boolean;
}

export function AiLogo({ children, label, top, left, right, bottom, size = 80, isCenter = false }: AiLogoProps) {
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const frame = useRef(0);
  const speed = useRef(1.5 + Math.random() * 2);
  const ampY = useRef(5 + Math.random() * 10);
  const ampX = useRef(3 + Math.random() * 5);
  const phase = useRef(Math.random() * Math.PI * 2);

  useEffect(() => {
    function animate() {
      const t = Date.now() / 1000;
      setOffset({
        y: Math.sin(t / speed.current + phase.current) * ampY.current,
        x: Math.cos(t / (speed.current * 1.4) + phase.current + 0.5) * ampX.current,
      });
      frame.current = requestAnimationFrame(animate);
    }
    frame.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame.current);
  }, []);

  return (
    <motion.div
      className="absolute z-[3] cursor-default"
      style={{
        top, left, right, bottom,
        width: size,
        height: size,
        marginTop: offset.y,
        marginLeft: offset.x,
      }}
      whileHover={{ scale: 1.12 }}
    >
      <div
        className={`w-full h-full rounded-[18px] flex items-center justify-center transition-all duration-300 ${
          isCenter
            ? "bg-[var(--surface)] border-2 border-[var(--accent)] shadow-[0_0_40px_var(--accent-glow)]"
            : "bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--accent)] hover:shadow-[0_0_30px_var(--accent-glow)]"
        }`}
      >
        {children}
      </div>
      <div
        className={`absolute -bottom-5 left-1/2 -translate-x-1/2 font-[family-name:var(--font-jetbrains-mono)] text-[7px] tracking-wider uppercase whitespace-nowrap ${
          isCenter ? "text-[var(--accent)] text-[9px]" : "text-[var(--text-muted)]"
        }`}
      >
        {label}
      </div>
    </motion.div>
  );
}
