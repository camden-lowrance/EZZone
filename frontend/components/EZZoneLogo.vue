<template>
  <!-- Header wordmark: "EZ" cyan stripes, "Zone" green stripes -->
  <svg
    viewBox="0 0 360 72"
    xmlns="http://www.w3.org/2000/svg"
    aria-label="EZZone"
    class="ezzone-wordmark"
  >
    <defs>
      <!-- Horizontal stripe fill for "EZ" (cyan) -->
      <pattern id="wp-ez" x="0" y="15" width="360" height="11" patternUnits="userSpaceOnUse">
        <rect width="360" height="7.5" fill="#1adaff" />
        <rect y="7.5" width="360" height="3.5" fill="#0a0d12" />
      </pattern>
      <!-- Horizontal stripe fill for "Zone" (green) -->
      <pattern id="wp-zone" x="0" y="15" width="360" height="11" patternUnits="userSpaceOnUse">
        <rect width="360" height="7.5" fill="#1aff8c" />
        <rect y="7.5" width="360" height="3.5" fill="#0a0d12" />
      </pattern>
    </defs>
    <text
      x="4"
      y="60"
      font-family="Orbitron, 'Exo 2', sans-serif"
      font-weight="900"
      font-size="64"
      letter-spacing="-1"
    >
      <tspan fill="url(#wp-ez)">EZ</tspan><tspan fill="url(#wp-zone)">Zone</tspan>
    </text>
  </svg>
</template>

<style scoped>
.ezzone-wordmark {
  display: block;
  height: 48px;
  width: auto;
}
</style>
