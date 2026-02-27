<template>
  <!-- GeoJSON: document with coordinate brackets -->
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
          stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
    <polyline points="14 2 14 8 20 8"
              stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
    <!-- { } brackets suggesting JSON/geo data -->
    <text x="7" y="18" font-family="monospace" font-size="6.5" font-weight="700"
          fill="currentColor" letter-spacing="0.5">{ }</text>
    <!-- small dot suggesting a coordinate point -->
    <circle cx="12" cy="13" r="1.5" fill="currentColor"/>
  </svg>
</template>

<script setup>
defineProps({ size: { type: Number, default: 20 } })
</script>
