"use client";

export function GridBackground() {
  return (
    <>
      {/* Perspective grid */}
      <div className="fixed inset-0 pointer-events-none z-0" style={{ perspective: "600px", overflow: "hidden" }}>
        <div
          className="absolute"
          style={{
            width: "200%",
            height: "200%",
            left: "-50%",
            top: 0,
            backgroundImage:
              "linear-gradient(rgba(20,184,166,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(20,184,166,0.04) 1px, transparent 1px)",
            backgroundSize: "80px 80px",
            transform: "rotateX(60deg) translateY(-40%)",
            transformOrigin: "center top",
            maskImage: "linear-gradient(to bottom, rgba(0,0,0,0.25) 0%, transparent 50%)",
            WebkitMaskImage: "linear-gradient(to bottom, rgba(0,0,0,0.25) 0%, transparent 50%)",
            animation: "grid-scroll 20s linear infinite",
          }}
        />
      </div>

      {/* Scanlines */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          zIndex: 9999,
          background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.02) 2px, rgba(0,0,0,0.02) 4px)",
        }}
      />
    </>
  );
}
