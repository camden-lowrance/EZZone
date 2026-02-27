<template>
  <!--
    Precise EZZone Hero Logo (Matching PNG):
    - Top: Voronoi-style management zones with white outlines on rainbow gradient
    - Middle: EZZone wordmark with horizontal glitch stripes (Cyan/Blue for EZ, Green for Zone)
    - Bottom: 3D perspective field lines in a "valley" pattern
    - Frame: Rounded badge with neon green glow
  -->
  <svg
    viewBox="0 0 1000 560"
    xmlns="http://www.w3.org/2000/svg"
    aria-label="EZZone"
    class="ezzone-hero"
  >
    <defs>
      <!-- Field Gradient -->
      <linearGradient id="g-field" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%"   stop-color="#052c1a" />
        <stop offset="100%" stop-color="#008f5d" />
      </linearGradient>

      <!-- Internal Shadow Gradients (Bleed to Text) -->
      <linearGradient id="g-shadow-down" x1="0" y1="0" x2="0" y2="1">
        <stop offset="50%" stop-color="#0d1117" stop-opacity="0" />
        <stop offset="100%" stop-color="#0d1117" stop-opacity="0.9" />
      </linearGradient>
      <linearGradient id="g-shadow-up" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#0d1117" stop-opacity="0.9" />
        <stop offset="50%" stop-color="#0d1117" stop-opacity="0" />
      </linearGradient>

      <!-- Heavy Outer Glow/Shadow -->
      <filter id="f-heavy-glow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="6" result="blur" />
        <feFlood flood-color="#00ff88" flood-opacity="0.4" result="color" />
        <feComposite in="color" in2="blur" operator="in" result="glow" />
        <!-- Drop shadow -->
        <feDropShadow dx="0" dy="4" stdDeviation="8" flood-color="#000" flood-opacity="0.8" />
        <feMerge>
          <feMergeNode in="glow" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>

      <!-- Text Stripe Patterns -->
      <pattern id="p-stripes-ez" x="0" y="0" width="1000" height="12" patternUnits="userSpaceOnUse">
        <rect width="1000" height="8" fill="#1adaff" />
        <rect y="8" width="1000" height="4" fill="#0d1117" />
      </pattern>
      <pattern id="p-stripes-zone" x="0" y="0" width="1000" height="12" patternUnits="userSpaceOnUse">
        <rect width="1000" height="8" fill="#1aff8c" />
        <rect y="8" width="1000" height="4" fill="#0d1117" />
      </pattern>

      <!-- Carbon/Checker Pattern -->
      <pattern id="p-checker" width="12" height="12" patternUnits="userSpaceOnUse">
        <rect width="6" height="6" fill="white" fill-opacity="0.03" />
        <rect x="6" y="6" width="6" height="6" fill="white" fill-opacity="0.03" />
      </pattern>

      <!-- Clip for Top Section -->
      <clipPath id="c-top">
        <rect x="65" y="65" width="870" height="135" rx="30" />
      </clipPath>
      
      <!-- Clip for Bottom Section -->
      <clipPath id="c-bottom">
        <rect x="65" y="385" width="870" height="95" rx="30" />
      </clipPath>

      <!-- Valley atmospheric glow -->
      <radialGradient id="g-valley-glow" cx="50%" cy="100%" r="80%">
        <stop offset="0%" stop-color="#00ff88" stop-opacity="0.4" />
        <stop offset="100%" stop-color="#00ff88" stop-opacity="0" />
      </radialGradient>
    </defs>

    <!-- Main Badge Background -->
    <rect x="40" y="40" width="920" height="480" rx="80" fill="#0d1117" />
    <rect x="40" y="40" width="920" height="480" rx="80" fill="url(#p-checker)" />

    <!-- ── TOP: Management Zones (Filled irregular polygons) ── -->
    <g clip-path="url(#c-top)">
      <!-- Zone 1: Red (left column) -->
      <path d="M 65,65 L 308,65 Q 342,100 335,132 Q 318,165 308,200 L 65,200 Z" fill="#cc2200" />
      <!-- Zone 2: Orange (upper center) -->
      <path d="M 308,65 L 665,65 Q 650,95 642,132 Q 575,115 500,117 Q 420,118 335,132 Q 342,100 308,65 Z" fill="#e87d00" />
      <!-- Zone 3: Blue (right column) -->
      <path d="M 665,65 L 935,65 L 935,200 L 662,200 Q 640,165 642,132 Q 650,95 665,65 Z" fill="#0055cc" />
      <!-- Zone 4: Green (lower center) -->
      <path d="M 335,132 Q 420,118 500,117 Q 575,115 642,132 Q 640,165 662,200 L 308,200 Q 318,165 335,132 Z" fill="#228844" />
      <!-- Zone borders -->
      <g fill="none" stroke="white" stroke-width="2.5" stroke-opacity="0.85">
        <path d="M 308,65 Q 342,100 335,132 Q 318,165 308,200" />
        <path d="M 665,65 Q 650,95 642,132 Q 640,165 662,200" />
        <path d="M 335,132 Q 420,118 500,117 Q 575,115 642,132" />
      </g>
      <!-- Shadow bleed (fade into text area) -->
      <rect x="65" y="65" width="870" height="135" fill="url(#g-shadow-down)" />
    </g>

    <!-- ── MIDDLE: EZZone Wordmark ── -->
    <g transform="translate(500, 300)">
      <text
        text-anchor="middle"
        font-family="Orbitron, 'Exo 2', sans-serif"
        font-weight="900"
        font-size="185"
        letter-spacing="-7"
        dominant-baseline="middle"
      >
        <tspan fill="url(#p-stripes-ez)">EZ</tspan><tspan fill="url(#p-stripes-zone)">Zone</tspan>
      </text>
      <!-- Subtler, wider glitch cuts -->
      <g fill="#0d1117" opacity="0.8">
        <rect x="-440" y="-90" width="150" height="4" />
        <rect x="-200" y="-120" width="120" height="3" />
        <rect x="-50" y="-40" width="200" height="4" />
        <rect x="220" y="-110" width="180" height="3" />
        <rect x="-450" y="20" width="900" height="2" />
      </g>
    </g>

    <!-- ── BOTTOM: Field ── -->
    <g clip-path="url(#c-bottom)">
      <rect x="65" y="385" width="870" height="100" fill="url(#g-field)" />
      <!-- Converging perspective lines -->
      <g fill="none" stroke="white" stroke-width="2.5" stroke-opacity="0.8">
        <line x1="500" y1="385" x2="500" y2="485" stroke-width="3" />
        <line x1="300" y1="385" x2="100" y2="485" />
        <line x1="420" y1="385" x2="380" y2="485" />
        <line x1="580" y1="385" x2="620" y2="485" />
        <line x1="700" y1="385" x2="900" y2="485" />
        <!-- Curved rows -->
        <path d="M65,405 Q500,450 935,405" stroke-width="1.5" stroke-opacity="0.6" />
        <path d="M65,440 Q500,485 935,440" stroke-width="1.5" stroke-opacity="0.6" />
        <path d="M65,475 Q500,520 935,475" stroke-width="1.5" stroke-opacity="0.6" />
      </g>
      
      <!-- Valley glow + Shadow Bleed overlay (Fade from text) -->
      <rect x="65" y="385" width="870" height="100" fill="url(#g-valley-glow)" />
      <rect x="65" y="385" width="870" height="100" fill="url(#g-shadow-up)" />
    </g>

    <!-- ── FRAME: Heavy Border ── -->
    <rect x="40" y="40" width="920" height="480" rx="80" 
          fill="none" stroke="#00ff88" stroke-width="5" filter="url(#f-heavy-glow)" />
    
    <!-- Inner subtle bezel -->
    <rect x="46" y="46" width="908" height="468" rx="54" 
          fill="none" stroke="white" stroke-width="1" stroke-opacity="0.1" />
  </svg>
</template>

<style scoped>
.ezzone-hero {
  display: block;
  width: min(48rem, 95vw);
  height: auto;
}
</style>
