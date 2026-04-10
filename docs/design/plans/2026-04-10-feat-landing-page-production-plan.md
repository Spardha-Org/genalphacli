---
title: "feat: Production Landing Page"
type: feat
status: active
date: 2026-04-10
---

# feat: Production Landing Page

## Overview

Port `web/landing-preview.html` to production Next.js code. The HTML preview is the approved design — this plan converts it to React components with Framer Motion, xterm.js, Tailwind, and self-hosted fonts.

## Reference

Design spec: `web/landing-preview.html` (open in browser to see all sections and interactions)

## Implementation Phases

### Phase 1: Foundation (deps + layout + background)

**Tasks:**

- [ ] Install deps: `framer-motion`, `@xterm/xterm`, `@xterm/addon-fit`
- [ ] Download JetBrains Mono font files, configure via `next/font/local` in layout.tsx
- [ ] Add CSS custom properties to `globals.css` (copy color palette from HTML `:root`)
- [ ] Create `components/landing/grid-background.tsx` — perspective grid + scanlines (CSS-only, fixed position)
- [ ] Create `components/landing/section-divider.tsx` — animated gradient line
- [ ] Update `(public)/page.tsx` to import all section components
- [ ] Remove old landing page content

**Files:**
```
web/src/app/globals.css                    # Add :root color vars
web/src/app/(public)/page.tsx              # Import all sections
web/src/components/landing/grid-background.tsx
web/src/components/landing/section-divider.tsx
```

**Success criteria:**
- [ ] Page loads with dark background, perspective grid, scanlines
- [ ] JetBrains Mono renders from local font

### Phase 2: Hero Section (left text + right xterm.js terminal)

**Tasks:**

- [ ] Create `components/landing/hero-section.tsx`:
  - Split grid layout (1fr 1.1fr)
  - Status HUD (PARALLEL_ENGINES: ONLINE etc.)
  - Headline with gradient text
  - Subtitle + CTA buttons (Launch App + View Source)
  - All text animated with Framer Motion stagger
- [ ] Create `components/landing/hero-terminal.tsx`:
  - xterm.js instance with dark theme matching our palette
  - Custom key handler: intercepts Enter, ArrowUp/Down
  - Command registry: `hello`, `genalpha --help`, `genalpha parse`, `genalpha build`, `make dev`, `whoami`, `ls`, `clear`, `help`
  - `hello` command triggers ASCII GENALPHA banner with line-by-line reveal
  - Auto-plays `hello` on mount after 1.5s delay
  - Addon-fit for responsive sizing
- [ ] Create `components/landing/ascii-banner.ts` — ASCII art data + typing helper

**Files:**
```
web/src/components/landing/hero-section.tsx
web/src/components/landing/hero-terminal.tsx
web/src/components/landing/ascii-banner.ts
```

**Success criteria:**
- [ ] Hero renders with split layout
- [ ] Terminal auto-plays `hello` → ASCII banner appears
- [ ] User can type commands and get responses
- [ ] Terminal resizes with viewport

### Phase 3: Horizontal Parallax Flow Section

**Tasks:**

- [ ] Create `components/landing/flow-section.tsx`:
  - Outer container with `height: 500vh` for scroll distance
  - Sticky inner container (`position: sticky; top: 0; height: 100vh`)
  - Framer Motion `useScroll` on the outer ref + `useTransform` mapping scrollYProgress to translateX
  - Contains intro text + 3 flow cards + connector arrows
- [ ] Create `components/landing/flow-card.tsx`:
  - Receives: step number, tag, title, description, code lines
  - Code block with staggered line reveal (Framer `useInView` + `staggerChildren`)
  - Hover: lift + border glow
- [ ] Animated connector arrows between cards (inline SVG with dash animation)

**Files:**
```
web/src/components/landing/flow-section.tsx
web/src/components/landing/flow-card.tsx
```

**Success criteria:**
- [ ] Section locks while scrolling, cards move horizontally
- [ ] Code lines in cards appear one-by-one when card enters view
- [ ] Smooth 60fps scroll-linked animation
- [ ] Releases scroll after last card is fully visible

### Phase 4: Feature Showcase Section

**Tasks:**

- [ ] Create `components/landing/showcase-section.tsx`:
  - Grid layout: text left (tag, headline, paragraph, feature list), SVG right
  - Framer Motion reveal on scroll
- [ ] Create `components/landing/conversion-svg.tsx`:
  - Animated SVG: code panel → flowing dots → parser box → CLI/MCP output panels
  - Keep SMIL animations from HTML (they work in JSX)
  - Wrap in a component that triggers animation when in view

**Files:**
```
web/src/components/landing/showcase-section.tsx
web/src/components/landing/conversion-svg.tsx
```

**Success criteria:**
- [ ] Text and SVG reveal on scroll
- [ ] SVG animation plays (code lines appear, dots flow, outputs fade in)

### Phase 5: AI Integrations Section

**Tasks:**

- [ ] Create `components/landing/ai-section.tsx`:
  - Grid layout: floating logos left, text right (mirror of hero)
  - SVG thread lines connecting logos with animated pulse dots
- [ ] Create `components/landing/ai-logo.tsx`:
  - Receives: SVG icon, label, position
  - Framer Motion `animate` with custom float/dribble using `useMotionValue` + sine wave
  - Hover: scale + glow
- [ ] Inline SVG logos for: Claude, OpenAI, Gemini, Cursor, Copilot, Anthropic, GenAlpha (center)

**Files:**
```
web/src/components/landing/ai-section.tsx
web/src/components/landing/ai-logo.tsx
```

**Success criteria:**
- [ ] Logos float independently with gentle dribble
- [ ] Thread lines visible with traveling pulse dots
- [ ] Right text reveals on scroll
- [ ] Hover on logos shows glow effect

### Phase 6: CTA + ASCII Zoom Transition

**Tasks:**

- [ ] Create `components/landing/cta-section.tsx`:
  - Tag, headline, subtitle, CTA buttons
  - ASCII banner component that reveals line-by-line on scroll (Framer `useInView`)
- [ ] Implement zoom takeover:
  - After ASCII lines finish, fixed overlay fades in
  - ASCII text scales up 8x via Framer `animate`
  - After 2s, overlay fades out + `window.scrollTo(0)` instant
  - Overlay unmounts, user is back at hero
  - Re-arms via state reset so it loops
- [ ] Glow effect behind CTA (radial gradient, CSS)

**Files:**
```
web/src/components/landing/cta-section.tsx
```

**Success criteria:**
- [ ] ASCII banner animates in at bottom
- [ ] Zoom takeover fills viewport
- [ ] Scrolls to top after animation
- [ ] Works on repeat visits to bottom

### Phase 7: Polish + Cleanup

**Tasks:**

- [ ] Delete `web/landing-preview.html` (no longer needed)
- [ ] Mobile responsive: stack hero grid, hide terminal on mobile, flow section fallback
- [ ] Ensure nav links (#flow, #features) work with smooth scroll
- [ ] Test all Framer Motion animations on slower hardware (reduce motion media query)
- [ ] Add `prefers-reduced-motion` fallback (disable animations, show static content)
- [ ] Verify Next.js build passes
- [ ] Verify 94 Python tests still pass

**Success criteria:**
- [ ] Page looks identical to HTML preview
- [ ] Works on mobile (graceful degradation)
- [ ] Build clean, no TypeScript errors
- [ ] Respects reduced motion preferences

## Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| framer-motion | latest | Scroll animations, reveals, hover, parallax |
| @xterm/xterm | 5.x | Interactive hero terminal |
| @xterm/addon-fit | 0.10.x | Terminal auto-resize |
| next/font/local | built-in | Self-hosted JetBrains Mono |

## File Structure

```
web/src/components/landing/
  grid-background.tsx       # Perspective grid + scanlines
  section-divider.tsx       # Animated gradient line
  hero-section.tsx          # Status HUD + headline + CTA
  hero-terminal.tsx         # xterm.js interactive terminal
  ascii-banner.ts           # ASCII art data + helpers
  flow-section.tsx          # Horizontal parallax scroll container
  flow-card.tsx             # PARSE/BUILD/USE card
  showcase-section.tsx      # "Not just a code generator" + feature list
  conversion-svg.tsx        # Animated code→CLI/MCP SVG
  ai-section.tsx            # AI logos + text
  ai-logo.tsx               # Single floating logo
  cta-section.tsx           # Bottom CTA + ASCII zoom takeover
```

## References

- Design spec: `web/landing-preview.html`
- Brainstorm: `docs/design/brainstorms/2026-04-10-landing-page-implementation-brainstorm.md`
- [Framer Motion scroll animations](https://motion.dev/docs/react-scroll-animations)
- [xterm.js docs](https://xtermjs.org/)
