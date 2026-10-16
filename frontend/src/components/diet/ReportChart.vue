<script setup>
import InteractiveDietChart from './InteractiveDietChart.vue'
defineProps({chart:{type:Object,required:true}})
</script>
<template><InteractiveDietChart :chart="chart"/></template>
