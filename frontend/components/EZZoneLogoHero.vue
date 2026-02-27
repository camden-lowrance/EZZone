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
      <!-- Zone Gradient (Strictly Red to Blue, full width) -->
      <linearGradient id="g-rainbow" gradientUnits="userSpaceOnUse" x1="65" y1="0" x2="935" y2="0">
        <stop offset="0%"   stop-color="#ff3333" />
        <stop offset="100%" stop-color="#3366ff" />
      </linearGradient>

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

    <!-- ── TOP: Management Zones (Natural Geometric Mesh) ── -->
    <g clip-path="url(#c-top)">
      <!-- Background Gradient -->
      <rect x="60" y="60" width="880" height="140" fill="url(#g-rainbow)" />
      
      <!-- Distinct Geometric Pattern: Interlocking Staggered Polygons -->
      <!-- This creates a 'mesh' feel that is orderly but biologically plausible (like cells or plots) -->
      <g fill="none" stroke="white" stroke-width="2.5" stroke-opacity="0.9" stroke-linejoin="round" stroke-linecap="square">
        <!-- Horizontal undulating dividers -->
        <path d="M60,110 L180,120 L300,100 L450,115 L600,95 L750,110 L940,100" />
        <path d="M60,155 L180,165 L300,145 L450,160 L600,140 L750,155 L940,145" />
        
        <!-- Angled Vertical Dividers (Staggered to prevent a rigid grid look) -->
        <!-- Row 1 -->
        <line x1="180" y1="60" x2="180" y2="120" />
        <line x1="450" y1="60" x2="450" y2="115" />
        <line x1="750" y1="60" x2="750" y2="110" />
        
        <!-- Row 2 -->
        <line x1="300" y1="100" x2="300" y2="145" />
        <line x1="600" y1="95" x2="600" y2="140" />
        <line x1="900" y1="100" x2="900" y2="145" /> <!-- Extra edge detail -->
        
        <!-- Row 3 -->
        <line x1="180" y1="165" x2="180" y2="200" />
        <line x1="450" y1="160" x2="450" y2="200" />
        <line x1="750" y1="155" x2="750" y2="200" />
      </g>
      
      <!-- Shadow Bleed overlay (Fade to text) -->
      <rect x="60" y="60" width="880" height="140" fill="url(#g-shadow-down)" />
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
