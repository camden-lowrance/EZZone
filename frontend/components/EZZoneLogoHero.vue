<template>
  <svg
    viewBox="0 0 1000 560"
    xmlns="http://www.w3.org/2000/svg"
    aria-label="EZZone"
    class="ezzone-hero"
  >
    <defs>
      <linearGradient id="g-map-gradient" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#e62e36" />
        <stop offset="50%" stop-color="#802e8a" />
        <stop offset="100%" stop-color="#1a66b3" />
      </linearGradient>

      <linearGradient id="g-field" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#052c1a" />
        <stop offset="100%" stop-color="#008f5d" />
      </linearGradient>

      <linearGradient id="g-shadow-down" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#15191e" stop-opacity="0" />
        <stop offset="100%" stop-color="#15191e" stop-opacity="1" />
      </linearGradient>
      <linearGradient id="g-shadow-up" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#15191e" stop-opacity="1" />
        <stop offset="100%" stop-color="#15191e" stop-opacity="0" />
      </linearGradient>

      <filter id="f-heavy-glow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="6" result="blur" />
        <feFlood flood-color="#33ff99" flood-opacity="0.6" result="color" />
        <feComposite in="color" in2="blur" operator="in" result="glow" />
        <feDropShadow
          dx="0"
          dy="4"
          stdDeviation="8"
          flood-color="#000"
          flood-opacity="0.8"
        />
        <feMerge>
          <feMergeNode in="glow" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>

      <pattern
        id="p-stripes-ez"
        x="0"
        y="0"
        width="1000"
        height="12"
        patternUnits="userSpaceOnUse"
      >
        <rect width="1000" height="8" fill="#1adaff" />
        <rect y="8" width="1000" height="4" fill="#15191e" />
      </pattern>
      <pattern
        id="p-stripes-zone"
        x="0"
        y="0"
        width="1000"
        height="12"
        patternUnits="userSpaceOnUse"
      >
        <rect width="1000" height="8" fill="#33ff99" />
        <rect y="8" width="1000" height="4" fill="#15191e" />
      </pattern>

      <clipPath id="c-top">
        <rect x="65" y="65" width="870" height="135" rx="20" />
      </clipPath>

      <clipPath id="c-bottom">
        <rect x="65" y="385" width="870" height="100" rx="20" />
      </clipPath>

      <radialGradient id="g-valley-glow" cx="50%" cy="100%" r="80%">
        <stop offset="0%" stop-color="#33ff99" stop-opacity="0.3" />
        <stop offset="100%" stop-color="#33ff99" stop-opacity="0" />
      </radialGradient>
    </defs>

    <rect x="40" y="40" width="920" height="480" rx="40" fill="#15191e" />

    <g clip-path="url(#c-top)">
      <rect
        x="65"
        y="65"
        width="870"
        height="135"
        fill="url(#g-map-gradient)"
      />

      <path
        d="
        M 65 110 L 140 130 L 220 90 L 300 140 L 400 80 L 500 130 L 600 90 L 720 140 L 830 80 L 935 120
        M 140 130 L 160 200
        M 220 90 L 180 65
        M 300 140 L 330 200
        M 400 80 L 420 65
        M 500 130 L 520 200
        M 600 90 L 640 65
        M 720 140 L 700 200
        M 830 80 L 800 65
        M 220 90 L 320 65
        M 400 80 L 360 120
        M 600 90 L 550 140
        M 830 80 L 880 150
        "
        fill="none"
        stroke="white"
        stroke-width="3"
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-opacity="0.9"
      />

      <rect x="65" y="140" width="870" height="60" fill="url(#g-shadow-down)" />
    </g>

    <g transform="translate(500, 295)">
      <text
        text-anchor="middle"
        font-family="'Orbitron', sans-serif"
        font-weight="900"
        font-size="160"
        letter-spacing="-2"
        dominant-baseline="middle"
      >
        <tspan fill="url(#p-stripes-ez)">EZ</tspan>
        <tspan fill="url(#p-stripes-zone)">Zone</tspan>
      </text>

      <g fill="#15191e" opacity="0.9">
        <rect x="-350" y="-70" width="120" height="5" />
        <rect x="-180" y="-40" width="80" height="4" />
        <rect x="-10" y="20" width="150" height="5" />
        <rect x="220" y="-60" width="110" height="4" />
        <rect x="-420" y="55" width="840" height="3" />
      </g>
    </g>

    <g clip-path="url(#c-bottom)">
      <rect x="65" y="385" width="870" height="100" fill="url(#g-field)" />

      <g fill="none" stroke="white" stroke-width="2.5" stroke-opacity="0.85">
        <line x1="500" y1="385" x2="500" y2="485" stroke-width="3.5" />
        <line x1="300" y1="385" x2="65" y2="485" />
        <line x1="400" y1="385" x2="250" y2="485" />
        <line x1="600" y1="385" x2="750" y2="485" />
        <line x1="700" y1="385" x2="935" y2="485" />

        <path
          d="M65,415 Q500,450 935,415"
          stroke-width="2"
          stroke-opacity="0.7"
        />
        <path
          d="M65,450 Q500,490 935,450"
          stroke-width="2"
          stroke-opacity="0.7"
        />
      </g>

      <rect
        x="65"
        y="385"
        width="870"
        height="100"
        fill="url(#g-valley-glow)"
      />
      <rect x="65" y="385" width="870" height="40" fill="url(#g-shadow-up)" />
    </g>

    <rect
      x="40"
      y="40"
      width="920"
      height="480"
      rx="40"
      fill="none"
      stroke="#33ff99"
      stroke-width="6"
      filter="url(#f-heavy-glow)"
    />
  </svg>
</template>

<style scoped>
/* Ensure you have: @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&display=swap'); in your global CSS */
.ezzone-hero {
  display: block;
  width: min(48rem, 95vw);
  height: auto;
}
</style>
