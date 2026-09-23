<script setup>
defineProps({ name: { type: String, default: 'health' } })
const paths = {
  health: 'M3 12h5l3-8 4 16 3-8h3',
  home: 'M3 10 12 3l9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z',
  profile: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 21v-2a8 8 0 0 1 16 0v2',
  diet: 'M5 3v7m4-7v7M3 3v5a4 4 0 0 0 8 0V3M7 12v9M20 3v18m0-18c-5 2-6 9 0 10',
  exercise: 'M5 8v8M2 10v4m3-2h14m0-4v8m3-6v4',
  sleep: 'M20.9 13A9 9 0 1 1 11 3.1 7 7 0 0 0 20.9 13Z',
  cycle: 'M12 3C9 7 5 11 5 15a7 7 0 0 0 14 0c0-4-4-8-7-12Zm-3 12a3 3 0 0 0 3 3',
  arrow: 'M5 12h14m-5-5 5 5-5 5',
  check: 'm5 12 4 4L19 6',
}
</script>

<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path :d="paths[name] || paths.health" />
  </svg>
</template>
