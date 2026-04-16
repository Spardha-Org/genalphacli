---
date: 2026-04-10
topic: landing-page-implementation
---

# Landing Page Implementation — HTML Preview to Production Next.js

## What We're Building

Port the approved `web/landing-preview.html` design to production Next.js code with proper React components, Tailwind CSS, Framer Motion animations, and xterm.js terminal. The HTML preview is the source of truth for design — we're converting it to quality React code, not redesigning.

## Reference

The complete design lives in `web/landing-preview.html` — 5 sections:

1. **Hero**: Status HUD left + interactive terminal right (xterm.js with ASCII GENALPHA banner)
2. **Horizontal Parallax Flow**: Scroll-locked PARSE → BUILD → USE cards with code examples
3. **Feature Showcase**: "NOT JUST A CODE GENERATOR" text + animated SVG conversion scene
4. **AI Integrations**: Floating real logos (Claude, OpenAI, Gemini, Cursor, Copilot, Anthropic) with thread connections + "STITCH TO ANY AI" text
5. **CTA + ASCII Zoom**: "STOP WRITING BOILERPLATE" + ASCII banner that zooms to fill viewport then loops to top

## Key Decisions

- **Animation library**: Framer Motion — useInView for reveals, useScroll + useTransform for horizontal parallax, motion components for hover/float effects
- **Terminal**: xterm.js — real terminal emulator for the hero interactive shell, with custom command handler
- **Component structure**: Single page.tsx imports section components from `components/landing/`
- **Fonts**: Next.js local font for JetBrains Mono (self-hosted, no Google Fonts CDN)
- **Horizontal parallax**: Framer Motion useScroll + useTransform mapping vertical scroll to horizontal translateX
- **Styling**: Tailwind CSS with CSS custom properties for the accent color palette (already in the HTML)
- **SVG animations**: Keep inline SVG with SMIL animations (they work in React with dangerouslySetInnerHTML or as components)
- **Background effects**: CSS-only (perspective grid, scanlines) — no canvas/WebGL

## Component Breakdown

```
web/src/components/landing/
  hero-section.tsx          # Status HUD + headline + CTA (left side)
  hero-terminal.tsx         # xterm.js interactive terminal (right side)
  flow-section.tsx          # Horizontal parallax scroll with 3 flow cards
  flow-card.tsx             # Individual PARSE/BUILD/USE card
  showcase-section.tsx      # "Not just a code generator" + SVG scene
  conversion-svg.tsx        # Animated code→parser→CLI/MCP SVG
  ai-section.tsx            # AI logos grid + text (mirror of hero)
  ai-logo.tsx               # Single floating logo with dribble animation
  cta-section.tsx           # Bottom CTA + ASCII zoom takeover
  ascii-banner.tsx          # Reusable ASCII art GENALPHA component
  grid-background.tsx       # Perspective grid + scanlines overlay
  section-divider.tsx       # Animated gradient divider line
```

## Dependencies to Add

- `framer-motion` — scroll animations, reveal, hover effects
- `@xterm/xterm` — terminal emulator for hero
- `@xterm/addon-fit` — auto-resize terminal to container

## Open Questions

_None — all resolved during brainstorm._

## Next Steps

→ `/workflows:plan` for implementation phases and file-by-file tasks
