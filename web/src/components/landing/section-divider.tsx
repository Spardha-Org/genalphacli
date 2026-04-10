"use client";

export function SectionDivider() {
  return (
    <div
      className="h-px max-w-[1200px] mx-auto opacity-30"
      style={{
        background: "linear-gradient(90deg, transparent, var(--border), rgba(20,184,166,0.25), var(--border), transparent)",
        backgroundSize: "200% 100%",
        animation: "gradient-x 4s ease-in-out infinite",
      }}
    />
  );
}
