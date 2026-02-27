<template>
  <!--
    Hero badge logo:
    - Top band: 8 parallelogram "field rows from above" with rainbow gradient
    - Middle: EZZone wordmark (same stripe technique, larger)
    - Bottom: perspective field lines converging to vanishing point
    - Outer: rounded rect with green glow border
  -->
  <svg
    viewBox="0 0 600 400"
    xmlns="http://www.w3.org/2000/svg"
    aria-label="EZZone"
    class="ezzone-hero"
  >
    <defs>
      <!-- Green outer glow for badge border -->
      <filter id="hf-glow" x="-8%" y="-8%" width="116%" height="116%">
        <feGaussianBlur stdDeviation="6" in="SourceAlpha" result="blur" />
        <feFlood flood-color="#00ff88" flood-opacity="0.55" result="color" />
        <feComposite in="color" in2="blur" operator="in" result="glow" />
        <feMerge>
          <feMergeNode in="glow" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>

      <!-- Subtle text glow -->
      <filter id="hf-text-glow" x="-5%" y="-20%" width="110%" height="140%">
        <feGaussianBlur stdDeviation="3" in="SourceAlpha" result="blur" />
        <feFlood flood-color="#00e8ff" flood-opacity="0.4" result="color" />
        <feComposite in="color" in2="blur" operator="in" result="glow" />
        <feMerge>
          <feMergeNode in="glow" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>

      <!-- Rainbow gradient across the top field-row shapes -->
      <!-- gradientUnits="userSpaceOnUse" so it spans actual pixel coords -->
      <linearGradient id="hg-rainbow" gradientUnits="userSpaceOnUse" x1="24" y1="0" x2="578" y2="0">
        <stop offset="0%"   stop-color="#ff2828" />
        <stop offset="20%"  stop-color="#ff38c0" />
        <stop offset="40%"  stop-color="#b038ff" />
        <stop offset="60%"  stop-color="#3878ff" />
        <stop offset="80%"  stop-color="#00c8ff" />
        <stop offset="100%" stop-color="#00ff88" />
      </linearGradient>

      <!--
        8 parallelogram shapes: slot_w=69, shape_w=61, skew=10px (top edge shifted right)
        Shape i: BL=(24+i*69, 115), BR=(85+i*69, 115), TR=(95+i*69, 22), TL=(34+i*69, 22)
      -->
      <clipPath id="hc-field-rows">
        <polygon points="24,115  85,115  95,22  34,22"  />
        <polygon points="93,115  154,115 164,22 103,22" />
        <polygon points="162,115 223,115 233,22 172,22" />
        <polygon points="231,115 292,115 302,22 241,22" />
        <polygon points="300,115 361,115 371,22 310,22" />
        <polygon points="369,115 430,115 440,22 379,22" />
        <polygon points="438,115 499,115 509,22 448,22" />
        <polygon points="507,115 568,115 578,22 517,22" />
      </clipPath>

      <!-- Stripe patterns for hero EZZone text (13px period) -->
      <pattern id="hp-ez" x="0" y="148" width="600" height="13" patternUnits="userSpaceOnUse">
        <rect width="600" height="9"   fill="#1adaff" />
        <rect y="9" width="600" height="4" fill="#0a0d12" />
      </pattern>
      <pattern id="hp-zone" x="0" y="148" width="600" height="13" patternUnits="userSpaceOnUse">
        <rect width="600" height="9"   fill="#1aff8c" />
        <rect y="9" width="600" height="4" fill="#0a0d12" />
      </pattern>

      <!-- Clip for bottom field-lines section -->
      <clipPath id="hc-field-lines">
        <rect x="18" y="258" width="564" height="124" />
      </clipPath>

      <!-- Radial green glow rising from bottom of field lines -->
      <radialGradient id="hg-field-glow" cx="50%" cy="100%" r="65%">
        <stop offset="0%"   stop-color="#00ff88" stop-opacity="0.18" />
        <stop offset="100%" stop-color="#00ff88" stop-opacity="0"    />
      </radialGradient>
    </defs>

    <!-- ── Badge background ── -->
    <rect x="8" y="8" width="584" height="384" rx="20" fill="#111418" />

    <!-- ── Top: rainbow parallelogram field rows ── -->
    <rect x="0" y="0" width="600" height="130"
          fill="url(#hg-rainbow)"
          clip-path="url(#hc-field-rows)" />

    <!-- Separator line below field rows -->
    <line x1="18" y1="123" x2="582" y2="123" stroke="#1c2028" stroke-width="3" />

    <!-- ── Middle: EZZone wordmark ── -->
    <text
      x="300" y="235"
      text-anchor="middle"
      font-family="Orbitron, 'Exo 2', sans-serif"
      font-weight="900"
      font-size="90"
      letter-spacing="-2"
      filter="url(#hf-text-glow)"
    >
      <tspan fill="url(#hp-ez)">EZ</tspan><tspan fill="url(#hp-zone)">Zone</tspan>
    </text>

    <!-- ── Bottom: perspective field lines ── -->
    <!-- Dark background for this section -->
    <rect x="18" y="258" width="564" height="124" fill="#0a0e12" />

    <!-- Lines from vanishing point (300, 430) to top of section at y=258 -->
    <g clip-path="url(#hc-field-lines)" stroke="white" stroke-width="1.5" fill="none" opacity="0.65">
      <line x1="300" y1="430" x2="40"  y2="258" />
      <line x1="300" y1="430" x2="115" y2="258" />
      <line x1="300" y1="430" x2="190" y2="258" />
      <line x1="300" y1="430" x2="300" y2="258" />
      <line x1="300" y1="430" x2="410" y2="258" />
      <line x1="300" y1="430" x2="485" y2="258" />
      <line x1="300" y1="430" x2="560" y2="258" />
    </g>

    <!-- Green upward glow on field lines -->
    <rect x="18" y="258" width="564" height="124" fill="url(#hg-field-glow)" />

    <!-- ── Badge border with green glow ── -->
    <!-- Soft outer glow layer -->
    <rect x="8" y="8" width="584" height="384" rx="20"
          fill="none" stroke="#00ff88" stroke-width="10" stroke-opacity="0.15" />
    <!-- Sharp bright border -->
    <rect x="8" y="8" width="584" height="384" rx="20"
          fill="none" stroke="#00ff88" stroke-width="2"
          filter="url(#hf-glow)" />
  </svg>
</template>

<style scoped>
.ezzone-hero {
  display: block;
  width: min(26rem, 80vw);
  height: auto;
}
</style>
